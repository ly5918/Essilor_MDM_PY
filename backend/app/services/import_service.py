"""导入域业务层（对应 Java CmdImportServiceImpl）。

职责：业务规则编排——文件级预检、行级 DQ 与四类分流、任务状态推导、
审批联动（批量导入确认 / 导入行跨BU合并）。数据读写一律调 import_repo；
通用插入走 core.query.dynamic_insert（自动补 id/del_flag）。

流程（对应总设计泳道「批量导入确认 IMPORT_BATCH」）：
  上传 → 解析 → 文件级预检（必填列缺失整批退回）
  → 行级 DQ + 批次内去重 + 存量匹配 → 四类分流（Exact / Suspected / New / Invalid）
  → applyOutcome 回写统计 → New>0 提交「批量导入确认」审批
  → 审批通过 publish_new_rows：逐条生成 One ID 并发布主档
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from ..core.db import table
from ..core.query import dynamic_insert
from ..repositories import import_repo
from ..repositories.import_repo import now

# ---- 常量（与 Java CmdImportServiceImpl 逐字对齐）----
STATUS_WAIT_REVIEW = "WAIT_REVIEW"
STATUS_PARTIAL = "PARTIAL_SUCCESS"
STATUS_FAILED = "FAILED"
STATUS_COMPLETED = "COMPLETED"
ROW_SUCCESS, ROW_FAILED, ROW_GOVERNANCE, ROW_SKIPPED = "SUCCESS", "FAILED", "GOVERNANCE", "SKIPPED"
HANDLING_FIX, HANDLING_GOVERNANCE, HANDLING_IGNORE = "FIX", "GOVERNANCE", "IGNORE"
RESULT_EXACT, RESULT_SUSPECTED, RESULT_NEW, RESULT_INVALID = "EXACT", "SUSPECTED", "NEW", "INVALID"
FIELD_LEGAL_NAME, FIELD_CREDIT_CODE = "legal_name", "credit_code"
CORE_FIELDS = {FIELD_LEGAL_NAME, FIELD_CREDIT_CODE}
CREDIT_CODE_PATTERN = re.compile(r"^[0-9A-Z]{18}$")

# 「待处置」状态聚合（前端 listImportJobs(pendingOnly=true) 与菜单角标同口径）
PENDING_JOB_STATUSES = [STATUS_WAIT_REVIEW, "RUNNING", STATUS_PARTIAL]


class ImportBizError(Exception):
    """业务错误：Router 层翻译为 R.fail 可读提示，而非 500。"""


# ============================ 基础工具 ============================


def gen_job_code() -> str:
    return "IMP-" + uuid.uuid4().hex[:8].upper()


def norm(v: Optional[str]) -> str:
    """批次内去重键：去空白 + 大写。"""
    return re.sub(r"\s+", "", (v or "")).upper()


def resolve_job_status(total: int, exact: int, suspected: int, created: int,
                       invalid: int) -> str:
    """全部 Invalid→Failed；部分 Invalid→部分成功；有疑似/新建→待复核；否则完成。"""
    if invalid > 0 and invalid == total:
        return STATUS_FAILED
    if invalid > 0:
        return STATUS_PARTIAL
    if suspected > 0 or created > 0:
        return STATUS_WAIT_REVIEW
    return STATUS_COMPLETED


def dq_score_of(errors: List[str], result_type: str) -> float:
    """行级质量分：100 起步每个问题 -20，Invalid 保底 40（与单条申请 DQ 口径区分）。"""
    score = max(0, 100 - len(errors) * 20)
    if result_type == RESULT_INVALID:
        score = max(score, 40)
    return float(score)


def _nz(v) -> int:
    return int(v) if v is not None else 0


# ============================ 任务查询 / 统计 ============================


async def get_job_or_fail(conn, job_code: str) -> dict:
    job = await import_repo.get_job_by_code(conn, job_code)
    if job is None:
        raise ImportBizError(f"导入任务不存在：{job_code}")
    return job


async def list_jobs(conn, page: int, size: int,
                    job_status_list: Optional[List[str]] = None,
                    pending_only: bool = False) -> dict:
    """任务分页；job_status_list 为状态聚合过滤，pending_only 按「待处置」口径（与菜单角标一致）。"""
    if pending_only:
        job_status_list = PENDING_JOB_STATUSES
    return await import_repo.list_jobs(conn, page, size, job_status_list=job_status_list)


async def get_job_stats(conn) -> dict:
    """导入中心全局统计（服务端全量聚合，修复「指标卡全 0」）。"""
    return await import_repo.aggregate_job_stats(conn)


def build_result_vo(job: dict) -> dict:
    """任务分流结果 VO（含五分流 routes 卡，与 Java buildRoutes 对齐）。"""
    exact, suspected, created = _nz(job.get("exact_count")), _nz(job.get("suspected_count")), _nz(job.get("new_count"))
    review, invalid = _nz(job.get("review_count")), _nz(job.get("invalid_count"))

    def route(result: str, handling: str, owner: str, count: int) -> dict:
        return {"result": result, "handling": handling, "owner": owner,
                "count": count, "detail": f"查看{count}条"}

    return {
        "jobCode": job["job_code"],
        "exact": exact, "suspected": suspected, "created": created,
        "review": review, "invalid": invalid,
        "routes": [
            route("Exact", "关联已有One ID", "System", exact),
            route("Suspected", "进入人工治理", "BU/GC Steward", suspected),
            route("Review", "规则或业务复核", "BU Steward", review),
            route("New", "审批后生成One ID", "Steward", created),
            route("Invalid", "返回修复", "Business User", invalid),
        ],
    }


# ============================ 任务登记 ============================


async def create_job_registration(conn, *, file_name: str, body: dict) -> str:
    """新建导入任务（Java createJob：仅登记任务，不解析文件）。"""
    job_code = gen_job_code()
    await import_repo.insert_job(conn, {
        "job_code": job_code, "job_name": file_name, "file_name": file_name,
        "scene": body.get("scene") or "DOOR",
        "bu_scope": body.get("buScope") or body.get("bu_scope"),
        "total_count": body.get("totalCount") or body.get("total_count") or 0,
        "submit_by": body.get("submitBy") or body.get("submit_by") or "Business User",
        "submit_time": now(), "job_status": STATUS_WAIT_REVIEW,
        "remark": body.get("remark"), "create_time": now(),
    })
    return job_code


# ============================ 模板 / 映射 ============================


async def list_templates(conn) -> List[dict]:
    """模板清单（status 0→Published / 其余→Draft，含字段数）。"""
    out = []
    for tpl in await import_repo.list_templates(conn):
        field_count = await import_repo.count_mappings(conn, tpl["template_code"])
        out.append({
            "id": tpl["id"], "templateCode": tpl["template_code"],
            "templateName": tpl["template_name"], "scene": tpl.get("scene"),
            "buScope": tpl.get("bu_scope"), "customerType": tpl.get("customer_type"),
            "productLine": tpl.get("product_line"), "sourceSystem": tpl.get("source_system"),
            "versionNo": tpl.get("version_no"),
            "status": "Published" if tpl.get("status") == "0" else "Draft",
            "fieldCount": field_count, "remark": tpl.get("remark"),
        })
    return out


async def list_mappings(conn, template_code: Optional[str]) -> List[dict]:
    """字段映射（错误策略与必填同口径：必填→Reject Row / 选填→Warning Row）。"""
    out = []
    for m in await import_repo.list_mappings(conn, template_code):
        required = (m.get("is_required") or "N") == "Y"
        out.append({
            "id": m["id"], "templateId": m.get("template_id"),
            "templateCode": m["template_code"], "columnIndex": m.get("column_index"),
            "columnName": m.get("column_name"), "fieldCode": m["field_code"],
            "fieldName": m.get("field_name"), "dataType": m.get("data_type"),
            "isRequired": m.get("is_required"), "defaultValue": m.get("default_value"),
            "errorStrategy": "Reject Row" if required else "Warning Row",
        })
    return out


async def save_mapping(conn, body: dict) -> str:
    """新增/编辑上传字段（Java saveMapping：无 id 走新增，含唯一性校验与主键保护）。"""
    template_code = (body.get("templateCode") or body.get("template_code") or "").strip()
    column_name = (body.get("columnName") or body.get("column_name") or "").strip()
    field_code = (body.get("fieldCode") or body.get("field_code") or "").strip()
    mapping_id = body.get("id") or body.get("mappingId")
    if not template_code or not column_name or not field_code:
        raise ImportBizError("模板编码、源列与目标字段编码不能为空")

    template = await import_repo.get_template_by_code(conn, template_code)
    if template is None:
        raise ImportBizError(f"导入模板不存在：{template_code}")
    existing = await import_repo.list_mappings(conn, template["template_code"])

    if mapping_id:  # ---- 编辑 ----
        for m in existing:
            if m["id"] != int(mapping_id) and field_code.lower() == m["field_code"].lower():
                raise ImportBizError(f"目标字段编码 [{field_code}] 在模板中已存在")
        required = "Y" if (body.get("isRequired") or body.get("is_required")) == "Y" else "N"
        await import_repo.update_mapping(conn, int(mapping_id), {
            "column_name": column_name, "field_code": field_code,
            "field_name": body.get("fieldName") or body.get("field_name"),
            "data_type": body.get("dataType") or body.get("data_type") or "Text",
            "is_required": required,
        })
        return f"已更新映射「{column_name}」"

    # ---- 新增（Java insertMapping：字段/列唯一性校验 + 列序号顺延）----
    for m in existing:
        if field_code.lower() == m["field_code"].lower():
            raise ImportBizError(f"目标字段编码 [{field_code}] 在模板中已存在")
        if column_name.lower() == (m.get("column_name") or m["field_code"]).lower():
            raise ImportBizError(f"源列 [{column_name}] 在模板中已存在")
    next_idx = await import_repo.max_column_index(conn, template["template_code"]) + 1
    required = "Y" if (body.get("isRequired") or body.get("is_required")) == "Y" else "N"
    await import_repo.insert_mapping(conn, {
        "template_id": template["id"], "template_code": template["template_code"],
        "column_index": next_idx, "order_num": next_idx, "status": "0",
        "is_required": required, "column_name": column_name, "field_code": field_code,
        "field_name": body.get("fieldName") or body.get("field_name"),
        "data_type": body.get("dataType") or body.get("data_type") or "Text",
        "default_value": body.get("defaultValue") or body.get("default_value"),
        "create_time": now(),
    })
    return f"已新增上传字段「{column_name}」，模板下载 / 表头预检 / 行级 DQ 将自动包含该列"


async def delete_mapping(conn, mapping_id: int) -> str:
    """删除映射（主键保护：legal_name / credit_code 不可删）。"""
    rows = await import_repo.list_mappings(conn)
    target = next((m for m in rows if m["id"] == mapping_id), None)
    if target is None:
        raise ImportBizError(f"映射不存在：{mapping_id}")
    if target["field_code"] in CORE_FIELDS:
        raise ImportBizError("主键字段（客户名称 / 统一社会信用代码）不可删除")
    await import_repo.soft_delete_mapping(conn, mapping_id)
    return f"已移除上传字段「{target.get('column_name') or target['field_code']}」"


async def build_template_workbook(conn, template_code: str):
    """按字段映射动态生成「仅表头」的模板工作簿（Java downloadTemplate）。

    返回 (template, openpyxl.Workbook)；Router 层负责输出为 xlsx 流。
    """
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill

    template = await import_repo.get_template_by_code(conn, template_code)
    if template is None:
        raise ImportBizError(f"导入模板不存在：{template_code}")
    mappings = await import_repo.list_mappings(conn, template["template_code"])
    if not mappings:
        raise ImportBizError(f"模板[{template['template_name']}]未配置字段映射，无法生成模板文件")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = template.get("sheet_name") or "Template"
    head_font = Font(bold=True, size=11)
    head_fill = PatternFill(fill_type="solid", fgColor="D9D9D9")
    head_align = Alignment(horizontal="center", vertical="center")
    for col, m in enumerate(mappings, start=1):
        cell = ws.cell(row=1, column=col, value=m.get("column_name") or m["field_code"])
        cell.font, cell.fill, cell.alignment = head_font, head_fill, head_align
        ws.column_dimensions[cell.column_letter].width = max(14, len(cell.value or "") * 2)
    return template, wb


# ============================ 上传管线 ============================


def _cell_str(v) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def parse_upload_rows(file_bytes: bytes) -> List[Dict[str, str]]:
    """解析上传 xlsx：首行表头 → 按列名取值的字典列表（空行跳过）。"""
    import io as _io

    import openpyxl
    wb = openpyxl.load_workbook(_io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active
    rows: List[Dict[str, str]] = []
    header: List[str] = []
    for r_idx, row in enumerate(ws.iter_rows(values_only=True)):
        if r_idx == 0:
            header = [_cell_str(v) or "" for v in row]
            continue
        if not any(_cell_str(v) for v in row):
            continue
        item = {}
        for c_idx, name in enumerate(header):
            if name:
                item[name] = _cell_str(row[c_idx]) if c_idx < len(row) else None
        rows.append(item)
    wb.close()
    return rows


def pre_check_header(rows: List[Dict[str, str]], mappings: List[dict]) -> str:
    """文件级预检：表头必须包含模板全部「必填」列；返回缺失列名串（空=通过）。

    选填列缺失不阻断整批（与错误策略「必填→Reject / 选填→Warning」同口径）。
    """
    missing = []
    for m in mappings:
        if (m.get("is_required") or "N") != "Y":
            continue
        col = m.get("column_name") or m["field_code"]
        if rows and col not in rows[0]:
            missing.append(col)
    return "、".join(missing)


async def create_job_from_upload(conn, *, template_code: str, file_name: str,
                                 file_bytes: bytes, error_strategy: Optional[str],
                                 duplicate_strategy: Optional[str], scene: Optional[str],
                                 bu_scope: Optional[str], source_system: Optional[str],
                                 operator: str = "Business User") -> Tuple[str, dict]:
    """上传主流程（Java uploadJob）：预检 → 建任务 → 行级分流 → 回写统计 → 提交审批。

    返回 (job_code, 分流结果 VO)。业务规则失败抛 ImportBizError。
    """
    template = await import_repo.get_template_by_code(conn, template_code)
    if template is None:
        raise ImportBizError(f"导入模板不存在：{template_code}")
    mappings = await import_repo.list_mappings(conn, template["template_code"])
    if not mappings:
        raise ImportBizError(f"模板[{template['template_name']}]未配置字段映射，无法解析上传文件")

    rows = parse_upload_rows(file_bytes)

    # ---- 文件级预检：缺列或无数据行 → 整批退回，不建任务 ----
    missing = pre_check_header(rows, mappings)
    if missing:
        raise ImportBizError(f"文件预检未通过：表头缺少列 {missing}，已整批退回（请使用最新模板填写）")
    if not rows:
        raise ImportBizError("文件预检未通过：未解析到数据行，已整批退回")

    # ---- 建任务 ----
    job_code = gen_job_code()
    job = await import_repo.insert_job(conn, {
        "job_code": job_code, "job_name": file_name, "file_name": file_name,
        "scene": scene or template.get("scene") or "DOOR",
        "template_id": template["id"],
        "template_code": template["template_code"],
        "template_version": template.get("version_no"),
        "bu_scope": bu_scope or template.get("bu_scope"),
        "total_count": len(rows),
        "error_strategy": error_strategy or "REJECT_ROW",
        "duplicate_strategy": duplicate_strategy or "GOVERNANCE",
        "precheck_status": "PASS", "precheck_msg": "表头校验通过",
        "job_status": STATUS_WAIT_REVIEW,
        "submit_by": operator, "submit_time": now(), "create_time": now(),
    })

    # ---- 行级 DQ + 批次内去重 + 存量匹配 → 四类分流 ----
    outcome = await classify_rows(conn, job, mappings, rows)
    exact, suspected, created, invalid = outcome
    await import_repo.update_job(conn, job["id"], {
        "exact_count": exact, "suspected_count": suspected, "new_count": created,
        "review_count": 0, "invalid_count": invalid, "success_count": exact + created,
        "job_status": resolve_job_status(len(rows), exact, suspected, created, invalid),
        "progress": 100, "end_time": now(),
    })

    # ---- New 行 > 0 → 提交「批量导入确认」审批 ----
    if created > 0:
        await submit_import_approval(conn, job, outcome, operator)

    # ---- 审计留痕 ----
    await _record_audit(conn, "IMPORT", f"批量导入上传：{file_name}", job_code,
                        None, operator, "BU_STEWARD",
                        risk_level="High" if invalid > 0 else "Low")

    job = await import_repo.get_job_by_code(conn, job_code)
    return job_code, build_result_vo(job)


def template_start_row(job: dict) -> int:
    v = job.get("data_start_row") or 2
    return v if v >= 2 else 2


async def classify_rows(conn, job: dict, mappings: List[dict],
                        rows: List[Dict[str, str]]) -> Tuple[int, int, int, int]:
    """行级处理：DQ 校验 + 批次内去重 + 存量匹配 → 四类分流（Java classifyRows）。

    优先级：Invalid > 批次内重复(Suspected) > 存量 Exact > 名称疑似(Suspected) > New。
    """
    name_col = next((m.get("column_name") or m["field_code"] for m in mappings
                     if m["field_code"] == FIELD_LEGAL_NAME), None)
    code_col = next((m.get("column_name") or m["field_code"] for m in mappings
                     if m["field_code"] == FIELD_CREDIT_CODE), None)
    data_start_row = template_start_row(job)
    batch_codes: Dict[str, int] = {}
    batch_names: Dict[str, int] = {}
    exact = suspected = created = invalid = 0

    for idx, data in enumerate(rows):
        row_no = data_start_row + idx
        legal_name = _cell_str(data.get(name_col)) if name_col else None
        credit_code = _cell_str(data.get(code_col)) if code_col else None

        # 1) 行级 DQ：必填列缺失 + 信用代码格式
        errors: List[str] = []
        for m in mappings:
            if (m.get("is_required") or "N") == "Y":
                col = m.get("column_name") or m["field_code"]
                if not _cell_str(data.get(col)):
                    errors.append(f"必填列缺失：{col}")
        if credit_code and not CREDIT_CODE_PATTERN.match(credit_code.upper()):
            errors.append("信用代码格式错误（应为 18 位大写字母数字）")

        # 2) 四类分流
        result_type = row_status = handling = match_state = match_one_id = None
        match_score = None
        if errors:
            result_type, row_status, handling = RESULT_INVALID, ROW_FAILED, HANDLING_FIX
        elif credit_code and norm(credit_code) in batch_codes:
            result_type, row_status, handling = RESULT_SUSPECTED, ROW_GOVERNANCE, HANDLING_GOVERNANCE
            match_state = RESULT_SUSPECTED
            errors.append(f"批次内与第 {batch_codes[norm(credit_code)]} 行信用代码重复")
        elif legal_name and norm(legal_name) in batch_names:
            result_type, row_status, handling = RESULT_SUSPECTED, ROW_GOVERNANCE, HANDLING_GOVERNANCE
            match_state = RESULT_SUSPECTED
            errors.append(f"批次内与第 {batch_names[norm(legal_name)]} 行客户名称重复")
        else:
            exact_hit = (await import_repo.find_active_by_credit_code(conn, credit_code)
                         if credit_code else None)
            if exact_hit:
                result_type, row_status = RESULT_EXACT, ROW_SUCCESS
                match_state, match_one_id, match_score = RESULT_EXACT, exact_hit["one_id"], 100.0
            else:
                name_hit = (await import_repo.find_by_legal_name(conn, legal_name)
                            if legal_name else None)
                if name_hit:
                    result_type, row_status = RESULT_SUSPECTED, ROW_GOVERNANCE
                    handling, match_state = HANDLING_GOVERNANCE, RESULT_SUSPECTED
                    match_one_id, match_score = name_hit["one_id"], 75.0
                    errors.append(f"与存量主档名称相同（候选 {name_hit['one_id']}），需治理确认")
                else:
                    result_type, row_status = RESULT_NEW, ROW_SUCCESS
                    match_state = RESULT_NEW

        if credit_code:
            batch_codes.setdefault(norm(credit_code), row_no)
        if legal_name:
            batch_names.setdefault(norm(legal_name), row_no)

        await import_repo.insert_row(conn, {
            "job_id": job["id"], "job_code": job["job_code"], "row_no": row_no,
            "row_status": row_status, "result_type": result_type, "one_id": match_one_id,
            "bu_scope": job.get("bu_scope"), "legal_name": legal_name,
            "credit_code": credit_code, "dq_score": dq_score_of(errors, result_type),
            "match_state": match_state, "match_score": match_score,
            "raw_json": json.dumps(_named_map(data, mappings, False), ensure_ascii=False),
            "parsed_json": json.dumps(_named_map(data, mappings, True), ensure_ascii=False),
            "error_count": len(errors),
            "error_summary": "；".join(errors) if errors else None,
            "handling": handling, "create_time": now(),
        })

        if result_type == RESULT_EXACT:
            exact += 1
        elif result_type == RESULT_SUSPECTED:
            suspected += 1
        elif result_type == RESULT_NEW:
            created += 1
        else:
            invalid += 1
    return exact, suspected, created, invalid


def _named_map(row_data: Dict[str, str], mappings: List[dict], by_field: bool) -> dict:
    """行数据按模板列（或字段编码）整理为有序 Map（Java toNamedMap）。"""
    out: Dict[str, object] = {}
    for m in mappings:
        col = m.get("column_name") or m["field_code"]
        out[m["field_code"] if by_field else col] = row_data.get(col)
    return out


# ============================ 行级治理动作 ============================


async def row_action(conn, row_id: int, action: str, one_id: Optional[str],
                     operator: str = "BU Steward") -> str:
    """行治理（Java rowAction）：LINK 关联已有 / EXCLUDE 排除 / RETURN 退回修复。

    LINK 的目标主档在另一个 BU（跨BU命中）时，不直接关联——
    升级为 MERGE 合并审批（BU 初审 → GC 决策），批准后回写行状态。
    """
    row = await import_repo.get_row(conn, row_id)
    if row is None:
        raise ImportBizError(f"导入行不存在：{row_id}")
    job = await import_repo.get_job_by_code(conn, row["job_code"])
    if job is None:
        raise ImportBizError(f"导入任务不存在：{row.get('job_code')}")
    t = (action or "").strip().upper()

    if t == "LINK":
        target = one_id or row.get("one_id")
        if not target:
            raise ImportBizError("请填写要关联的 One ID")
        target_customer = await import_repo.find_active_by_one_id(conn, target)
        if target_customer and job.get("bu_scope") and \
                job["bu_scope"] != target_customer.get("bu_scope"):
            # 跨BU命中 → 行保持 Suspected，升级 MERGE 审批
            await import_repo.update_row(conn, row["id"], {
                "handling": f"跨BU合并审批中（{target}）", "update_time": now()})
            await recalc_job_counts(conn, job)
            return await launch_row_merge(conn, job, row, target_customer, operator)
        await import_repo.update_row(conn, row["id"], {
            "result_type": RESULT_EXACT, "row_status": ROW_SUCCESS, "one_id": target,
            "match_state": RESULT_EXACT, "match_score": 100.0, "error_count": 0,
            "handling": None, "error_summary": None, "update_time": now()})
        message = f"已关联 One ID {target}"
    elif t == "EXCLUDE":
        await import_repo.update_row(conn, row["id"], {
            "result_type": RESULT_INVALID, "row_status": ROW_SKIPPED,
            "handling": HANDLING_IGNORE, "error_count": 1,
            "error_summary": "人工排除（不纳入主档）", "update_time": now()})
        message = "该行已排除，不再纳入主档"
    elif t == "RETURN":
        await import_repo.update_row(conn, row["id"], {
            "result_type": RESULT_INVALID, "row_status": ROW_FAILED,
            "handling": HANDLING_FIX, "error_count": 1,
            "error_summary": "退回修复（数据疑似重复，需线下核实后再导入）",
            "update_time": now()})
        message = "该行已退回修复"
    else:
        raise ImportBizError(f"不支持的治理动作：{action}（仅支持 LINK / EXCLUDE / RETURN）")

    await recalc_job_counts(conn, job)
    await _record_audit(conn, "GOVERNANCE", f"导入行治理[{t}]：{row.get('legal_name')}（{message}）",
                        job["job_code"], row.get("one_id"), operator, "BU_STEWARD")
    return message


async def recalc_job_counts(conn, job: dict) -> None:
    """按行明细重算任务统计与状态（治理动作后调用，Java recalcJobCounts）。"""
    rows = await import_repo.list_rows_by_job(conn, job["id"])
    exact = suspected = created = review = invalid = 0
    for r in rows:
        rt = r.get("result_type") or ""
        if rt == RESULT_EXACT:
            exact += 1
        elif rt == RESULT_SUSPECTED:
            suspected += 1
        elif rt == RESULT_NEW:
            created += 1
        elif rt == "REVIEW":
            review += 1
        else:
            invalid += 1
    total = len(rows)
    await import_repo.update_job(conn, job["id"], {
        "exact_count": exact, "suspected_count": suspected, "new_count": created,
        "review_count": review, "invalid_count": invalid, "success_count": exact + created,
        "job_status": resolve_job_status(total, exact, suspected, created + review, invalid)})


# ============================ 审批联动 ============================


async def submit_import_approval(conn, job: dict, outcome: Tuple[int, int, int, int],
                                 operator: str) -> str:
    """存在 New 行时创建「批量导入确认」审批待办并启动流程实例。"""
    from ..services.sequence import gen_code
    from ..services.trace import log_action
    from ..workflow.engine import start_instance

    exact, suspected, created, invalid = outcome
    rows = await import_repo.list_rows_by_job(conn, job["id"])
    scores = [float(r["dq_score"]) for r in rows if r.get("dq_score") is not None]
    avg_dq = round(sum(scores) / len(scores), 1) if scores else 0.0
    task_no = await gen_code(conn, "AP-", 4, "APPROVAL")
    evidence = {
        "批次均分": f"{avg_dq} 分（{len(rows)} 行）",
        "分流结论": f"Exact {exact} / Suspected {suspected} / New {created} / Invalid {invalid}",
        "总行数": job.get("total_count") or len(rows),
    }
    task_vals = await dynamic_insert(conn, table("cmd_approval_task"), dict(
        task_no=task_no, task_category="APPROVAL", biz_type="IMPORT", biz_id=job["job_code"],
        biz_title=f"批量导入确认：{job.get('file_name')}", scene_code="IMPORT_BATCH",
        applicant_name=operator, bu_scope=job.get("bu_scope"),
        scope="BU", current_node_code="BU_REVIEW", current_node_name="BU Scope 批量确认",
        assignee_name="BU Steward", assignee_role="BU_STEWARD", status="PENDING",
        risk_level="High" if invalid > 0 else "Medium",
        duplicate_state="SUSPECTED" if suspected > 0 else "NEW",
        cross_bu_flag="N", submit_time=now(), sla_due=now(), sla_state="NORMAL",
        dq_score=avg_dq, evidence_json=evidence, remark="批量导入 New 行待确认"))
    await log_action(conn, task_id=task_vals.get("id"), task_no=task_no, one_id=None,
                     action_type="SUBMIT", action_name="提交批量导入确认",
                     from_node_code="APPLY", to_node_code="BU_REVIEW",
                     operator_name=operator, operator_role="BU_STEWARD", opinion="")
    try:
        await start_instance(
            scene_code="IMPORT_BATCH", biz_type="IMPORT", biz_no=task_no,
            variables={"taskNo": task_no, "bizType": "IMPORT", "bizId": job["job_code"],
                       "sceneCode": "IMPORT_BATCH", "buScope": job.get("bu_scope") or "",
                       "riskLevel": "High" if invalid > 0 else "Medium",
                       "duplicateState": "SUSPECTED" if suspected > 0 else "NEW",
                       "dqScore": avg_dq})
    except Exception:
        pass  # 引擎异常不影响导入结果（Java 防御式口径），流程中心可手工重试
    return task_no


async def on_approval(conn, job_code: str, action_type: str, operator: str) -> None:
    """审批回调（Java onApproval）：approve→New 行生成 One ID；reject→FAILED；return→待复核。"""
    job = await import_repo.get_job_by_code(conn, job_code)
    if job is None:
        return
    t = (action_type or "").strip().upper()
    patch: dict = {"end_time": now()}
    if t == "APPROVE":
        published = await publish_new_rows(conn, job)
        patch["job_status"] = STATUS_COMPLETED
        patch["remark"] = (job.get("remark") or "") + \
            f"审批通过：{published} 条 New 行已生成 One ID（审批人：{operator}）"
    elif t == "REJECT":
        patch["job_status"] = STATUS_FAILED
        patch["error_message"] = f"批量导入确认被拒绝（审批人：{operator}）"
    elif t == "RETURN":
        patch["job_status"] = STATUS_WAIT_REVIEW
        patch["remark"] = (job.get("remark") or "") + f"审批退回补充（审批人：{operator}）"
    else:
        return
    await import_repo.update_job(conn, job["id"], patch)


async def publish_new_rows(conn, job: dict) -> int:
    """审批通过：为全部 New 行生成客户主档（One ID + active），回写行 One ID。"""
    from ..services import sequence as seq
    rows = [r for r in await import_repo.list_rows_by_job(conn, job["id"])
            if r.get("result_type") == RESULT_NEW]
    count = 0
    for row in rows:
        one_id = await seq.gen_one_id(conn)
        await dynamic_insert(conn, table("cmd_customer"), dict(
            one_id=one_id,
            legal_name=row.get("legal_name") or f"未命名导入客户 {row['row_no']}",
            credit_code=row.get("credit_code"), bu_scope=row.get("bu_scope"),
            country="中国", status="active", source_system="IMPORT",
            source_id=job["job_code"], dq_score=row.get("dq_score"),
            match_state=RESULT_NEW, duplicate_flag="N",
            remark=f"批量导入生成：{job['job_code']} 第 {row['row_no']} 行",
            create_time=now(), update_time=now()))
        await import_repo.update_row(conn, row["id"], {
            "one_id": one_id, "remark": f"审批通过，已生成 One ID {one_id}",
            "update_time": now()})
        count += 1
    return count


async def launch_row_merge(conn, job: dict, row: dict, target_customer: dict,
                           operator: str) -> str:
    """导入行跨BU命中 → 发起「跨BU客户合并」审批（MERGE 场景，mode=ROW_LINK）。"""
    from ..services.sequence import gen_code
    from ..services.trace import log_action

    task_no = await gen_code(conn, "AP-", 4, "APPROVAL")
    snapshot = {"mode": "ROW_LINK", "rowId": row["id"], "targetOneId": target_customer["one_id"]}
    evidence = {
        "合并模式": "批量导入行 → 跨BU存量主档（关联已有 One ID，需 GC 决策）",
        "发起原因": f"导入行与 {target_customer.get('bu_scope')} 主档疑似重复（跨BU），升级合并审批",
        "导入行": f"{row['job_code']} 第 {row['row_no']} 行 · {row.get('legal_name')}",
        "目标记录": f"{target_customer['one_id']} · {target_customer.get('legal_name')}"
                   f" · {target_customer.get('bu_scope')}",
    }
    merge_task_vals = await dynamic_insert(conn, table("cmd_approval_task"), dict(
        task_no=task_no, task_category="APPROVAL", biz_type="MERGE", biz_id=str(row["id"]),
        biz_title=f"跨BU合并：{row.get('legal_name')} → {target_customer.get('legal_name')}",
        scene_code="MERGE", applicant_name=operator, bu_scope=job.get("bu_scope"),
        scope="BU", current_node_code="BU_REVIEW", current_node_name="BU Scope 初审",
        assignee_name="BU Steward", assignee_role="BU_STEWARD", status="PENDING",
        risk_level="High", duplicate_state="SUSPECTED", cross_bu_flag="Y",
        one_id=target_customer["one_id"], submit_time=now(), sla_due=now(), sla_state="NORMAL",
        evidence_json=evidence, biz_snapshot_json=snapshot,
        remark="导入行跨BU疑似重复，BU 发起合并审批"))
    await log_action(conn, task_id=merge_task_vals.get("id"), task_no=task_no,
                     one_id=target_customer["one_id"],
                     action_type="SUBMIT", action_name="发起跨BU合并（导入行关联已有）",
                     from_node_code="APPLY", to_node_code="BU_REVIEW",
                     operator_name=operator, operator_role="BU_STEWARD", opinion="")
    await _record_audit(conn, "MERGE",
                        f"导入行跨BU疑似重复，发起合并审批：{row.get('legal_name')}"
                        f" → {target_customer.get('legal_name')}",
                        task_no, target_customer["one_id"], operator, "BU_STEWARD",
                        risk_level="High")
    return (f"跨BU命中（目标 {target_customer.get('bu_scope')} 主档 "
            f"{target_customer['one_id']}），已发起客户合并审批 {task_no}，批准后自动关联")


async def apply_row_link_merge(conn, task: dict) -> None:
    """ROW_LINK 合并审批批准后：导入行回写为 Exact 并关联目标 One ID。"""
    snapshot = task.get("biz_snapshot_json") or {}
    row_id = snapshot.get("rowId")
    target = snapshot.get("targetOneId")
    if row_id is None or not target:
        return
    row = await import_repo.get_row(conn, int(row_id))
    if row is None:
        return
    await import_repo.update_row(conn, row["id"], {
        "result_type": RESULT_EXACT, "row_status": ROW_SUCCESS, "one_id": target,
        "match_state": RESULT_EXACT, "match_score": 100.0, "error_count": 0,
        "handling": None, "error_summary": None,
        "remark": f"跨BU合并审批通过，已关联 {target}", "update_time": now()})
    job = await import_repo.get_job_by_code(conn, row["job_code"])
    if job:
        await recalc_job_counts(conn, job)


# ============================ 审计 ============================


async def _record_audit(conn, event_type: str, event_name: str, biz_id: str,
                        one_id: Optional[str], operator: str, operator_role: str,
                        result: str = "SUCCESS", risk_level: str = "Low") -> None:
    from ..services.sequence import gen_code
    event_id = await gen_code(conn, "AE-", 4, "AE")
    await import_repo.insert_audit_event(conn, {
        "event_id": event_id,
        "event_type": event_type, "event_name": event_name,
        "biz_type": "IMPORT", "biz_id": biz_id, "one_id": one_id,
        "operator_name": operator, "operator_role": operator_role,
        "event_time": now(), "result": result, "risk_level": risk_level})

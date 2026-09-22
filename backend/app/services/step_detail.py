"""流程跟踪「分步骤明细」服务：1:1 移植 Java CmdFlowTraceServiceImpl#fillStepDetails
与 CmdFlowStepDetailMapper 的查询口径。

解决「流程跟踪点开某个已完成节点，下方看不到历史记录」的问题：
Python 版 flow_trace 此前恒返回 stepDetails=[]，前端只能渲染兜底文案。

原则（与 Java 版一致）：
- 只读真实业务表，不臆造数据；POC 未落的表用 notes 说明口径；
- 明细按 nodeCode 与泳道步骤一一对应，前端只负责渲染；
- 所有场景（新建 / 变更 / 停用 / 导入 / 合并 / 规则变更 / 集成失败）的每个节点
  都有内容可看：业务节点读业务表，其余节点回退「节点动作 + 步骤日志」历史。
"""
from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy import text

from ..services import ocr_service

DASH = "—"
NODE_BU_REVIEW = "BU_REVIEW"
NODE_GC_REVIEW = "GC_REVIEW"

# 动作类型 → 所属节点（Java mapByActionType / nodeOfActionType 口径）
_ACTION_NODE: Dict[str, str] = {
    "SUBMIT": "APPLY", "CLAIM": "APPLY",
    "APPROVE": NODE_BU_REVIEW,
    "ESCALATE": NODE_GC_REVIEW,
    "RETURN": NODE_BU_REVIEW, "REJECT": NODE_BU_REVIEW,
}


# ---------------------------------------------------------------------------
# 小工具（Java 同名方法口径）
# ---------------------------------------------------------------------------

def _s(o) -> str:
    """展示值：None / 空串 → '—'。datetime 转 'YYYY-MM-DD HH:MM:SS'。"""
    if o is None:
        return DASH
    if hasattr(o, "strftime"):
        v = o.strftime("%Y-%m-%d %H:%M:%S")
        return v[:16] if len(v) > 16 else v
    v = str(o)
    return DASH if v.strip() == "" else v


def _dt(o) -> str:
    if o is None:
        return DASH
    if hasattr(o, "strftime"):
        return o.strftime("%Y-%m-%d %H:%M:%S")[:16]
    return str(o).replace("T", " ")[:16]


def _is_blank(o) -> bool:
    return o is None or str(o).strip() == ""


def _cv(c: Optional[dict], key: str):
    """主档字段取值（customer 可能为 None，例如任务无 One ID 时）——Java cv() 口径。"""
    return None if c is None else c.get(key)


def _num(o) -> int:
    try:
        return int(float(str(o).strip()))
    except (TypeError, ValueError):
        return 0


def _f(o) -> float:
    try:
        return float(str(o).strip())
    except (TypeError, ValueError):
        return 0.0


def _grade(score: float) -> str:
    if score <= 0:
        return DASH
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    return "D"


def _routing(match_state: str) -> str:
    st = (match_state or "").upper()
    if st == "EXACT":
        return "命中精确匹配：强制关联已有 One ID，不允许新创主数据"
    if st in ("SUSPECT", "SUSPECTED"):
        return "疑似重复：转入 BU Scope 人工治理，确认 Same-BU 或升级 Cross-BU"
    if st == "REVIEW":
        return "需人工复核：证据不足，退回补充材料"
    if st == "INVALID":
        return "无效匹配：数据不合法，进入治理任务"
    return "未发现重复（NEW）：直接进入人工初审"


def _status_label(status: Optional[str]) -> str:
    return {"COMPLETED": "已完成", "CURRENT": "进行中",
            "PENDING": "待执行", "TERMINATED": "已终止"}.get((status or "").upper(), _s(status))


def _status_tone(status: Optional[str]) -> str:
    return {"COMPLETED": "success", "CURRENT": "warning", "TERMINATED": "danger"}.get(
        (status or "").upper(), "info")


def _risk_tone(risk: Optional[str]) -> str:
    return {"HIGH": "danger", "MEDIUM": "warning", "LOW": "success"}.get((risk or "").upper(), "info")


def _node_of_action(a: dict) -> str:
    """动作归属节点：优先 to_node_code，其次按动作类型推断（Java 口径）。"""
    to_code = (a.get("to_node_code") or "").strip().upper()
    if to_code:
        return to_code
    return _ACTION_NODE.get((a.get("action_type") or "").upper(), "")


def _new_detail(step: dict) -> dict:
    return {
        "nodeCode": step["nodeCode"], "nodeName": step["nodeName"],
        "phaseName": step["phaseName"], "lane": step["lane"], "status": step["status"],
        "summary": "", "fields": [], "tables": [], "notes": [],
    }


def _field(d: dict, label: str, value, tone: Optional[str] = None) -> None:
    d["fields"].append({"label": label, "value": _s(value), "tone": tone})


def _table(d: dict, title: str, columns: List[str], rows: List[List[str]]) -> None:
    """无数据时不建表，由调用方改用 notes 说明口径（Java 口径）。"""
    if not rows:
        return
    d["tables"].append({"title": title, "columns": columns, "rows": rows})


def _actions_for_node(actions: List[dict], node_code: str) -> List[dict]:
    out = []
    for a in actions:
        if _node_of_action(a) == node_code.upper():
            out.append(a)
    return out


# ---------------------------------------------------------------------------
# 一次性数据装配（对应 Java CmdFlowStepDetailMapper 的各 @Select）
# ---------------------------------------------------------------------------

async def _load_ctx(conn, task: dict) -> dict:
    one_id = task.get("one_id") or ""
    biz_id = task.get("biz_id") or task.get("task_no") or ""

    customer = None
    if one_id and one_id != "-":
        r = (await conn.execute(text(
            "SELECT one_id, legal_name, legal_name_en, credit_code, tax_no, customer_type,"
            " product_line, bu_scope, country, province, city, address, contact_name,"
            " contact_phone, contact_email, status, source_system, source_id,"
            " CAST(dq_score AS CHAR) AS dq_score, dq_grade, match_state, duplicate_flag,"
            " CAST(version_no AS CHAR) AS version_no,"
            " DATE_FORMAT(effective_from, '%Y-%m-%d %H:%i') AS effective_from,"
            " CAST(flow_instance_id AS CHAR) AS flow_instance_id, flow_status"
            " FROM cmd_customer WHERE one_id = :o AND del_flag = '0' LIMIT 1"
        ), {"o": one_id})).mappings().first()
        customer = dict(r) if r else None

    # 批量导入：申请不挂单一 One ID，业务主键是批次号
    import_job, import_rows = None, []
    if customer is None and biz_id:
        r = (await conn.execute(text(
            "SELECT job_code, job_name, file_name, template_code, template_version, bu_scope,"
            " scene, error_strategy, duplicate_strategy,"
            " CAST(total_count AS CHAR) AS total_count, CAST(success_count AS CHAR) AS success_count,"
            " CAST(exact_count AS CHAR) AS exact_count, CAST(suspected_count AS CHAR) AS suspected_count,"
            " CAST(new_count AS CHAR) AS new_count, CAST(invalid_count AS CHAR) AS invalid_count,"
            " job_status, submit_by, DATE_FORMAT(submit_time, '%Y-%m-%d %H:%i:%s') AS submit_time"
            " FROM cmd_import_job WHERE job_code = :j AND del_flag = '0' LIMIT 1"
        ), {"j": biz_id})).mappings().first()
        import_job = dict(r) if r else None
        if import_job:
            rows = (await conn.execute(text(
                "SELECT CAST(row_no AS CHAR) AS row_no, row_status, result_type, one_id,"
                " legal_name, credit_code, bu_scope, CAST(dq_score AS CHAR) AS dq_score,"
                " match_state, CAST(error_count AS CHAR) AS error_count, error_summary,"
                " NULLIF(JSON_UNQUOTE(JSON_EXTRACT(parsed_json, '$.address')), 'null') AS address,"
                " NULLIF(JSON_UNQUOTE(JSON_EXTRACT(parsed_json, '$.city')), 'null') AS city,"
                " NULLIF(JSON_UNQUOTE(JSON_EXTRACT(parsed_json, '$.province')), 'null') AS province,"
                " NULLIF(JSON_UNQUOTE(JSON_EXTRACT(parsed_json, '$.contact_phone')), 'null') AS contact_phone,"
                " NULLIF(JSON_UNQUOTE(JSON_EXTRACT(parsed_json, '$.contact_name')), 'null') AS contact_name,"
                " NULLIF(JSON_UNQUOTE(JSON_EXTRACT(parsed_json, '$.legal_name_en')), 'null') AS legal_name_en,"
                " NULLIF(JSON_UNQUOTE(JSON_EXTRACT(parsed_json, '$.tax_no')), 'null') AS tax_no,"
                " NULLIF(JSON_UNQUOTE(JSON_EXTRACT(parsed_json, '$.product_line')), 'null') AS product_line,"
                " NULLIF(JSON_UNQUOTE(JSON_EXTRACT(parsed_json, '$.contact_email')), 'null') AS contact_email"
                " FROM cmd_import_row WHERE job_code = :j AND del_flag = '0' ORDER BY row_no"
            ), {"j": biz_id})).mappings().all()
            import_rows = [dict(x) for x in rows]

    att_biz = one_id if (one_id and one_id != "-") else biz_id
    attachments = [dict(x) for x in (await conn.execute(text(
        "SELECT file_name, category, ocr_status, file_type, CAST(file_size AS CHAR) AS file_size,"
        " DATE_FORMAT(create_time, '%Y-%m-%d %H:%i') AS create_time"
        " FROM cmd_attachment WHERE biz_id = :b AND del_flag = '0' ORDER BY id"
    ), {"b": att_biz})).mappings().all()]

    ocr_rows = [dict(x) for x in (await conn.execute(text(
        "SELECT field_code, field_name, ocr_value, confirmed_value, CAST(confidence AS CHAR) AS confidence,"
        " needs_review, ocr_engine, DATE_FORMAT(create_time, '%Y-%m-%d %H:%i') AS create_time"
        " FROM cmd_ocr_result WHERE biz_id = :b AND del_flag = '0' ORDER BY id"
    ), {"b": att_biz})).mappings().all()]

    candidates: List[dict] = [dict(x) for x in (await conn.execute(text(
        "SELECT m.one_id, m.legal_name, m.credit_code, m.bu_scope, m.customer_level,"
        " CAST(m.total_score AS CHAR) AS total_score, m.is_best, m.status"
        " FROM cmd_match_candidate m JOIN cmd_match_result r ON r.id = m.match_id"
        " WHERE r.biz_id = :b AND m.del_flag = '0' ORDER BY m.total_score DESC LIMIT 5"
    ), {"b": att_biz})).mappings().all()]
    candidate_source = "cmd_match_candidate"

    credit_code = str(customer.get("credit_code") or "") if customer else ""
    if not candidates and credit_code and one_id and one_id != "-":
        candidates = [dict(x) for x in (await conn.execute(text(
            "SELECT one_id, legal_name, credit_code, bu_scope, CAST(dq_score AS CHAR) AS dq_score,"
            " match_state, status FROM cmd_customer"
            " WHERE del_flag = '0' AND one_id <> :o AND credit_code = :c LIMIT 5"
        ), {"o": one_id, "c": credit_code})).mappings().all()]
        candidate_source = "同信用代码复算"

    legacy = [dict(x) for x in (await conn.execute(text(
        "SELECT source_system, source_code, source_name, bu_scope, mapping_type, status"
        " FROM cmd_legacy_mapping WHERE one_id = :o AND del_flag = '0' ORDER BY id"
    ), {"o": att_biz})).mappings().all()] if att_biz else []

    int_runs = [dict(x) for x in (await conn.execute(text(
        "SELECT run_code, endpoint_name, target_system, direction, run_status,"
        " CAST(total_count AS CHAR) AS total_count, CAST(success_count AS CHAR) AS success_count,"
        " CAST(failed_count AS CHAR) AS failed_count, CAST(attempt_count AS CHAR) AS attempt_count,"
        " DATE_FORMAT(start_time, '%Y-%m-%d %H:%i') AS start_time,"
        " CAST(duration_ms AS CHAR) AS duration_ms, error_message"
        " FROM int_run WHERE del_flag = '0' ORDER BY start_time DESC LIMIT 5"
    ))).mappings().all()]

    log_scope = one_id if (one_id and one_id != "-") else task.get("task_no") or "-"
    step_logs = [dict(x) for x in (await conn.execute(text(
        "SELECT CAST(step_seq AS CHAR) AS step_seq, step_type, node_code, node_name,"
        " action_type, action_name, operator_name, operator_role,"
        " DATE_FORMAT(create_time, '%Y-%m-%d %H:%i:%s') AS create_time,"
        " from_status, to_status, opinion"
        " FROM cmd_workflow_step_log WHERE (one_id = :s OR task_no = :t) AND del_flag = '0'"
        " ORDER BY step_seq, id"
    ), {"s": log_scope, "t": task.get("task_no") or "-"})).mappings().all()]

    audit_events = [dict(x) for x in (await conn.execute(text(
        "SELECT event_id, event_type, event_name, operator_name, operator_role,"
        " DATE_FORMAT(event_time, '%Y-%m-%d %H:%i') AS event_time, result, risk_level"
        " FROM audit_event WHERE (one_id = :s OR biz_id = :t) AND del_flag = '0'"
        " ORDER BY event_time DESC LIMIT 10"
    ), {"s": log_scope, "t": task.get("task_no") or "-"})).mappings().all()]

    merge_records = [dict(x) for x in (await conn.execute(text(
        "SELECT merge_code, survivor_one_id, merged_one_id, merge_type, merge_strategy,"
        " reason, status, can_rollback, DATE_FORMAT(create_time, '%Y-%m-%d %H:%i') AS create_time"
        " FROM cmd_merge_record WHERE (merged_one_id = :b OR survivor_one_id = :b) AND del_flag = '0'"
        " ORDER BY create_time DESC LIMIT 5"
    ), {"b": att_biz})).mappings().all()] if att_biz else []

    return {
        "customer": customer, "import_job": import_job, "import_rows": import_rows,
        "attachments": attachments, "ocr_rows": ocr_rows, "candidates": candidates,
        "candidate_source": candidate_source, "legacy": legacy, "int_runs": int_runs,
        "step_logs": step_logs, "audit_events": audit_events, "merge_records": merge_records,
    }


# ---------------------------------------------------------------------------
# 节点明细装配（Java buildStepDetail 的 switch 分发 + 场景扩展）
# ---------------------------------------------------------------------------

def _detail_for_step(task: dict, step: dict, ctx: dict, actions: List[dict]) -> dict:
    d = _new_detail(step)
    node = (step.get("nodeCode") or "").upper()
    c = ctx["customer"]

    builder = _BUILDERS.get(node)
    if builder is not None:
        builder(d, task, step, ctx, actions)
    else:
        _generic_node_detail(d, task, step, ctx, actions)
    return d


def _apply_detail(d, task, step, ctx, actions):
    applicant = task.get("applicant_name") or "申请人"
    d["summary"] = (f"{_s(applicant)} 于 {_dt(task.get('submit_time'))} 提交「"
                    f"{_s(task.get('biz_title'))}」的申请")
    _field(d, "申请编号", task.get("task_no"))
    _field(d, "客户主题", task.get("biz_title"))
    _field(d, "业务类型", task.get("biz_type"))
    _field(d, "归属 BU", task.get("bu_scope"))
    _field(d, "风险等级", task.get("risk_level"), _risk_tone(task.get("risk_level")))
    _field(d, "申请人", task.get("applicant_name"))
    _field(d, "提交时间", _dt(task.get("submit_time")))
    _field(d, "当前节点", task.get("current_node_name"))
    d["notes"].append("提交同时生成 One ID 与首版本快照（cmd_customer / cmd_customer_version），并写入 SUBMIT 轨迹。")
    d["notes"].append("OCR / DQ / Duplicate Check 为系统自动节点，随提交一次执行完，不占用人工审批任务。")
    if ctx["import_job"]:
        d["notes"].append(f"本次为批量导入申请：业务主键是批次号 {_s(ctx['import_job'].get('job_code'))}"
                          "（cmd_import_job），One ID 由 New 行在批准后逐行生成。")


def _customer_or_note(d, task, c):
    if c is None:
        d["notes"].append("该申请未关联客户主档（cmd_approval_task.one_id 为空），因此无法展示主档字段——"
                          "这不是数据丢失，而是该场景本身不以单一客户为装配对象。")


def _input_detail(d, task, step, ctx, actions):
    c = ctx["customer"]
    if c is None and ctx["import_job"]:
        _input_detail_for_import(d, task, ctx)
        return
    d["summary"] = "录入客户主档核心字段并上传营业执照等证明材料，提交时完成落库与首版本快照"
    _customer_or_note(d, task, c)
    _field(d, "法定名称", _cv(c, "legal_name"))
    _field(d, "英文名称", _cv(c, "legal_name_en"))
    _field(d, "统一社会信用代码", _cv(c, "credit_code"),
           "warning" if _is_blank(_cv(c, "credit_code")) else None)
    _field(d, "税号", _cv(c, "tax_no"))
    _field(d, "客户类型", _cv(c, "customer_type"))
    _field(d, "产品线", _cv(c, "product_line"))
    _field(d, "国家 / 省 / 市", f"{_s(_cv(c, 'country'))} / {_s(_cv(c, 'province'))} / {_s(_cv(c, 'city'))}")
    _field(d, "注册地址", _cv(c, "address"))
    _field(d, "联系人", _cv(c, "contact_name"))
    _field(d, "联系电话", _cv(c, "contact_phone"))
    _field(d, "联系邮箱", _cv(c, "contact_email"))
    _field(d, "来源系统", _cv(c, "source_system"))

    rows = [[_s(f.get("file_name")), _s(f.get("category")), _s(f.get("ocr_status")),
             _s(f.get("file_type")), _s(f.get("file_size")), _s(f.get("create_time"))]
            for f in ctx["attachments"]]
    _table(d, "附件清单（cmd_attachment，biz_id = One ID / 申请编号）",
           ["文件名", "分类", "OCR 状态", "类型", "大小(字节)", "上传时间"], rows)
    if not rows:
        d["notes"].append("该实例未落附件记录：POC 演示环境走「按文件名预置识别」的模拟 OCR，不生成实体附件。")
    d["notes"].append("展示的是主档当前值：本次未录入的字段在 cmd_customer 中为 NULL，显示「—」，也是 DQ 扣分项来源。")


def _input_detail_for_import(d, task, ctx):
    job, import_rows = ctx["import_job"], ctx["import_rows"]
    sample = _pick_sample_row(import_rows)
    d["summary"] = (f"按模板解析导入文件并按行装配数据：批次 {_s(job.get('job_code'))}（{_s(job.get('file_name'))}），"
                    f"共 {_s(job.get('total_count'))} 行")
    _field(d, "导入批次", f"{_s(job.get('job_code'))} · {_s(job.get('job_name'))}")
    _field(d, "导入文件", job.get("file_name"))
    _field(d, "导入模板", f"{_s(job.get('template_code'))} {_s(job.get('template_version'))}")
    _field(d, "业务场景", job.get("scene"))
    _field(d, "归属 BU", job.get("bu_scope"))
    _field(d, "总行数 / 成功", f"{_s(job.get('total_count'))} / {_s(job.get('success_count'))}")
    _field(d, "分流结果", f"Exact {_s(job.get('exact_count'))} · New {_s(job.get('new_count'))}"
                         f" · Suspected {_s(job.get('suspected_count'))} · Invalid {_s(job.get('invalid_count'))}",
           "warning" if _num(job.get("invalid_count")) > 0 else None)
    _field(d, "错误策略 / 重复策略", f"{_s(job.get('error_strategy'))} / {_s(job.get('duplicate_strategy'))}")
    _field(d, "提交人", job.get("submit_by"))
    _field(d, "提交时间", _dt(job.get("submit_time")))
    if sample:
        _field(d, "法定名称（样例行）", sample.get("legal_name"))
        _field(d, "统一社会信用代码（样例行）", sample.get("credit_code"))
        _field(d, "注册地址（样例行）", sample.get("address"))
        _field(d, "联系人 / 电话（样例行）",
               f"{_s(sample.get('contact_name'))} / {_s(sample.get('contact_phone'))}")
    rows = [[_s(r.get("row_no")), _s(r.get("legal_name")), _s(r.get("credit_code")),
             _s(r.get("result_type")), _s(r.get("row_status")), _s(r.get("one_id")),
             _s(r.get("dq_score")), _s(r.get("error_count")), _s(r.get("error_summary"))]
            for r in import_rows]
    _table(d, "导入行明细（cmd_import_row）",
           ["行号", "客户名称", "统一社会信用代码", "分流结果", "行状态", "生成 One ID", "DQ 分", "错误数", "错误摘要"], rows)
    d["notes"].append("批量导入申请不挂单一 One ID：装配对象是「批次 + 行」，上表每一行都是文件里的真实数据行。")


def _pick_sample_row(import_rows: List[dict]) -> dict:
    for t in ("NEW", "EXACT", "SUSPECTED"):
        for r in import_rows:
            if str(r.get("result_type") or "").upper() == t:
                return r
    return import_rows[0] if import_rows else {}


def _ocr_detail(d, task, step, ctx, actions):
    c = ctx["customer"]
    d["summary"] = "营业执照识别完成，抽取客户法定名称 / 统一社会信用代码 / 注册地址 / 省份 / 城市 并回填主档"
    ocr_rows = ctx["ocr_rows"]
    persisted = bool(ocr_rows)
    rows = []
    for r in ocr_rows:
        confirmed = r.get("confirmed_value") or r.get("ocr_value")
        rows.append([_s(r.get("field_name")), _s(confirmed),
                     "待人工复核" if str(r.get("needs_review") or "").upper() == "Y" else "已回填主档",
                     _s(r.get("confidence"))])
    if not persisted:
        conf: Dict[str, str] = {}
        preset = ocr_service.recognize_of_customer(
            _cv(c, "legal_name"), _cv(c, "credit_code")) if c else None
        if preset and preset.get("fields"):
            for f in preset["fields"]:
                conf[f["field"]] = f["confidence"]
        for label, key in (("客户法定名称", "legal_name"), ("统一社会信用代码", "credit_code"),
                           ("注册地址", "address"), ("省份", "province"), ("城市", "city")):
            rows.append([label, _s(_cv(c, key)), "已回填主档", conf.get(label, DASH)])
    _field(d, "识别引擎", _s(ocr_rows[0].get("ocr_engine")) if persisted else "POC 预置识别（ocr_service）")
    _field(d, "识别字段数", len(rows))
    _field(d, "识别结果来源", "cmd_ocr_result" if persisted else "主档回填值（未落识别明细表）")
    _table(d, "识别字段与回填结果", ["字段", "识别值", "回填状态", "置信度"], rows)
    if not persisted:
        d["notes"].append("POC 环境 OCR 按文件名匹配预置结果，cmd_ocr_result 为空；"
                          "上表「识别值」是识别后实际写入客户主档的字段值（cmd_customer）。")


def _dq_detail(d, task, step, ctx, actions):
    c = ctx["customer"]
    if c is None and ctx["import_job"]:
        _dq_detail_for_import(d, task, ctx)
        return
    rows: List[List[str]] = []
    deducted = hits = 0

    hit = _dq_row(rows, "统一社会信用代码", "必填（关键匹配字段）", _cv(c, "credit_code"), 12)
    deducted += hit
    hits += 1 if hit > 0 else 0
    hit = _dq_row(rows, "注册地址", "必填完整性", _cv(c, "address"), 8)
    deducted += hit
    hits += 1 if hit > 0 else 0
    region_missing = _is_blank(_cv(c, "province")) or _is_blank(_cv(c, "city"))
    rows.append(["省份 + 城市", "值域规范性", f"{_s(_cv(c, 'province'))} / {_s(_cv(c, 'city'))}",
                 "扣分" if region_missing else "通过", "-4" if region_missing else "0"])
    if region_missing:
        deducted += 4
        hits += 1
    for dim, val in (("联系人", _cv(c, "contact_name")), ("联系电话", _cv(c, "contact_phone"))):
        hit = _dq_row(rows, dim, "完整性", val, 4)
        deducted += hit
        hits += 1 if hit > 0 else 0

    info_miss = sum(_info_row(rows, dim, rule, val) for dim, rule, val in (
        ("法定名称", "必填（主档唯一标识）", _cv(c, "legal_name")),
        ("客户类型", "值域规范性", _cv(c, "customer_type")),
        ("税号", "完整性（提示）", _cv(c, "tax_no")),
        ("联系邮箱", "完整性（提示）", _cv(c, "contact_email")),
        ("产品线", "完整性（提示）", _cv(c, "product_line")),
    ))

    recomputed = max(0, 100 - deducted)
    stored_raw = task.get("dq_score")
    stored = _num(stored_raw) if stored_raw is not None else recomputed

    d["summary"] = (f"DQ 质量分 {_s(stored_raw if stored_raw is not None else recomputed)}（等级 {_s(_cv(c, 'dq_grade'))}）："
                    + ("5 项计分检查全部通过" if hits == 0 else f"命中 {hits} 项扣分，共扣 {deducted} 分")
                    + (f"；另有 {info_miss} 项提示缺失（不计分）" if info_miss else ""))
    _field(d, "DQ 总分", stored_raw if stored_raw is not None else recomputed,
           "success" if hits == 0 else "warning")
    _field(d, "质量等级", _cv(c, "dq_grade"))
    _field(d, "扣分合计", f"-{deducted}")
    _field(d, "提示项", f"{info_miss} 项（不计分）", "info" if info_miss > 0 else "success")
    _field(d, "路由结论", "自动校验通过，进入匹配分流" if hits == 0 else "存在扣分项，进入人工治理时需重点复核")
    _table(d, "DQ 检查项明细", ["检查维度", "规则", "当前值", "结果", "扣分"], rows)
    d["notes"].append("分值与等级来自 cmd_customer.dq_score / dq_grade（提交时确定性打分：缺信用代码 -12、"
                      "缺地址 -8、缺省市 -4、缺联系人 -4、缺电话 -4；≥90→A、≥75→B、≥60→C、<60→D）。")
    d["notes"].append(f"按同一规则对当前主档复算得 {recomputed} 分，"
                      + ("与存储分值一致。" if recomputed == stored
                         else f"与存储分值（{stored}）不一致——说明主档在打分后被修改过。"))


def _dq_detail_for_import(d, task, ctx):
    job, import_rows = ctx["import_job"], ctx["import_rows"]
    rows: List[List[str]] = []
    error_total = invalid_rows = scored = 0
    min_score, total = 100, 0.0
    for r in import_rows:
        err = _num(r.get("error_count"))
        error_total += err
        if err > 0 or str(r.get("result_type") or "").upper() == "INVALID":
            invalid_rows += 1
        score = _f(r.get("dq_score"))
        if score > 0:
            total += score
            scored += 1
            min_score = min(min_score, int(score))
        rows.append([_s(r.get("row_no")), _s(r.get("legal_name")), _s(r.get("credit_code")),
                     _s(r.get("dq_score")), _grade(score), "通过" if err == 0 else "扣分",
                     "0" if err == 0 else f"-{err * 4}", _s(r.get("error_summary"))])
    avg = total / scored if scored else 0.0
    d["summary"] = (f"按行校验 {len(import_rows)} 条：平均 DQ {avg:.2f}"
                    f"（最低 {_s(min_score) if scored else DASH}），命中问题行 {invalid_rows} 条、错误合计 {error_total} 项")
    _field(d, "校验口径", "逐行 DQ（100 起，按缺失 / 格式错误扣分）")
    _field(d, "平均 DQ 分", f"{avg:.2f}", "success" if avg >= 90 else "warning")
    _field(d, "最低 DQ 分", _s(min_score) if scored else DASH, "danger" if scored and min_score < 60 else None)
    _field(d, "问题行数", f"{invalid_rows} / {len(import_rows)}", "warning" if invalid_rows > 0 else "success")
    _field(d, "错误合计", f"{error_total} 项", "warning" if error_total > 0 else "success")
    _field(d, "Invalid 行数", job.get("invalid_count"), "danger" if _num(job.get("invalid_count")) > 0 else None)
    _table(d, "逐行校验明细（cmd_import_row）",
           ["行号", "客户名称", "统一社会信用代码", "DQ 分", "等级", "结果", "扣分", "错误摘要"], rows)
    d["notes"].append("DQ 分与 error_count / error_summary 由导入引擎逐行落库（cmd_import_row），本节点只做汇总展示。")


def _dq_row(rows: List[List[str]], dim: str, rule: str, value, deduction: int) -> int:
    missing = _is_blank(value)
    rows.append([dim, rule, _s(value), "扣分" if missing else "通过", f"-{deduction}" if missing else "0"])
    return deduction if missing else 0


def _info_row(rows: List[List[str]], dim: str, rule: str, value) -> int:
    missing = _is_blank(value)
    rows.append([dim, rule, _s(value), "缺失（提示）" if missing else "通过", "0"])
    return 1 if missing else 0


def _dup_detail(d, task, step, ctx, actions):
    c = ctx["customer"]
    match_state = str(_cv(c, "match_state") or "")
    rows = [[_s(m.get("one_id")), _s(m.get("legal_name")), _s(m.get("credit_code")),
             _s(m.get("bu_scope")), _s(m.get("total_score") or m.get("dq_score")),
             "最佳候选" if (str(m.get("is_best") or "").upper() == "Y") else "候选"]
            for m in ctx["candidates"]]
    d["summary"] = f"匹配结论 {_s(match_state) or task.get('duplicate_state')}，候选 {len(rows)} 条"
    _field(d, "匹配状态", match_state or task.get("duplicate_state"),
           "warning" if match_state.upper() in ("SUSPECT", "SUSPECTED", "EXACT") else "success")
    _field(d, "疑似重复标记", "是" if str(_cv(c, "duplicate_flag") or "").upper() == "Y" else "否")
    _field(d, "路由结论", _routing(match_state))
    _table(d, "匹配候选（" + ctx["candidate_source"] + "）",
           ["One ID", "法定名称", "统一社会信用代码", "归属 BU", "匹配分", "判定"], rows)
    if not rows:
        d["notes"].append("未发现同统一社会信用代码的其他主数据，按 NEW 直接进入人工初审。")
    d["notes"].append("SUSPECTED 候选必须经 BU Scope 初审确认（Same-BU 关联）或升级 GC 做跨 BU 决策，不允许自动合并。")


def _review_detail(d, task, step, ctx, actions):
    node = (step.get("nodeCode") or "").upper()
    gc = node == NODE_GC_REVIEW
    opinion = step.get("opinion")
    d["summary"] = (opinion if opinion and str(opinion).strip()
                    else ("等待 GC Steward 做跨 BU 证据核对与 One ID 决策"
                          if gc else "等待 BU Steward 初审：确认 Same-BU 证据或升级 Cross-BU"))
    _field(d, "节点", step.get("nodeName"))
    _field(d, "泳道", step.get("lane"))
    _field(d, "办理人", step.get("assignee") or task.get("assignee_name"))
    _field(d, "办理角色", "GC_STEWARD" if gc else "BU_STEWARD")
    _field(d, "决策时限（SLA）", _dt(task.get("sla_due")))
    _field(d, "执行状态", _status_label(step.get("status")), _status_tone(step.get("status")))

    rows = [[_s(a.get("action_time")), _s(a.get("action_name") or a.get("action_type")),
             _s(a.get("operator_name")), _s(a.get("operator_role")),
             f"{_s(a.get('before_state'))} → {_s(a.get('after_state'))}", _s(a.get("opinion"))]
            for a in _actions_for_node(actions, node)]
    _table(d, ("GC 决策动作" if gc else "BU 初审动作") + "（cmd_approval_action）",
           ["时间", "动作", "操作人", "角色", "状态流转", "意见"], rows)
    if not rows:
        d["notes"].append("该节点尚未产生审批动作，当前为待办状态（工作项列表可领取处理）。")
    d["notes"].append("GC 决策结果：关联已有 One ID（LINK）/ 新创主数据（CREATE_NEW）/ 确认合并（MERGE）。"
                      if gc else
                      "BU 初审结果：确认 Same-BU（关联本地组织）/ 升级 GC（Cross-BU）/ 退回补充证据。")


def _result_detail(d, task, step, ctx, actions):
    c = ctx["customer"]
    d["summary"] = f"生成 / 关联结果：One ID {_s(task.get('one_id'))}，主数据状态 {_s(_cv(c, 'status'))}"
    _field(d, "One ID", task.get("one_id"))
    _field(d, "主数据状态", _cv(c, "status"))
    _field(d, "质量等级", _cv(c, "dq_grade"))
    _field(d, "匹配状态", _cv(c, "match_state"))
    _field(d, "版本号", _cv(c, "version_no"))
    _field(d, "生效时间", _cv(c, "effective_from"))
    _field(d, "流程实例 ID", task.get("flow_instance_id"))
    _field(d, "引擎状态镜像", task.get("flow_status"))
    rows = [[_s(m.get("source_system")), _s(m.get("source_code")), _s(m.get("source_name")),
             _s(m.get("bu_scope")), _s(m.get("mapping_type")),
             "有效" if str(m.get("status")) == "0" else "停用"]
            for m in ctx["legacy"]]
    _table(d, "来源系统编码映射（cmd_legacy_mapping）",
           ["来源系统", "来源编码", "来源名称", "BU", "类型", "状态"], rows)
    if not rows:
        d["notes"].append("该客户暂无本地编码映射；建立后 One ID 与 DMS+ / SAP / Cloud 编码一一对应。")


def _publish_detail(d, task, step, ctx, actions):
    d["summary"] = "按主数据发布契约，把 One ID 与编码映射下发到下游系统（DMS+ / SAP / Cloud）"
    rows = [[_s(r.get("run_code")), _s(r.get("endpoint_name")), _s(r.get("target_system")),
             _s(r.get("direction")), _s(r.get("run_status")),
             f"{_s(r.get('success_count'))} / {_s(r.get('total_count'))}", _s(r.get("failed_count")),
             _s(r.get("attempt_count")), _s(r.get("duration_ms")), _s(r.get("start_time"))]
            for r in ctx["int_runs"]]
    _table(d, "集成通道运行记录（int_run，按通道最近 5 次）",
           ["运行编号", "端点", "目标系统", "方向", "状态", "成功/总数", "失败", "重试", "耗时(ms)", "开始时间"], rows)
    d["notes"].append("int_run 为通道级运行记录（POC 未建客户级下发明细 int_message），用于说明下发通路的实时健康度。")
    d["notes"].append("下发失败不阻塞主流程，由 Retry / Resubmit 机制重投；可在「集成监控」页下钻失败原因并手动重试。")


def _trace_detail(d, task, step, ctx, actions):
    logs = ctx["step_logs"]
    d["summary"] = f"按 One ID / 申请编号串联的步骤执行总账共 {len(logs)} 条，任务状态 {_s(task.get('status'))}"
    _field(d, "One ID", task.get("one_id"))
    _field(d, "任务编号", task.get("task_no"))
    _field(d, "流程实例 ID", task.get("flow_instance_id"))
    _field(d, "引擎状态镜像", task.get("flow_status"))
    _field(d, "当前节点", task.get("current_node_name"))
    _field(d, "当前处理人", task.get("assignee_name"))
    rows = [[_s(l.get("step_seq")), _s(l.get("step_type")), _s(l.get("node_name")),
             _s(l.get("action_name")), _s(l.get("operator_name")), _s(l.get("operator_role")),
             _s(l.get("create_time")), _s(l.get("opinion"))]
            for l in logs]
    _table(d, "步骤执行日志（cmd_workflow_step_log）",
           ["序号", "类型", "节点", "动作", "操作人", "角色", "时间", "意见"], rows)
    if not rows:
        d["notes"].append("该对象暂无步骤日志；每次提交 / 系统自动检查 / 人工决策都会写入一条，作为跨系统追溯主键。")


def _audit_detail(d, task, step, ctx, actions):
    events = ctx["audit_events"]
    d["summary"] = f"该对象相关审计事件共 {len(events)} 条（含变更、审批、合并、权限与集成事件）"
    rows = [[_s(e.get("event_id")), _s(e.get("event_type")), _s(e.get("event_name")),
             _s(e.get("operator_name")), _s(e.get("result")), _s(e.get("risk_level")),
             _s(e.get("event_time"))]
            for e in events]
    _table(d, "审计事件（audit_event，按 One ID / 申请编号）",
           ["事件编号", "类型", "事件", "操作人", "结果", "风险", "时间"], rows)
    if not rows:
        d["notes"].append("该对象暂无审计事件记录。")
    d["notes"].append("Before / After 快照存 audit_event.before_json / after_json，审计数据只增不改，Auditor 只读。")


# ---------------------------------------------------------------------------
# 场景扩展节点（Java 版未覆盖，这里补齐保证「所有工作流的每个节点都有记录可看」）
# ---------------------------------------------------------------------------

def _merge_candidates_detail(d, task, step, ctx, actions):
    """MERGE：疑似重复发现 / 候选对比准备。"""
    _dup_detail(d, task, step, ctx, actions)
    d["nodeName"] = step["nodeName"]
    compare = (step.get("nodeCode") or "").upper() == "COMPARE"
    if compare:
        d["summary"] = (f"候选对比准备：信用代码 / 经营地址 / 名称 / 来源与层级五维对比，"
                        f"候选 {len(ctx['candidates'])} 条")
        d["notes"].insert(0, "对比维度与 cmd_match_candidate.field_compare_json 口径一致；名称仅作辅助线索。")


def _evidence_detail(d, task, step, ctx, actions):
    """MERGE：补充业务证据。"""
    d["summary"] = "确认客户身份、上传附件并说明业务背景（证据快照存 cmd_approval_task.evidence_json）"
    _field(d, "申请编号", task.get("task_no"))
    _field(d, "存活 One ID（保留）", (task.get("evidence_json") or {}).get("survivor_one_id")
           if isinstance(task.get("evidence_json"), dict) else None)
    _field(d, "合并 One ID（被合并）", (task.get("evidence_json") or {}).get("merged_one_id")
           if isinstance(task.get("evidence_json"), dict) else task.get("one_id"))
    rows = [[_s(f.get("file_name")), _s(f.get("category")), _s(f.get("ocr_status")), _s(f.get("create_time"))]
            for f in ctx["attachments"]]
    _table(d, "证据附件（cmd_attachment）", ["文件名", "分类", "OCR 状态", "上传时间"], rows)
    if not rows:
        d["notes"].append("该申请未上传实体附件：POC 以证据 JSON（evidence_json）承载合并依据。")


def _merge_exec_detail(d, task, step, ctx, actions):
    """MERGE：执行合并 / 新建（cmd_merge_record）。"""
    records = ctx["merge_records"]
    d["summary"] = (f"更新 Golden Record：合并记录 {len(records)} 条"
                    if records else "合并尚未执行：等待审批通过后由 END 事件触发（execMergeTask 口径）")
    _field(d, "合并 One ID", task.get("one_id") or task.get("biz_id"))
    _field(d, "任务状态", task.get("status"))
    _field(d, "当前节点", task.get("current_node_name"))
    rows = [[_s(m.get("merge_code")), _s(m.get("survivor_one_id")), _s(m.get("merged_one_id")),
             _s(m.get("merge_type")), _s(m.get("merge_strategy")), _s(m.get("status")),
             "可回滚" if str(m.get("can_rollback")) == "Y" else "—", _s(m.get("create_time"))]
            for m in records]
    _table(d, "合并记录（cmd_merge_record）",
           ["合并编号", "保留 One ID", "被合并 One ID", "类型", "策略", "状态", "回滚", "时间"], rows)
    if not records:
        d["notes"].append("合并执行记录在审批 END 事件里落库（cmd_merge_record），生效前该表无本单记录属正常状态。")


def _xref_detail(d, task, step, ctx, actions):
    """MERGE：建立交叉引用（旧 One ID → 保留 One ID，cmd_legacy_mapping）。"""
    _result_detail(d, task, step, ctx, actions)
    d["summary"] = "保留 Legacy Code 与 Source Snapshot（旧 One ID → 保留 One ID）"
    if not ctx["legacy"]:
        d["notes"].insert(0, "交叉引用在合并生效后写入 cmd_legacy_mapping；当前尚未生效，暂无映射记录。")


def _integration_detail(d, task, step, ctx, actions):
    """INTEGRATION_FAIL 全链路节点：读 int_run 通道运行 + 本节点动作历史。"""
    d["summary"] = f"集成运行任务视角：节点「{step.get('nodeName')}」，通道最近运行 {len(ctx['int_runs'])} 条"
    rows = [[_s(r.get("run_code")), _s(r.get("endpoint_name")), _s(r.get("target_system")),
             _s(r.get("direction")), _s(r.get("run_status")),
             f"{_s(r.get('success_count'))} / {_s(r.get('total_count'))}",
             _s(r.get("failed_count")), _s(r.get("attempt_count")), _s(r.get("start_time"))]
            for r in ctx["int_runs"]]
    _table(d, "集成通道运行记录（int_run）",
           ["运行编号", "端点", "目标系统", "方向", "状态", "成功/总数", "失败", "重试", "开始时间"], rows)
    _append_node_history(d, step, ctx, actions)
    if not rows:
        d["notes"].append("POC 环境 int_run 暂无运行记录，可先在「集成监控」页模拟一次通道运行。")


def _generic_node_detail(d, task, step, ctx, actions):
    """兜底：任何未专项实现的节点都展示「节点元信息 + 本节点动作 + 步骤日志」历史。"""
    d["summary"] = f"节点「{step.get('nodeName')}」执行情况（{step.get('phaseName')} 阶段 · {step.get('lane')} 泳道）"
    _field(d, "节点编码", step.get("nodeCode"))
    _field(d, "节点类型", step.get("nodeType"))
    _field(d, "执行状态", _status_label(step.get("status")), _status_tone(step.get("status")))
    _field(d, "操作人", step.get("operator") or task.get("assignee_name"))
    _field(d, "操作时间", _dt(step.get("actionTime")))
    if step.get("opinion"):
        _field(d, "意见", step.get("opinion"))
    _append_node_history(d, step, ctx, actions)
    d["notes"].append("该节点暂无专项明细模板：上方表格展示的是本任务在该节点真实发生的动作与步骤日志"
                      "（cmd_approval_action / cmd_workflow_step_log）。")


def _append_node_history(d, step, ctx, actions):
    node = (step.get("nodeCode") or "").upper()
    arows = [[_s(a.get("action_time")), _s(a.get("action_name") or a.get("action_type")),
              _s(a.get("operator_name")), _s(a.get("operator_role")), _s(a.get("opinion"))]
             for a in _actions_for_node(actions, node)]
    _table(d, "节点动作记录（cmd_approval_action）", ["时间", "动作", "操作人", "角色", "意见"], arows)
    lrows = [[_s(l.get("create_time")), _s(l.get("action_name")), _s(l.get("operator_name")),
              _s(l.get("operator_role")), _s(l.get("opinion"))]
             for l in ctx["step_logs"] if str(l.get("node_code") or "").upper() == node]
    _table(d, "步骤日志（cmd_workflow_step_log）", ["时间", "动作", "操作人", "角色", "意见"], lrows)
    if not arows and not lrows:
        d["notes"].append("该节点尚未产生执行记录（等待前置节点流转后写入）。")


# 节点编码 → 装配器（Java buildStepDetail 的 switch + 场景扩展）
_BUILDERS: Dict[str, object] = {
    "APPLY": _apply_detail,
    "INPUT": _input_detail,
    "OCR": _ocr_detail,
    "DQ": _dq_detail,
    "DUP": _dup_detail,
    NODE_BU_REVIEW: _review_detail,
    NODE_GC_REVIEW: _review_detail,
    "RESULT": _result_detail,
    "PUBLISH": _publish_detail,
    "TRACE": _trace_detail,
    "AUDIT": _audit_detail,
    # MERGE 场景扩展
    "CAND": _merge_candidates_detail,
    "COMPARE": _merge_candidates_detail,
    "EVID": _evidence_detail,
    "MERGE_EXEC": _merge_exec_detail,
    "XREF": _xref_detail,
    # INTEGRATION_FAIL 场景扩展
    "RUN": _integration_detail, "CALL": _integration_detail, "DETECT": _integration_detail,
    "RETRY": _integration_detail, "ALERT": _integration_detail, "ACK": _integration_detail,
    "MONITOR": _integration_detail, "BIZ_RESULT": _integration_detail,
}


async def build_step_details(conn, task: dict, steps: List[dict], actions: List[dict]) -> List[dict]:
    """为每个泳道步骤装配节点级明细（flow_trace 接口调用）。"""
    ctx = await _load_ctx(conn, task)
    return [_detail_for_step(task, step, ctx, actions) for step in steps]

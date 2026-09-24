"""客户主档服务：提交新建申请 → 落 cmd_customer_application + cmd_approval_task → 启动 SpiffWorkflow；
审批通过（流程 END）后发布为 cmd_customer 黄金记录。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, desc

from ..core.db import get_engine, table
from ..services import sequence as seq
from ..services.duplicate import duplicate_check
from ..workflow.engine import start_instance, reset_instance_node


# 提交必填项（对齐总设计「提交校验」+ 主档必填属性）：
# legal_name 是主档主键属性；credit_code 是主要匹配依据（允许暂缺但要显式确认）；
# customer_type / bu_scope 是分层与数据权限维度——缺任一项则整单不可入库。
REQUIRED_SUBMIT_FIELDS = (
    ("legal_name", "客户法定名称"),
    ("customer_type", "客户类型"),
    ("bu_scope", "归属BU"),
)


def validate_submit(payload) -> None:
    """提交前校验（BUG-PY-04）：全空表单不得产生主档垃圾数据。

    此前 `legal_name: str` 只保证「字段存在」，空串照样通过，于是出现
    GC-00000005（名称/信用代码皆空、状态 Active）这类脏数据。
    """
    missing = [label for code, label in REQUIRED_SUBMIT_FIELDS
               if not str(getattr(payload, code, None) or "").strip()]
    if missing:
        raise ValueError("请填写必填项：" + "、".join(missing))
    if not str(getattr(payload, "credit_code", None) or "").strip():
        raise ValueError("请填写必填项：统一社会信用代码")


def _blank(value) -> bool:
    return value is None or not str(value).strip()


def dq_score_for(values: dict) -> tuple[float, str]:
    """确定性 DQ 打分（口径与流程跟踪 DQ 节点展示完全一致）。

    100 分起扣：缺信用代码 -12、缺经营地址 -8、缺省市 -4、缺联系人 -4、缺联系电话 -4；
    等级 ≥90→A、≥75→B、≥60→C、<60→D。

    此前新建客户全程不打分，`cmd_customer.dq_score` 恒为 NULL——
    列表「DQ 分数」列空白、统计 avgDqScore=0，而流程跟踪里却按同一规则把分数
    现算出来展示，两边对不上（测试报告：部分客户 DQ 分数为空）。
    """
    score = 100
    if _blank(values.get("credit_code")):
        score -= 12
    if _blank(values.get("address")):
        score -= 8
    if _blank(values.get("province")) or _blank(values.get("city")):
        score -= 4
    if _blank(values.get("contact_name")):
        score -= 4
    if _blank(values.get("contact_phone")):
        score -= 4
    score = max(0, score)
    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D"
    return float(score), grade


async def cross_bu_conflicts(conn, credit_code: Optional[str], bu_scope: Optional[str],
                             exclude_one_id: Optional[str] = None) -> list[dict]:
    """同信用代码在**其它 BU** 的已发布主档 / 在途申请（跨BU判定的事实来源）。

    为什么不能只看查重 peers：duplicate_check 只回传「命中的最佳候选」一条，
    当同码记录里既有本 BU 的也有别的 BU 的时候，最佳候选若是本 BU，跨BU 就被漏判
    （「两个 BU 各自批准、GC 无待办」的根因之一）。这里按信用代码把同码记录全量捞出来，
    任何一条 BU 不同即视为跨BU。
    """
    code = (credit_code or "").strip()
    bu = (bu_scope or "").strip()
    if not code:
        return []
    out: list[dict] = []
    cust = table("cmd_customer")
    for r in (await conn.execute(
        select(cust.c.one_id, cust.c.legal_name, cust.c.bu_scope, cust.c.status)
        .where(cust.c.credit_code == code)
        .where(cust.c.status == "active")
        .where(cust.c.del_flag == "0")
    )).mappings().all():
        if (r["bu_scope"] or "").strip() == bu:
            continue
        if exclude_one_id and r["one_id"] == exclude_one_id:
            continue
        out.append({"one_id": r["one_id"], "legal_name": r["legal_name"],
                    "bu_scope": r["bu_scope"], "source": "MASTER"})
    app = table("cmd_customer_application")
    for r in (await conn.execute(
        select(app.c.one_id, app.c.legal_name, app.c.bu_scope, app.c.app_no)
        .where(app.c.credit_code == code)
        .where(app.c.status.in_(["pending", "returned"]))
        .where(app.c.del_flag == "0")
    )).mappings().all():
        if (r["bu_scope"] or "").strip() == bu:
            continue
        if exclude_one_id and r["one_id"] == exclude_one_id:
            continue
        out.append({"one_id": r["one_id"], "legal_name": r["legal_name"],
                    "bu_scope": r["bu_scope"], "app_no": r["app_no"],
                    "source": "IN_FLIGHT"})
    return out


async def submit_customer(payload, actor: str = "demo") -> dict:
    validate_submit(payload)
    engine = get_engine()
    async with engine.begin() as conn:
        one_id = await seq.gen_one_id(conn)
        app_no = await seq.gen_app_no(conn)
        # 提交人：审批详情「提交人」/ 流程跟踪「申请人」的数据源。
        # 取值优先级：前端传入 applicant_name → 服务入参 actor（非默认 demo 时）→ 兜底默认业务角色。
        # 此前从未写入 applicant_name，导致该列在审批详情恒显示「-」（测试报告 BUG-PY-03）。
        applicant = ((getattr(payload, "applicant_name", None) or "").strip()
                     or (actor if actor and actor != "demo" else "Business User"))
        # 查重对齐 Java matchExisting：信用代码 → EXACT；名称（规范化相等或 Dice≥0.85）→ SUSPECTED；
        # 同信用代码在途申请 → SUSPECTED（上一单未审完时不判 NEW）
        # 查重对齐总设计 V6.1：主依据 = 信用代码 + 经营地址，客户名称仅作辅助线索；
        # 阈值与标准化策略取自 match_rule（scene=CREATE）
        dup = await duplicate_check(conn, payload.credit_code, payload.legal_name,
                                    getattr(payload, "address", None), scene="CREATE")
        # 跨BU 判定：比较命中记录的 BU 与申请 BU（在途申请同样带 bu_scope，前端 crossBu 仅作覆盖）。
        # 关键修正（BUG-PY-06）：不能只看查重命中的那一条 peers——同码记录可能同时存在
        # 本 BU 与其它 BU 的多条，最佳候选落在本 BU 时跨BU 会被漏判，于是两个 BU 各自批准、
        # GC 永远收不到待办。这里对同码记录做全量比对，任一 BU 不同即判跨BU。
        cross_peers = await cross_bu_conflicts(conn, payload.credit_code,
                                              payload.bu_scope, exclude_one_id=one_id)
        cross_bu = bool(payload.cross_bu) or bool(cross_peers)
        if not cross_bu and dup["duplicate_flag"] == "Y" and dup["peers"]:
            cross_bu = any((p.get("bu_scope") or "") != (payload.bu_scope or "")
                           for p in dup["peers"])
        risk = "High" if (dup["duplicate_flag"] == "Y" or cross_bu) else "Medium"

        # 命中存量时写入治理证据（含「候选One ID」键）——
        # 审批端 _is_duplicate_link_approval 依据该键渲染「关联已有/创建新主档」决策按钮组
        evidence = None
        if dup["duplicate_flag"] == "Y" and dup["peers"]:
            masters = [p for p in dup["peers"] if p.get("source") == "MASTER"]
            flights = [p for p in dup["peers"] if p.get("source") == "IN_FLIGHT"]
            contrib = dup["peers"][0].get("contributions") or {}
            if flights:
                # 命中的是尚未审批完成的申请，不是已发布主档——文案必须区分，
                # 否则审批人/审计看到的是一条库里并不存在的「命中主档」
                basis = ("同一统一社会信用代码 " + str(payload.credit_code)
                         + " 存在尚未审批完成的在途申请（"
                         + "、".join(f"{p.get('app_no') or ''}" for p in flights if p.get("app_no"))
                         + "），库中暂无该主体的已发布主档")
            else:
                basis = f"主依据（信用代码 / 经营地址）命中已发布主档：{payload.credit_code}"
            top = dup["peers"][0]
            evidence = {
                "候选One ID": "、".join(
                    f"{p['one_id']} · {p.get('legal_name') or ''}" for p in dup["peers"]),
                "匹配状态": dup["match_state"],
                "命中来源": "在途申请" if flights else "已发布主档",
                "在途申请": "是" if flights else "否",
                # 申请侧 / 候选侧成对字段：审批弹窗的「字段级对比」按这些键配对渲染
                # （申请名称/信用代码/注册地址/申请BU/申请来源系统 vs 候选*）。
                # 缺了申请侧键，对比表每一行都只会显示「（空）」，等于没有证据。
                "申请名称": payload.legal_name or "",
                "信用代码": payload.credit_code or "",
                "注册地址": payload.address or "",
                "申请BU": payload.bu_scope or "",
                "申请来源系统": payload.source_system or "",
                "候选名称": top.get("legal_name") or "",
                "候选信用代码": top.get("credit_code") or "",
                "候选经营地址": top.get("address") or "",
                "候选BU": top.get("bu_scope") or "",
                "匹配得分": f"{dup.get('score') or 0:.0f}",
                "字段贡献": "；".join(f"{k} {v:.0f}" for k, v in contrib.items()) or "—",
                "查重依据": basis,
                "匹配口径": dup.get("basis") or "",
                "跨BU": "是" if cross_bu else "否",
                # 跨BU 事实清单：GC 决策需要知道「到底和哪几条、哪个 BU 撞了」，
                # 只给一个候选 One ID 会让「跨BU」结论无法核对（BUG-PY-06）
                "跨BU命中记录": "；".join(
                    f"{p['one_id']} · {p.get('legal_name') or ''} · {p.get('bu_scope') or ''}"
                    for p in cross_peers) or "无",
            }

        app_id = await seq.next_id(conn, "cmd_customer_application")
        # DQ 质量分：提交即按确定性规则打分并落库（申请单 + 待办 + 流程变量），
        # 供「客户详情 / 列表 DQ 分数列 / DQ 统计」直接读取，无需事后复算。
        dq_value, dq_grade = dq_score_for({
            "credit_code": payload.credit_code, "address": payload.address,
            "province": payload.province, "city": payload.city,
            "contact_name": payload.contact_name, "contact_phone": payload.contact_phone,
        })
        await conn.execute(table("cmd_customer_application").insert().values(
            id=app_id, app_no=app_no, one_id=one_id,
            legal_name=payload.legal_name, legal_name_en=payload.legal_name_en,
            short_name=payload.short_name, credit_code=payload.credit_code,
            tax_no=payload.tax_no, customer_type=payload.customer_type,
            customer_level=payload.customer_level, product_line=payload.product_line,
            bu_scope=payload.bu_scope, gc_scope_flag=payload.gc_scope_flag,
            country=payload.country, province=payload.province, city=payload.city,
            address=payload.address, payer_id=payload.payer_id,
            contact_name=payload.contact_name, contact_phone=payload.contact_phone,
            contact_email=payload.contact_email,             status="pending",
            source_system=payload.source_system, match_state=dup["match_state"],
            duplicate_flag=dup["duplicate_flag"], dq_score=dq_value, dq_grade=dq_grade,
            del_flag="0", create_by=0, create_time=datetime.now(),
        ))

        task_id = await seq.next_id(conn, "cmd_approval_task")
        await conn.execute(table("cmd_approval_task").insert().values(
            id=task_id, task_no=app_no, task_category="APPROVAL",
            biz_type="CUSTOMER_CREATE", biz_id=one_id, biz_title=payload.legal_name,
            one_id=one_id, scene_code="CUSTOMER_CREATE", bu_scope=payload.bu_scope,
            scope="BU", current_node_code="BU_REVIEW", current_node_name="BU初审",
            assignee_role="BU_STEWARD", status="PENDING", risk_level=risk,
            duplicate_state=dup["match_state"], cross_bu_flag="Y" if cross_bu else "N",
            dq_score=dq_value, evidence_json=evidence,
            applicant_name=applicant, applicant_id=getattr(payload, "applicant_id", None),
            submit_time=datetime.now(), del_flag="0", create_by=0, create_time=datetime.now(),
        ))

        await start_instance(
            scene_code="CUSTOMER_CREATE", biz_type="CUSTOMER_CREATE", biz_no=app_no,
            variables={
                "taskNo": app_no, "bizType": "CUSTOMER_CREATE", "oneId": one_id,
                "buScope": payload.bu_scope or "", "crossBu": cross_bu,
                "riskLevel": risk, "duplicateState": dup["match_state"],
                "dqScore": dq_value, "sceneCode": "CUSTOMER_CREATE",
            },
        )

        # 轨迹：提交步骤日志（流程中心步骤条数据源）
        from .trace import log_step
        await log_step(
            conn, one_id=one_id, task_no=app_no, step_type="SUBMIT",
            node_code="APPLY", node_name="创建客户申请",
            action_type="SUBMIT", action_name="提交申请",
            operator_name=applicant, operator_role="BU_USER",
            from_status="-", to_status="pending",
        )

        # 轨迹：提交动作（与 Java CmdCustomerServiceImpl 一致——审批轨迹时间线与
        # 流程跟踪「提交业务申请」节点的历史记录数据源）
        from .trace import log_action
        await log_action(
            conn, task_id=task_id, task_no=app_no, one_id=one_id,
            action_type="SUBMIT", action_name="提交申请",
            from_node_code="APPLY", to_node_code="APPLY",
            operator_name=applicant, operator_role="BU_USER",
            opinion=payload.remark if getattr(payload, "remark", None) else "",
        )

        # 3.1) Duplicate Check 命中 → 生成疑似重复治理任务（对齐 Java createDuplicateTask：
        #      同BU → SUSPECT；跨BU → CROSS_BU 升 GC）。Exact/Suspected 都由治理者决定关联或新建。
        gov_task_code = None
        if (dup["duplicate_flag"] == "Y" and dup["peers"]) or cross_peers:
            gov_task_code = await seq.gen_code(conn, "GOV-", 4, "GOVERNANCE")
            gid = await seq.next_id(conn, "cmd_governance_task")
            await conn.execute(table("cmd_governance_task").insert().values(
                id=gid, task_code=gov_task_code,
                task_type="CROSS_BU" if cross_bu else "SUSPECT",
                biz_type="CUSTOMER_CREATE", biz_id=app_no,
                one_id=one_id, subject=payload.legal_name,
                bu_scope=payload.bu_scope or "",
                cross_bu_flag="Y" if cross_bu else "N",
                risk_level="High" if cross_bu else "Medium",
                match_state=dup["match_state"],
                status="OPEN", evidence_json=evidence,
                del_flag="0", create_by=0, create_time=datetime.now(),
            ))

        # 4) 回执：把 Duplicate Check 结论回流给提交人（对齐 Java fillDuplicateReceipt）。
        #    此前只返回 app_no/one_id/match_state，前端《查重回执》的申请编号/当前节点/
        #    匹配结论/命中记录全部是「—」，且疑似匹配只在审批端可见——提交人彻底盲了。
        matched = dup["peers"][0] if dup["peers"] else None
        match_state = dup["match_state"]
        match_state_name = {"EXACT": "精准重复", "SUSPECTED": "疑似重复"}.get(match_state, "新客户")

        # 同主体在途申请条数：按统一社会信用代码统计，含本次刚提交的这条
        in_flight_count = 1
        if payload.credit_code:
            app_t = table("cmd_customer_application")
            in_flight_count = (await conn.execute(
                select(func.count()).select_from(app_t)
                .where(app_t.c.credit_code == payload.credit_code)
                .where(app_t.c.status.in_(["pending", "returned"]))
                .where(app_t.c.del_flag == "0")
            )).scalar() or 0

        receipt = {
            "customer_id": app_id,
            "one_id": one_id,
            "task_no": app_no,
            "app_no": app_no,
            "scene_code": "CUSTOMER_CREATE",
            "status": "pending",
            "task_status": "PENDING",
            "current_node_code": "BU_REVIEW",
            "current_node_name": "BU初审",
            "assignee_role": "BU_STEWARD",
            "risk_level": risk,
            "match_state": match_state,
            "match_state_name": match_state_name,
            "duplicate_flag": dup["duplicate_flag"],
            "cross_bu": cross_bu,
            "in_flight_count": int(in_flight_count),
        }

        if matched is None:
            receipt["matched_in_flight"] = False
            receipt["duplicate_hint"] = (
                f"未命中既有主档，但库中同一统一社会信用代码下另有 {in_flight_count - 1} 条尚未审批完成的申请，"
                "请到「治理与审批」确认是否属于同一家客户。"
                if in_flight_count > 1 else "未命中既有主档，按新客户进入审批。"
            )
        else:
            receipt.update({
                "matched_one_id": matched["one_id"],
                "matched_name": matched.get("legal_name"),
                "matched_credit_code": matched.get("credit_code"),
                "matched_bu_scope": matched.get("bu_scope"),
                "matched_status": matched.get("status"),
                "matched_in_flight": bool(matched.get("in_flight")),
            })
            if matched.get("in_flight"):
                # 在途候选：补对方申请编号与当前节点，提交人据此知道「该找谁、卡在哪个环节」
                receipt["matched_task_no"] = matched.get("app_no")
                task_t = table("cmd_approval_task")
                peer_task = (await conn.execute(
                    select(task_t.c.current_node_name, task_t.c.submit_time)
                    .where(task_t.c.one_id == matched["one_id"])
                    .where(task_t.c.status == "PENDING")
                    .where(task_t.c.del_flag == "0")
                    .order_by(desc(task_t.c.submit_time))
                    .limit(1)
                )).first()
                if peer_task is not None:
                    receipt["matched_node_name"] = peer_task._mapping["current_node_name"]
                    st = peer_task._mapping["submit_time"]
                    receipt["matched_submit_time"] = st.isoformat() if st else None
            if matched.get("in_flight"):
                hint = (f"系统判定为「{match_state_name}」：与 {matched['one_id']}"
                        f"（{matched.get('legal_name') or ''}） 高度相似，且该记录仍是一条尚未审批完成的「在途申请」")
                if receipt.get("matched_task_no"):
                    hint += f"（申请编号 {receipt['matched_task_no']}"
                    if receipt.get("matched_node_name"):
                        hint += f"，当前节点 {receipt['matched_node_name']}"
                    hint += "）"
                hint += "。请到「治理与审批」跟踪两条待办，由 Data Steward 判定是否合并到同一 One ID——不要重复提交第三次。"
            else:
                hint = (f"系统判定为「{match_state_name}」：与 {matched['one_id']}"
                        f"（{matched.get('legal_name') or ''}） 高度相似，该记录已是已发布主档。"
                        f"批准后将按合并流程把本条关联到 {matched['one_id']}。")
                if gov_task_code:
                    hint += f" 已生成疑似重复治理任务 {gov_task_code}。"
            receipt["duplicate_hint"] = hint

        receipt["peers"] = dup["peers"]

    return receipt


async def resubmit_application(app_no: str, payload, actor: str = "Business User") -> dict:
    """被退回申请的「修改重报」（总设计两级审批口径：BU 初审退回 → 申请人修改 → 重进 BU 初审）。

    - 仅 status=returned 的申请可重报；仅更新前端传入的非空字段；
    - 用合并后的关键字段重新查重 / 重打 DQ 分（改对了信用代码，重复状态要跟着变）；
    - 同步重开审批任务行（RETURNED → PENDING，节点拉回 BU Scope 初审），
      并把流程实例镜像从 EndEvent 拉回 BU_REVIEW（复用退回修复的 reset_instance_node）。
    """
    import json as _json
    engine = get_engine()
    async with engine.begin() as conn:
        app_t = table("cmd_customer_application")
        app_row = (await conn.execute(
            select(app_t).where(app_t.c.app_no == app_no, app_t.c.del_flag == "0")
        )).mappings().first()
        if app_row is None:
            raise ValueError("申请单不存在")
        if (app_row["status"] or "") != "returned":
            raise ValueError(f"仅被退回的申请可修改重报（当前状态：{app_row['status']}）")

        updates: dict = {}
        for f in ("legal_name", "legal_name_en", "credit_code", "short_name", "address",
                  "contact_name", "contact_phone", "contact_email"):
            v = getattr(payload, f, None)
            if v is not None and str(v).strip():
                updates[f] = str(v).strip()
        legal_name = updates.get("legal_name") or app_row["legal_name"]
        if not (legal_name or "").strip():
            raise ValueError("客户法定名称不能为空")
        credit_code = updates.get("credit_code") or app_row["credit_code"]
        address = updates.get("address") or app_row["address"]
        bu_scope = app_row["bu_scope"]

        # 重跑查重 / 跨BU 判定 / DQ 评分（与 submit_customer 同口径）
        dup = await duplicate_check(conn, credit_code, legal_name, address, scene="CREATE")
        cross_peers = await cross_bu_conflicts(conn, credit_code, bu_scope,
                                               exclude_one_id=app_row["one_id"])
        cross_bu = bool(cross_peers) or (
            dup["duplicate_flag"] == "Y"
            and any((p.get("bu_scope") or "") != (bu_scope or "") for p in dup["peers"]))
        risk = "High" if (dup["duplicate_flag"] == "Y" or cross_bu) else "Medium"
        dq_value, dq_grade = dq_score_for({
            "credit_code": credit_code, "address": address,
            "province": app_row["province"], "city": app_row["city"],
            "contact_name": updates.get("contact_name") or app_row["contact_name"],
            "contact_phone": updates.get("contact_phone") or app_row["contact_phone"],
        })

        # 命中存量时重写治理证据（键与 submit_customer 对齐，审批弹窗按这些键配对渲染）
        evidence = None
        if dup["duplicate_flag"] == "Y" and dup["peers"]:
            flights = [p for p in dup["peers"] if p.get("source") == "IN_FLIGHT"]
            top = dup["peers"][0]
            evidence = {
                "候选One ID": "、".join(
                    f"{p['one_id']} · {p.get('legal_name') or ''}" for p in dup["peers"]),
                "匹配状态": dup["match_state"],
                "命中来源": "在途申请" if flights else "已发布主档",
                "在途申请": "是" if flights else "否",
                "申请名称": legal_name or "",
                "信用代码": credit_code or "",
                "注册地址": address or "",
                "申请BU": bu_scope or "",
                "候选名称": top.get("legal_name") or "",
                "候选信用代码": top.get("credit_code") or "",
                "候选经营地址": top.get("address") or "",
                "匹配得分": f"{dup.get('score') or 0:.0f}",
                "查重依据": ("重报后复检：主依据（信用代码 / 经营地址）命中 "
                             f"{payload.credit_code or credit_code or ''}")
                            if credit_code else "重报后复检：名称相似命中",
                "匹配口径": dup.get("basis") or "",
                "跨BU": "是" if cross_bu else "否",
                "跨BU命中记录": "；".join(
                    f"{p['one_id']} · {p.get('legal_name') or ''} · {p.get('bu_scope') or ''}"
                    for p in cross_peers) or "无",
            }

        # 1) 申请单：改字段 + 状态回 pending + 重复/DQ 快照刷新
        await conn.execute(app_t.update().where(app_t.c.app_no == app_no).values(
            **updates, status="pending", match_state=dup["match_state"],
            duplicate_flag=dup["duplicate_flag"], dq_score=dq_value, dq_grade=dq_grade,
            update_time=datetime.now()))
        # 2) 审批任务行：重开到 BU Scope 初审（BU 队列可见）
        await conn.execute(table("cmd_approval_task").update()
                           .where(table("cmd_approval_task").c.task_no == app_no)
                           .values(status="PENDING", scope="BU",
                                   current_node_code="BU_REVIEW", current_node_name="BU初审",
                                   assignee_role="BU_STEWARD", risk_level=risk,
                                   duplicate_state=dup["match_state"],
                                   cross_bu_flag="Y" if cross_bu else "N",
                                   dq_score=dq_value,
                                   evidence_json=_json.dumps(evidence, ensure_ascii=False)
                                   if evidence else None,
                                   submit_time=datetime.now()))
        # 3) 流程实例镜像：BPMN 无 return 分支时实例已在 EndEvent/COMPLETED，
        #    重报等于把流程拉回 BU_REVIEW 等待点（与 reset_instance_node 同一机制）
        await reset_instance_node(app_no, "BU_REVIEW")
        # 4) 轨迹：时间线 + 步骤条都要体现「修改重报」这一步
        from .trace import log_action, log_step
        remark = (getattr(payload, "remark", None) or "").strip() or "修改重报"
        applicant = ((getattr(payload, "applicant_name", None) or "").strip() or actor)
        await log_action(
            conn, task_id=app_row["id"], task_no=app_no, one_id=app_row["one_id"],
            action_type="RESUBMIT", action_name=remark,
            from_node_code="APPLY", to_node_code="BU_REVIEW",
            operator_name=applicant, operator_role="BU_USER", opinion=remark,
        )
        await log_step(
            conn, one_id=app_row["one_id"], task_no=app_no,
            step_type="BUSINESS", node_code="BU_REVIEW", node_name="BU Scope 初审",
            action_type="RESUBMIT", action_name=remark,
            operator_name=applicant, operator_role="BU_USER",
            from_status="RETURNED", to_status="PENDING", opinion=remark,
        )

        return {"appNo": app_no, "oneId": app_row["one_id"], "status": "pending",
                "currentNodeName": "BU Scope 初审", "assigneeRole": "BU_STEWARD",
                "matchState": dup["match_state"], "duplicateFlag": dup["duplicate_flag"],
                "dqScore": dq_value, "dqGrade": dq_grade, "riskLevel": risk}


async def publish_customer(conn, app_row, outcome: str, decision: str = "") -> Optional[str]:
    """审批通过（outcome=approved）后发布主档；驳回则仅更新申请状态。

    decision：审批端动作键（merge/create_new/exclude 等）——
    - create_new / exclude：治理者判定「排除重复·创建新主档」，不链路到既有主档；
    - 其余（含 merge）：EXACT 命中时 merged_to 关联存量主档首个候选。
    """
    if outcome == "rejected":
        await conn.execute(
            table("cmd_customer_application").update()
            .where(table("cmd_customer_application").c.app_no == app_row["app_no"])
            .values(status="rejected", approved_time=datetime.now())
        )
        return None

    # 重复命中：链路到既有主档；否则新建黄金记录。
    # 注意：提交时写入的 match_state 只是当时的快照，审批期间存量可能已变化
    # （例：同主体的前一单先被批准发布），因此发布前必须按设计口径重新查重一次。
    one_id = app_row["one_id"]
    merged_to = None
    forced_reason = ""
    fresh = await duplicate_check(conn, app_row["credit_code"], app_row["legal_name"],
                                  app_row.get("address"), scene="CREATE")
    same_code_master = None
    if app_row["credit_code"]:
        cust_t = table("cmd_customer")
        same_code_master = (await conn.execute(
            select(cust_t.c.one_id)
            .where(cust_t.c.credit_code == app_row["credit_code"])
            .where(cust_t.c.status == "active")
            .where(cust_t.c.del_flag == "0")
            .order_by(desc(cust_t.c.create_time))
            .limit(1)
        )).first()
    if same_code_master is not None and same_code_master._mapping["one_id"] != one_id:
        # 统一社会信用代码是国家唯一标识：同码已有主档时绝不新建第二条黄金记录，
        # 否则「两条申请都批准」会产出同码双主档，直接破掉设计文档「One ID 稳定」的硬约束。
        merged_to = same_code_master._mapping["one_id"]
        if (decision or "").lower() in ("create_new", "exclude"):
            forced_reason = ("审批判定为「排除重复·继续新建」，但库中已存在同一统一社会信用代码的"
                             "已发布主档，按 One ID 唯一性强制关联，未新建黄金记录")
    elif (decision or "").lower() not in ("create_new", "exclude"):
        # 治理者选择「关联 / 合并」：命中已发布主档即链路过去（含按地址判出的 EXACT/SUSPECTED）
        master_peers = [p for p in fresh["peers"] if p.get("source") == "MASTER"]
        if master_peers and master_peers[0]["one_id"] != one_id:
            merged_to = master_peers[0]["one_id"]

    # 幂等守卫：one_id 已有主档时先分辨「是不是同一主体」，不能见占用就吞——
    #   · 同一主体（信用代码一致；申请无码时退而比对法定名称）：重复审批/重放，
    #     幂等返回即可，否则撞唯一键 500（真实案例：升级误发布后 GC 再点「退回BU」报错）；
    #   · 不同主体：one_id 被无关记录占用（典型：提交时预分配的号段随后被演示种子
    #     数据占用，如 AP-20260923-0001 预分 GC-00000002、种子库随后灌入苏州新视野）。
    #     若照旧吞掉，申请单显示「已批准」、主档里却找不到这家客户，治理者
    #     「排除重复·继续新建」的决策被静默丢弃——必须重新分配 One ID 继续发布。
    one_id_reassign_note = ""
    existing = (await conn.execute(
        select(table("cmd_customer").c.credit_code, table("cmd_customer").c.legal_name)
        .where(table("cmd_customer").c.one_id == one_id)
    )).first()
    if existing is not None and not merged_to:
        ex = existing._mapping
        same_entity = (
            (app_row["credit_code"] and ex["credit_code"] == app_row["credit_code"])
            or (not app_row["credit_code"] and ex["legal_name"] == app_row["legal_name"])
        )
        if same_entity:
            await conn.execute(
                table("cmd_customer_application").update()
                .where(table("cmd_customer_application").c.app_no == app_row["app_no"])
                .values(status="approved", effective_from=datetime.now(), approved_time=datetime.now())
            )
            return one_id
        one_id_reassign_note = (
            f"提交时预分配的 One ID {one_id} 已被其他主体"
            f"（{ex['legal_name'] or '未知主体'}）占用，发布时重新分配为 ")
        one_id = await seq.gen_one_id(conn)
        one_id_reassign_note += one_id

    if merged_to:
        # 关联到既有主档：本单不新建黄金记录（设计文档：Exact / 治理后关联已有 One ID）
        vals = {
            "status": "approved",
            "merged_to_one_id": merged_to,
            "effective_from": datetime.now(),
            "approved_time": datetime.now(),
        }
        if forced_reason:
            vals["remark"] = forced_reason
        await conn.execute(
            table("cmd_customer_application").update()
            .where(table("cmd_customer_application").c.app_no == app_row["app_no"])
            .values(**vals)
        )
        return merged_to

    # 同码还有更早提交的在途申请（本条是后提交却先被批准）→ 在本单备注留痕，
    # 提示治理者跟进前一单的处置，避免同一主体留下两条「都已批准」的记录
    earlier_in_flight = None
    if app_row["credit_code"]:
        app_t = table("cmd_customer_application")
        earlier_in_flight = (await conn.execute(
            select(app_t.c.app_no)
            .where(app_t.c.credit_code == app_row["credit_code"])
            .where(app_t.c.status.in_(["pending", "returned"]))
            .where(app_t.c.del_flag == "0")
            .where(app_t.c.id < app_row["id"])
            .order_by(app_t.c.id)
            .limit(1)
        )).first()

    cust_id = await seq.next_id(conn, "cmd_customer")
    # 发布时把 DQ 分值带进黄金记录（申请单上已有则沿用，历史单据为空则按同一规则现算），
    # 保证主档列表「DQ 分数」列 / DQ 统计 / 客户详情三处口径一致。
    dq_value, dq_grade = dq_score_for(dict(app_row))
    await conn.execute(table("cmd_customer").insert().values(
        id=cust_id, one_id=one_id, legal_name=app_row["legal_name"],
        legal_name_en=app_row["legal_name_en"], short_name=app_row["short_name"],
        credit_code=app_row["credit_code"], tax_no=app_row["tax_no"],
        customer_type=app_row["customer_type"], customer_level=app_row["customer_level"],
        product_line=app_row["product_line"], bu_scope=app_row["bu_scope"],
        gc_scope_flag=app_row["gc_scope_flag"], country=app_row["country"],
        province=app_row["province"], city=app_row["city"], address=app_row["address"],
        payer_id=app_row["payer_id"], contact_name=app_row["contact_name"],
        contact_phone=app_row["contact_phone"], contact_email=app_row["contact_email"],
        status="active", source_system=app_row["source_system"],
        match_state=app_row["match_state"], duplicate_flag=app_row["duplicate_flag"],
        dq_score=dq_value, dq_grade=dq_grade,
        merged_to_one_id=merged_to, del_flag="0", approved_by=0, approved_time=datetime.now(),
        create_by=0, create_time=datetime.now(),
    ))
    vals = {"status": "approved", "effective_from": datetime.now(),
            "approved_time": datetime.now(), "dq_score": dq_value, "dq_grade": dq_grade,
            # one_id 同步回写申请单：正常场景等于原值；号段被占用重新分配时
            # 让申请单指向真正发布出去的那条主档
            "one_id": one_id}
    remark_parts = []
    if one_id_reassign_note:
        remark_parts.append(one_id_reassign_note)
    if earlier_in_flight is not None:
        remark_parts.append(f"本条已发布为 One ID {one_id}；同信用代码仍有更早提交的在途申请 "
                            f"{earlier_in_flight._mapping['app_no']} 待处置，请跟进确认是否同一主体")
    if remark_parts:
        vals["remark"] = "；".join(remark_parts)
    await conn.execute(
        table("cmd_customer_application").update()
        .where(table("cmd_customer_application").c.app_no == app_row["app_no"])
        .values(**vals)
    )
    # 疑似重复但暂时无主档可关联（命中的是仍在途的另一单）：
    # 发布后必须留下治理线索，否则库里出现「duplicate_flag=Y 且 mergedToOneId 为空」的悬空态，
    # 既不知道跟谁重复、也没人跟进（报告中的「SUSPECTED批准后未建立合并关系」）。
    if (app_row.get("duplicate_flag") or "N") == "Y" and merged_to is None:
        await ensure_suspect_governance(conn, app_row, one_id)
    return one_id


async def ensure_suspect_governance(conn, app_row, one_id: str) -> Optional[str]:
    """为「疑似重复但未建立关联」的已发布客户登记一条治理任务（幂等）。

    治理者在「治理与审批 → 治理任务」里能直接看到：跟哪个 One ID 疑似重复、
    对方是本 BU 还是跨 BU、当前卡在哪个节点，从而决定「关联已有 / 确认新建 / 退回修复」。
    """
    if app_row.get("merged_to_one_id"):
        return None
    gov = table("cmd_governance_task")
    exist = (await conn.execute(
        select(gov.c.task_code).where(gov.c.one_id == one_id)
        .where(gov.c.status == "OPEN").where(gov.c.del_flag == "0")
    )).first()
    if exist is not None:
        return exist._mapping["task_code"]
    code = (app_row.get("credit_code") or "").strip()
    peers = await cross_bu_conflicts(conn, code, app_row.get("bu_scope"),
                                     exclude_one_id=one_id) if code else []
    conflict = ("；".join(f"{p['one_id']} · {p.get('legal_name') or ''} · {p.get('bu_scope') or ''}"
                          for p in peers) or "同码在途申请（对方尚未发布主档）")
    task_code = await seq.gen_code(conn, "GOV-", 4, "GOVERNANCE")
    gid = await seq.next_id(conn, "cmd_governance_task")
    await conn.execute(gov.insert().values(
        id=gid, task_code=task_code,
        task_type="CROSS_BU" if peers else "SUSPECT",
        biz_type="CUSTOMER_CREATE", biz_id=app_row.get("app_no"),
        one_id=one_id, subject=app_row.get("legal_name"),
        bu_scope=app_row.get("bu_scope") or "",
        cross_bu_flag="Y" if peers else "N",
        risk_level="High" if peers else "Medium",
        match_state=app_row.get("match_state") or "SUSPECTED",
        status="OPEN",
        evidence_json={"匹配状态": app_row.get("match_state") or "SUSPECTED",
                       "命中冲突": conflict,
                       "说明": "疑似重复已发布但当时无可关联主档，需人工确认合并目标或确认新建"},
        del_flag="0", create_by=0, create_time=datetime.now(),
    ))
    return task_code


MATCH_EXCLUDED_STATUS = ("merged", "rejected", "draft")


async def _dup_enrich_customers(conn, rows: list[dict]) -> None:
    """Java enrichDuplicatePeers 口径：按信用代码整组算重复组 + 在途申请摘要。"""
    if not rows:
        return
    codes = sorted({r["credit_code"] for r in rows if r.get("credit_code")})
    cust = table("cmd_customer")
    app = table("cmd_customer_application")
    task = table("cmd_approval_task")

    grouped: dict[str, list[dict]] = {}
    if codes:
        peers = (await conn.execute(
            select(cust).where(cust.c.credit_code.in_(codes),
                               cust.c.status.notin_(MATCH_EXCLUDED_STATUS))
        )).mappings().all()
        for p in peers:
            grouped.setdefault(p["credit_code"], []).append(dict(p))
    grouped_apps: dict[str, list[dict]] = {}
    if codes:
        apps = (await conn.execute(
            select(app).where(app.c.credit_code.in_(codes),
                              app.c.status.in_(["pending", "returned"]))
        )).mappings().all()
        for a in apps:
            grouped_apps.setdefault(a["credit_code"], []).append(dict(a))

    # One ID → 最新审批任务（补当前节点 + 申请编号）
    peer_one_ids = [c["one_id"] for grp in list(grouped.values()) + list(grouped_apps.values())
                    for c in grp if c.get("one_id")]
    pending_tasks: dict[str, dict] = {}
    if peer_one_ids:
        tasks = (await conn.execute(
            select(task).where(task.c.one_id.in_(peer_one_ids)).order_by(task.c.id.desc())
        )).mappings().all()
        for t in tasks:
            pending_tasks.setdefault(t["one_id"], dict(t))

    for row in rows:
        code = row.get("credit_code")
        group = grouped.get(code, []) if code else []
        apps = grouped_apps.get(code, []) if code else []
        row["dup_group_size"] = max(1, len(group) + len(apps))
        row["dup_in_flight_count"] = len(apps)
        parts: list[str] = []
        for other in apps:
            sb = other.get("one_id") or "-"
            t = pending_tasks.get(other.get("one_id"))
            if t and t.get("current_node_name"):
                sb += f"（{t['current_node_name']}）"
            if other.get("app_no"):
                sb += f" 申请编号 {other['app_no']}"
            parts.append(sb + " · 在途申请")
        for other in group:
            if other.get("one_id") == row.get("one_id"):
                continue
            t = pending_tasks.get(other.get("one_id"))
            sb = (other.get("one_id") or "-") + " · " + (other.get("status") or "")
            if t and t.get("current_node_name"):
                sb += f"（{t['current_node_name']}）"
            if t and t.get("task_no"):
                sb += f" 申请编号 {t['task_no']}"
            parts.append(sb)
        row["dup_peer_summary"] = (
            "同一统一社会信用代码下另有 " + str(len(parts)) + " 条记录：" + "；".join(parts)
        ) if parts else ""


async def list_customers(bu_scope: Optional[str] = None, status: Optional[str] = None,
                         keyword: Optional[str] = None, page: int = 1, size: int = 20):
    engine = get_engine()
    cust = table("cmd_customer")
    conds = [cust.c.del_flag == "0"]
    if bu_scope:
        conds.append(cust.c.bu_scope == bu_scope)
    if status:
        conds.append(cust.c.status == status)
    if keyword:
        like = f"%{keyword}%"
        conds.append(cust.c.legal_name.like(like) | cust.c.short_name.like(like) |
                     cust.c.one_id.like(like) | cust.c.credit_code.like(like) |
                     cust.c.payer_id.like(like))

    conn = await engine.connect()
    try:
        rows = (await conn.execute(
            select(cust).where(*conds).order_by(cust.c.id.desc())
            .limit(size).offset((page - 1) * size))).mappings().all()
        total = (await conn.execute(
            select(func.count()).select_from(cust).where(*conds))).scalar() or 0
        result = [dict(r) for r in rows]
        await _dup_enrich_customers(conn, result)
    finally:
        await conn.close()
    return {"total": int(total), "rows": result}


async def customer_stats(bu_scope: Optional[str] = None, status: Optional[str] = None,
                         keyword: Optional[str] = None, customer_type: Optional[str] = None):
    """Java selectCustomerStats 口径：与列表共用条件，pendingCount = 在途申请数。"""
    engine = get_engine()
    cust = table("cmd_customer")
    app = table("cmd_customer_application")
    conds = [cust.c.del_flag == "0"]
    if bu_scope:
        conds.append(cust.c.bu_scope == bu_scope)
    if status:
        conds.append(cust.c.status == status)
    if customer_type:
        conds.append(cust.c.customer_type == customer_type)
    if keyword:
        like = f"%{keyword}%"
        conds.append(cust.c.legal_name.like(like) | cust.c.short_name.like(like) |
                     cust.c.one_id.like(like) | cust.c.credit_code.like(like) |
                     cust.c.payer_id.like(like))

    conn = await engine.connect()
    try:
        rows = (await conn.execute(select(cust).where(*conds))).mappings().all()
        app_conds = [app.c.del_flag == "0", app.c.status.in_(["pending", "returned"])]
        if bu_scope:
            app_conds.append(app.c.bu_scope == bu_scope)
        if keyword:
            like = f"%{keyword}%"
            app_conds.append(app.c.legal_name.like(like) | app.c.one_id.like(like) |
                             app.c.credit_code.like(like))
        pending_count = (await conn.execute(
            select(func.count()).select_from(app).where(*app_conds))).scalar() or 0
    finally:
        await conn.close()

    active = cross_bu = dup = scored = 0
    dq_sum = 0.0
    for r in rows:
        if r["status"] == "active":
            active += 1
        if r.get("gc_scope_flag") == "Y":
            cross_bu += 1
        if r.get("duplicate_flag") == "Y":
            dup += 1
        dq = r.get("dq_score") or 0
        if dq > 0:
            dq_sum += float(dq)
            scored += 1
    return {
        "total": len(rows), "activeCount": active, "pendingCount": int(pending_count),
        "crossBuCount": cross_bu, "duplicateCount": dup,
        "avgDqScore": round(dq_sum / scored) if scored else 0,
    }


async def list_applications(status: Optional[str] = None, keyword: Optional[str] = None,
                            page: int = 1, size: int = 20):
    """申请单列表：toApplicationVO 契约（含 taskNo/taskStatus/currentNodeName/重复组富化）。"""
    engine = get_engine()
    app = table("cmd_customer_application")
    task = table("cmd_approval_task")
    conds = [app.c.del_flag == "0"]
    if status:
        conds.append(app.c.status == status)
    if keyword:
        like = f"%{keyword}%"
        conds.append(app.c.legal_name.like(like) | app.c.one_id.like(like) |
                     app.c.credit_code.like(like) | app.c.app_no.like(like))
    conn = await engine.connect()
    try:
        rows = [dict(r) for r in (await conn.execute(
            select(app).where(*conds).order_by(app.c.id.desc())
            .limit(size).offset((page - 1) * size))).mappings().all()]
        total = (await conn.execute(
            select(func.count()).select_from(app).where(*conds))).scalar() or 0
        one_ids = [r["one_id"] for r in rows if r.get("one_id")]
        tasks: dict[str, dict] = {}
        if one_ids:
            for t in (await conn.execute(
                select(task).where(task.c.one_id.in_(one_ids)).order_by(task.c.id.desc())
            )).mappings().all():
                tasks.setdefault(t["one_id"], dict(t))
        # 主档状态兜底（存量申请可能已发布）
        cust = table("cmd_customer")
        cust_map: dict[str, str] = {}
        if one_ids:
            for c in (await conn.execute(
                select(cust.c.one_id, cust.c.status).where(cust.c.one_id.in_(one_ids))
            )).mappings().all():
                cust_map[c["one_id"]] = c["status"]
    finally:
        await conn.close()

    for r in rows:
        t = tasks.get(r.get("one_id"))
        if t:
            r["task_no"] = t.get("task_no")
            r["task_status"] = t.get("status")
            r["current_node_name"] = t.get("current_node_name")
        # 主档已发布则行状态对齐主档（Java 口径：申请态与主档态分离展示）
        c_status = cust_map.get(r.get("one_id"))
        if c_status and r.get("status") == "approved":
            r["flow_status"] = "PUBLISHED"
        # 重复组富化（复用主档口径）
        await _dup_enrich_single(r)
    return {"total": int(total), "rows": rows}


async def _dup_enrich_single(row: dict) -> None:
    """申请单行的重复组富化（单行版，查同信用代码分组）。"""
    engine = get_engine()
    code = row.get("credit_code")
    row.setdefault("dup_group_size", 1)
    row.setdefault("dup_in_flight_count", 0)
    row.setdefault("dup_peer_summary", "")
    if not code:
        return
    conn = await engine.connect()
    try:
        cust = table("cmd_customer")
        app = table("cmd_customer_application")
        peers = (await conn.execute(
            select(cust).where(cust.c.credit_code == code,
                               cust.c.status.notin_(MATCH_EXCLUDED_STATUS))
        )).mappings().all()
        apps = (await conn.execute(
            select(app).where(app.c.credit_code == code,
                              app.c.status.in_(["pending", "returned"]))
        )).mappings().all()
    finally:
        await conn.close()
    row["dup_group_size"] = max(1, len(peers) + len(apps))
    parts = []
    for a in apps:
        if a.get("one_id") == row.get("one_id"):
            continue
        sb = (a.get("one_id") or "-") + " · 在途申请"
        if a.get("app_no"):
            sb += f" 申请编号 {a['app_no']}"
        parts.append(sb)
    row["dup_in_flight_count"] = len(parts)
    if parts:
        row["dup_peer_summary"] = "同一统一社会信用代码下另有 " + str(len(parts)) + " 条在途申请：" + "；".join(parts)

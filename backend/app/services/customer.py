"""客户主档服务：提交新建申请 → 落 cmd_customer_application + cmd_approval_task → 启动 SpiffWorkflow；
审批通过（流程 END）后发布为 cmd_customer 黄金记录。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, func, desc

from ..core.db import get_engine, table
from ..services import sequence as seq
from ..services.duplicate import duplicate_check
from ..workflow.engine import start_instance


async def submit_customer(payload, actor: str = "demo") -> dict:
    engine = get_engine()
    async with engine.begin() as conn:
        one_id = await seq.gen_one_id(conn)
        app_no = await seq.gen_app_no(conn)
        # 查重对齐 Java matchExisting：信用代码 → EXACT；名称（规范化相等或 Dice≥0.85）→ SUSPECTED；
        # 同信用代码在途申请 → SUSPECTED（上一单未审完时不判 NEW）
        dup = await duplicate_check(conn, payload.credit_code, payload.legal_name)
        # 跨BU 判定对齐 Java：服务端比较命中主档 BU 与申请 BU（前端 crossBu 仅作覆盖）
        cross_bu = bool(payload.cross_bu)
        if not cross_bu and dup["duplicate_flag"] == "Y" and dup["peers"]:
            peer_bus = (await conn.execute(
                select(table("cmd_customer").c.bu_scope).where(
                    table("cmd_customer").c.one_id.in_([p["one_id"] for p in dup["peers"]])
                ))).all()
            cross_bu = any((r._mapping["bu_scope"] or "") != (payload.bu_scope or "")
                           for r in peer_bus)
        risk = "High" if dup["duplicate_flag"] == "Y" else "Medium"

        # 命中存量时写入治理证据（含「候选One ID」键）——
        # 审批端 _is_duplicate_link_approval 依据该键渲染「关联已有/创建新主档」决策按钮组
        evidence = None
        if dup["duplicate_flag"] == "Y" and dup["peers"]:
            evidence = {
                "候选One ID": "、".join(
                    f"{p['one_id']} · {p.get('legal_name') or ''}" for p in dup["peers"]),
                "匹配状态": dup["match_state"],
                "查重依据": f"统一社会信用代码 {payload.credit_code} 命中存量主档",
                "跨BU": "是" if cross_bu else "否",
            }

        app_id = await seq.next_id(conn, "cmd_customer_application")
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
            duplicate_flag=dup["duplicate_flag"], del_flag="0", create_by=0, create_time=datetime.now(),
        ))

        task_id = await seq.next_id(conn, "cmd_approval_task")
        await conn.execute(table("cmd_approval_task").insert().values(
            id=task_id, task_no=app_no, task_category="APPROVAL",
            biz_type="CUSTOMER_CREATE", biz_id=one_id, biz_title=payload.legal_name,
            one_id=one_id, scene_code="CUSTOMER_CREATE", bu_scope=payload.bu_scope,
            scope="BU", current_node_code="BU_REVIEW", current_node_name="BU初审",
            assignee_role="BU_STEWARD", status="PENDING", risk_level=risk,
            duplicate_state=dup["match_state"], cross_bu_flag="Y" if cross_bu else "N",
            evidence_json=evidence,
            submit_time=datetime.now(), del_flag="0", create_by=0, create_time=datetime.now(),
        ))

        await start_instance(
            scene_code="CUSTOMER_CREATE", biz_type="CUSTOMER_CREATE", biz_no=app_no,
            variables={
                "taskNo": app_no, "bizType": "CUSTOMER_CREATE", "oneId": one_id,
                "buScope": payload.bu_scope or "", "crossBu": cross_bu,
                "riskLevel": risk, "duplicateState": dup["match_state"],
                "dqScore": None, "sceneCode": "CUSTOMER_CREATE",
            },
        )

        # 轨迹：提交步骤日志（流程中心步骤条数据源）
        from .trace import log_step
        await log_step(
            conn, one_id=one_id, task_no=app_no, step_type="SUBMIT",
            node_code="APPLY", node_name="创建客户申请",
            action_type="SUBMIT", action_name="提交申请",
            operator_name="applicant", operator_role="BU_USER",
            from_status="-", to_status="pending",
        )

        # 轨迹：提交动作（与 Java CmdCustomerServiceImpl 一致——审批轨迹时间线与
        # 流程跟踪「提交业务申请」节点的历史记录数据源）
        from .trace import log_action
        await log_action(
            conn, task_id=task_id, task_no=app_no, one_id=one_id,
            action_type="SUBMIT", action_name="提交申请",
            from_node_code="APPLY", to_node_code="APPLY",
            operator_name="applicant", operator_role="BU_USER",
            opinion=payload.remark if getattr(payload, "remark", None) else "",
        )

        # 3.1) Duplicate Check 命中 → 生成疑似重复治理任务（对齐 Java createDuplicateTask：
        #      同BU → SUSPECT；跨BU → CROSS_BU 升 GC）。Exact/Suspected 都由治理者决定关联或新建。
        gov_task_code = None
        if dup["duplicate_flag"] == "Y" and dup["peers"]:
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

    # 重复命中：链路到既有主档；否则新建黄金记录
    one_id = app_row["one_id"]
    merged_to = None
    if ((decision or "").lower() not in ("create_new", "exclude")
            and app_row["duplicate_flag"] == "Y" and app_row["match_state"] == "EXACT"):
        peers = await duplicate_check(conn, app_row["credit_code"])
        if peers["peers"]:
            merged_to = peers["peers"][0]["one_id"]

    # 幂等守卫：one_id 已有主档（如重复审批/重放）不重复 INSERT——
    # 否则撞唯一键直接 500（真实案例：升级误发布后 GC 再点「退回BU」报 Internal Server Error）
    existing = (await conn.execute(
        select(table("cmd_customer").c.id)
        .where(table("cmd_customer").c.one_id == one_id)
    )).first()
    if existing is not None:
        await conn.execute(
            table("cmd_customer_application").update()
            .where(table("cmd_customer_application").c.app_no == app_row["app_no"])
            .values(status="approved", effective_from=datetime.now(), approved_time=datetime.now())
        )
        return one_id

    cust_id = await seq.next_id(conn, "cmd_customer")
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
        merged_to_one_id=merged_to, del_flag="0", approved_by=0, approved_time=datetime.now(),
        create_by=0, create_time=datetime.now(),
    ))
    await conn.execute(
        table("cmd_customer_application").update()
        .where(table("cmd_customer_application").c.app_no == app_row["app_no"])
        .values(status="approved", effective_from=datetime.now(), approved_time=datetime.now())
    )
    return one_id


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

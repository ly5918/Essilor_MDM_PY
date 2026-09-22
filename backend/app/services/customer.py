"""客户主档服务：提交新建申请 → 落 cmd_customer_application + cmd_approval_task → 启动 SpiffWorkflow；
审批通过（流程 END）后发布为 cmd_customer 黄金记录。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, func

from ..core.db import get_engine, table
from ..services import sequence as seq
from ..services.duplicate import duplicate_check
from ..workflow.engine import start_instance


async def submit_customer(payload, actor: str = "demo") -> dict:
    engine = get_engine()
    async with engine.begin() as conn:
        one_id = await seq.gen_one_id(conn)
        app_no = await seq.gen_app_no(conn)
        dup = await duplicate_check(conn, payload.credit_code)
        cross_bu = bool(payload.cross_bu)
        risk = "High" if dup["duplicate_flag"] == "Y" else "Medium"

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

    return {
        "app_no": app_no, "one_id": one_id,
        "match_state": dup["match_state"], "duplicate_flag": dup["duplicate_flag"],
        "cross_bu": cross_bu, "peers": dup["peers"],
    }


async def publish_customer(conn, app_row, outcome: str) -> Optional[str]:
    """审批通过（outcome=approved）后发布主档；驳回则仅更新申请状态。"""
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
    if app_row["duplicate_flag"] == "Y" and app_row["match_state"] == "EXACT":
        peers = await duplicate_check(conn, app_row["credit_code"])
        if peers["peers"]:
            merged_to = peers["peers"][0]["one_id"]

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

"""工作台仪表盘 API — 1:1 对齐 CmdDashboardServiceImpl 统计口径。

统计全部由业务表实时聚合；buScope 为空表示 GC 全局视图。
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import select, func, and_, or_

from ..core.db import get_engine, table
from ..schemas import R

router = APIRouter(prefix="/cmd/dashboard", tags=["仪表盘"])


async def _count(conn, t, *conds) -> int:
    stmt = select(func.count()).select_from(t)
    if conds:
        stmt = stmt.where(*conds)
    return (await conn.execute(stmt)).scalar() or 0


@router.get("/stats")
async def stats(buScope: Optional[str] = Query(None)):
    cust = table("cmd_customer")
    app_t = table("cmd_customer_application")
    task = table("cmd_approval_task")
    gov = table("cmd_governance_task")
    node = table("cmd_hierarchy_node")

    conn = await get_engine().connect()
    try:
        # --- 客户统计（主档表只存已发布 Golden Record） ---
        cust_conds = [cust.c.del_flag == "0"] if hasattr(cust.c, "del_flag") else []
        base = list(cust_conds)
        if buScope:
            base.append(cust.c.bu_scope == buScope)
        customer_total = await _count(conn, cust, *base)
        customer_active = await _count(conn, cust, *base, cust.c.status == "active")
        customer_inactive = await _count(conn, cust, *base, cust.c.status == "inactive")

        # 在途申请 = 申请单表 pending + returned（嵌套 OR 口径）
        app_conds = []
        if buScope:
            app_conds.append(app_t.c.bu_scope == buScope)
        customer_pending = await _count(conn, app_t, *app_conds,
                                        or_(app_t.c.status == "pending", app_t.c.status == "returned"))

        # --- 待办统计 ---
        returned_count = await _count(conn, task, task.c.status == "returned")
        sla_overdue_count = 0
        if hasattr(task.c, "sla_state"):
            sla_overdue_count = await _count(conn, task, task.c.sla_state == "OVERDUE")

        # --- 待办节点分布（PENDING OR RETURNED，按 current_node_name 归组，空入「待分配」） ---
        rows = (await conn.execute(
            select(task.c.current_node_name, func.count()).where(
                or_(task.c.status.in_(["PENDING", "pending"]),
                    task.c.status.in_(["RETURNED", "returned"]))
            ).group_by(task.c.current_node_name)
        )).all()
        pending_by_node: dict = {}
        for name, cnt in rows:
            key = name if name else "待分配"
            pending_by_node[key] = pending_by_node.get(key, 0) + cnt
        pending_by_node = dict(sorted(pending_by_node.items(), key=lambda kv: -kv[1]))

        # --- 治理指标（未闭环 = 非 RESOLVED/CLOSED） ---
        def _gov_conds(ttype):
            return [gov.c.task_type == ttype,
                    gov.c.status != "RESOLVED", gov.c.status != "CLOSED"]

        gov_suspect = await _count(conn, gov, *_gov_conds("SUSPECTED"))
        gov_review = await _count(conn, gov, *_gov_conds("REVIEW"))
        gov_new = await _count(conn, gov, *_gov_conds("NEW"))
        gov_cross_bu = await _count(conn, gov, *_gov_conds("CROSS_BU"))

        # --- 层级节点（口径：已归位上树的节点；「待归位」登记节点不计入，
        #     它们由「客户层级 › 待归位主数据」单独统计，两边互补不重复） ---
        node_conds = [or_(node.c.hierarchy_type.is_(None),
                          node.c.hierarchy_type != "UNASSIGNED")]
        if buScope:
            node_conds.append(node.c.bu_scope == buScope)
        hierarchy_node_count = await _count(conn, node, *node_conds)
    finally:
        await conn.close()

    return R.ok({
        "customerTotal": customer_total,
        "customerActive": customer_active,
        "customerPending": customer_pending,
        "customerInactive": customer_inactive,
        "returnedCount": returned_count,
        "slaOverdueCount": sla_overdue_count,
        "pendingByNode": pending_by_node,
        "govSuspectCount": gov_suspect,
        "govReviewCount": gov_review,
        "govNewCount": gov_new,
        "govCrossBuCount": gov_cross_bu,
        "hierarchyNodeCount": hierarchy_node_count,
    })


@router.get("/notifications")
async def notifications():
    """工作台通知列表（NotificationVO[] 契约：id/title/time/type/read）。"""
    t = table("cmd_notification")
    conn = await get_engine().connect()
    try:
        rows = (await conn.execute(
            t.select().where(t.c.del_flag == "0")
            .order_by(t.c.id.desc()).limit(20))).mappings().all()
    finally:
        await conn.close()
    items = [{
        "id": str(r["id"]),
        "title": r.get("title") or "",
        "time": str(r.get("send_time") or r.get("create_time") or ""),
        "type": r.get("notice_type") or "info",
        "read": (r.get("is_read") == "Y"),
    } for r in rows]
    return R.ok(items)

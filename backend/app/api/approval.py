"""审批队列 / 待办 / 审批动作 API。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import select, func, desc

from ..core.db import get_engine, table, flow_instance_table
from ..schemas import R, ApprovalAction
from ..services import approval as svc

router = APIRouter(prefix="/cmd/approval", tags=["审批"])

# 终态（DONE 页签口径）
FINAL_STATUSES = ("COMPLETED", "REJECTED", "APPROVED", "CANCELLED")


async def _enrich_peer_in_flight(conn, rows: list[dict]) -> None:
    """Java enrichPeerInFlight 口径：同主体（信用代码）其它在途申请条数与摘要。"""
    if not rows:
        return
    one_ids = sorted({r["one_id"] for r in rows if r.get("one_id")})
    for r in rows:
        r["dup_peer_in_flight"] = 0
        r["dup_peer_summary"] = ""
    if not one_ids:
        return
    cust = table("cmd_customer")
    app = table("cmd_customer_application")
    task = table("cmd_approval_task")

    credit_by_one: dict[str, str] = {}
    for c in (await conn.execute(
        select(cust.c.one_id, cust.c.credit_code).where(cust.c.one_id.in_(one_ids))
    )).mappings().all():
        if c["credit_code"]:
            credit_by_one[c["one_id"]] = c["credit_code"]
    for a in (await conn.execute(
        select(app.c.one_id, app.c.credit_code).where(app.c.one_id.in_(one_ids))
    )).mappings().all():
        if a["credit_code"]:
            credit_by_one[a["one_id"]] = a["credit_code"]
    codes = sorted(set(credit_by_one.values()))
    if not codes:
        return

    flight_apps = (await conn.execute(
        select(app).where(app.c.credit_code.in_(codes),
                          app.c.status.in_(["pending", "returned"]))
    )).mappings().all()
    peer_one_ids = [a["one_id"] for a in flight_apps if a.get("one_id")]
    pending_tasks: dict[str, dict] = {}
    if peer_one_ids:
        for t in (await conn.execute(
            select(task).where(task.c.one_id.in_(peer_one_ids),
                               task.c.status == "PENDING")
            .order_by(task.c.id.desc())
        )).mappings().all():
            pending_tasks.setdefault(t["one_id"], dict(t))

    for row in rows:
        code = credit_by_one.get(row.get("one_id"))
        if not code:
            continue
        count = 0
        parts: list[str] = []
        for peer in flight_apps:
            if peer["credit_code"] != code or peer.get("one_id") == row.get("one_id"):
                continue
            count += 1
            t = pending_tasks.get(peer.get("one_id"))
            sb = peer.get("one_id") or "-"
            if t and t.get("current_node_name"):
                sb += f"（{t['current_node_name']}）"
            if peer.get("app_no"):
                sb += f" 申请编号 {peer['app_no']}"
            parts.append(sb)
        row["dup_peer_in_flight"] = count
        row["dup_peer_summary"] = (
            "同一统一社会信用代码下另有 " + str(len(parts)) + " 条在途申请：" + "；".join(parts)
        ) if parts else ""


@router.get("/list")
async def list_approval(
    taskCategory: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    buScope: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
):
    """队列口径（与 Java 一致）：
    ALL = PENDING+RETURNED（不按建表分类过滤）；DONE = 终态；RETURNED = 状态 RETURNED；
    其余按 taskCategory 列匹配。"""
    t = table("cmd_approval_task")
    conds = [t.c.del_flag == "0"]
    cat = (taskCategory or "").upper()
    if cat in ("ALL", "DONE", "RETURNED"):
        if cat == "ALL":
            conds.append(t.c.status.in_(["PENDING", "RETURNED"]))
        elif cat == "DONE":
            conds.append(t.c.status.in_(FINAL_STATUSES))
        else:
            conds.append(t.c.status == "RETURNED")
    elif cat:
        conds.append(t.c.task_category == cat)
    if status:
        conds.append(t.c.status == status)
    if scope:
        conds.append(t.c.scope == scope.upper())
    if role:
        conds.append(t.c.assignee_role == role)
    if buScope:
        conds.append(t.c.bu_scope == buScope)
    if keyword:
        like = f"%{keyword}%"
        conds.append(t.c.biz_title.like(like) | t.c.task_no.like(like) |
                     t.c.one_id.like(like))

    conn = await get_engine().connect()
    try:
        rows = [dict(r) for r in (await conn.execute(
            select(t).where(*conds).order_by(t.c.id.desc())
            .limit(size).offset((page - 1) * size))).mappings().all()]
        total = (await conn.execute(
            select(func.count()).select_from(t).where(*conds))).scalar() or 0
        await _enrich_peer_in_flight(conn, rows)
    finally:
        await conn.close()
    return R.ok({"total": int(total), "rows": rows})


@router.get("/stats")
async def approval_stats():
    """Java selectTaskStats 口径：myTodo / myDone / returned / slaOverdue。"""
    t = table("cmd_approval_task")
    conn = await get_engine().connect()
    try:
        my_todo = (await conn.execute(select(func.count()).select_from(t).where(
            t.c.status == "PENDING", t.c.del_flag == "0"))).scalar() or 0
        my_done = (await conn.execute(select(func.count()).select_from(t).where(
            t.c.status.in_(FINAL_STATUSES), t.c.del_flag == "0"))).scalar() or 0
        returned = (await conn.execute(select(func.count()).select_from(t).where(
            t.c.status == "RETURNED", t.c.del_flag == "0"))).scalar() or 0
        sla_overdue = (await conn.execute(select(func.count()).select_from(t).where(
            t.c.sla_state == "OVERDUE", t.c.del_flag == "0"))).scalar() or 0
    finally:
        await conn.close()
    return R.ok({"myTodo": int(my_todo), "myDone": int(my_done),
                 "returned": int(returned), "slaOverdue": int(sla_overdue)})


@router.get("/kpi")
async def approval_kpi(scope: str = Query("BU")):
    """Java selectKpi 口径：待我处理 / 临近SLA / 已超时 / 退回待补充 / 本周已处理。"""
    t = table("cmd_approval_task")
    scope_val = "GC" if scope.upper() == "GC" else "BU"

    async def count_by(*conds):
        conn_vals = conds + (t.c.del_flag == "0",)
        return (await conn.execute(
            select(func.count()).select_from(t).where(*conn_vals))).scalar() or 0

    from datetime import datetime, timedelta
    week_start = datetime.now() - timedelta(days=datetime.now().weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    conn = await get_engine().connect()
    try:
        rows = [
            {"label": "待我处理", "value": int(await count_by(t.c.scope == scope_val, t.c.status == "PENDING")),
             "hint": "状态为待处理且分配给当前用户的任务"},
            {"label": "临近SLA", "value": int(await count_by(t.c.scope == scope_val, t.c.sla_state == "DUE_SOON")),
             "hint": "SLA 即将到期"},
            {"label": "已超时", "value": int(await count_by(t.c.scope == scope_val, t.c.sla_state == "OVERDUE")),
             "hint": "已超过 SLA 应完成时间"},
            {"label": "退回待补充", "value": int(await count_by(t.c.scope == scope_val, t.c.status == "RETURNED")),
             "hint": "已退回申请人，等待补充材料"},
            {"label": "本周已处理", "value": int(await count_by(
                t.c.scope == scope_val, t.c.status.in_(FINAL_STATUSES), t.c.finish_time >= week_start)),
             "hint": "本周一以来完成的任务"},
        ]
    finally:
        await conn.close()
    return R.ok(rows)


@router.get("/task/{task_no}/detail")
async def approval_task_detail(task_no: str):
    """处理详情（含决策标签与操作按钮）：加工为 CmdApprovalDetailVo 契约，不裸发表行。"""
    vo = await svc.task_detail(task_no)
    if vo is None:
        return R.fail(f"待办任务不存在：{task_no}", code=404)
    return R.ok(vo)


@router.get("/flow/{key}")
async def approval_flow(key: str):
    """返回某审批任务对应流程实例的整体信息（节点/状态/变量）。"""
    row = (await (await get_engine().connect()).execute(
        flow_instance_table.select().where(flow_instance_table.c.biz_no == key))).mappings().first()
    if row is None:
        return R.fail("流程实例不存在", code=404)
    return R.ok({"biz_no": row["biz_no"], "status": row["status"],
                 "current_node": row["current_node"], "data": row["data_json"]})


@router.get("/instance/list")
async def approval_instance_list(page: int = Query(1, ge=1), size: int = Query(100, ge=1, le=200)):
    rows = (await (await get_engine().connect()).execute(
        flow_instance_table.select().order_by(desc(flow_instance_table.c.update_time))
        .limit(size).offset((page - 1) * size))).mappings().all()
    return R.ok([dict(r) for r in rows])


@router.post("/action")
async def do_action(req: ApprovalAction):
    # 前端发数字主键 taskId（Java 口径）；纯数字先反查任务编号
    task_ref = (req.task_no or "").strip()
    if task_ref.isdigit():
        conn = await get_engine().connect()
        try:
            row = (await conn.execute(
                select(table("cmd_approval_task").c.task_no)
                .where(table("cmd_approval_task").c.id == int(task_ref)))).first()
        finally:
            await conn.close()
        if row is None:
            return R.fail(f"待办任务不存在：{task_ref}", code=404)
        task_ref = row[0]
    # 动作键统一转小写（前端发 APPROVE/REJECT/RETURN/ESCALATE/MERGE/EXCLUDE/CREATE_NEW）
    action = (req.action or "").strip().lower()
    result = await svc.do_action(task_ref, action, req.actor, req.opinion or "", req.role)
    return R.ok(result, msg="审批完成")


@router.get("/workflow-steps")
async def workflow_steps(oneId: Optional[str] = Query(None), taskNo: Optional[str] = Query(None)):
    """工作流步骤执行日志（WorkflowStepVO[]）：按 oneId 或 taskNo 查询 cmd_workflow_step_log。"""
    if not oneId and not taskNo:
        return R.ok([])
    log_t = table("cmd_workflow_step_log")
    conds = [log_t.c.del_flag == "0"]
    if taskNo:
        conds.append(log_t.c.task_no == taskNo)
    else:
        conds.append(log_t.c.one_id == oneId)
    conn = await get_engine().connect()
    try:
        rows = [dict(r) for r in (await conn.execute(
            log_t.select().where(*conds).order_by(log_t.c.step_seq))).mappings().all()]
    finally:
        await conn.close()
    return R.ok(rows)


@router.get("/{id}")
async def get_approval(id: int):
    t = table("cmd_approval_task")
    row = (await (await get_engine().connect()).execute(
        select(t).where(t.c.id == id))).mappings().first()
    if row is None:
        return R.fail("任务不存在", code=404)
    return R.ok(dict(row))

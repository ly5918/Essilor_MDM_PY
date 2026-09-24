"""客户变更 API（CUSTOMER_CHANGE 审批流）。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import select, func, desc

from ..core.db import get_engine, table
from ..core.query import list_table
from ..schemas import R, ChangeSubmit, ChangeResubmit
from ..services import sequence as seq

router = APIRouter(prefix="/cmd/change", tags=["变更"])


@router.get("/list")
async def change_list(
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    changeType: Optional[str] = Query(None),
    buScope: Optional[str] = Query(None),
    oneId: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
):
    t = table("cmd_change_request")
    conds = [t.c.del_flag == "0"]
    if status:
        conds.append(t.c.status == status)
    if changeType:
        conds.append(t.c.change_type == changeType)
    if buScope:
        conds.append(t.c.bu_scope == buScope)
    if oneId:
        conds.append(t.c.one_id == oneId)
    if keyword:
        like = f"%{keyword}%"
        conds.append(t.c.request_code.like(like) | t.c.one_id.like(like) |
                     t.c.legal_name.like(like))
    stmt = select(t).where(*conds)
    conn = await get_engine().connect()
    try:
        rows = (await conn.execute(
            stmt.order_by(t.c.id.desc()).limit(size).offset((page - 1) * size))).mappings().all()
        total = (await conn.execute(
            select(func.count()).select_from(t).where(*conds))).scalar()
    finally:
        await conn.close()
    return R.ok({"total": int(total), "rows": [dict(r) for r in rows]})


@router.post("")
async def submit_change(payload: ChangeSubmit):
    engine = get_engine()
    async with engine.begin() as conn:
        # 客户名称取主档法人名称：此前直接把 one_id 写进 legal_name，
        # 停用/变更列表「客户名称」列显示成 GC-00000004（总设计要求展示客户名称）
        cust = (await conn.execute(
            select(table("cmd_customer").c.legal_name)
            .where(table("cmd_customer").c.one_id == payload.one_id))).scalar()
        legal_name = cust or payload.one_id
        request_code = await seq.gen_code(conn, "CH-", 4, "CHANGE")
        rid = await seq.next_id(conn, "cmd_change_request")
        await conn.execute(table("cmd_change_request").insert().values(
            id=rid, request_code=request_code, one_id=payload.one_id,
            legal_name=legal_name, change_type=payload.change_type,
            change_reason=payload.change_reason, bu_scope=payload.bu_scope,
            target_status=payload.target_status, is_key_change=payload.is_key_change,
            status="PENDING", del_flag="0", create_by=0, create_time=datetime.now(),
        ))
        tid = await seq.next_id(conn, "cmd_approval_task")
        await conn.execute(table("cmd_approval_task").insert().values(
            id=tid, task_no=request_code, task_category="APPROVAL",
            biz_type="CUSTOMER_CHANGE", biz_id=payload.one_id, biz_title=payload.one_id,
            one_id=payload.one_id, scene_code="CUSTOMER_CHANGE", bu_scope=payload.bu_scope,
            scope="BU", current_node_code="BU_REVIEW", current_node_name="BU初审",
            assignee_role="BU_STEWARD", status="PENDING", risk_level="Medium",
            submit_time=datetime.now(), del_flag="0", create_by=0, create_time=datetime.now(),
        ))
        from ..services.trace import log_step
        await log_step(conn, one_id=payload.one_id, task_no=request_code,
                       step_type="SUBMIT", node_code="APPLY", node_name="提交变更申请",
                       action_type="SUBMIT", action_name="提交申请",
                       operator_name="applicant", operator_role="BU_USER",
                       from_status="-", to_status="PENDING")
        # 提交动作轨迹（与 Java 口径一致：审批轨迹 / 流程跟踪节点历史的数据源）
        from ..services.trace import log_action
        await log_action(conn, task_id=tid, task_no=request_code, one_id=payload.one_id,
                         action_type="SUBMIT", action_name="提交申请",
                         from_node_code="APPLY", to_node_code="APPLY",
                         operator_name="applicant", operator_role="BU_USER",
                         opinion=payload.change_reason or "")
    return R.ok({"request_code": request_code}, msg="变更申请已提交")


@router.post("/{request_code}/resubmit")
async def resubmit_change(request_code: str, payload: ChangeResubmit):
    """被退回变更单「修改重报」（总设计：BU Scope 退回或补充材料 → 申请人修改后重进初审）。

    - 仅 status=RETURNED 可重报；仅更新传入的非空字段（变更原因 / 目标状态）；
    - 变更单状态 RETURNED → PENDING，审批任务行重开到 BU Scope 初审；
    - 流程实例用 reset_instance_node 真正拉回 BU_REVIEW 等待位（与新建申请重报同机制）。
    """
    from ..services.trace import log_action, log_step
    from ..workflow.engine import reset_instance_node

    engine = get_engine()
    async with engine.begin() as conn:
        t = table("cmd_change_request")
        row = (await conn.execute(
            select(t).where(t.c.request_code == request_code, t.c.del_flag == "0")
        )).mappings().first()
        if row is None:
            return R.fail("变更单不存在", code=400)
        if (row["status"] or "") != "RETURNED":
            return R.fail(f"仅被退回的变更单可修改重报（当前状态：{row['status']}）", code=400)

        updates: dict = {k: v for k, v in {
            "change_reason": (payload.change_reason or "").strip() or None,
            "target_status": (payload.target_status or "").strip() or None,
        }.items() if v}
        remark = (payload.remark or "").strip() or "修改重报"
        applicant = (payload.applicant_name or "").strip() or "Business User"

        # 1) 变更单：改字段 + 状态回 PENDING
        await conn.execute(t.update().where(t.c.request_code == request_code).values(
            **updates, status="PENDING", update_time=datetime.now()))
        # 2) 审批任务行：重开到 BU Scope 初审（BU 队列可见）
        await conn.execute(table("cmd_approval_task").update()
                           .where(table("cmd_approval_task").c.task_no == request_code)
                           .values(status="PENDING", scope="BU",
                                   current_node_code="BU_REVIEW", current_node_name="BU初审",
                                   assignee_role="BU_STEWARD", submit_time=datetime.now()))
        # 3) 流程实例镜像 + 引擎：拉回 BU_REVIEW READY 位
        await reset_instance_node(request_code, "BU_REVIEW")
        # 4) 轨迹：时间线 + 步骤条体现「修改重报」
        await log_action(
            conn, task_id=row["id"], task_no=request_code, one_id=row["one_id"],
            action_type="RESUBMIT", action_name=remark,
            from_node_code="APPLY", to_node_code="BU_REVIEW",
            operator_name=applicant, operator_role="BU_USER",
            opinion=updates.get("change_reason") or remark,
        )
        await log_step(
            conn, one_id=row["one_id"], task_no=request_code,
            step_type="BUSINESS", node_code="BU_REVIEW", node_name="BU Scope 初审",
            action_type="RESUBMIT", action_name=remark,
            operator_name=applicant, operator_role="BU_USER",
            from_status="RETURNED", to_status="PENDING",
            opinion=updates.get("change_reason") or remark,
        )
    return R.ok({"requestCode": request_code, "status": "PENDING",
                 "currentNodeName": "BU Scope 初审"},
                msg="修改重报成功，已重新进入 BU Scope 初审")


@router.get("/fields")
async def change_fields():
    """可变更字段（取元数据字段表）。"""
    t = table("md_field")
    rows = (await (await get_engine().connect()).execute(
        select(t).where(t.c.del_flag == "0"))).mappings().all()
    return R.ok([dict(r) for r in rows])


@router.get("/kpi")
async def change_kpi():
    t = table("cmd_change_request")
    conn = await get_engine().connect()
    try:
        total = (await conn.execute(select(func.count()).select_from(t).where(t.c.del_flag == "0"))).scalar() or 0
        pending = (await conn.execute(select(func.count()).select_from(t).where(t.c.status == "PENDING"))).scalar() or 0
        approved = (await conn.execute(select(func.count()).select_from(t).where(t.c.status == "APPROVED"))).scalar() or 0
        effective = (await conn.execute(select(func.count()).select_from(t).where(t.c.status == "EFFECTIVE"))).scalar() or 0
    finally:
        await conn.close()
    return R.ok({"total": total, "pending": pending, "approved": approved, "effective": effective})


@router.get("/versions/{one_id}")
async def change_versions(one_id: str):
    t = table("cmd_change_request")
    rows = (await (await get_engine().connect()).execute(
        select(t).where(t.c.one_id == one_id).order_by(desc(t.c.create_time)))).mappings().all()
    return R.ok([dict(r) for r in rows])


@router.get("/{one_id}/deactivateResult")
async def deactivate_result(one_id: str):
    """停用预演：返回该主数据是否被其他记录引用 / 关联数量。"""
    cust = table("cmd_customer")
    rel = table("cmd_hierarchy_relation")
    conn = await get_engine().connect()
    try:
        cust_row = (await conn.execute(select(cust).where(cust.c.one_id == one_id))).mappings().first()
        relations = 0
        try:
            relations = (await conn.execute(
                select(func.count()).select_from(rel).where(rel.c.child_one_id == one_id))).scalar() or 0
        except Exception:
            relations = 0
    finally:
        await conn.close()
    return R.ok({"one_id": one_id, "exists": cust_row is not None,
                 "status": cust_row["status"] if cust_row else None,
                 "relation_count": relations})


@router.post("/{request_code}/cancel")
async def cancel_change(request_code: str):
    async with get_engine().begin() as conn:
        await conn.execute(
            table("cmd_change_request").update()
            .where(table("cmd_change_request").c.request_code == request_code)
            .values(status="CANCELLED"))
    return R.ok(msg="变更单已取消")


@router.get("/{request_code}/detail")
async def change_detail(request_code: str):
    t = table("cmd_change_request")
    row = (await (await get_engine().connect()).execute(
        select(t).where(t.c.request_code == request_code))).mappings().first()
    if row is None:
        return R.fail("变更单不存在", code=404)
    return R.ok(dict(row))


@router.post("/{request_code}/effect")
async def effect_change(request_code: str):
    """变更「生效」：唯一写主档入口。"""
    engine = get_engine()
    async with engine.begin() as conn:
        cr = (await conn.execute(
            table("cmd_change_request").select()
            .where(table("cmd_change_request").c.request_code == request_code))).mappings().first()
        if cr is None:
            return R.fail("变更单不存在", code=404)
        cr = dict(cr)
        await conn.execute(
            table("cmd_change_request").update()
            .where(table("cmd_change_request").c.request_code == request_code)
            .values(status="EFFECTIVE", effective_time=datetime.now()))
        # 若停用类变更，更新主档状态（change_type 大小写不敏感；
        # target_status 统一小写——全库主档状态约定为 active/inactive）
        if (cr["change_type"] or "").upper() == "DEACTIVATE" and cr.get("target_status"):
            await conn.execute(
                table("cmd_customer").update().where(table("cmd_customer").c.one_id == cr["one_id"])
                .values(status=(cr["target_status"] or "").lower(), effective_to=datetime.now()))
    return R.ok(msg="变更已生效")

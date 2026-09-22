"""客户变更 API（CUSTOMER_CHANGE 审批流）。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import select, func, desc

from ..core.db import get_engine, table
from ..core.query import list_table
from ..schemas import R, ChangeSubmit
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
        request_code = await seq.gen_code(conn, "CH-", 4, "CHANGE")
        rid = await seq.next_id(conn, "cmd_change_request")
        await conn.execute(table("cmd_change_request").insert().values(
            id=rid, request_code=request_code, one_id=payload.one_id,
            legal_name=payload.one_id, change_type=payload.change_type,
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

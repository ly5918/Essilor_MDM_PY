"""客户主档 / 新建申请 API。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import select, func, desc

from ..core.db import get_engine, table
from ..core.query import list_table
from ..schemas import R, CustomerSubmit
from ..services import customer as svc

router = APIRouter(prefix="/cmd/customer", tags=["客户主档"])


@router.get("/list")
async def list_customers(
    buScope: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
):
    data = await svc.list_customers(buScope, status, keyword, page, size)
    return R.ok(data)


@router.get("/stats")
async def customer_stats(
    buScope: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    customerType: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
):
    """Java selectCustomerStats 口径：与列表共用条件，pendingCount = 在途申请。"""
    data = await svc.customer_stats(buScope, status, keyword, customerType)
    return R.ok(data)


@router.get("/application/list")
async def application_list(
    status: Optional[str] = Query(None),
    buScope: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
):
    """申请单列表：toApplicationVO 契约（taskNo/taskStatus/currentNodeName/重复组富化）。"""
    data = await svc.list_applications(status, keyword, page, size)
    return R.ok(data)


@router.get("/application/stats")
async def application_stats():
    t = table("cmd_customer_application")
    conn = await get_engine().connect()
    try:
        total = (await conn.execute(select(func.count()).select_from(t))).scalar() or 0
        pending = (await conn.execute(select(func.count()).select_from(t).where(t.c.status == "pending"))).scalar() or 0
        approved = (await conn.execute(select(func.count()).select_from(t).where(t.c.status == "approved"))).scalar() or 0
        rejected = (await conn.execute(select(func.count()).select_from(t).where(t.c.status == "rejected"))).scalar() or 0
    finally:
        await conn.close()
    return R.ok({"total": total, "pending": pending, "approved": approved, "rejected": rejected})


@router.post("")
async def create_customer(payload: CustomerSubmit):
    """提交新建申请：必填校验失败按业务错误回 400（BUG-PY-04）。"""
    try:
        result = await svc.submit_customer(payload)
    except ValueError as e:
        return R.fail(str(e), code=400)
    return R.ok(result, msg="提交成功，已启动审批流程")


@router.get("/oneId/{one_id}")
async def get_by_one_id(one_id: str):
    engine = get_engine()
    cust = table("cmd_customer")
    row = (await (await engine.connect()).execute(
        select(cust).where(cust.c.one_id == one_id))).mappings().first()
    if row is None:
        return R.fail("客户不存在", code=404)
    return R.ok(dict(row))


@router.put("/deactivate/{one_id}")
async def deactivate(one_id: str):
    from datetime import datetime
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(
            table("cmd_customer").update().where(table("cmd_customer").c.one_id == one_id)
            .values(status="inactive", effective_to=datetime.now()))
    return R.ok(msg="已停用")

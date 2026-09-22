"""侧边导航角标 API。"""
from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import select, func

from ..core.db import get_engine, table
from ..schemas import R

router = APIRouter(prefix="/cmd/nav", tags=["导航"])


@router.get("/badge")
async def nav_badge(role: str = Query("ALL")):
    """返回各菜单角标计数（待办/预警等）。"""
    task = table("cmd_approval_task")
    cust = table("cmd_customer")
    change = table("cmd_change_request")
    gov = table("cmd_governance_task")
    conn = await get_engine().connect()
    try:
        pending = (await conn.execute(
            select(func.count()).select_from(task).where(task.c.status == "PENDING"))).scalar() or 0
        customers = (await conn.execute(
            select(func.count()).select_from(cust).where(cust.c.del_flag == "0"))).scalar() or 0
        changes = (await conn.execute(
            select(func.count()).select_from(change).where(change.c.status == "PENDING"))).scalar() or 0
        gov_open = (await conn.execute(
            select(func.count()).select_from(gov).where(gov.c.status == "OPEN"))).scalar() or 0
        dups = (await conn.execute(
            select(func.count()).select_from(cust).where(cust.c.del_flag == "0", cust.c.duplicate_flag == "Y"))).scalar() or 0
    finally:
        await conn.close()
    return R.ok({
        "approval": {"pending": pending},
        "customer": {"total": customers, "duplicate": dups},
        "change": {"pending": changes},
        "governance": {"open": gov_open},
    })

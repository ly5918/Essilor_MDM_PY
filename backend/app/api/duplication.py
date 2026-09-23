"""重复核验 API。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, Body
from sqlalchemy import select

from ..core.db import get_engine, table
from ..schemas import R
from ..services.duplicate import duplicate_check

router = APIRouter(prefix="/cmd/duplication", tags=["重复核验"])


@router.get("/candidate")
async def candidate(creditCode: str = Query(None, description="统一社会信用代码（主依据）"),
                    legalName: str = Query(None, description="客户名称（辅助线索）"),
                    address: str = Query(None, description="经营地址（主依据）")):
    """重复核验：主依据 = 信用代码 + 经营地址，客户名称仅作辅助线索（总设计 V6.1 口径）。"""
    engine = get_engine()
    async with engine.connect() as conn:
        data = await duplicate_check(conn, creditCode, legalName, address, scene="CREATE")
    return R.ok(data)


@router.put("/link")
async def link(body: dict = Body(...)):
    """将某 One ID 关联到主数据（master），写入合并关系。"""
    one_id = body.get("oneId") or body.get("one_id")
    master = body.get("masterOneId") or body.get("master") or body.get("survivorOneId")
    if not one_id:
        return R.fail("缺少 oneId", code=400)
    async with get_engine().begin() as conn:
        await conn.execute(
            table("cmd_customer").update().where(table("cmd_customer").c.one_id == one_id)
            .values(merged_to_one_id=master, match_state="EXACT", duplicate_flag="Y",
                    effective_to=datetime.now()))
    return R.ok(msg=f"已关联 One ID {one_id} → {master}")


@router.put("/confirmNew")
async def confirm_new(body: dict = Body(...)):
    """确认为新客户：将待审批申请置为可进入新建审批。"""
    app_no = body.get("appNo") or body.get("app_no")
    if app_no:
        async with get_engine().begin() as conn:
            await conn.execute(
                table("cmd_customer_application").update()
                .where(table("cmd_customer_application").c.app_no == app_no)
                .values(status="pending"))
    return R.ok(msg="已进入新客户审批")

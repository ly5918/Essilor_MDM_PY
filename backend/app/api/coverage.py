"""验收覆盖清单 API（poc_coverage_topic）。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from ..core.db import get_engine, table
from ..core.query import list_table
from ..schemas import R

router = APIRouter(prefix="/cmd/coverage", tags=["覆盖清单"])


@router.get("/list")
async def coverage_list(page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=200),
                        demoStatus: Optional[str] = None, keyword: Optional[str] = None):
    conn = await get_engine().connect()
    try:
        data = await list_table(conn, table("poc_coverage_topic"), page=page, size=size,
                                filters={"demo_status": demoStatus}, keyword=keyword,
                                order_by=table("poc_coverage_topic").c.order_num.asc())
    finally:
        await conn.close()
    return R.ok(data)

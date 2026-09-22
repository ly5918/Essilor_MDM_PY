"""审计中心 API（audit_event / audit_export_log）。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..core.db import get_engine, table
from ..core.query import list_table, dynamic_insert
from ..schemas import R

router = APIRouter(prefix="/cmd/audit", tags=["审计"])


@router.get("/list")
async def audit_list(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    eventType: Optional[str] = None,
    bizType: Optional[str] = None,
    operatorName: Optional[str] = None,
    riskLevel: Optional[str] = None,
    keyword: Optional[str] = None,
):
    conn = await get_engine().connect()
    try:
        data = await list_table(
            conn, table("audit_event"), page=page, size=size,
            filters={"event_type": eventType, "biz_type": bizType,
                     "operator_name": operatorName, "risk_level": riskLevel},
            keyword=keyword,
            order_by=table("audit_event").c.event_time.desc(),
        )
    finally:
        await conn.close()
    return R.ok(data)


class ExportReq(BaseModel):
    export_type: str = "AUDIT_LIST"
    filter_json: Optional[dict] = None
    file_name: Optional[str] = None


@router.get("/export")
async def audit_export(
    page: int = Query(1, ge=1),
    size: int = Query(1000, ge=1, le=5000),
    eventType: Optional[str] = None,
    keyword: Optional[str] = None,
):
    """导出审计明细：落一条 audit_export_log，返回模拟文件信息（与原系统行为一致）。"""
    conn = await get_engine().connect()
    try:
        data = await list_table(
            conn, table("audit_event"), page=page, size=size,
            filters={"event_type": eventType}, keyword=keyword,
            order_by=table("audit_event").c.event_time.desc(),
        )
    finally:
        await conn.close()
    async with get_engine().begin() as wconn:
        code = f"AUD-EXP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        file_name = f"audit_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        await dynamic_insert(wconn, table("audit_export_log"), {
            "export_code": code, "export_type": "AUDIT_LIST",
            "filter_json": {"eventType": eventType, "keyword": keyword},
            "file_name": file_name, "row_count": data["total"],
            "export_status": "DONE", "export_time": datetime.now(),
            "operator_id": 1, "operator_name": "admin",
        })
    return R.ok({"file_name": file_name, "row_count": data["total"], "list": data["list"]})


@router.post("/export")
async def audit_export_post(body: Optional[dict] = None):
    """前端用 POST 触发导出（body 可带过滤条件），行为与 GET 版一致。"""
    body = dict(body or {})
    return await audit_export(
        page=int(body.get("page", 1)),
        size=int(body.get("size", 1000)),
        eventType=body.get("eventType"),
        keyword=body.get("keyword"),
    )


@router.get("/export/list")
async def export_log_list(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=200)):
    conn = await get_engine().connect()
    try:
        data = await list_table(conn, table("audit_export_log"), page=page, size=size,
                                order_by=table("audit_export_log").c.create_time.desc())
    finally:
        await conn.close()
    return R.ok(data)

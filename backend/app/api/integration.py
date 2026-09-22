"""集成中心 API（int_endpoint / int_run / int_message）。"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..core.db import get_engine, table
from ..core.query import list_table, dynamic_insert, dynamic_update, get_row
from ..schemas import R

router = APIRouter(prefix="/cmd/integration", tags=["集成中心"])


@router.get("/endpoint/list")
async def endpoint_list(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=200),
                        direction: Optional[str] = None, targetSystem: Optional[str] = None,
                        status: Optional[str] = None, keyword: Optional[str] = None):
    conn = await get_engine().connect()
    try:
        data = await list_table(conn, table("int_endpoint"), page=page, size=size,
                                filters={"direction": direction, "target_system": targetSystem,
                                         "status": status},
                                keyword=keyword, keyword_cols=("endpoint_code", "endpoint_name", "target_system"),
                                order_by=table("int_endpoint").c.create_time.desc())
    finally:
        await conn.close()
    return R.ok(data)


@router.get("/endpoint/{endpoint_id}")
async def endpoint_detail(endpoint_id: int):
    conn = await get_engine().connect()
    try:
        row = await get_row(conn, table("int_endpoint"), endpoint_id)
    finally:
        await conn.close()
    return R.ok(row)


class EndpointPayload(BaseModel):
    endpoint_code: Optional[str] = None
    endpoint_name: Optional[str] = None
    direction: Optional[str] = None
    protocol: Optional[str] = None
    target_system: Optional[str] = None
    endpoint_url: Optional[str] = None
    auth_type: Optional[str] = None
    biz_type: Optional[str] = None
    message_format: Optional[str] = None
    max_retry: Optional[int] = None
    status: Optional[str] = None
    remark: Optional[str] = None


@router.post("/endpoint")
async def create_endpoint(payload: EndpointPayload):
    d = payload.model_dump(exclude_none=True)
    d.setdefault("endpoint_code", f"EP-{uuid.uuid4().hex[:8].upper()}")
    d.setdefault("status", "DRAFT")
    async with get_engine().begin() as conn:
        vals = await dynamic_insert(conn, table("int_endpoint"), d)
    return R.ok({"id": vals.get("id"), "endpoint_code": vals.get("endpoint_code")}, msg="端点已创建")


@router.put("/endpoint/{endpoint_id}")
async def update_endpoint(endpoint_id: int, payload: EndpointPayload):
    async with get_engine().begin() as conn:
        await dynamic_update(conn, table("int_endpoint"), endpoint_id, payload.model_dump(exclude_none=True))
    return R.ok(msg="端点已更新")


@router.post("/endpoint/{endpoint_id}/publish")
async def publish_endpoint(endpoint_id: int):
    async with get_engine().begin() as conn:
        await dynamic_update(conn, table("int_endpoint"), endpoint_id, {"status": "PUBLISHED"})
    return R.ok(msg="端点已发布")


@router.post("/endpoint/{endpoint_id}/test")
async def test_endpoint(endpoint_id: int):
    """连通性测试：原系统为模拟返回，这里同样返回成功样例。"""
    conn = await get_engine().connect()
    try:
        row = await get_row(conn, table("int_endpoint"), endpoint_id)
    finally:
        await conn.close()
    if not row:
        return R.fail("端点不存在")
    return R.ok({"endpoint_code": row.get("endpoint_code"),
                 "http_status": 200, "latency_ms": 80,
                 "message": "模拟连通性测试通过"})


@router.get("/run/list")
async def run_list(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=200),
                   runStatus: Optional[str] = None, endpointCode: Optional[str] = None,
                   keyword: Optional[str] = None):
    conn = await get_engine().connect()
    try:
        data = await list_table(conn, table("int_run"), page=page, size=size,
                                filters={"run_status": runStatus, "endpoint_code": endpointCode},
                                keyword=keyword, keyword_cols=("run_code", "endpoint_name", "biz_id"),
                                order_by=table("int_run").c.create_time.desc())
    finally:
        await conn.close()
    return R.ok(data)


@router.post("/run/{run_id}/retry")
async def retry_run(run_id: int):
    """重试失败批次：复制一条新 run 记录并置为成功（模拟）。"""
    async with get_engine().begin() as conn:
        src = await get_row(conn, table("int_run"), run_id)
        if not src:
            return R.fail("批次不存在")
        vals = await dynamic_insert(conn, table("int_run"), {
            "run_code": f"RUN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}",
            "endpoint_code": src.get("endpoint_code"),
            "endpoint_name": src.get("endpoint_name"),
            "direction": src.get("direction"),
            "target_system": src.get("target_system"),
            "biz_type": src.get("biz_type"),
            "trigger_type": "MANUAL_RETRY",
            "run_status": "SUCCESS",
            "total_count": src.get("total_count") or 0,
            "success_count": src.get("total_count") or 0,
            "failed_count": 0,
            "attempt_count": 1,
            "max_attempt": src.get("max_attempt") or 3,
            "parent_run_id": run_id,
            "start_time": datetime.now(), "end_time": datetime.now(),
            "duration_ms": 120,
        })
    return R.ok({"run_code": vals.get("run_code")}, msg="重试批次已生成")


@router.get("/message/list")
async def message_list(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=200),
                       endpointCode: Optional[str] = None, status: Optional[str] = None,
                       keyword: Optional[str] = None):
    conn = await get_engine().connect()
    try:
        data = await list_table(conn, table("int_message"), page=page, size=size,
                                filters={"endpoint_code": endpointCode, "status": status},
                                keyword=keyword, keyword_cols=("message_id", "biz_id", "one_id"),
                                order_by=table("int_message").c.create_time.desc())
    finally:
        await conn.close()
    return R.ok(data)

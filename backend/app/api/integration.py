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
async def endpoint_list(page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=200),
                        direction: Optional[str] = None, targetSystem: Optional[str] = None,
                        status: Optional[str] = None, keyword: Optional[str] = None):
    """前端期望裸数组（不分页包装）。"""
    conn = await get_engine().connect()
    try:
        data = await list_table(conn, table("int_endpoint"), page=page, size=size,
                                filters={"direction": direction, "target_system": targetSystem,
                                         "status": status},
                                keyword=keyword, keyword_cols=("endpoint_code", "endpoint_name", "target_system"),
                                order_by=table("int_endpoint").c.create_time.desc())
    finally:
        await conn.close()
    return R.ok(data["rows"])


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
    d.setdefault("status", 0)  # int_endpoint.status 为 0/1 整型（0=Active），写字符串会导致 500
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
        await dynamic_update(conn, table("int_endpoint"), endpoint_id, {"status": 1})  # 发布=置 1（原 "PUBLISHED" 字符串会让整型列报错 500）
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
@router.put("/run/{run_id}/retry")
async def retry_run(run_id: int):
    """失败批次重试：生成集成失败处理审批（治理批准后由回调生成重试运行）。"""
    async with get_engine().begin() as conn:
        src = await get_row(conn, table("int_run"), run_id)
        if not src:
            return R.fail("批次不存在")
        # 已有在途审批则不重复发起
        from sqlalchemy import select as _select
        inflight = (await conn.execute(
            _select(table("cmd_approval_task").c.task_no).where(
                table("cmd_approval_task").c.biz_type == "INTEGRATION_FAIL",
                table("cmd_approval_task").c.biz_id == str(run_id),
                table("cmd_approval_task").c.status == "PENDING",
                table("cmd_approval_task").c.del_flag == "0"))).first()
        if inflight:
            return R.ok({"taskNo": inflight[0]}, msg="该批次已有在途失败处理审批")
        from ..services.rule_flow import start_integration_retry_flow
        task_no = await start_integration_retry_flow(conn, run_id, src)
        if task_no is None:
            return R.fail("仅失败/重试中的批次可发起失败处理审批")
    return R.ok({"taskNo": task_no}, msg="集成失败处理审批已发起")


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

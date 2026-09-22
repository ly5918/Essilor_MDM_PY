"""数据质量（DQ）规则 / 评分卡 / 模拟 API。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, Body
from sqlalchemy import select, func

from ..core.db import get_engine, table
from ..core.query import list_table, dynamic_insert, dynamic_update
from ..schemas import R

router = APIRouter(prefix="/cmd/dq", tags=["数据质量"])


@router.get("/rule/list")
async def dq_rule_list(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=200)):
    conn = await get_engine().connect()
    try:
        data = await list_table(conn, table("dq_rule"), page=page, size=size)
    finally:
        await conn.close()
    return R.ok(data)


@router.post("/rule")
async def dq_rule_create(body: dict = Body(...)):
    body = dict(body)
    body.setdefault("create_time", datetime.now())
    async with get_engine().begin() as conn:
        vals = await dynamic_insert(conn, table("dq_rule"), body)
    return R.ok(vals, msg="DQ 规则已创建")


@router.get("/rule/{rule_id}")
async def dq_rule_detail(rule_id: int):
    conn = await get_engine().connect()
    try:
        row = (await conn.execute(select(table("dq_rule")).where(
            table("dq_rule").c.id == rule_id))).mappings().first()
    finally:
        await conn.close()
    return R.ok(dict(row) if row else None)


@router.put("/rule/{rule_id}")
async def dq_rule_update(rule_id: int, body: dict = Body(...)):
    body = {k: v for k, v in dict(body).items() if k != "id"}
    body.setdefault("update_time", datetime.now())
    async with get_engine().begin() as conn:
        await dynamic_update(conn, table("dq_rule"), rule_id, body)
    return R.ok(msg="DQ 规则已更新")


@router.delete("/rule/{rule_id}")
async def dq_rule_delete(rule_id: int):
    async with get_engine().begin() as conn:
        await conn.execute(table("dq_rule").update().where(table("dq_rule").c.id == rule_id).values(del_flag="1"))
    return R.ok(msg="DQ 规则已删除")


@router.get("/scorecard")
async def dq_scorecard(oneId: Optional[str] = Query(None)):
    try:
        t = table("dq_scorecard")
        rows = (await (await get_engine().connect()).execute(select(t))).mappings().all()
        return R.ok([dict(r) for r in rows])
    except Exception:
        return R.ok([])


@router.post("/simulate")
async def dq_simulate(body: dict = Body(...)):
    """模拟 DQ 校验：返回字段级评分（演示用确定性结果）。"""
    fields = body.get("fields", [])
    results = []
    for i, f in enumerate(fields):
        results.append({"field": f, "score": 100 - i * 7 % 30, "level": "PASS" if i % 3 else "WARN"})
    return R.ok({"overall": 88, "items": results})


@router.post("/reEvaluate")
async def dq_re_evaluate(body: dict = Body(...)):
    async with get_engine().begin() as conn:
        job_code = f"DQR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        await dynamic_insert(conn, table("dq_reeval_job"), {
            "job_code": job_code, "job_name": "历史数据重评估",
            "scope_type": body.get("scopeType", "ALL"),
            "scope_value": body.get("scopeValue", ""),
            "execute_mode": "ASYNC", "job_status": "RUNNING",
            "from_version": body.get("fromVersion", ""), "to_version": body.get("toVersion", ""),
            "start_time": datetime.now()})
    return R.ok({"job_code": job_code}, msg="历史数据重评估任务已创建，旧规则版本与旧分数保留")


@router.get("/reEvaluate/impact")
async def dq_re_evaluate_impact():
    return R.ok({"affected": 0, "changedScore": 0, "risk": "LOW"})

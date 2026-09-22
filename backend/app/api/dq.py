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
async def dq_rule_list():
    """DQ 规则清单（裸数组，前端 listDqRules 契约）。"""
    conn = await get_engine().connect()
    try:
        rows = (await conn.execute(
            select(table("dq_rule")).where(table("dq_rule").c.del_flag == "0")
            .order_by(table("dq_rule").c.id))).mappings().all()
    finally:
        await conn.close()
    return R.ok([dict(r) for r in rows])


@router.post("/rule")
async def dq_rule_create(body: dict = Body(...)):
    body = dict(body)
    # NOT NULL 无默认值列兜底（前端/测试载荷可能缺省）
    body.setdefault("rule_type", "CUSTOM")
    body.setdefault("check_type", "NOT_NULL")
    body.setdefault("model_code", "CUSTOMER")
    body.setdefault("is_preset", "N")
    body.setdefault("order_num", 0)
    body.setdefault("version_no", "v1")
    body.setdefault("status", "0")  # 草稿：DQ_RULE_CHANGE 审批通过后置 1
    body.setdefault("create_time", datetime.now())
    async with get_engine().begin() as conn:
        vals = await dynamic_insert(conn, table("dq_rule"), body)
        # 总设计泳道：规则草稿 → BU 验证 → GC 一致性验证 → 生效
        from ..services.rule_flow import start_rule_change_flow
        task_no = await start_rule_change_flow(
            conn, "DQ_RULE_CHANGE", "dq_rule", int(vals.get("id") or 0),
            {**body, "id": vals.get("id")}, "新增",
            actor=str(body.get("create_by") or "demo"))
    return R.ok({**vals, "taskNo": task_no}, msg="DQ 规则草稿已创建，审批通过后生效")


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
        old = (await conn.execute(
            select(table("dq_rule")).where(table("dq_rule").c.id == rule_id))).mappings().first()
        if old is None:
            return R.fail("DQ 规则不存在", code=404)
        old = dict(old)
        # 修改落草稿（status=0），审批通过后恢复生效；拒绝则回滚旧值
        new_vals = {**body, "status": "0"}
        await dynamic_update(conn, table("dq_rule"), rule_id, new_vals)
        from ..services.rule_flow import start_rule_change_flow
        task_no = await start_rule_change_flow(
            conn, "DQ_RULE_CHANGE", "dq_rule", rule_id,
            {**{k: old.get(k) for k in ("rule_code", "rule_name", "version_no")},
             **body}, "修改", actor="demo")
    return R.ok({"taskNo": task_no}, msg="DQ 规则修改已提交审批，通过后生效")


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

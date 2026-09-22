"""匹配规则 / 模拟 API（实体重合识别）。"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query, Body
from sqlalchemy import select

from ..core.db import get_engine, table
from ..core.query import list_table, dynamic_insert
from ..schemas import R

router = APIRouter(prefix="/cmd/match", tags=["匹配"])


@router.get("/rule/list")
async def match_rule_list():
    """匹配规则清单（裸数组，前端 listMatchRules 契约）。"""
    conn = await get_engine().connect()
    try:
        rows = (await conn.execute(
            select(table("match_rule")).where(table("match_rule").c.del_flag == "0")
            .order_by(table("match_rule").c.id))).mappings().all()
    finally:
        await conn.close()
    return R.ok([dict(r) for r in rows])


@router.post("/rule")
async def match_rule_create(body: dict = Body(...)):
    body = dict(body)
    body.setdefault("is_preset", "N")
    body.setdefault("version_no", "v1")
    body.setdefault("status", "0")  # 草稿：MATCH_RULE_CHANGE 审批通过后置 1
    body.setdefault("create_time", datetime.now())
    async with get_engine().begin() as conn:
        vals = await dynamic_insert(conn, table("match_rule"), body)
        # 总设计泳道：规则调整 → BU 候选验证 → GC 候选验证 → 生效
        from ..services.rule_flow import start_rule_change_flow
        task_no = await start_rule_change_flow(
            conn, "MATCH_RULE_CHANGE", "match_rule", int(vals.get("id") or 0),
            {**body, "id": vals.get("id")}, "新增", actor="demo")
    return R.ok({**vals, "taskNo": task_no}, msg="匹配规则草稿已创建，审批通过后生效")


@router.get("/rule/{rule_id}")
async def match_rule_detail(rule_id: int):
    conn = await get_engine().connect()
    try:
        row = (await conn.execute(select(table("match_rule")).where(
            table("match_rule").c.id == rule_id))).mappings().first()
    finally:
        await conn.close()
    return R.ok(dict(row) if row else None)


@router.put("/rule/{rule_id}")
async def match_rule_update(rule_id: int, body: dict = Body(...)):
    from ..core.query import dynamic_update
    body = {k: v for k, v in dict(body).items() if k != "id"}
    body.setdefault("update_time", datetime.now())
    async with get_engine().begin() as conn:
        old = (await conn.execute(
            select(table("match_rule")).where(table("match_rule").c.id == rule_id))).mappings().first()
        if old is None:
            return R.fail("匹配规则不存在", code=404)
        old = dict(old)
        # 修改落草稿（status=0），审批通过后恢复生效；拒绝则回滚旧值
        new_vals = {**body, "status": "0"}
        await dynamic_update(conn, table("match_rule"), rule_id, new_vals)
        from ..services.rule_flow import start_rule_change_flow
        task_no = await start_rule_change_flow(
            conn, "MATCH_RULE_CHANGE", "match_rule", rule_id,
            {**{k: old.get(k) for k in ("rule_code", "rule_name", "version_no")},
             **body}, "修改", actor="demo")
    return R.ok({"taskNo": task_no}, msg="匹配规则修改已提交审批，通过后生效")


@router.delete("/rule/{rule_id}")
async def match_rule_delete(rule_id: int):
    async with get_engine().begin() as conn:
        await conn.execute(table("match_rule").update().where(table("match_rule").c.id == rule_id).values(del_flag="1"))
    return R.ok(msg="匹配规则已删除")


@router.post("/simulate")
async def match_simulate(body: dict = Body(...)):
    """模拟匹配：对给定记录返回候选重合。"""
    name = body.get("legalName") or body.get("legal_name") or ""
    credit = body.get("creditCode") or body.get("credit_code") or ""
    cust = table("cmd_customer")
    conn = await get_engine().connect()
    try:
        candidates = []
        if credit:
            rows = (await conn.execute(
                select(cust).where(cust.c.credit_code == credit, cust.c.del_flag == "0"))).mappings().all()
            candidates = [dict(r) for r in rows]
        elif name:
            rows = (await conn.execute(
                select(cust).where(cust.c.legal_name.like(f"%{name}%"), cust.c.del_flag == "0"))).mappings().all()
            candidates = [dict(r) for r in rows]
    finally:
        await conn.close()
    return R.ok({"candidates": candidates, "exact": len(candidates) > 0})

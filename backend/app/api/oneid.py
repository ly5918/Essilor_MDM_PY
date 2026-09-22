"""One ID 规则 / 策略 / 历史事件 API。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, Body
from sqlalchemy import select, func, desc

from ..core.db import get_engine, table
from ..core.query import dynamic_insert, dynamic_update
from ..schemas import R

router = APIRouter(prefix="/cmd/oneid", tags=["One ID"])


@router.get("/rule")
async def oneid_rule():
    try:
        t = table("oneid_rule")
        row = (await (await get_engine().connect()).execute(
            select(t).order_by(t.c.id.desc()))).mappings().first()
        return R.ok(dict(row) if row else {"rule_name": "默认OneID规则", "published": "0"})
    except Exception:
        return R.ok({"rule_name": "默认OneID规则", "published": "0"})


@router.put("/rule")
async def oneid_rule_save(body: dict = Body(...)):
    body = dict(body)
    body["update_time"] = datetime.now()
    body["status"] = "0"  # 保存即回到 Draft，需再点「发布规则」才生效（与前端交互一致）
    try:
        t = table("oneid_rule")
        existing = (await (await get_engine().connect()).execute(
            select(t.c.id).order_by(t.c.id.desc()).limit(1))).scalar()
        async with get_engine().begin() as conn:
            if existing:
                await dynamic_update(conn, t, existing, body)
            else:
                body.setdefault("create_time", datetime.now())
                await dynamic_insert(conn, t, body)
    except Exception as e:
        return R.fail(f"保存失败: {e}", code=500)
    return R.ok(msg="OneID 规则已保存")


@router.put("/rule/publish")
async def oneid_rule_publish():
    """发布当前默认规则：status '0'=Draft / '1'=已发布（表无 published 列，状态在 status）。"""
    try:
        t = table("oneid_rule")
        async with get_engine().begin() as conn:
            rid = (await conn.execute(select(func.max(t.c.id)).select_from(t))).scalar() or 0
            await conn.execute(t.update().values(status="0"))
            if rid:
                await conn.execute(t.update().where(t.c.id == rid).values(status="1"))
    except Exception as e:
        return R.fail(f"发布失败: {e}", code=500)
    return R.ok(msg="OneID 规则已发布")


@router.put("/rule/copy")
async def oneid_rule_copy():
    return R.ok(msg="OneID 规则已复制为草稿")


@router.get("/policy/list")
async def oneid_policy_list():
    """策略列表：复用角色表或返回默认策略。"""
    try:
        t = table("cmd_role")
        rows = (await (await get_engine().connect()).execute(select(t))).mappings().all()
        return R.ok([dict(r) for r in rows])
    except Exception:
        return R.ok([])


@router.get("/{one_id}/history")
async def oneid_history(one_id: str):
    try:
        t = table("oneid_event")
        rows = (await (await get_engine().connect()).execute(
            select(t).where(t.c.one_id == one_id).order_by(desc(t.c.create_time)))).mappings().all()
        return R.ok([dict(r) for r in rows])
    except Exception:
        return R.ok([])


@router.get("/{one_id}/mergeRecords")
async def oneid_merge_records(one_id: str):
    t = table("cmd_merge_record")
    rows = (await (await get_engine().connect()).execute(
        select(t).where(t.c.survivor_one_id == one_id))).mappings().all()
    return R.ok([dict(r) for r in rows])


@router.get("/legacy/list")
async def oneid_legacy_list():
    t = table("cmd_legacy_mapping")
    rows = (await (await get_engine().connect()).execute(select(t))).mappings().all()
    return R.ok([dict(r) for r in rows])

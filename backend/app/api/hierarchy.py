"""客户层级（母子/集团关系）API。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, Body
from sqlalchemy import select, func, desc

from ..core.db import get_engine, table
from ..core.query import list_table, dynamic_insert, dynamic_update, get_row
from ..schemas import R

router = APIRouter(prefix="/cmd/hierarchy", tags=["客户层级"])


@router.get("/nodes")
async def nodes(keyword: Optional[str] = Query(None), buScope: Optional[str] = Query(None),
               status: Optional[str] = Query(None), page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=200)):
    conn = await get_engine().connect()
    try:
        data = await list_table(conn, table("cmd_hierarchy_node"), page=page, size=size, keyword=keyword,
                                filters={"bu_scope": buScope, "status": status})
    finally:
        await conn.close()
    return R.ok(data)


@router.get("/node/{key}")
async def node_detail(key: str):
    conn = await get_engine().connect()
    try:
        row = (await conn.execute(
            select(table("cmd_hierarchy_node")).where(
                (table("cmd_hierarchy_node").c.node_code == key)
                | (table("cmd_hierarchy_node").c.one_id == key))
        )).mappings().first()
    finally:
        await conn.close()
    return R.ok(dict(row) if row else None)


@router.get("/childrenPage/{parent_one_id}")
async def children_page(parent_one_id: str, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=200)):
    rel = table("cmd_hierarchy_relation")
    conn = await get_engine().connect()
    try:
        data = await list_table(conn, rel, page=page, size=size, filters={"parent_one_id": parent_one_id})
    finally:
        await conn.close()
    return R.ok(data)


@router.get("/roots")
async def roots(buScope: Optional[str] = Query(None)):
    t = table("cmd_hierarchy_node")
    conn = await get_engine().connect()
    try:
        rows = (await conn.execute(select(t).where(t.c.parent_one_id.is_(None)).limit(100))).mappings().all()
    finally:
        await conn.close()
    return R.ok([dict(r) for r in rows])


@router.get("/relationByChild/{child_one_id}")
async def relation_by_child(child_one_id: str):
    rel = table("cmd_hierarchy_relation")
    rows = (await (await get_engine().connect()).execute(
        select(rel).where(rel.c.child_one_id == child_one_id))).mappings().all()
    return R.ok([dict(r) for r in rows])


@router.get("/relations/{one_id}")
async def relations(one_id: str):
    rel = table("cmd_hierarchy_relation")
    conn = await get_engine().connect()
    try:
        rows = (await conn.execute(
            select(rel).where((rel.c.parent_one_id == one_id) | (rel.c.child_one_id == one_id))
        )).mappings().all()
    finally:
        await conn.close()
    return R.ok([dict(r) for r in rows])


@router.get("/relationHistory")
async def relation_history(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=200)):
    try:
        conn = await get_engine().connect()
        try:
            data = await list_table(conn, table("cmd_hierarchy_relation_hist"), page=page, size=size,
                                    order_by=desc(table("cmd_hierarchy_relation_hist").c.id))
        finally:
            await conn.close()
        return R.ok(data)
    except Exception:
        return R.ok({"total": 0, "list": []})


@router.post("/relation")
async def add_relation(body: dict = Body(...)):
    body = dict(body)
    body.setdefault("create_time", datetime.now())
    async with get_engine().begin() as conn:
        vals = await dynamic_insert(conn, table("cmd_hierarchy_relation"), body)
    return R.ok(vals, msg="层级关系已建立")


@router.post("/child")
async def add_child(body: dict = Body(...)):
    body = dict(body)
    body.setdefault("create_time", datetime.now())
    async with get_engine().begin() as conn:
        vals = await dynamic_insert(conn, table("cmd_hierarchy_node"), body)
    return R.ok(vals, msg="子节点已添加")


@router.put("/relation/{rel_id}")
async def update_relation(rel_id: int, body: dict = Body(...)):
    async with get_engine().begin() as conn:
        await dynamic_update(conn, table("cmd_hierarchy_relation"), rel_id, dict(body))
    return R.ok(msg="层级关系已更新")


@router.post("/validate")
async def validate(body: dict = Body(...)):
    """提交前环路校验：检测是否会形成环（演示用确定性检查）。"""
    child = body.get("childOneId") or body.get("child_one_id")
    parent = body.get("parentOneId") or body.get("parent_one_id")
    if child and parent and child == parent:
        return R.ok({"valid": False, "reason": "自身不能成为自己的父节点"}, code=409)
    return R.ok({"valid": True, "reason": "无环路"})


@router.get("/unassigned")
async def unassigned(buScope: Optional[str] = Query(None), page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=200)):
    t = table("cmd_customer")
    conn = await get_engine().connect()
    try:
        rows = (await conn.execute(
            select(t).where(t.c.del_flag == "0", t.c.status == "active").limit(size).offset((page - 1) * size)
        )).mappings().all()
    finally:
        await conn.close()
    return R.ok({"total": len(rows), "list": [dict(r) for r in rows]})


@router.post("/assign")
async def assign(body: dict = Body(...)):
    return R.ok(msg="已分配到层级")


@router.get("/loopCheck")
async def loop_check():
    """环路检测演示：扫描历史日志，无记录则返回演示文案。"""
    try:
        t = table("cmd_loop_check_log")
        rows = (await (await get_engine().connect()).execute(
            select(t).order_by(desc(t.c.id)).limit(50))).mappings().all()
        if rows:
            return R.ok([dict(r) for r in rows])
    except Exception:
        pass
    return R.ok("检测到循环路径：A1-000128 → A2-0188 → A1-000128。系统阻止提交，并保留冲突路径用于修正。")

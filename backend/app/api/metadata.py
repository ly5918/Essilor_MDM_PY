"""元数据（动态表单）API。"""
from __future__ import annotations

from typing import Optional

from datetime import datetime
from fastapi import APIRouter, Query, Body
from sqlalchemy import select, func

from ..core.db import get_engine, table
from ..core.query import dynamic_insert, dynamic_update, get_row
from ..schemas import R

router = APIRouter(prefix="/cmd/metadata", tags=["元数据"])


@router.get("/field/list")
async def field_list(modelCode: str = Query("CUSTOMER"), status: str = Query("1")):
    f = table("md_field")
    rows = (await (await get_engine().connect()).execute(
        select(f).where(f.c.model_code == modelCode).where(f.c.status == status)
        .order_by(f.c.order_num))).mappings().all()
    return R.ok([dict(r) for r in rows])


@router.get("/valueset/list")
async def valueset_list():
    vs = table("md_value_set")
    rows = (await (await get_engine().connect()).execute(select(vs))).mappings().all()
    return R.ok([dict(r) for r in rows])


@router.delete("/field/{field_id}")
async def field_delete(field_id: int):
    async with get_engine().begin() as conn:
        await conn.execute(
            table("md_field").update().where(table("md_field").c.id == field_id)
            .values(del_flag="1", status="0"))
    return R.ok(msg="字段已删除")


@router.post("/field")
async def field_create(body: dict = Body(...)):
    body = dict(body)
    body.setdefault("create_time", datetime.now())
    async with get_engine().begin() as conn:
        vals = await dynamic_insert(conn, table("md_field"), body)
    return R.ok(vals, msg="字段已创建")


@router.put("/field")
async def field_update(body: dict = Body(...)):
    body = dict(body)
    fid = body.pop("id", None)
    if fid is None:
        return R.fail("缺少 id", code=400)
    async with get_engine().begin() as conn:
        await dynamic_update(conn, table("md_field"), fid, body)
    return R.ok(msg="字段已更新")


@router.get("/field/{field_id}")
async def field_detail(field_id: int):
    row = await get_row(await get_engine().connect(), table("md_field"), field_id)
    if row is None:
        return R.fail("字段不存在", code=404)
    return R.ok(row)


@router.get("/version/list")
async def version_list():
    mv = table("md_model_version")
    rows = (await (await get_engine().connect()).execute(select(mv).order_by(mv.c.id.desc()))).mappings().all()
    return R.ok([dict(r) for r in rows])


@router.post("/version")
async def version_create(body: dict = Body(...)):
    body = dict(body)
    body.setdefault("create_time", datetime.now())
    async with get_engine().begin() as conn:
        vals = await dynamic_insert(conn, table("md_model_version"), body)
    return R.ok(vals, msg="版本已创建")


@router.post("/version/publish")
async def version_publish(version: Optional[str] = Query(None)):
    """发布元数据版本：将目标版本置为已发布（published='1'），其余置 0。"""
    mv = table("md_model_version")
    async with get_engine().begin() as conn:
        cond = mv.c.version == version if version else mv.c.id == (
            (await conn.execute(select(func.max(mv.c.id)).select_from(mv))).scalar() or 0)
        await conn.execute(mv.update().values(published="0"))
        await conn.execute(mv.update().where(cond).values(published="1", status="1"))
    return R.ok(msg="元数据版本已发布")


@router.post("/valueset")
async def valueset_create(body: dict = Body(...)):
    body = dict(body)
    body.setdefault("create_time", datetime.now())
    async with get_engine().begin() as conn:
        vals = await dynamic_insert(conn, table("md_value_set"), body)
    return R.ok(vals, msg="值集已创建")


@router.delete("/valueset/{vs_id}")
async def valueset_delete(vs_id: int):
    async with get_engine().begin() as conn:
        await conn.execute(table("md_value_set").update().where(table("md_value_set").c.id == vs_id).values(del_flag="1"))
    return R.ok(msg="值集已删除")

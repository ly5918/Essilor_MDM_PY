"""元数据（动态表单）API。"""
from __future__ import annotations

from typing import Optional

from datetime import datetime
from fastapi import APIRouter, Query, Body
from sqlalchemy import select, func

from ..core.db import get_engine, table
from ..core.query import dynamic_insert, dynamic_update, get_row
from ..schemas import R
from ..services import metadata_service

router = APIRouter(prefix="/cmd/metadata", tags=["元数据"])


@router.get("/field/list")
async def field_list(keyword: str = Query(None), modelCode: str = Query(None)):
    """字段目录：与 Java selectFieldList 对齐——过滤软删、可选过滤、回填 deleteGuard。"""
    async with get_engine().connect() as conn:
        rows = await metadata_service.list_fields(conn, keyword=keyword, model_code=modelCode)
    return R.ok(rows)


@router.get("/valueset/list")
async def valueset_list():
    vs = table("md_value_set")
    rows = (await (await get_engine().connect()).execute(select(vs))).mappings().all()
    return R.ok([dict(r) for r in rows])


@router.delete("/field/{field_id}")
async def field_delete(field_id: int):
    """逻辑删除字段；核心主数据字段拒绝删除（对应 Java deleteField 守卫）。"""
    try:
        async with get_engine().begin() as conn:
            await metadata_service.delete_field(conn, field_id)
    except ValueError as e:
        return R.fail(str(e), code=500)
    return R.ok(msg="字段已删除")


@router.post("/field")
async def field_create(body: dict = Body(...)):
    body = dict(body)
    body.setdefault("create_time", datetime.now())
    async with get_engine().begin() as conn:
        # 不带 version_no 的创建请求（脚本/第三方直调）默认落入当前已发布版本，
        # 否则 NULL/默认值会散落成游离行，把旧版本顶成第二个「Current」（历史污染）
        if not body.get("version_no"):
            body["version_no"] = await metadata_service.current_published_version(conn)
        # 未显式指定状态时按 Draft 落库（发布动作只能走版本发布，保持单一 Current 口径）
        body.setdefault("status", "1")
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
    """模型版本列表：由 md_field 按版本号推导（对应 Java selectVersionList）。"""
    async with get_engine().connect() as conn:
        rows = await metadata_service.list_versions(conn)
    return R.ok(rows)


@router.post("/version")
async def version_create():
    """新建版本：克隆当前已发布版本为 Draft，返回新版本号（前端不携带请求体）。"""
    async with get_engine().begin() as conn:
        target = await metadata_service.create_version(conn)
    return R.ok(target, msg="已创建新版本")


@router.api_route("/version/publish", methods=["PUT", "POST"])
async def version_publish(version: Optional[str] = Query(None)):
    """发布模型版本（前端走 PUT，与 Java @PutMapping 对齐；POST 保留兼容）。"""
    try:
        async with get_engine().begin() as conn:
            message = await metadata_service.publish_version(conn, version)
    except ValueError as e:
        return R.fail(str(e), code=400)
    return R.ok(message)


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

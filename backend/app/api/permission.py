"""权限矩阵 / 角色管理 API（cmd_role / cmd_role_permission / cmd_user_role）。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select

from ..core.db import get_engine, table
from ..core.query import list_table, dynamic_insert, dynamic_update
from ..schemas import R

router = APIRouter(prefix="/cmd/permission", tags=["权限"])


@router.get("/role/list")
async def role_list(page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=200),
                    keyword: Optional[str] = None, status: Optional[str] = None):
    conn = await get_engine().connect()
    try:
        data = await list_table(conn, table("cmd_role"), page=page, size=size,
                                filters={"status": status}, keyword=keyword,
                                order_by=table("cmd_role").c.order_num.asc())
    finally:
        await conn.close()
    return R.ok(data)


@router.get("/matrix")
async def permission_matrix(roleCode: Optional[str] = None):
    """返回角色 × 资源权限矩阵。"""
    conn = await get_engine().connect()
    try:
        roles = (await conn.execute(select(table("cmd_role")).where(
            table("cmd_role").c.del_flag == "0").order_by(table("cmd_role").c.order_num)
        )).mappings().all()
        perms_stmt = select(table("cmd_role_permission")).where(
            table("cmd_role_permission").c.del_flag == "0")
        if roleCode:
            perms_stmt = perms_stmt.where(table("cmd_role_permission").c.role_code == roleCode)
        perms = (await conn.execute(perms_stmt)).mappings().all()
    finally:
        await conn.close()
    role_list = [dict(r) for r in roles]
    perm_list = [dict(p) for p in perms]
    # 组装矩阵：{ resource_code: { role_code: access_mode } }
    matrix: dict = {}
    for p in perm_list:
        res = p.get("resource_code")
        matrix.setdefault(res, {"resource_name": p.get("resource_name"), "perm_type": p.get("perm_type"), "roles": {}})
        matrix[res]["roles"][p.get("role_code")] = p.get("access_mode")
    return R.ok({
        "roles": [{"roleCode": r.get("role_code"), "roleName": r.get("role_name"),
                   "roleType": r.get("role_type")} for r in role_list],
        "resources": matrix,
    })


class RolePayload(BaseModel):
    role_code: Optional[str] = None
    role_name: Optional[str] = None
    role_type: Optional[str] = None
    scope_type: Optional[str] = None
    default_bu: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


@router.post("/role")
async def create_role(payload: RolePayload):
    async with get_engine().begin() as conn:
        vals = await dynamic_insert(conn, table("cmd_role"), payload.model_dump(exclude_none=True))
    return R.ok({"id": vals.get("id")}, msg="角色已创建")


@router.put("/role/{role_id}")
async def update_role(role_id: int, payload: RolePayload):
    async with get_engine().begin() as conn:
        await dynamic_update(conn, table("cmd_role"), role_id, payload.model_dump(exclude_none=True))
    return R.ok(msg="角色已更新")


@router.put("/role")
async def update_role_by_body(payload: RolePayload, id: Optional[int] = Query(None)):
    """前端把 id 放 body 的更新形式。"""
    if not id:
        return R.fail("缺少角色 id", code=400)
    return await update_role(id, payload)

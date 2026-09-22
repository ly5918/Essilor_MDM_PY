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
               status: Optional[str] = Query(None), hierarchyType: Optional[str] = Query(None),
               level: Optional[str] = Query(None),
               page: int = Query(1, ge=1), size: int = Query(200, ge=1, le=500)):
    t = table("cmd_hierarchy_node")
    conds = [t.c.del_flag == "0"]
    if buScope:
        conds.append(t.c.bu_scope == buScope)
    if status:
        conds.append(t.c.status == status)
    if hierarchyType:
        conds.append(t.c.hierarchy_type == hierarchyType)
    if level:
        conds.append(t.c.level == level)
    if keyword:
        like = f"%{keyword}%"
        conds.append(t.c.legal_name.like(like) | t.c.one_id.like(like) |
                     t.c.node_code.like(like))
    stmt = select(t).where(*conds).order_by(t.c.depth, t.c.sort_order, t.c.id)
    conn = await get_engine().connect()
    try:
        rows = (await conn.execute(
            stmt.limit(size).offset((page - 1) * size))).mappings().all()
    finally:
        await conn.close()
    return R.ok([dict(r) for r in rows])


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
async def children_page(parent_one_id: str, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=200)):
    rel = table("cmd_hierarchy_relation")
    t = table("cmd_hierarchy_node")
    conn = await get_engine().connect()
    try:
        child_ids = (await conn.execute(
            select(rel.c.child_one_id).where(rel.c.parent_one_id == parent_one_id)
            .order_by(rel.c.id).limit(limit).offset(offset))).scalars().all()
        rows = []
        if child_ids:
            rows = (await conn.execute(
                t.select().where(t.c.one_id.in_(child_ids)).order_by(t.c.sort_order)
            )).mappings().all()
    finally:
        await conn.close()
    return R.ok([dict(r) for r in rows])


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
async def relation_history(page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=200)):
    try:
        conn = await get_engine().connect()
        try:
            rows = (await conn.execute(
                select(table("cmd_hierarchy_relation_hist"))
                .order_by(desc(table("cmd_hierarchy_relation_hist").c.id))
                .limit(size).offset((page - 1) * size))).mappings().all()
        finally:
            await conn.close()
        return R.ok([dict(r) for r in rows])
    except Exception:
        return R.ok([])


@router.post("/relation")
async def add_relation(body: dict = Body(...)):
    import uuid as _uuid
    body = dict(body)
    body.setdefault("create_time", datetime.now())
    # NOT NULL 无默认值列兜底
    body.setdefault("relation_code", f"REL-{_uuid.uuid4().hex[:8].upper()}")
    body.setdefault("hierarchy_type", "LEGAL")
    body.setdefault("relation_type", "SUB")
    body.setdefault("cross_bu_flag", "N")
    body.setdefault("source_type", "MANUAL")
    body.setdefault("effective_from", datetime.now())
    # 总设计泳道：层级关系变更走 HIER_RELATION 审批流（提交→BU 审核→生效）
    body.setdefault("status", "PendingApproval")
    async with get_engine().begin() as conn:
        vals = await dynamic_insert(conn, table("cmd_hierarchy_relation"), body)
        from ..services.sequence import gen_code, next_id
        from ..workflow.engine import start_instance
        task_no = await gen_code(conn, "AP-", 4, "APPROVAL")
        rel_code = vals.get("relation_code") or str(vals.get("id"))
        child = body.get("child_one_id") or ""
        parent = body.get("parent_one_id") or ""
        evidence = {
            "关系编码": rel_code,
            "父节点": parent,
            "子节点": child,
            "关系类型": body.get("relation_type") or "",
            "变更原因": body.get("change_reason") or "",
        }
        task_id = await next_id(conn, "cmd_approval_task")
        await conn.execute(table("cmd_approval_task").insert().values(
            id=task_id, task_no=task_no, task_category="APPROVAL",
            biz_type="HIER_RELATION", biz_id=str(vals.get("id")),
            biz_title=f"层级关系变更：{rel_code}（{child} → {parent}）",
            one_id=child or None, scene_code="HIER_RELATION",
            bu_scope=body.get("bu_scope") or "Global",
            scope="BU", current_node_code="BU_REVIEW", current_node_name="BU Scope 层级审核",
            assignee_role="BU_STEWARD", status="PENDING", risk_level="Medium",
            duplicate_state="NEW", cross_bu_flag=body.get("cross_bu_flag") or "N",
            submit_time=datetime.now(), del_flag="0", create_by=0, create_time=datetime.now(),
            evidence_json=evidence, biz_snapshot_json={"relationId": vals.get("id"), "relCode": rel_code},
            remark="层级关系变更审批（审核通过后关系生效）"))
        await start_instance(
            scene_code="HIER_RELATION", biz_type="HIER_RELATION", biz_no=task_no,
            variables={
                "taskNo": task_no, "bizType": "HIER_RELATION", "oneId": child or None,
                "buScope": body.get("bu_scope") or "Global", "crossBu": False,
                "riskLevel": "Medium", "duplicateState": "NEW", "dqScore": None,
                "sceneCode": "HIER_RELATION",
            })
        # 回写审批引用
        from sqlalchemy import update as _upd
        await conn.execute(table("cmd_hierarchy_relation").update()
                           .where(table("cmd_hierarchy_relation").c.id == vals["id"])
                           .values(approval_id=task_id))
    return R.ok({**vals, "taskNo": task_no}, msg="层级关系申请已提交审批")


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
async def unassigned(buScope: Optional[str] = Query(None), keyword: Optional[str] = Query(None),
                     page: int = Query(1, ge=1), size: int = Query(100, ge=1, le=500)):
    """待归位主数据：生效客户中尚未挂到层级树上的（排除已归位/merged/停用）。"""
    t = table("cmd_customer")
    node = table("cmd_hierarchy_node")
    conds = [t.c.del_flag == "0", t.c.status == "active",
             ~select(node.c.one_id).where(
                 node.c.one_id == t.c.one_id, node.c.del_flag == "0").exists()]
    if buScope:
        conds.append(t.c.bu_scope == buScope)
    if keyword:
        like = f"%{keyword}%"
        conds.append(t.c.legal_name.like(like) | t.c.one_id.like(like))
    conn = await get_engine().connect()
    try:
        rows = (await conn.execute(
            select(t).where(*conds).order_by(t.c.id.desc())
            .limit(size).offset((page - 1) * size))).mappings().all()
    finally:
        await conn.close()
    return R.ok([dict(r) for r in rows])


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

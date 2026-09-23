"""客户层级（母子/集团关系）API。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, Body
from sqlalchemy import select, func, desc, or_

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
        # 🚨 防重预检：同一子客户已有生效/在途关系时明确拒绝（此前撞唯一键直接 500，
        #    错误被前端弹窗吞掉——用户看不到提示、审批任务也不生成）
        rel_t = table("cmd_hierarchy_relation")
        dup = (await conn.execute(
            select(rel_t).where(
                rel_t.c.child_one_id == (body.get("child_one_id") or ""),
                rel_t.c.del_flag == "0",
                rel_t.c.status.in_(("PendingApproval", "Effective"))))).mappings().first()
        if dup:
            return R.fail(
                f"子客户 {body.get('child_one_id')} 已存在"
                f"{'生效' if dup['status'] == 'Effective' else '审批中'}的层级关系"
                f"（{dup['relation_code']}：{dup['child_one_id']} → {dup['parent_one_id']}），请勿重复提交",
                code=409)
        vals = await dynamic_insert(conn, rel_t, body)
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


# ---------- 归位预检 / 归位（对齐总设计：Loop Check → 级别推导 → 完整路径重建 → 祖先计数刷新 → 关系留痕） ----------

_LEVEL_BY_DEPTH = {2: "A2", 3: "A1"}


_HIER_TYPE_BY_LEVEL = {"A3": "COMMERCIAL", "A2": "LEGAL", "A1": "DOOR"}


def _hier_type_by_level(level: str) -> str:
    """级别 → 层级类型（对齐 Java CmdConstants.hierTypeOfLevel）：
    A3 顶层集团 → Commercial Entity（COMMERCIAL）；
    A2 主账户 → Main Account（LEGAL）；A1 门店 → Door（DOOR）。"""
    return _HIER_TYPE_BY_LEVEL.get(level or "", "LEGAL")


async def _node_by_one_id(conn, one_id: str):
    if not one_id:
        return None
    n = table("cmd_hierarchy_node")
    row = (await conn.execute(
        select(n).where(n.c.one_id == one_id, n.c.del_flag == "0"))).mappings().first()
    return dict(row) if row else None


async def _customer_by_one_id(conn, one_id: str):
    if not one_id:
        return None
    t = table("cmd_customer")
    row = (await conn.execute(
        select(t).where(t.c.one_id == one_id, t.c.del_flag == "0"))).mappings().first()
    return dict(row) if row else None


async def mount_node_for_relation(conn, child_one_id: str, parent_one_id: str, now=None) -> bool:
    """层级关系审批生效后，把子客户同步挂到层级树（与 /assign 的节点登记同口径）。

    🚨 此前审批回调只把 relation 置 Effective、不写 node —— relation 与 node 脱节，
    客户在层级树和「待归位」列表里永远看不到挂载结果（已生效却仍待归位）。
    父节点不在树上（数据异常）时返回 False 且不动树。
    """
    now = now or datetime.now()
    parent = await _node_by_one_id(conn, parent_one_id)
    if not parent:
        return False
    child_level = _LEVEL_BY_DEPTH.get(parent["depth"] + 1, "A1")
    child_depth = parent["depth"] + 1
    child = await _node_by_one_id(conn, child_one_id)
    cust = await _customer_by_one_id(conn, child_one_id)
    child_name = (child or {}).get("legal_name") or (cust or {}).get("legal_name") or child_one_id
    full_path = f"{parent['full_path'] or ''}{child_one_id}/"
    path_names = f"{parent['path_names']}/{child_name}" if parent.get("path_names") else child_name
    node_t = table("cmd_hierarchy_node")
    if child:
        await conn.execute(node_t.update().where(node_t.c.id == child["id"]).values(
            parent_one_id=parent_one_id, level=child_level, depth=child_depth,
            node_code=f"{child_level}-{child_one_id}", full_path=full_path,
            path_names=path_names, hierarchy_type=_hier_type_by_level(child_level),
            status="active", update_time=now))
    else:
        await dynamic_insert(conn, node_t, {
            "node_code": f"{child_level}-{child_one_id}", "one_id": child_one_id,
            "legal_name": child_name,
            "hierarchy_type": _hier_type_by_level(child_level),
            "level": child_level, "parent_one_id": parent_one_id,
            "full_path": full_path, "path_names": path_names,
            "depth": child_depth, "bu_scope": (cust or {}).get("bu_scope"),
            "children_count": 0, "descendants": 0,
            "status": "active", "sort_order": 0, "effective_from": now,
            "create_by": 0, "create_time": now, "update_time": now})
    fresh = await _node_by_one_id(conn, child_one_id)
    if fresh:
        await _rebuild_subtree(conn, fresh, child_depth, full_path, path_names)
    # 祖先计数 +1（新链）
    chain = await _chain_up(conn, parent_one_id)
    for anc in chain:
        await conn.execute(node_t.update().where(node_t.c.id == anc["id"]).values(
            children_count=anc["children_count"]
            + (1 if anc["one_id"] == parent_one_id else 0),
            descendants=anc["descendants"] + 1, update_time=now))
    return True


async def _chain_up(conn, one_id: str, max_depth: int = 8):
    """沿 parent_one_id 向上收集祖先节点（含自身），用于环路检测与路径构建。"""
    chain, seen, cur = [], set(), one_id
    while cur and cur not in seen and len(chain) < max_depth:
        seen.add(cur)
        node = await _node_by_one_id(conn, cur)
        if not node:
            break
        chain.append(node)
        cur = node.get("parent_one_id")
    return chain


def _check_item(check_type: str, label: str, result: str, message: str,
                conflict_path: str | None = None, suggestion: str | None = None):
    return {"checkType": check_type, "label": label, "checkResult": result,
            "message": message, "conflictPath": conflict_path, "suggestion": suggestion}


async def _evaluate_relation(conn, parent_one_id: str, child_one_id: str,
                             change_reason: str = "", as_root: bool = False) -> dict:
    """归位/改挂前的完整预检：环路 + 级别 + 路径 + 跨BU，返回前端 HierarchyValidateVO（camelCase）。

    as_root=True 且无父节点时走「顶级节点」口径：登记为 A3 集团（第 1 级），不建父子关系。
    """
    import time
    t0 = time.time()
    parent = await _node_by_one_id(conn, parent_one_id)
    child_node = await _node_by_one_id(conn, child_one_id)
    child_cust = await _customer_by_one_id(conn, child_one_id)

    parent_name = (parent or {}).get("legal_name") or parent_one_id
    child_name = (child_node or {}).get("legal_name") \
        or (child_cust or {}).get("legal_name") or child_one_id

    # ---------- 顶级节点（A3 集团）：系统刚上线时的第一个节点 ----------
    if as_root and not parent_one_id:
        root_checks: list[dict] = []
        if not child_node and not child_cust:
            root_checks.append(_check_item("TARGET", "目标节点", "FAIL",
                                           f"{child_one_id} 既不在层级树中，也不是生效客户主数据",
                                           suggestion="请先在「新建客户」完成创建并审批通过，或选择已有节点"))
        else:
            src = "层级树" if child_node else "客户主档"
            root_checks.append(_check_item("TARGET", "目标节点", "PASS",
                                           f"{child_name} 存在于{src}，可作为顶级节点"))
            root_checks.append(_check_item("LOOP", "环路检测", "PASS",
                                           "顶级节点没有上级链路，不存在环路风险"))
            root_checks.append(_check_item("LEVEL", "级别推导", "PASS",
                                           "顶级节点固定为 A3（第 1 级），无需父节点推导"))
            root_checks.append(_check_item("PATH", "路径重建", "PASS",
                                           f"归位后完整路径：{child_name}"))
            root_checks.append(_check_item("CROSS_BU", "跨BU检查", "PASS",
                                           "顶级节点无父节点可比对，不涉及跨 BU"))
        root_passed = not any(c["checkResult"] == "FAIL" for c in root_checks)
        return {
            "checkCode": "", "passed": root_passed,
            "blockedReason": next((c["message"] for c in root_checks if c["checkResult"] == "FAIL"), None),
            "relationLabel": f"（顶级节点）→ {child_name}",
            "parentName": "（无 · 顶级节点）", "childName": child_name,
            "parentLevel": "", "parentDepth": 0,
            "childLevel": "A3", "childDepth": 1,
            "previewPath": f"/{child_one_id}/", "previewPathNames": child_name,
            "crossBu": False, "requiresGcApproval": False, "relationType": "",
            "maxDepth": 3, "childMounted": child_node is not None,
            "childCurrentParentOneId": (child_node or {}).get("parent_one_id") or "",
            "childCurrentLevel": (child_node or {}).get("level") or "",
            "checks": root_checks,
            "executeTime": datetime.now().isoformat(timespec="seconds"),
            "durationMs": int((time.time() - t0) * 1000),
        }
    parent_level = (parent or {}).get("level") or ""
    parent_depth = int((parent or {}).get("depth") or 0)
    child_depth = parent_depth + 1
    child_level = _LEVEL_BY_DEPTH.get(child_depth, "")
    cross_bu = bool(parent and (child_node or child_cust)
                    and (child_node or child_cust).get("bu_scope")
                    and parent.get("bu_scope") != (child_node or child_cust).get("bu_scope"))

    checks: list[dict] = []

    # 1. 环路检测：父节点向上链路中不能出现子节点
    loop_path, loop_names = "", ""
    if not parent:
        checks.append(_check_item("LOOP", "环路检测", "FAIL", f"父节点 {parent_one_id} 不存在或已删除"))
    else:
        chain = await _chain_up(conn, parent_one_id)
        if child_one_id in {c["one_id"] for c in chain}:
            loop_names = " → ".join(c["legal_name"] for c in chain)
            checks.append(_check_item("LOOP", "环路检测", "FAIL",
                                      f"环路冲突：{child_name} 在 {parent_name} 的上级链路中",
                                      conflict_path=loop_names,
                                      suggestion="请选择该子节点子树之外的节点作为父节点"))
        else:
            checks.append(_check_item("LOOP", "环路检测", "PASS", "无环路，父子关系合法"))

    # 2. 级别推导：A3 → A2 → A1，最多三级
    if not child_level:
        checks.append(_check_item("LEVEL", "级别推导", "FAIL",
                                  f"{parent_name}（{parent_level}）已是末端 A1，不能再挂子节点",
                                  suggestion="请选择 A3 / A2 节点作为目标父节点"))
    else:
        checks.append(_check_item("LEVEL", "级别推导", "PASS",
                                  f"{parent_name}（{parent_level}，第 {parent_depth} 级）→ 归位后 {child_level}（第 {child_depth} 级）"))

    # 3. 完整路径重建
    preview_path = preview_names = ""
    if parent and child_level:
        preview_path = f"{parent['full_path'] or ''}{child_one_id}/"
        preview_names = f"{parent['path_names']}/{child_name}" if parent.get("path_names") else child_name
        checks.append(_check_item("PATH", "路径重建", "PASS", f"归位后完整路径：{preview_names}"))
    elif parent:
        checks.append(_check_item("PATH", "路径重建", "WARN", "级别校验未通过，无法构建路径"))

    # 4. 跨 BU 检查：跨 BU 归位需升级 GC Scope 审批
    if cross_bu:
        checks.append(_check_item("CROSS_BU", "跨BU检查", "WARN",
                                  f"父节点 BU {parent.get('bu_scope')} 与客户 BU {(child_node or child_cust).get('bu_scope')} 不一致",
                                  suggestion="跨 BU 归位需升级 GC Scope 审批"))
    else:
        checks.append(_check_item("CROSS_BU", "跨BU检查", "PASS", "同 BU 归位"))

    passed = not any(c["checkResult"] == "FAIL" for c in checks)
    blocked = next((c["message"] for c in checks if c["checkResult"] == "FAIL"), None)

    return {
        "checkCode": "",
        "passed": passed,
        "blockedReason": blocked,
        "relationLabel": f"{parent_name} → {child_name}",
        "parentName": parent_name,
        "childName": child_name,
        "parentLevel": parent_level,
        "parentDepth": parent_depth,
        "childLevel": child_level,
        "childDepth": child_depth,
        "previewPath": preview_path,
        "previewPathNames": preview_names,
        "crossBu": cross_bu,
        "requiresGcApproval": cross_bu,
        "relationType": f"{parent_level}_{child_level}" if parent_level and child_level else "",
        "maxDepth": 3,
        "childMounted": child_node is not None,
        "childCurrentParentOneId": (child_node or {}).get("parent_one_id") or "",
        "childCurrentLevel": (child_node or {}).get("level") or "",
        "checks": checks,
        "executeTime": datetime.now().isoformat(timespec="seconds"),
        "durationMs": int((time.time() - t0) * 1000),
    }


async def _rebuild_subtree(conn, node: dict, depth: int, full_path: str, path_names: str):
    """节点改挂后递归重建其子树的 depth / level / full_path / path_names。"""
    n = table("cmd_hierarchy_node")
    children = (await conn.execute(
        select(n).where(n.c.parent_one_id == node["one_id"], n.c.del_flag == "0"))).mappings().all()
    for ch in children:
        ch = dict(ch)
        new_depth = depth + 1
        new_level = _LEVEL_BY_DEPTH.get(new_depth, ch.get("level") or "A1")
        new_path = f"{full_path}{ch['one_id']}/"
        new_names = f"{path_names}/{ch['legal_name']}" if path_names else ch["legal_name"]
        await conn.execute(n.update().where(n.c.id == ch["id"]).values(
            depth=new_depth, level=new_level, full_path=new_path, path_names=new_names,
            update_time=datetime.now()))
        await _rebuild_subtree(conn, ch, new_depth, new_path, new_names)


@router.post("/validate")
async def validate(body: dict = Body(...)):
    """归位预检：环路检测 + 级别推导 + 完整路径重建 + 跨BU检查（实时读库，与提交口径一致）。

    root=true 且无父节点 → 顶级节点预检（登记为 A3 集团）。
    """
    child = body.get("childOneId") or body.get("child_one_id") or ""
    parent = body.get("parentOneId") or body.get("parent_one_id") or ""
    as_root = bool(body.get("root") or body.get("asRoot"))
    async with get_engine().connect() as conn:
        vo = await _evaluate_relation(conn, parent, child, body.get("changeReason") or "",
                                      as_root=as_root)
    return R.ok(vo)


@router.post("/assign")
async def assign(body: dict = Body(...)):
    """归位落库：登记/更新节点 + 新建关系 + 历史留痕 + 祖先计数刷新（不覆盖历史）。

    root=true 且未传父节点时为「建立顶级节点」：登记为 A3 集团（第 1 级），不建父子关系行。
    """
    import json as _json
    import uuid as _uuid

    one_id = body.get("oneId") or body.get("one_id") or ""
    parent_one_id = body.get("parentId") or body.get("parent_one_id") or ""
    change_reason = body.get("changeReason") or body.get("change_reason") or "新门店归属确认"
    remark = body.get("remark")
    as_root = bool(body.get("root") or body.get("asRoot"))
    if not one_id or (not parent_one_id and not as_root):
        return R.fail("缺少 oneId 或目标父节点", code=400)

    node_t = table("cmd_hierarchy_node")
    rel_t = table("cmd_hierarchy_relation")
    hist_t = table("cmd_hierarchy_relation_hist")
    now = datetime.now()

    async with get_engine().begin() as conn:
        vo = await _evaluate_relation(conn, parent_one_id, one_id, change_reason, as_root=as_root)
        if not vo["passed"]:
            return R.fail(vo.get("blockedReason") or "校验未通过", code=409)

        # ---------- 顶级节点：只登记节点，不建父子关系（relation.parent_one_id 非空） ----------
        if as_root and not parent_one_id:
            old_parent_one_id = vo["childCurrentParentOneId"]
            child_node = await _node_by_one_id(conn, one_id)
            if child_node:
                await conn.execute(node_t.update().where(node_t.c.id == child_node["id"]).values(
                    parent_one_id=None, level="A3", depth=1, hierarchy_type="COMMERCIAL",
                    node_code=f"A3-{one_id}", full_path=vo["previewPath"],
                    path_names=vo["previewPathNames"], status="active", update_time=now))
            else:
                child_cust = await _customer_by_one_id(conn, one_id)
                await dynamic_insert(conn, node_t, {
                    "node_code": f"A3-{one_id}", "one_id": one_id,
                    "legal_name": vo["childName"], "hierarchy_type": "COMMERCIAL",
                    "level": "A3", "parent_one_id": None,
                    "full_path": vo["previewPath"], "path_names": vo["previewPathNames"],
                    "depth": 1, "bu_scope": (child_cust or {}).get("bu_scope"),
                    "children_count": 0, "descendants": 0,
                    "status": "active", "sort_order": 0, "effective_from": now,
                    "create_by": 0, "create_time": now, "update_time": now,
                })
            # 由子节点提升为顶级：旧父子关系失效 + 旧链计数还原
            if old_parent_one_id:
                old_rels = (await conn.execute(
                    select(rel_t).where(rel_t.c.child_one_id == one_id,
                                        rel_t.c.parent_one_id == old_parent_one_id,
                                        rel_t.c.del_flag == "0"))).mappings().all()
                for old in old_rels:
                    await conn.execute(rel_t.update().where(rel_t.c.id == old["id"]).values(
                        status="Replaced", del_flag="1", update_time=now))
                    await dynamic_insert(conn, hist_t, {
                        "relation_id": old["id"], "relation_code": old["relation_code"],
                        "version_no": 1, "operation": "REPLACE",
                        "hierarchy_type": old["hierarchy_type"], "relation_type": old["relation_type"],
                        "parent_one_id": old["parent_one_id"], "child_one_id": one_id,
                        "status": "Replaced", "change_reason": change_reason,
                        "snapshot_json": _json.dumps({k: str(v) for k, v in dict(old).items()},
                                                     ensure_ascii=False),
                        "remark": remark, "create_by": 0, "create_time": now,
                    })
                old_chain = await _chain_up(conn, old_parent_one_id)
                for anc in old_chain:
                    await conn.execute(node_t.update().where(node_t.c.id == anc["id"]).values(
                        children_count=anc["children_count"] - (1 if anc["one_id"] == old_parent_one_id else 0),
                        descendants=anc["descendants"] - 1, update_time=now))
                fresh_root = await _node_by_one_id(conn, one_id)
                await _rebuild_subtree(conn, fresh_root, 1, vo["previewPath"], vo["previewPathNames"])
            return R.ok({"oneId": one_id, "parentId": None, "level": "A3", "root": True},
                        msg=f"顶级节点已建立：{vo['childName']} 已登记为 A3 集团（第 1 级）")

        parent = await _node_by_one_id(conn, parent_one_id)
        child_node = await _node_by_one_id(conn, one_id)
        child_cust = await _customer_by_one_id(conn, one_id)
        child_name = vo["childName"]
        child_level, child_depth = vo["childLevel"], vo["childDepth"]
        full_path = vo["previewPath"]
        path_names = vo["previewPathNames"]
        old_parent_one_id = vo["childCurrentParentOneId"]

        # 1) 节点登记 / 更新（新归位客户登记为节点；已在树上则视为改挂）
        #    必须同时刷新 hierarchy_type：此前只改 level/parent，导致「已登记待归位」
        #    （UNASSIGNED）的节点行归位后类型仍是 UNASSIGNED，被前端建树时继续剔除——
        #    归位成功了却永远不出现在层级树上。
        if child_node:
            await conn.execute(node_t.update().where(node_t.c.id == child_node["id"]).values(
                parent_one_id=parent_one_id, level=child_level, depth=child_depth,
                node_code=f"{child_level}-{one_id}", full_path=full_path, path_names=path_names,
                hierarchy_type=_hier_type_by_level(child_level),
                status="active", update_time=now))
        else:
            await dynamic_insert(conn, node_t, {
                "node_code": f"{child_level}-{one_id}", "one_id": one_id,
                "legal_name": child_name,
                "hierarchy_type": _hier_type_by_level(child_level),
                "level": child_level, "parent_one_id": parent_one_id,
                "full_path": full_path, "path_names": path_names,
                "depth": child_depth, "bu_scope": (child_cust or {}).get("bu_scope"),
                "children_count": 0, "descendants": 0,
                "status": "active", "sort_order": 0, "effective_from": now,
                "create_by": 0, "create_time": now, "update_time": now,
            })

        # 2) 改挂时旧关系失效（留痕不物理删除）
        if old_parent_one_id:
            old_rels = (await conn.execute(
                select(rel_t).where(rel_t.c.child_one_id == one_id,
                                    rel_t.c.parent_one_id == old_parent_one_id,
                                    rel_t.c.del_flag == "0"))).mappings().all()
            for old in old_rels:
                await conn.execute(rel_t.update().where(rel_t.c.id == old["id"]).values(
                    status="Replaced", del_flag="1", update_time=now))
                await dynamic_insert(conn, hist_t, {
                    "relation_id": old["id"], "relation_code": old["relation_code"],
                    "version_no": 1, "operation": "REPLACE",
                    "hierarchy_type": old["hierarchy_type"], "relation_type": old["relation_type"],
                    "parent_one_id": old["parent_one_id"], "child_one_id": one_id,
                    "status": "Replaced", "change_reason": change_reason,
                    "snapshot_json": _json.dumps({k: str(v) for k, v in dict(old).items()},
                                                 ensure_ascii=False),
                    "remark": remark, "create_by": 0, "create_time": now,
                })

        # 3) 新关系 + 历史留痕
        rel_vals = await dynamic_insert(conn, rel_t, {
            "relation_code": f"REL-{_uuid.uuid4().hex[:8].upper()}",
            "hierarchy_type": _hier_type_by_level(child_level), "relation_type": vo["relationType"],
            "parent_one_id": parent_one_id, "child_one_id": one_id,
            "bu_scope": (child_cust or {}).get("bu_scope"),
            "cross_bu_flag": "Y" if vo["crossBu"] else "N",
            "effective_from": now, "status": "Effective",
            "change_reason": change_reason, "source_type": "MANUAL",
            "remark": remark, "create_by": 0, "create_time": now,
        })
        await dynamic_insert(conn, hist_t, {
            "relation_id": rel_vals["id"], "relation_code": rel_vals["relation_code"],
            "version_no": 1, "operation": "CREATE",
            "hierarchy_type": _hier_type_by_level(child_level), "relation_type": vo["relationType"],
            "parent_one_id": parent_one_id, "child_one_id": one_id,
            "effective_from": now, "status": "Effective", "change_reason": change_reason,
            "snapshot_json": _json.dumps(
                {"parent": parent_one_id, "child": one_id, "level": child_level,
                 "fullPath": full_path, "pathNames": path_names}, ensure_ascii=False),
            "remark": remark, "create_by": 0, "create_time": now,
        })

        # 4) 子树路径重建（改挂且子节点带子树时）
        fresh = await _node_by_one_id(conn, one_id)
        await _rebuild_subtree(conn, fresh, child_depth, full_path, path_names)

        # 5) 祖先计数刷新：新链 +1，旧链（改挂时）-1
        chain = await _chain_up(conn, parent_one_id)
        for anc in chain:
            await conn.execute(node_t.update().where(node_t.c.id == anc["id"]).values(
                children_count=anc["children_count"] + (1 if anc["one_id"] == parent_one_id else 0),
                descendants=anc["descendants"] + 1, update_time=now))
        if old_parent_one_id:
            old_chain = await _chain_up(conn, old_parent_one_id)
            for anc in old_chain:
                await conn.execute(node_t.update().where(node_t.c.id == anc["id"]).values(
                    children_count=anc["children_count"] - (1 if anc["one_id"] == old_parent_one_id else 0),
                    descendants=anc["descendants"] - 1, update_time=now))

    return R.ok({"oneId": one_id, "parentId": parent_one_id, "level": vo["childLevel"]},
                msg=f"归位成功：{vo['childName']} 已挂到 {vo['parentName']} 之下（{vo['childLevel']}）")


@router.get("/unassigned")
async def unassigned(buScope: Optional[str] = Query(None), keyword: Optional[str] = Query(None),
                     page: int = Query(1, ge=1), size: int = Query(500, ge=1, le=1000)):
    """待归位主数据：已生效、但**尚未挂到 A3-A2-A1 层级树**上的客户。

    口径必须与「客户列表 → 层级归属」列严格互补（测试报告 BUG-PY-05）：
    - 前端建树时会把 `hierarchy_type='UNASSIGNED'` 的登记节点剔除（还没挂父节点）；
      客户列表只要查不到层级位置、且状态 active，就标「待归位」。
    - 所以本接口不能只用「有没有节点行」判断：客户审批通过后若已自动登记为
      UNASSIGNED 节点，节点行存在却没上树，用「有无节点行」会把这批客户从待归位
      列表里漏掉 → 出现「客户详情标待归位、待归位列表却是 0」的计数矛盾。
    现在的判定：**不存在任何「非 UNASSIGNED」的层级节点**即视为待归位
    （无节点行、仅有登记节点两种情况都覆盖），并排除已合并与已停用客户。
    """
    t = table("cmd_customer")
    node = table("cmd_hierarchy_node")
    # 「已上树」= 存在一条不是登记态（UNASSIGNED）的节点行；NULL 类型视为已上树（历史数据兜底）
    mounted = select(node.c.one_id).where(
        node.c.one_id == t.c.one_id,
        node.c.del_flag == "0",
        or_(node.c.hierarchy_type.is_(None), node.c.hierarchy_type != "UNASSIGNED"),
    ).exists()
    conds = [
        t.c.del_flag == "0",
        t.c.status == "active",
        ~mounted,
        # 已并入其它主档的记录不再单独归位（文档口径：排除 merged）
        or_(t.c.merged_to_one_id.is_(None), t.c.merged_to_one_id == ""),
    ]
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
        # 节点登记情况（已登记待归位 / 未登记）——状态列与「建议层级」的数据源
        node_rows = {}
        one_ids = [r["one_id"] for r in rows if r.get("one_id")]
        if one_ids:
            for n in (await conn.execute(
                select(node).where(node.c.one_id.in_(one_ids),
                                   node.c.del_flag == "0"))).mappings().all():
                node_rows[n["one_id"]] = dict(n)
    finally:
        await conn.close()
    out = []
    for r in rows:
        d = dict(r)
        hit = node_rows.get(d.get("one_id"))
        out.append({
            # 显式输出前端 VO 契约（与 CmdHierarchyUnassignedRow 一一对应）
            "oneId": d.get("one_id"),
            "legalName": d.get("legal_name"),
            "buScope": d.get("bu_scope"),
            "customerStatus": d.get("status"),
            "sourceSystem": d.get("source_system"),
            "dqScore": d.get("dq_score"),
            "approvedTime": d.get("approved_time") or d.get("create_time"),
            "registered": hit is not None,
            "nodeCode": (hit or {}).get("node_code") or "",
            # 建议层级：登记节点上已有级别则沿用，否则默认 A1（门店/子公司层级）
            "suggestedLevel": (hit or {}).get("level") or "A1",
            "remark": d.get("remark") or "",
        })
    return R.ok(out)


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

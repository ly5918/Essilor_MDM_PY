"""客户变更 API（CUSTOMER_CHANGE 审批流）。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import select, func, desc

from ..core.db import get_engine, table
from ..core.query import list_table
from ..schemas import R, ChangeSubmit, ChangeResubmit
from ..services import sequence as seq

router = APIRouter(prefix="/cmd/change", tags=["变更"])


@router.get("/list")
async def change_list(
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    changeType: Optional[str] = Query(None),
    buScope: Optional[str] = Query(None),
    oneId: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
):
    t = table("cmd_change_request")
    conds = [t.c.del_flag == "0"]
    if status:
        conds.append(t.c.status == status)
    if changeType:
        conds.append(t.c.change_type == changeType)
    if buScope:
        conds.append(t.c.bu_scope == buScope)
    if oneId:
        conds.append(t.c.one_id == oneId)
    if keyword:
        like = f"%{keyword}%"
        conds.append(t.c.request_code.like(like) | t.c.one_id.like(like) |
                     t.c.legal_name.like(like))
    stmt = select(t).where(*conds)
    conn = await get_engine().connect()
    try:
        rows = (await conn.execute(
            stmt.order_by(t.c.id.desc()).limit(size).offset((page - 1) * size))).mappings().all()
        total = (await conn.execute(
            select(func.count()).select_from(t).where(*conds))).scalar()
    finally:
        await conn.close()
    return R.ok({"total": int(total), "rows": [dict(r) for r in rows]})


@router.post("")
async def submit_change(payload: ChangeSubmit):
    engine = get_engine()
    async with engine.begin() as conn:
        # 客户名称取主档法人名称：此前直接把 one_id 写进 legal_name，
        # 停用/变更列表「客户名称」列显示成 GC-00000004（总设计要求展示客户名称）
        cust_row = (await conn.execute(
            select(table("cmd_customer"))
            .where(table("cmd_customer").c.one_id == payload.one_id))).mappings().first()
        legal_name = (cust_row or {}).get("legal_name") or payload.one_id
        request_code = await seq.gen_code(conn, "CH-", 4, "CHANGE")
        rid = await seq.next_id(conn, "cmd_change_request")
        await conn.execute(table("cmd_change_request").insert().values(
            id=rid, request_code=request_code, one_id=payload.one_id,
            legal_name=legal_name, change_type=payload.change_type,
            change_reason=payload.change_reason, bu_scope=payload.bu_scope,
            target_status=payload.target_status, is_key_change=payload.is_key_change,
            status="PENDING", del_flag="0", create_by=0, create_time=datetime.now(),
        ))
        tid = await seq.next_id(conn, "cmd_approval_task")

        # ---- 字段级变更明细（Before/After 证据链）----
        # 此前后端直接丢弃前端上传的 diffs，cmd_change_diff 恒为空，
        # 审批弹窗「治理证据」没有修改的内容。此处补齐：
        # 1) 属性变更：按前端明细逐行落库，Before 由主档当前值回填；
        # 2) 逻辑停用：合成一行「状态」diff（active → target_status）；
        # 3) 同步把差异写进审批任务 evidence_json，审批弹窗可直接看到修改内容。
        md_rows = (await conn.execute(
            select(table("md_field").c.field_code, table("md_field").c.field_name,
                   table("md_field").c.is_key_field, table("md_field").c.is_sensitive,
                   table("md_field").c.physical_column)
            .where(table("md_field").c.del_flag == "0", table("md_field").c.status == "0")
        )).mappings().all()
        md_map: dict = {}
        for m in md_rows:
            # 多版本字段目录按 field_code 去重（发布态优先，已在查询里过滤）
            md_map.setdefault(m["field_code"], m)
        cust = dict(cust_row) if cust_row else {}

        def _before_of(field_code: str) -> tuple[Optional[str], bool, bool]:
            m = md_map.get(field_code)
            if m is None:
                return None, False, False
            col = m["physical_column"] or field_code
            raw = cust.get(col)
            before = None if raw is None else str(raw)
            return before, (m["is_key_field"] == "Y"), (m["is_sensitive"] == "Y")

        diff_rows: list[dict] = []
        for item in (payload.diffs or []):
            if not item.field_code:
                continue
            before, is_key, is_sensitive = _before_of(item.field_code)
            after = (item.after_value or "").strip()
            if (before or "") == after:
                flag = "SAME"
            elif not before:
                flag = "ADD"
            elif not after:
                flag = "DELETE"
            else:
                flag = "MODIFY"
            diff_rows.append({
                "field_code": item.field_code,
                "field_name": item.field_name or (md_map.get(item.field_code, {}) or {}).get("field_name") or item.field_code,
                "before_value": before, "after_value": after,
                "is_key_field": "Y" if is_key else "N",
                "is_sensitive": "Y" if is_sensitive else "N",
                "change_flag": flag,
            })
        if (payload.change_type or "").upper() == "DEACTIVATE":
            # 停用类变更本身不采集字段行：合成「状态」行，让修改内容可见可追溯
            before, _, _ = _before_of("status")
            diff_rows.append({
                "field_code": "status", "field_name": "状态",
                "before_value": before or "active",
                "after_value": (payload.target_status or "inactive").strip(),
                "is_key_field": "Y", "is_sensitive": "N", "change_flag": "MODIFY",
            })

        has_key = any(r["is_key_field"] == "Y" for r in diff_rows)
        if diff_rows:
            await conn.execute(table("cmd_change_request").update()
                               .where(table("cmd_change_request").c.id == rid)
                               .values(is_key_change="Y" if has_key else "N"))
            for idx, r in enumerate(diff_rows):
                did = await seq.next_id(conn, "cmd_change_diff")
                await conn.execute(table("cmd_change_diff").insert().values(
                    id=did, request_id=rid, request_code=request_code, order_num=idx,
                    del_flag="0", create_by=0, create_time=datetime.now(), **r))

        type_text = "逻辑停用" if (payload.change_type or "").upper() == "DEACTIVATE" else "属性变更"
        evidence = {"变更类型": type_text, "客户名称": legal_name}
        for r in diff_rows:
            before_txt = r["before_value"] if r["before_value"] not in (None, "") else "(空)"
            after_txt = r["after_value"] if r["after_value"] not in (None, "") else "(清空)"
            key_mark = "（关键）" if r["is_key_field"] == "Y" else ""
            evidence[f"{r['field_name']}{key_mark}"] = f"{before_txt} → {after_txt}"
        if payload.change_reason:
            evidence["变更说明"] = payload.change_reason
        if payload.effective_date:
            evidence["计划生效日"] = str(payload.effective_date)

        await conn.execute(table("cmd_approval_task").insert().values(
            id=tid, task_no=request_code, task_category="APPROVAL",
            biz_type="CUSTOMER_CHANGE", biz_id=payload.one_id, biz_title=legal_name,
            one_id=payload.one_id, scene_code="CUSTOMER_CHANGE", bu_scope=payload.bu_scope,
            scope="BU", current_node_code="BU_REVIEW", current_node_name="BU初审",
            assignee_role="BU_STEWARD", status="PENDING", risk_level="Medium",
            evidence_json=evidence,
            submit_time=datetime.now(), del_flag="0", create_by=0, create_time=datetime.now(),
        ))
        from ..services.trace import log_step
        await log_step(conn, one_id=payload.one_id, task_no=request_code,
                       step_type="SUBMIT", node_code="APPLY", node_name="提交变更申请",
                       action_type="SUBMIT", action_name="提交申请",
                       operator_name="applicant", operator_role="BU_USER",
                       from_status="-", to_status="PENDING")
        # 提交动作轨迹（与 Java 口径一致：审批轨迹 / 流程跟踪节点历史的数据源）
        from ..services.trace import log_action
        await log_action(conn, task_id=tid, task_no=request_code, one_id=payload.one_id,
                         action_type="SUBMIT", action_name="提交申请",
                         from_node_code="APPLY", to_node_code="APPLY",
                         operator_name="applicant", operator_role="BU_USER",
                         opinion=payload.change_reason or "")
    return R.ok({"request_code": request_code}, msg="变更申请已提交")


@router.post("/{request_code}/resubmit")
async def resubmit_change(request_code: str, payload: ChangeResubmit):
    """被退回变更单「修改重报」（总设计：BU Scope 退回或补充材料 → 申请人修改后重进初审）。

    - 仅 status=RETURNED 可重报；仅更新传入的非空字段（变更原因 / 目标状态）；
    - 变更单状态 RETURNED → PENDING，审批任务行重开到 BU Scope 初审；
    - 流程实例用 reset_instance_node 真正拉回 BU_REVIEW 等待位（与新建申请重报同机制）。
    """
    from ..services.trace import log_action, log_step
    from ..workflow.engine import reset_instance_node

    engine = get_engine()
    async with engine.begin() as conn:
        t = table("cmd_change_request")
        row = (await conn.execute(
            select(t).where(t.c.request_code == request_code, t.c.del_flag == "0")
        )).mappings().first()
        if row is None:
            return R.fail("变更单不存在", code=400)
        if (row["status"] or "") != "RETURNED":
            return R.fail(f"仅被退回的变更单可修改重报（当前状态：{row['status']}）", code=400)

        updates: dict = {k: v for k, v in {
            "change_reason": (payload.change_reason or "").strip() or None,
            "target_status": (payload.target_status or "").strip() or None,
        }.items() if v}
        remark = (payload.remark or "").strip() or "修改重报"
        applicant = (payload.applicant_name or "").strip() or "Business User"

        # 1) 变更单：改字段 + 状态回 PENDING
        await conn.execute(t.update().where(t.c.request_code == request_code).values(
            **updates, status="PENDING", update_time=datetime.now()))
        # 2) 审批任务行：重开到 BU Scope 初审（BU 队列可见）
        await conn.execute(table("cmd_approval_task").update()
                           .where(table("cmd_approval_task").c.task_no == request_code)
                           .values(status="PENDING", scope="BU",
                                   current_node_code="BU_REVIEW", current_node_name="BU初审",
                                   assignee_role="BU_STEWARD", submit_time=datetime.now()))
        # 3) 流程实例镜像 + 引擎：拉回 BU_REVIEW READY 位
        await reset_instance_node(request_code, "BU_REVIEW")
        # 4) 轨迹：时间线 + 步骤条体现「修改重报」
        await log_action(
            conn, task_id=row["id"], task_no=request_code, one_id=row["one_id"],
            action_type="RESUBMIT", action_name=remark,
            from_node_code="APPLY", to_node_code="BU_REVIEW",
            operator_name=applicant, operator_role="BU_USER",
            opinion=updates.get("change_reason") or remark,
        )
        await log_step(
            conn, one_id=row["one_id"], task_no=request_code,
            step_type="BUSINESS", node_code="BU_REVIEW", node_name="BU Scope 初审",
            action_type="RESUBMIT", action_name=remark,
            operator_name=applicant, operator_role="BU_USER",
            from_status="RETURNED", to_status="PENDING",
            opinion=updates.get("change_reason") or remark,
        )
    return R.ok({"requestCode": request_code, "status": "PENDING",
                 "currentNodeName": "BU Scope 初审"},
                msg="修改重报成功，已重新进入 BU Scope 初审")


@router.get("/fields")
async def change_fields():
    """可变更字段（取元数据字段表）。"""
    t = table("md_field")
    # 连接必须显式关闭：此前内联 get_engine().connect() 不归还连接池，
    # 退出时触发 SAWarning「garbage collector ... non-checked-in connection」
    async with get_engine().connect() as conn:
        rows = (await conn.execute(
            select(t).where(t.c.del_flag == "0"))).mappings().all()
    return R.ok([dict(r) for r in rows])


@router.get("/kpi")
async def change_kpi():
    t = table("cmd_change_request")
    conn = await get_engine().connect()
    try:
        total = (await conn.execute(select(func.count()).select_from(t).where(t.c.del_flag == "0"))).scalar() or 0
        pending = (await conn.execute(select(func.count()).select_from(t).where(t.c.status == "PENDING"))).scalar() or 0
        approved = (await conn.execute(select(func.count()).select_from(t).where(t.c.status == "APPROVED"))).scalar() or 0
        effective = (await conn.execute(select(func.count()).select_from(t).where(t.c.status == "EFFECTIVE"))).scalar() or 0
    finally:
        await conn.close()
    return R.ok({"total": total, "pending": pending, "approved": approved, "effective": effective})


@router.get("/versions/{one_id}")
async def change_versions(one_id: str):
    t = table("cmd_change_request")
    async with get_engine().connect() as conn:
        rows = (await conn.execute(
            select(t).where(t.c.one_id == one_id).order_by(desc(t.c.create_time)))).mappings().all()
    return R.ok([dict(r) for r in rows])


@router.get("/{one_id}/deactivateResult")
async def deactivate_result(one_id: str):
    """停用预演：返回该主数据是否被其他记录引用 / 关联数量。"""
    cust = table("cmd_customer")
    rel = table("cmd_hierarchy_relation")
    conn = await get_engine().connect()
    try:
        cust_row = (await conn.execute(select(cust).where(cust.c.one_id == one_id))).mappings().first()
        relations = 0
        try:
            relations = (await conn.execute(
                select(func.count()).select_from(rel).where(rel.c.child_one_id == one_id))).scalar() or 0
        except Exception:
            relations = 0
    finally:
        await conn.close()
    return R.ok({"one_id": one_id, "exists": cust_row is not None,
                 "status": cust_row["status"] if cust_row else None,
                 "relation_count": relations})


@router.post("/{request_code}/cancel")
async def cancel_change(request_code: str):
    async with get_engine().begin() as conn:
        await conn.execute(
            table("cmd_change_request").update()
            .where(table("cmd_change_request").c.request_code == request_code)
            .values(status="CANCELLED"))
    return R.ok(msg="变更单已取消")


@router.get("/{request_code}/detail")
async def change_detail(request_code: str):
    t = table("cmd_change_request")
    async with get_engine().connect() as conn:
        row = (await conn.execute(
            select(t).where(t.c.request_code == request_code))).mappings().first()
        if row is None:
            return R.fail("变更单不存在", code=404)
        data = dict(row)
        # 字段级差异 + 审批轨迹：前端 ChangeDetailDialog 依赖 row.diffs / row.trail，
        # 此前只回裸申请行，详情弹窗 Before/After 恒为「无字段级差异」
        diffs = (await conn.execute(
            select(table("cmd_change_diff"))
            .where(table("cmd_change_diff").c.request_code == request_code,
                   table("cmd_change_diff").c.del_flag == "0")
            .order_by(table("cmd_change_diff").c.order_num, table("cmd_change_diff").c.id)
        )).mappings().all()
        acts = (await conn.execute(
            select(table("cmd_approval_action"))
            .where(table("cmd_approval_action").c.task_no == request_code,
                   table("cmd_approval_action").c.del_flag == "0")
            .order_by(table("cmd_approval_action").c.action_time)
        )).mappings().all()
    data["diffs"] = [dict(r) for r in diffs]
    result_map = {"APPROVE": "Approved", "REJECT": "Rejected", "RETURN": "Returned",
                  "ESCALATE": "Escalated", "SUBMIT": "Submitted", "RESUBMIT": "Resubmitted"}
    data["trail"] = [{
        "time": a["action_time"].strftime("%Y-%m-%d %H:%M:%S") if a.get("action_time") else None,
        "role": a.get("operator_role"),
        "operator": a.get("operator_name"),
        "action": a.get("action_name") or a.get("action_type"),
        "node": a.get("to_node_code"),
        "result": result_map.get((a.get("action_type") or "").upper(), a.get("action_type")),
        "opinion": a.get("opinion"),
    } for a in acts]
    data["approvalTaskNo"] = request_code
    return R.ok(data)


@router.post("/{request_code}/effect")
async def effect_change(request_code: str):
    """变更「生效」：唯一写主档入口。"""
    engine = get_engine()
    async with engine.begin() as conn:
        cr = (await conn.execute(
            table("cmd_change_request").select()
            .where(table("cmd_change_request").c.request_code == request_code))).mappings().first()
        if cr is None:
            return R.fail("变更单不存在", code=404)
        cr = dict(cr)
        await conn.execute(
            table("cmd_change_request").update()
            .where(table("cmd_change_request").c.request_code == request_code)
            .values(status="EFFECTIVE", effective_time=datetime.now()))
        # 若停用类变更，更新主档状态（change_type 大小写不敏感；
        # target_status 统一小写——全库主档状态约定为 active/inactive）
        if (cr["change_type"] or "").upper() == "DEACTIVATE" and cr.get("target_status"):
            await conn.execute(
                table("cmd_customer").update().where(table("cmd_customer").c.one_id == cr["one_id"])
                .values(status=(cr["target_status"] or "").lower(), effective_to=datetime.now()))
    return R.ok(msg="变更已生效")

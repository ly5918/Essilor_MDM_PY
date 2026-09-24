"""治理 / 合并 API（MERGE 审批流）。"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query
from sqlalchemy import select, func

from ..core.db import get_engine, table
from ..schemas import R, MergeLaunch
from ..services import sequence as seq

router = APIRouter(prefix="/cmd/governance", tags=["治理"])


@router.get("/list")
async def gov_list(taskType: str = Query(None), status: str = Query(None)):
    t = table("cmd_governance_task")
    stmt = select(t)
    if taskType:
        stmt = stmt.where(t.c.task_type == taskType)
    if status:
        stmt = stmt.where(t.c.status == status)
    rows = (await (await get_engine().connect()).execute(stmt)).mappings().all()
    return R.ok([dict(r) for r in rows])


@router.get("/stats")
async def gov_stats():
    t = table("cmd_governance_task")
    conn = await get_engine().connect()
    try:
        total = (await conn.execute(select(func.count()).select_from(t))).scalar()
        open_ = (await conn.execute(select(func.count()).select_from(t).where(t.c.status == "OPEN"))).scalar()
    finally:
        await conn.close()
    return R.ok({"total": total, "open": open_})


@router.post("/merge")
async def launch_merge(
    sourceOneId: str = Query(default="", alias="sourceOneId"),
    targetOneId: str = Query(default="", alias="targetOneId"),
    reason: str = Query(default=None),
    payload: MergeLaunch = None,
):
    """发起合并：创建治理任务 + MERGE 审批待办（流程首次审批时启动）。
    兼容两种入参：前端 query 参数（sourceOneId/targetOneId）或 JSON body（MergeLaunch）。"""
    survivor = (payload.survivor_one_id if payload and payload.survivor_one_id else sourceOneId) or ""
    merged = (payload.merged_one_id if payload and payload.merged_one_id else targetOneId) or ""
    if not survivor or not merged:
        return R.fail("缺少合并参数（survivor/merged One ID）")
    reason_txt = (payload.reason if payload else None) or reason
    payload = MergeLaunch(survivor_one_id=survivor, merged_one_id=merged, reason=reason_txt)
    engine = get_engine()
    async with engine.begin() as conn:
        # 是否跨BU：按两条主档的 bu_scope **实际对比**判定（旧版写死 CROSS_BU/Y——
        # 同BU合并也被打上跨BU标记、被迫升级 GC，BU「确认合并」永远办不完流程）。
        # 同BU → SUSPECT 治理任务 + cross_bu_flag=N（BU 可直接定案办结）；
        # 跨BU → CROSS_BU + Y（BU 初审只能升级 GC）。任一侧 BU 缺失按跨BU从紧处理。
        cust = table("cmd_customer")
        pair = {r["one_id"]: (r["bu_scope"] or "").strip() for r in (
            await conn.execute(
                select(cust.c.one_id, cust.c.bu_scope)
                .where(cust.c.one_id.in_([survivor, merged])))).mappings().all()}
        s_bu = pair.get(survivor, "")
        m_bu = pair.get(merged, "")
        cross_bu = not (s_bu and m_bu and s_bu == m_bu)
        common_bu = "" if cross_bu else s_bu
        task_code = await seq.gen_code(conn, "GOV-", 4, "GOVERNANCE")
        gid = await seq.next_id(conn, "cmd_governance_task")
        await conn.execute(table("cmd_governance_task").insert().values(
            id=gid, task_code=task_code,
            task_type="CROSS_BU" if cross_bu else "SUSPECT",
            biz_type="CUSTOMER", biz_id=payload.merged_one_id,
            one_id=payload.merged_one_id, subject=payload.merged_one_id,
            bu_scope=common_bu,
            cross_bu_flag="Y" if cross_bu else "N", risk_level="High",
            status="OPEN", evidence_json={"survivor_one_id": payload.survivor_one_id,
                                          "merged_one_id": payload.merged_one_id},
            del_flag="0", create_by=0, create_time=datetime.now(),
        ))
        merge_no = await seq.gen_code(conn, "MG-", 4, "MERGE_APPROVAL")
        tid = await seq.next_id(conn, "cmd_approval_task")
        # 合并审批走两级口径（对齐 swimlane._merge_scene 泳道：BU初审 → GC决策）：
        # 任务先落 BU Scope 初审（scope=BU → 进 BU 待办）。
        # · 跨BU（cross_bu_flag=Y）：BU 只能升级GC或退回，升级后 do_action 自动切
        #   scope=GC / assignee_role=GC_STEWARD 进 GC 队列定案；
        # · 同BU（cross_bu_flag=N）：BU 可直接「确认合并」办结并执行合并。
        # 旧值 scope="GC" + assignee_role="GC_STEWARD" 与 BU初审节点自相矛盾——
        # 单子出现在 GC 队列、BU 待办看不到，流程跟踪却显示「待 BU Steward 初审」。
        await conn.execute(table("cmd_approval_task").insert().values(
            id=tid, task_no=merge_no, task_category="GOVERNANCE",
            biz_type="MERGE", biz_id=payload.merged_one_id, biz_title=task_code,
            one_id=payload.merged_one_id, scene_code="MERGE", bu_scope=common_bu,
            scope="BU", current_node_code="BU_REVIEW", current_node_name="BU初审",
            assignee_role="BU_STEWARD", status="PENDING", risk_level="High",
            cross_bu_flag="Y" if cross_bu else "N", submit_time=datetime.now(),
            evidence_json={"survivor_one_id": payload.survivor_one_id,
                           "merged_one_id": payload.merged_one_id},
            del_flag="0", create_by=0, create_time=datetime.now(),
        ))
        from ..services.trace import log_step
        await log_step(conn, one_id=payload.merged_one_id, task_no=merge_no,
                       step_type="SUBMIT", node_code="CAND", node_name="疑似重复发现",
                       action_type="SUBMIT", action_name="发起合并流程",
                       operator_name="steward", operator_role="GC_STEWARD",
                       from_status="-", to_status="PENDING")
        # 提交动作轨迹（流程跟踪「疑似重复发现」节点历史的数据源）
        from ..services.trace import log_action
        await log_action(conn, task_id=tid, task_no=merge_no, one_id=payload.merged_one_id,
                         action_type="SUBMIT", action_name="发起合并流程",
                         from_node_code="CAND", to_node_code="CAND",
                         operator_name="steward", operator_role="GC_STEWARD",
                         opinion=payload.reason if getattr(payload, "reason", None) else "")
    return R.ok({"task_code": task_code, "merge_approval_no": merge_no}, msg="合并流程已发起")

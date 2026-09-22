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
async def launch_merge(payload: MergeLaunch):
    """发起合并：创建治理任务 + MERGE 审批待办（流程首次审批时启动）。"""
    engine = get_engine()
    async with engine.begin() as conn:
        task_code = await seq.gen_code(conn, "GOV-", 4, "GOVERNANCE")
        gid = await seq.next_id(conn, "cmd_governance_task")
        await conn.execute(table("cmd_governance_task").insert().values(
            id=gid, task_code=task_code, task_type="CROSS_BU",
            biz_type="CUSTOMER", biz_id=payload.merged_one_id,
            one_id=payload.merged_one_id, subject=payload.merged_one_id,
            bu_scope="", cross_bu_flag="Y", risk_level="High",
            status="OPEN", evidence_json={"survivor_one_id": payload.survivor_one_id,
                                          "merged_one_id": payload.merged_one_id},
            del_flag="0", create_by=0, create_time=datetime.now(),
        ))
        merge_no = await seq.gen_code(conn, "MG-", 4, "MERGE_APPROVAL")
        tid = await seq.next_id(conn, "cmd_approval_task")
        await conn.execute(table("cmd_approval_task").insert().values(
            id=tid, task_no=merge_no, task_category="GOVERNANCE",
            biz_type="MERGE", biz_id=payload.merged_one_id, biz_title=task_code,
            one_id=payload.merged_one_id, scene_code="MERGE", bu_scope="",
            scope="GC", current_node_code="BU_REVIEW", current_node_name="BU初审",
            assignee_role="GC_STEWARD", status="PENDING", risk_level="High",
            cross_bu_flag="Y", submit_time=datetime.now(),
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

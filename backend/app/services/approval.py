"""审批服务：doAction 推进 SpiffWorkflow 并触发业务回调。

对应原 CmdApprovalServiceImpl.doAction + linkFlowEngine：
- 首次动作时若流程未启动则启动（变更/合并）；新建客户在提交时已启动；
- approve/reject/escalate 驱动 BPMN 网关；
- 流程 END 时按 biz_type 回调：CUSTOMER_CREATE→发布主档；MERGE→execMergeTask；CUSTOMER_CHANGE→同步变更单状态。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, text

from ..core.db import get_engine, table, flow_instance_table
from ..workflow.engine import start_instance, complete_current
from .customer import publish_customer


async def _ensure_flow_started(conn, task: dict) -> None:
    biz_no = task["task_no"]
    exist = (await conn.execute(
        flow_instance_table.select().where(flow_instance_table.c.biz_no == biz_no))).first()
    if exist is not None:
        return
    biz_type = task["biz_type"]
    await start_instance(
        scene_code=biz_type, biz_type=biz_type, biz_no=biz_no,
        variables={
            "taskNo": biz_no, "bizType": biz_type, "bizId": task["biz_id"],
            "oneId": task.get("one_id") or "", "buScope": task.get("bu_scope") or "",
            "crossBu": task.get("cross_bu_flag") == "Y",
            "riskLevel": task.get("risk_level") or "Medium",
            "duplicateState": task.get("duplicate_state") or "NEW",
            "dqScore": float(task["dq_score"]) if task.get("dq_score") is not None else None,
            "sceneCode": biz_type,
        },
    )


async def do_action(task_no: str, action: str, actor: str,
                    opinion: str = "", role: Optional[str] = None) -> dict:
    engine = get_engine()
    async with engine.begin() as conn:
        task = (await conn.execute(
            table("cmd_approval_task").select()
            .where(table("cmd_approval_task").c.task_no == task_no))).mappings().first()
        if task is None:
            raise RuntimeError(f"审批任务不存在: {task_no}")
        task = dict(task)

        await _ensure_flow_started(conn, task)
        result = await complete_current(task_no, action, actor, opinion or "")
        outcome = result.get("outcome")
        node = result.get("current_node")
        next_role = result.get("role")

        # 轨迹：审批动作（时间线数据源）
        from .trace import log_action
        cur_node_code = task.get("current_node_code") or "BU_REVIEW"
        await log_action(
            conn, task_id=task.get("id"), task_no=task_no, one_id=task.get("one_id"),
            action_type=action.upper(), action_name=opinion or action.upper(),
            from_node_code=cur_node_code, to_node_code=node or cur_node_code,
            operator_name=actor, operator_role=task.get("assignee_role") or "SYSTEM",
            opinion=opinion or "",
        )

        # 更新审批任务行
        status = task["status"]
        if result["status"] == "COMPLETED":
            status = "REJECTED" if outcome == "rejected" else "COMPLETED"
        elif action == "escalate":
            status = "ESCALATED"
        elif action == "reject":
            status = "REJECTED"

        # 步骤日志（步骤条数据源）
        from .trace import log_step
        node_name_map = {"BU_REVIEW": "BU Scope 初审", "GC_REVIEW": "GC Scope 决策"}
        await log_step(
            conn, one_id=task.get("one_id"), task_no=task_no,
            step_type="BUSINESS", node_code=node or cur_node_code,
            node_name=node_name_map.get(node or cur_node_code, node or cur_node_code),
            action_type=action.upper(), action_name=opinion or action.upper(),
            operator_name=actor, operator_role=task.get("assignee_role") or "SYSTEM",
            from_status=task.get("status") or "-", to_status=status,
            opinion=opinion or "",
        )
        update_vals = {
            "current_node_code": node or task["current_node_code"],
            "assignee_role": next_role or task["assignee_role"],
            "opinion": opinion,
            "status": status,
        }
        if result["status"] == "COMPLETED":
            update_vals["finish_time"] = datetime.now()
        await conn.execute(
            table("cmd_approval_task").update()
            .where(table("cmd_approval_task").c.task_no == task_no).values(**update_vals))

        # 业务回调
        biz_type = task["biz_type"]
        if biz_type == "CUSTOMER_CREATE":
            app = (await conn.execute(
                table("cmd_customer_application").select()
                .where(table("cmd_customer_application").c.app_no == task_no))).mappings().first()
            if app is not None:
                await publish_customer(conn, dict(app), outcome or "approved")
        elif biz_type == "MERGE" and outcome == "approved":
            await exec_merge_task(conn, task)
        elif biz_type == "CUSTOMER_CHANGE" and outcome in ("approved",):
            await conn.execute(
                table("cmd_change_request").update()
                .where(table("cmd_change_request").c.request_code == task_no)
                .values(status="APPROVED", approved_by=0, approved_time=datetime.now()))

    result["task_status"] = status
    return result


async def exec_merge_task(conn, task: dict) -> None:
    """合并执行：被合并方置 inactive，写 cmd_merge_record 生效。"""
    evidence = task.get("evidence_json") or {}
    survivor = evidence.get("survivor_one_id") or task.get("biz_id")
    merged = evidence.get("merged_one_id")
    if not merged:
        return
    cust = table("cmd_customer")
    await conn.execute(cust.update().where(cust.c.one_id == merged).values(
        status="inactive", effective_to=datetime.now(), merged_to_one_id=survivor))
    from . import sequence as seq
    merge_code = await seq.gen_code(conn, "MRG-", 4, "MERGE")
    mid = await seq.next_id(conn, "cmd_merge_record")
    await conn.execute(table("cmd_merge_record").insert().values(
        id=mid, merge_code=merge_code, survivor_one_id=survivor, merged_one_id=merged,
        merge_type="MANUAL", status="EFFECTIVE", reason=task.get("remark"),
        del_flag="0", create_by=0, create_time=datetime.now()))

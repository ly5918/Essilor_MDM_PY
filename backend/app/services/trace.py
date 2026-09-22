"""工作流轨迹写入：步骤日志（cmd_workflow_step_log）+ 审批动作（cmd_approval_action）。

Java 版在提交 / 系统自动节点 / 人工审批时都会写轨迹，流程中心的
「流程跟踪 / 泳道图点亮」依赖这些记录。Python 版保持同一写入口径。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, func

from ..core.db import table


async def log_step(conn, *, one_id: Optional[str], task_no: str, step_type: str,
                   node_code: str, node_name: str, action_type: str, action_name: str,
                   operator_name: str = "system", operator_role: str = "SYSTEM",
                   from_status: str = "-", to_status: str = "-",
                   opinion: str = "", flow_instance_id: Optional[int] = None) -> None:
    """追加一条步骤日志（step_seq 按 one_id 内递增；无 one_id 按 task_no 递增）。"""
    log_t = table("cmd_workflow_step_log")
    scope_col = log_t.c.one_id if one_id else log_t.c.task_no
    scope_val = one_id or task_no
    base = (await conn.execute(
        select(func.max(log_t.c.step_seq)).where(scope_col == scope_val)
    )).scalar() or 0
    from ..services import sequence as seq
    rid = await seq.next_id(conn, "cmd_workflow_step_log")
    await conn.execute(log_t.insert().values(
        id=rid, one_id=one_id, task_no=task_no, flow_instance_id=flow_instance_id,
        step_seq=base + 1, step_type=step_type, node_code=node_code, node_name=node_name,
        action_type=action_type, action_name=action_name,
        operator_name=operator_name, operator_role=operator_role,
        from_status=from_status, to_status=to_status, opinion=opinion,
        del_flag="0", create_time=datetime.now(),
    ))


async def log_action(conn, *, task_id: Optional[int], task_no: str,
                     one_id: Optional[str], action_type: str, action_name: str,
                     from_node_code: str = "", to_node_code: str = "",
                     operator_name: str = "system", operator_role: str = "SYSTEM",
                     opinion: str = "") -> None:
    """追加一条审批动作轨迹（流程跟踪的时间线与泳道点亮数据源）。"""
    act = table("cmd_approval_action")
    from ..services import sequence as seq
    rid = await seq.next_id(conn, "cmd_approval_action")
    await conn.execute(act.insert().values(
        id=rid, task_id=task_id, task_no=task_no, one_id=one_id,
        action_type=action_type, action_name=action_name,
        from_node_code=from_node_code, to_node_code=to_node_code,
        operator_name=operator_name, operator_role=operator_role,
        action_time=datetime.now(), opinion=opinion,
        del_flag="0", create_time=datetime.now(),
    ))

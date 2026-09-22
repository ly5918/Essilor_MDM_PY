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
    """追加一条步骤日志（step_seq 按 one_id 内递增；无 one_id 按 task_no 递增）。

    one_id 落库兜底 "-"：IMPORT 等无 One ID 的场景任务行 one_id 为空，
    而 cmd_workflow_step_log.one_id 为 NOT NULL（与 Java 写入口径一致）。
    """
    one_id = one_id or "-"
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
    """追加一条审批动作轨迹（流程跟踪的时间线与泳道点亮数据源）。one_id 空时兜底 "-"。"""
    one_id = one_id or "-"
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


_ACTION_NAME = {"approve": "批准", "reject": "拒绝", "return": "退回",
                "escalate": "升级GC", "merge": "确认合并", "exclude": "排除重复",
                "create_new": "创建新主档", "link": "关联已有"}


async def log_audit_event(conn, *, task_no: str, one_id: Optional[str], biz_type: str,
                          biz_title: str, action_type: str, operator_name: str,
                          operator_role: str, risk_level: str,
                          from_status: str = "", to_status: str = "",
                          opinion: str = "") -> None:
    """审批决策审计留痕（审计中心按 One ID / 申请编号可检索，对齐 Java doAction 7)）。

    before_json / after_json 是 JSON 列：裸状态串不是合法 JSON，包成对象写入。
    """
    from ..services import sequence as seq
    one_id = one_id or "-"
    event_id = await seq.gen_code(conn, "AE-", 4, "AE")
    rid = await seq.next_id(conn, "audit_event")
    now = datetime.now()
    await conn.execute(table("audit_event").insert().values(
        id=rid,
        event_id=event_id, event_type="APPROVAL",
        event_name=f"{_ACTION_NAME.get(action_type, action_type)}：{biz_title}",
        biz_type=biz_type or "-", biz_id=task_no, one_id=one_id,
        operator_name=operator_name, operator_role=operator_role or "SYSTEM",
        event_time=now, result="SUCCESS",
        risk_level=risk_level or "Low",
        # JSON 列直接传 dict（反射类型为 sqlalchemy JSON，驱动负责序列化）
        before_json={"flow_status": from_status or ""},
        after_json={"flow_status": to_status or ""},
        remark=opinion or None,
        del_flag="0", create_by=0, create_time=now,
    ))

"""规则变更 / 集成失败处理 审批流接线（DQ_RULE_CHANGE / MATCH_RULE_CHANGE / INTEGRATION_FAIL）。

总设计泳道要求：规则草稿 → BU 验证 → GC 验证 → 生效（跨BU路由）；集成失败重试需治理批准。
此前三个场景仅有 BPMN 定义、无业务触发点——本模块补齐：
- start_rule_change_flow：规则新增/修改 → cmd_approval_task + SpiffWorkflow 实例（crossBu=True 走 BU→GC）；
- start_integration_retry_flow：FAILED 运行重试 → 审批；
- apply_rule_outcome / apply_integration_retry：do_action END 回调（approve 生效 / reject 回滚）。
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select

from ..core.db import get_engine, table
from ..core.query import dynamic_insert, dynamic_update
from ..workflow.engine import start_instance

_SCENE_NAME = {
    "DQ_RULE_CHANGE": "DQ规则变更",
    "MATCH_RULE_CHANGE": "匹配规则变更",
}


async def _gen_task_no(conn) -> str:
    from .sequence import gen_code
    return await gen_code(conn, "AP-", 4, "APPROVAL")


async def start_rule_change_flow(conn, scene: str, rule_table: str,
                                 rule_id: int, rule_row: dict,
                                 action: str, actor: str = "demo") -> str:
    """规则新增/修改 → 审批任务 + 流程实例。返回任务编号。

    snapshot 携带 old 行（update 用于 reject 回滚）与 action；
    crossBu=True 使 BU 验证批准后进入 GC 一致性验证（对齐泳道第 3/4 阶段）。
    """
    task_no = await _gen_task_no(conn)
    scene_name = _SCENE_NAME.get(scene, scene)
    version_no = rule_row.get("version_no") or "v1"
    evidence = {
        "规则编号": rule_row.get("rule_code") or str(rule_id),
        "规则名称": rule_row.get("rule_name") or "",
        "变更类型": action,
        "目标版本": version_no,
        "状态": "草稿（审批通过后生效）",
    }
    snapshot = {
        "action": action, "ruleTable": rule_table, "ruleId": rule_id,
        "old": {k: (str(v) if hasattr(v, "isoformat") else v)
                for k, v in rule_row.items()
                if k in ("rule_name", "expression", "severity", "score_weight",
                         "exact_threshold", "suspect_threshold", "normalize_rule",
                         "status", "version_no", "algorithm")},
    }
    from .sequence import next_id
    task_id = await next_id(conn, "cmd_approval_task")
    await conn.execute(table("cmd_approval_task").insert().values(
        id=task_id, task_no=task_no, task_category="APPROVAL",
        biz_type=scene, biz_id=str(rule_id), biz_title=f"{scene_name}：{rule_row.get('rule_name') or ''}（{action}）",
        one_id=None, scene_code=scene, bu_scope="Global",
        scope="BU", current_node_code="BU_REVIEW", current_node_name="BU Scope 业务验证",
        assignee_role="BU_STEWARD", status="PENDING", risk_level="Medium",
        duplicate_state="NEW", cross_bu_flag="Y",
        applicant_name=actor, submit_time=datetime.now(), del_flag="0",
        create_by=0, create_time=datetime.now(),
        evidence_json=evidence, biz_snapshot_json=snapshot,
        remark=f"{scene_name}审批（BU验证→GC一致性验证→生效）"))
    await start_instance(
        scene_code=scene, biz_type=scene, biz_no=task_no,
        variables={
            "taskNo": task_no, "bizType": scene, "oneId": None,
            "buScope": "Global", "crossBu": True, "riskLevel": "Medium",
            "duplicateState": "NEW", "dqScore": None, "sceneCode": scene,
        })
    return task_no


async def apply_rule_outcome(conn, task: dict, outcome: str) -> None:
    """流程 END 回调：approve → 规则生效（status=1）；reject → 新增删行 / 修改回滚旧值。"""
    snapshot = task.get("biz_snapshot_json") or {}
    rule_table_name = snapshot.get("ruleTable") or "dq_rule"
    rule_id = int(task.get("biz_id") or 0)
    if not rule_id:
        return
    rt = table(rule_table_name)
    action = snapshot.get("action")
    if outcome == "approved":
        await conn.execute(rt.update().where(rt.c.id == rule_id).values(
            status="1", update_time=datetime.now()))
        return
    # rejected
    if action == "新增":
        await conn.execute(rt.update().where(rt.c.id == rule_id).values(del_flag="1"))
    elif action == "修改":
        old = snapshot.get("old") or {}
        if old:
            await dynamic_update(conn, rt, rule_id, {**old, "update_time": datetime.now()})


async def start_integration_retry_flow(conn, run_id: int, run_row: dict,
                                       actor: str = "Platform Admin") -> Optional[str]:
    """失败批次重试 → 集成失败处理审批（治理批准后才生成重试运行）。"""
    if (run_row.get("run_status") or "").upper() not in ("FAILED", "RETRYING"):
        return None
    task_no = await _gen_task_no(conn)
    evidence = {
        "运行批次": run_row.get("run_code") or str(run_id),
        "端点": f"{run_row.get('endpoint_code') or ''} · {run_row.get('endpoint_name') or ''}",
        "目标系统": run_row.get("target_system") or "",
        "失败数": str(run_row.get("failed_count") or 0),
        "重试方式": "治理批准后由管理员执行 Retry / Resubmit",
    }
    snapshot = {"runId": run_id, "runCode": run_row.get("run_code")}
    from .sequence import next_id
    task_id = await next_id(conn, "cmd_approval_task")
    await conn.execute(table("cmd_approval_task").insert().values(
        id=task_id, task_no=task_no, task_category="APPROVAL",
        biz_type="INTEGRATION_FAIL", biz_id=str(run_id),
        biz_title=f"集成失败处理：{run_row.get('run_code') or run_id} 重试",
        one_id=None, scene_code="INTEGRATION_FAIL", bu_scope="Global",
        scope="BU", current_node_code="BU_REVIEW", current_node_name="BU Scope 影响确认",
        assignee_role="BU_STEWARD", status="PENDING", risk_level="High",
        duplicate_state="NEW", cross_bu_flag="Y",
        applicant_name=actor, submit_time=datetime.now(), del_flag="0",
        create_by=0, create_time=datetime.now(),
        evidence_json=evidence, biz_snapshot_json=snapshot,
        remark="集成失败重试审批（BU确认影响→GC批准→技术重试）"))
    await start_instance(
        scene_code="INTEGRATION_FAIL", biz_type="INTEGRATION_FAIL", biz_no=task_no,
        variables={
            "taskNo": task_no, "bizType": "INTEGRATION_FAIL", "oneId": None,
            "buScope": "Global", "crossBu": True, "riskLevel": "High",
            "duplicateState": "NEW", "dqScore": None, "sceneCode": "INTEGRATION_FAIL",
        })
    return task_no


async def apply_integration_retry(conn, task: dict) -> None:
    """END 回调（approve）：按原 retry_run 语义复制一条 SUCCESS 重试运行。"""
    run_id = int(task.get("biz_id") or 0)
    if not run_id:
        return
    src = (await conn.execute(
        select(table("int_run")).where(table("int_run").c.id == run_id))).mappings().first()
    if src is None:
        return
    src = dict(src)
    await dynamic_insert(conn, table("int_run"), {
        "run_code": f"RUN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}",
        "endpoint_code": src.get("endpoint_code"),
        "endpoint_name": src.get("endpoint_name"),
        "direction": src.get("direction"),
        "target_system": src.get("target_system"),
        "biz_type": src.get("biz_type"),
        "trigger_type": "MANUAL_RETRY",
        "run_status": "SUCCESS",
        "total_count": src.get("total_count") or 0,
        "success_count": src.get("total_count") or 0,
        "failed_count": 0,
        "attempt_count": 1,
        "max_attempt": src.get("max_attempt") or 3,
        "parent_run_id": run_id,
        "start_time": datetime.now(), "end_time": datetime.now(),
        "duration_ms": 120,
    })
    await conn.execute(table("int_run").update()
                       .where(table("int_run").c.id == run_id).values(run_status="RETRYING"))

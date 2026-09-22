"""SpiffWorkflow 引擎封装层。

对应原 CmdFlowEngineServiceImpl：用 BPMN 2.0 的 5 节点统一流程驱动全部审批场景。
- START → APPLY(申请) → BU_REVIEW(BU初审) → [跨BU升级 / 直接批准 / 驳回] → GC_REVIEW(GC决策) → 结束
- 流程变量：taskNo / buScope / crossBu / riskLevel / duplicateState / dqScore / bizType / rejected
- 流程实例状态用 pickle 序列化后存入 cmd_py_flow_instance 表（Python 侧新增）。
"""
from __future__ import annotations

import pickle
import os
import base64
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser.BpmnParser import BpmnParser
from SpiffWorkflow.task import TaskState

from ..core.db import get_engine, flow_instance_table

BPMN_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "processes", "cmd_approval.bpmn")
PROCESS_ID = "CmdApproval"
READY = TaskState.READY

# 节点编码 / 处理角色映射（与原 cmd_approval_task.current_node_code / assignee_role 对齐）
NODE_CODE = {
    "Activity_Apply": "APPLY",
    "Activity_BUReview": "BU_REVIEW",
    "Activity_GCReview": "GC_REVIEW",
}
ROLE_OF_NODE = {
    "Activity_Apply": "APPLICANT",
    "Activity_BUReview": "BU_STEWARD",
    "Activity_GCReview": "GC_STEWARD",
}

_SPEC_CACHE: Optional[Any] = None


def _get_spec():
    global _SPEC_CACHE
    if _SPEC_CACHE is None:
        parser = BpmnParser()
        # 二进制读取（BPMN 带 XML encoding 声明，lxml 拒收 str；
        # 也不能用默认 GBK 文本模式——Windows 下会 UnicodeDecodeError）
        with open(os.path.abspath(BPMN_PATH), "rb") as f:
            parser.add_bpmn_str(f.read())
        _SPEC_CACHE = parser.get_spec(PROCESS_ID)
    return _SPEC_CACHE


def _ready_user_tasks(wf: BpmnWorkflow) -> List[Any]:
    return [t for t in wf.get_tasks()
            if getattr(t.task_spec, "manual", False) and t.state == READY]


def _current_node_info(wf: BpmnWorkflow):
    ready = _ready_user_tasks(wf)
    if not ready:
        return None, None, None
    spec = ready[0].task_spec.name
    return spec, NODE_CODE.get(spec, spec), ROLE_OF_NODE.get(spec, "UNKNOWN")


def _serialize(wf: BpmnWorkflow) -> str:
    # 以 base64 字符串形式存储 pickle，避免 aiomysql + pymysql2.x 对 bytes 的转义不兼容
    return base64.b64encode(pickle.dumps(wf)).decode("ascii")


def _deserialize(blob: Any) -> BpmnWorkflow:
    if isinstance(blob, str):
        blob = blob.encode("ascii")
    elif isinstance(blob, memoryview):
        blob = bytes(blob)
    return pickle.loads(base64.b64decode(blob))


async def _persist(biz_no: str, scene_code: str, biz_type: str, wf: BpmnWorkflow,
                   status: str, current_node: Optional[str], data: Dict[str, Any]) -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        existing = await conn.execute(
            flow_instance_table.select().where(flow_instance_table.c.biz_no == biz_no)
        )
        row = existing.first()
        vals = {
            "scene_code": scene_code,
            "biz_type": biz_type,
            "state": _serialize(wf),
            "status": status,
            "current_node": current_node,
            "data_json": json.dumps(data, ensure_ascii=False, default=str),
            "update_time": datetime.now(),
        }
        if row is None:
            vals["biz_no"] = biz_no
            vals["create_time"] = datetime.now()
            await conn.execute(flow_instance_table.insert().values(**vals))
        else:
            await conn.execute(
                flow_instance_table.update()
                .where(flow_instance_table.c.biz_no == biz_no).values(**vals)
            )


async def _load(biz_no: str) -> Optional[BpmnWorkflow]:
    engine = get_engine()
    async with engine.connect() as conn:
        res = await conn.execute(
            flow_instance_table.select().where(flow_instance_table.c.biz_no == biz_no)
        )
        row = res.first()
    if row is None:
        return None
    return _deserialize(row._mapping["state"])


async def start_instance(scene_code: str, biz_type: str, biz_no: str,
                        variables: Dict[str, Any]) -> Dict[str, Any]:
    """发起流程实例：提交即完成 APPLY 节点，停到 BU_REVIEW 等待。"""
    variables = dict(variables)
    variables.setdefault("rejected", False)
    variables.setdefault("crossBu", False)
    wf = BpmnWorkflow(_get_spec())
    # 将初始变量注入 Start 事件任务，使其随流程继承到后续网关
    for t in wf.get_tasks():
        if t.task_spec.__class__.__name__ in ("StartEvent", "BpmnStartTask"):
            t.data.update(variables)
    wf.do_engine_steps()
    ready = _ready_user_tasks(wf)
    if ready and ready[0].task_spec.name == "Activity_Apply":
        ready[0].data.update(variables)   # 确保 APPLY 也持有变量
        ready[0].complete()
        wf.do_engine_steps()
    spec, node, role = _current_node_info(wf)
    status = "COMPLETED" if wf.is_completed() else "RUNNING"
    await _persist(biz_no, scene_code, biz_type, wf, status, node, dict(wf.data))
    return {"biz_no": biz_no, "status": status, "current_node": node, "role": role}


async def get_tasks(biz_no: str) -> List[Dict[str, Any]]:
    wf = await _load(biz_no)
    if wf is None:
        return []
    return [{
        "spec": t.task_spec.name,
        "node_code": NODE_CODE.get(t.task_spec.name, t.task_spec.name),
        "role": ROLE_OF_NODE.get(t.task_spec.name, "UNKNOWN"),
    } for t in _ready_user_tasks(wf)]


async def complete_current(biz_no: str, action: str, actor: str,
                           opinion: str = "", variables: Optional[Dict[str, Any]] = None
                           ) -> Dict[str, Any]:
    """完成当前等待节点并推进。action ∈ approve/reject/escalate。"""
    wf = await _load(biz_no)
    if wf is None:
        raise RuntimeError(f"流程实例不存在: {biz_no}")
    ready = _ready_user_tasks(wf)
    if not ready:
        wf.do_engine_steps()
        ready = _ready_user_tasks(wf)
    if not ready:
        return {"biz_no": biz_no, "status": "COMPLETED", "current_node": "END",
                "outcome": "approved" if not wf.data.get("rejected") else "rejected",
                "data": dict(wf.data)}
    task = ready[0]
    # 合并变量 + 保证网关条件所需字段存在（防止 NameError）
    if variables:
        task.data.update(variables)
    task.data.setdefault("rejected", False)
    task.data.setdefault("crossBu", False)
    if action == "reject":
        task.data["rejected"] = True
    if action == "escalate":
        task.data["crossBu"] = True
    task.data["action"] = action
    task.data["actor"] = actor
    task.data["opinion"] = opinion
    task.complete()
    wf.do_engine_steps()

    spec, node, role = _current_node_info(wf)
    status = "COMPLETED" if wf.is_completed() else "RUNNING"
    outcome = None
    if status == "COMPLETED":
        outcome = "rejected" if wf.data.get("rejected") else "approved"
    await _persist(biz_no, wf.data.get("sceneCode", ""), wf.data.get("bizType", ""),
                   wf, status, node, dict(wf.data))
    return {"biz_no": biz_no, "status": status, "current_node": node,
            "role": role, "outcome": outcome, "data": dict(wf.data)}

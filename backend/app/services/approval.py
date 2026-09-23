"""审批服务：doAction 推进 SpiffWorkflow 并触发业务回调。

对应原 CmdApprovalServiceImpl.doAction + linkFlowEngine：
- 首次动作时若流程未启动则启动（变更/合并）；新建客户在提交时已启动；
- approve/reject/escalate 驱动 BPMN 网关；
- 流程 END 时按 biz_type 回调：CUSTOMER_CREATE→发布主档；MERGE→execMergeTask；CUSTOMER_CHANGE→同步变更单状态。
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import select, text

from ..core.db import get_engine, table, flow_instance_table
from ..workflow.engine import start_instance, complete_current
from .customer import publish_customer

# ---- 常量（对齐 Java CmdConstants） ----------------------------------------
_FINAL_STATUSES = {"APPROVED", "REJECTED", "COMPLETED", "CANCELLED"}
_MATCH_EXACT, _MATCH_SUSPECTED, _MATCH_NEW = "EXACT", "SUSPECTED", "NEW"

# 任务状态 → 中文（审批详情头部 / 列表「状态」列）
_STATUS_TEXT = {
    "DRAFT": "草稿",
    "PENDING": "待审批",
    "APPROVED": "已批准",
    "COMPLETED": "已办结",
    "REJECTED": "已拒绝",
    "RETURNED": "已退回",
    "ESCALATED": "已升级",
    "CANCELLED": "已取消",
}


def _status_text(status: str) -> str:
    return _STATUS_TEXT.get((status or "").upper(), status or "-")


def _fmt_dt(value) -> str:
    """datetime → 展示串；空值返回空串（前端据此决定是否展示）。"""
    return value.strftime("%Y-%m-%d %H:%M") if isinstance(value, datetime) else ""


def _resolve_sla_text(sla_state: str) -> str:
    """SLA 状态 → 展示文案（对齐 Java resolveSlaText）。"""
    if sla_state == "OVERDUE":
        return "已超时"
    if sla_state == "DUE_SOON":
        return "临近SLA"
    return "正常"


def _build_decisions(task: dict) -> list[str]:
    """决策 / 判断标签（页面「BU初审判断 / GC治理决策」区，对齐 Java buildDecisions）。"""
    decisions: list[str] = []
    if (task.get("risk_level") or "").upper() == "HIGH":
        decisions.append("高风险：建议升级 GC Scope 复核")
    dq = task.get("dq_score")
    if dq is not None and float(dq) < 60:
        decisions.append("DQ 低于 60：建议退回补充材料")
    match = (task.get("duplicate_state") or "").upper()
    if _is_in_flight_duplicate(task):
        decisions.append("重复发单：同一信用代码存在尚未审批完成的在途申请，建议撤回本单或确认是否同一主体")
    elif _MATCH_SUSPECTED in match:
        decisions.append("疑似重复：需人工比对后决定关联已有或新建")
    elif _MATCH_EXACT in match:
        decisions.append("已命中存量：批准后关联已有 One ID")
    elif _MATCH_NEW in match:
        decisions.append("未命中存量：批准后生成新 One ID")
    if task.get("cross_bu_flag") == "Y":
        decisions.append("跨 BU 申请：需 GC Scope 参与决策")
    if not decisions:
        decisions.append("自动检查通过：可直接审批")
    return decisions


def _evidence_dict(task: dict) -> dict:
    """evidence_json 兼容两种形态：dict（JSON 列）与 str。"""
    ev = task.get("evidence_json")
    if isinstance(ev, dict):
        return ev
    if isinstance(ev, str) and ev.strip().startswith("{"):
        try:
            return json.loads(ev)
        except Exception:
            return {}
    return {}


def _is_in_flight_duplicate(task: dict) -> bool:
    """命中的是「尚未审批完成的在途申请」而非已发布主档。

    两者处置动作不同：在途申请还不是主档，「关联已有主档 / 确认合并」的语义不成立，
    正确动作是撤回本单或确认为不同主体后继续。
    """
    ev = _evidence_dict(task)
    return (str(ev.get("在途申请") or "").strip() == "是"
            or "在途" in str(ev.get("命中来源") or ""))


def _is_duplicate_link_approval(task: dict) -> bool:
    """单条创建命中**已发布主档**（EXACT/SUSPECTED 且证据含候选 One ID）→ 走合并决策按钮组。"""
    if _is_in_flight_duplicate(task):
        return False
    return (task.get("duplicate_state") in (_MATCH_EXACT, _MATCH_SUSPECTED)
            and "候选One ID" in (task.get("evidence_json") or ""))


# BU Scope 对**跨BU重复**不得执行的定案动作（总设计「故事一」：
# 单条创建与跨BU识别 = Business User 创建 → BU 初审 → GC 决策 → 关联已有 One ID 并发布）。
# 这里的护栏是服务端的最后一道闸：前端按钮组已经收敛，但接口仍可能被直接调用
# （脚本 / 旧页面缓存 / 手工 curl），必须在落库前拦住。
_CROSS_BU_BU_FORBIDDEN = {"approve", "merge", "exclude", "create_new"}


def _cross_bu_needs_gc(task: dict) -> bool:
    """该任务是否为「跨BU重复」，因而必须由 GC Scope 定案。"""
    if (task.get("cross_bu_flag") or "N") != "Y":
        return False
    if (task.get("scope") or "").upper() == "GC":
        return False
    return _is_duplicate_link_approval(task) or _is_in_flight_duplicate(task)


def _guard_cross_bu(task: dict, action: str) -> None:
    """跨BU重复在 BU Scope 上的定案动作一律拒绝，提示升级 GC。"""
    if _cross_bu_needs_gc(task) and (action or "").lower() in _CROSS_BU_BU_FORBIDDEN:
        raise RuntimeError(
            "该申请命中的是其它 BU 的同信用代码记录（跨BU重复），"
            "按治理口径须由 GC Scope 做合并/新建决策——请先「升级GC决策」，"
            "BU 侧不能直接批准或排除该重复")


def _approve_label(task: dict) -> str:
    """主审批按钮文案：严格按匹配结论区分（对齐 Java approveLabel / BUG-9 口径）。"""
    if task.get("biz_type") in ("CHANGE", "IMPORT"):
        # 变更 / 停用 / 批量导入确认无「新建 vs 合并」语义，统一为「批准」
        return "批准"
    match = (task.get("duplicate_state") or "").upper()
    if _is_in_flight_duplicate(task):
        return "确认重复·撤回本单"
    if match == _MATCH_NEW:
        return "批准新建"
    if _MATCH_EXACT in match or _MATCH_SUSPECTED in match:
        return "确认合并"
    return "批准"


def _build_actions(task: dict) -> list[dict]:
    """可执行操作按钮（按 Scope / 场景区分，对齐 Java buildActions）。"""
    status = (task.get("status") or "").upper()
    if status in _FINAL_STATUSES:
        # 终态任务（已批准/已拒绝/已退回/已取消/已完成）不再显示操作按钮
        return []
    gc = (task.get("scope") or "").upper() == "GC"
    act = lambda key, label, type_: {"key": key, "label": label, "type": type_}
    biz_type = task.get("biz_type") or ""
    if biz_type == "MERGE":
        # 跨BU客户合并：批准即「确认合并」——执行 Golden Record 合并 / 行级关联
        return [act("APPROVE", "确认合并", "primary"),
                act("REJECT", "拒绝合并", "danger"),
                act("RETURN", "退回BU", "warning")]
    if _is_in_flight_duplicate(task):
        # 命中的是在途申请（对方还不是主档）：处置是「撤回本单 / 确认为不同主体 / 退回修正」，
        # 不提供「关联已有主档」——合并到一个尚不存在的主档在业务上不成立
        if gc:
            return [act("REJECT", "确认重复·撤回本单", "danger"),
                    act("CREATE_NEW", "确认为不同主体·继续新建", "warning"),
                    act("RETURN", "退回BU修正信用代码", "info")]
        if task.get("cross_bu_flag") == "Y":
            # 跨BU在途重复：BU 无权单方定案（总设计「故事一」：BU初审→GC决策→关联已有并发布）。
            # 「确认为不同主体·继续新建」会把同码主体在另一个 BU 落成独立 Active 记录，
            # 直接绕开 GC——因此 BU 侧只保留「升级GC决策 / 撤回本单 / 退回」。
            return [act("ESCALATE", "升级GC决策", "primary"),
                    act("REJECT", "确认重复·撤回本单", "danger"),
                    act("RETURN", "退回补充", "info")]
        return [act("REJECT", "确认重复·撤回本单", "danger"),
                act("EXCLUDE", "确认为不同主体·继续新建", "warning"),
                act("RETURN", "退回补充", "info")]
    if _is_duplicate_link_approval(task):
        if gc:
            # GC Scope 决策：跨BU确认关联已有、创建新主档或退回修复
            return [act("MERGE", "确认关联已有", "primary"),
                    act("CREATE_NEW", "创建新主档", "success"),
                    act("RETURN", "退回BU修复", "warning")]
        if task.get("cross_bu_flag") == "Y":
            # BU Scope 初审：跨BU无权直接定案——只能升级 GC 或退回补充，
            # 不给「排除重复·继续新建」（否则会在另一个 BU 落成同码独立主档，
            # 泳道图上「BU初审 → GC决策」的核心场景直接走不通：BUG-PY-06）
            return [act("ESCALATE", "升级GC决策", "primary"),
                    act("RETURN", "退回补充", "info")]
        # Same-BU：BU 直接决策
        return [act("MERGE", "确认合并", "primary"),
                act("EXCLUDE", "排除重复·继续新建", "warning"),
                act("RETURN", "退回补充", "info")]
    # 默认分支：客户新建 NEW / 变更 / 停用 / 层级 / 批量导入确认等（无合并语义）
    actions = [act("APPROVE", _approve_label(task), "primary"),
               act("REJECT", "拒绝", "danger"),
               act("RETURN", "退回BU" if gc else "退回补充", "warning")]
    if not gc:
        actions.append(act("ESCALATE", "升级GC", "info"))
    return actions


async def task_detail(task_no: str) -> Optional[dict]:
    """按任务编号查询处理详情（对齐 Java selectDetailByTaskNo → CmdApprovalDetailVo）。

    前端审批弹窗依赖本接口派生字段：name/submitter/currentNode/sla/dq/duplicate/
    evidence/decisions/actions 均由任务行加工而来，不能直接下发裸表行。
    """
    conn = await get_engine().connect()
    try:
        row = (await conn.execute(
            select(table("cmd_approval_task")).where(
                table("cmd_approval_task").c.task_no == task_no))).mappings().first()
    finally:
        await conn.close()
    if row is None:
        return None
    task = dict(row)
    dq = task.get("dq_score")
    status = (task.get("status") or "").upper()
    return {
        # 雪花 id 必须以字符串下发：19 位超出 JS Number 安全整数（2^53），
        # JSON number 会被前端解析丢精度（822→800），导致动作打到错误任务
        "id": str(task.get("id")),
        "taskId": task.get("task_no"),
        "oneId": task.get("one_id") or "",
        "bizId": task.get("biz_id") or "",
        "name": task.get("biz_title") or "",
        "scene": task.get("biz_type") or "",
        "submitter": task.get("applicant_name") or "-",
        "currentNode": task.get("current_node_name") or "-",
        "sla": _resolve_sla_text(task.get("sla_state") or ""),
        "dq": "-" if dq is None else f"DQ {float(dq):g}",
        "duplicate": task.get("duplicate_state") or "-",
        "evidence": task.get("evidence_json") or "暂无治理证据",
        "decisions": _build_decisions(task),
        "actions": _build_actions(task),
        # 状态与办结信息：终态任务 actions 为空（设计如此——已办结不能再次审批），
        # 前端必须能把「没有按钮」解释清楚，而不是给个空白动作区让人猜。
        "status": status,
        "statusText": _status_text(status),
        "closed": status in _FINAL_STATUSES,
        "handler": task.get("assignee_name") or "",
        "submitTime": _fmt_dt(task.get("submit_time")),
        "finishTime": _fmt_dt(task.get("finish_time")),
        "opinion": task.get("opinion") or "",
    }


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
        # 终态任务拒绝重复动作：否则 complete_current 走「无待办节点」分支仍返回
        # COMPLETED，业务回调（如 publish_customer）会二次发布撞唯一键
        if (task.get("status") or "").upper() in _FINAL_STATUSES:
            raise RuntimeError(f"任务已办结（{task.get('status')}），不能重复审批: {task_no}")

        # 跨BU重复护栏（BUG-PY-06）：BU 不得对跨BU重复做定案，必须先升级 GC。
        _guard_cross_bu(task, action)

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
            if action == "return":
                # 退回BU：任务置 RETURNED 回 BU 队列修复（对齐 Java RETURN 口径），
                # 不能走 outcome 默认 approved 分支误判成办结
                status = "RETURNED"
            else:
                status = "REJECTED" if outcome == "rejected" else "COMPLETED"
        elif action == "reject":
            status = "REJECTED"
        # 升级后任务仍是「待决策」：保持 PENDING 并随节点切到 GC 队列。
        # 对齐 Java：ESCALATE_ACTIONS → skip 到 NODE_GC_REVIEW + resolveScope(nodeCode)，
        # 引擎节点已经是 GC_REVIEW；若在这里置 ESCALATED，任务会同时掉出
        # BU 队列（status 不在 PENDING/RETURNED）和 GC 队列（scope 仍是 BU）→ 永久孤儿。
        elif action == "escalate":
            status = "PENDING"

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
            # 名称与编码同步更新：current_node_name 是泳道图 resolve_current_node
            # 的回退信号，只改编码不改名会导致「上一步仍显示 to do」
            "current_node_name": {"BU_REVIEW": "BU Scope 初审",
                                  "GC_REVIEW": "GC Scope 决策"}.get(node, node) or task["current_node_name"],
            "assignee_role": next_role or task["assignee_role"],
            "opinion": opinion,
            "status": status,
        }
        # 节点推进到 GC 决策（升级动作）：scope 同步切到 GC，任务进入 GC 队列
        # （对齐 Java update.setScope(resolveScope(instance.getNodeCode(), ...))）
        if action == "escalate" or (next_role or "").upper() == "GC" or "GC" in (node or "").upper():
            update_vals["scope"] = "GC"
        if action == "return":
            # 退回BU：任务回到 BU 队列，当前节点回到申请起点等待修复重报
            update_vals["scope"] = "BU"
            update_vals["current_node_code"] = "APPLY"
            update_vals["current_node_name"] = "创建客户申请"
            update_vals["assignee_role"] = "BU_USER"
        if result["status"] == "COMPLETED" and status != "RETURNED":
            update_vals["finish_time"] = datetime.now()
        await conn.execute(
            table("cmd_approval_task").update()
            .where(table("cmd_approval_task").c.task_no == task_no).values(**update_vals))

        # 审计留痕：审批决策（审计中心可按 One ID / 申请编号检索，对齐 Java doAction 7)）
        from .trace import log_audit_event
        await log_audit_event(
            conn, task_no=task_no, one_id=task.get("one_id"),
            biz_type=task.get("biz_type") or task.get("scene_code") or "",
            biz_title=task.get("biz_title") or "-", action_type=action,
            operator_name=task.get("assignee_name") or "demo",
            operator_role=task.get("assignee_role") or "SYSTEM",
            risk_level=task.get("risk_level") or "Low",
            from_status=task.get("status") or "", to_status=status,
            opinion=opinion or "",
        )

        # 业务回调
        biz_type = task["biz_type"]
        if biz_type == "CUSTOMER_CREATE":
            app = (await conn.execute(
                table("cmd_customer_application").select()
                .where(table("cmd_customer_application").c.app_no == task_no))).mappings().first()
            if app is not None:
                if action == "return":
                    # 退回BU：申请退回待修复，绝不发布主档
                    await conn.execute(
                        table("cmd_customer_application").update()
                        .where(table("cmd_customer_application").c.app_no == task_no)
                        .values(status="returned"))
                elif result["status"] == "COMPLETED":
                    # 仅在流程真正走完时发布/驳回（修复：ESCALATE 时 outcome=None
                    # 曾被 `outcome or "approved"` 兜底成 approved，升级即误发布主档）
                    # 透传 GC/BU 决策键：create_new / exclude → 新建主档不链路已有
                    await publish_customer(conn, dict(app), outcome or "approved",
                                           decision=action)
                # 流程仍在流转（如 ESCALATE）：不动申请、不发布主档
        elif biz_type == "MERGE" and outcome == "approved":
            await exec_merge_task(conn, task)
        elif biz_type == "IMPORT" and result["status"] == "COMPLETED":
            # 批量导入确认审批闭环：approve→New 行生成 One ID / reject→FAILED / return→待复核
            from .import_service import on_approval
            action_type = {"approve": "APPROVE", "reject": "REJECT",
                           "return": "RETURN"}.get(action, action.upper())
            await on_approval(conn, task["biz_id"], action_type, actor or "BU Steward")
        elif biz_type == "CUSTOMER_CHANGE" and outcome in ("approved",):
            await conn.execute(
                table("cmd_change_request").update()
                .where(table("cmd_change_request").c.request_code == task_no)
                .values(status="APPROVED", approved_by=0, approved_time=datetime.now()))
        elif biz_type in ("DQ_RULE_CHANGE", "MATCH_RULE_CHANGE") and result["status"] == "COMPLETED":
            # 规则变更闭环：approve→规则生效（status=1）；reject→删草稿/回滚旧值
            from .rule_flow import apply_rule_outcome
            await apply_rule_outcome(conn, task, outcome or "approved")
        elif biz_type == "INTEGRATION_FAIL" and outcome == "approved":
            # 集成失败处理闭环：approve→生成重试运行并标记原批次 RETRYING
            from .rule_flow import apply_integration_retry
            await apply_integration_retry(conn, task)
        elif biz_type == "HIER_RELATION" and result["status"] == "COMPLETED":
            # 层级关系闭环：approve→关系生效；reject→关系作废
            new_status = "Effective" if (outcome or "approved") == "approved" else "Rejected"
            await conn.execute(
                table("cmd_hierarchy_relation").update()
                .where(table("cmd_hierarchy_relation").c.id == int(task["biz_id"]))
                .values(status=new_status, approved_time=datetime.now()))

    result["task_status"] = status
    return result


async def exec_merge_task(conn, task: dict) -> None:
    """合并执行：被合并方置 inactive，写 cmd_merge_record 生效。

    mode=ROW_LINK（批量导入行跨BU关联已有）时走导入域回写：行置 Exact 并关联目标。
    """
    snapshot = task.get("biz_snapshot_json") or {}
    if snapshot.get("mode") == "ROW_LINK":
        from .import_service import apply_row_link_merge
        await apply_row_link_merge(conn, task)
        return
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

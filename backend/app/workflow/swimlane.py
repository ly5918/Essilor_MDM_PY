"""泳道图步骤模板：1:1 复刻 Java CmdFlowEngineServiceImpl 的场景模板、
布局参数与状态推导（applyStepStatus / resolveCurrentNode）。"""
from __future__ import annotations

from typing import Optional

# ---------------- 泳道与节点常量（与 Java 一致） ----------------
LANE_BU_USER = "Business User"
LANE_SYS = "系统自动处理"
LANE_BU_STEWARD = "Data Steward BU Scope"
LANE_GC_STEWARD = "Data Steward GC Scope"
LANE_ADMIN = "Platform Admin"
LANE_AUDITOR = "Auditor（只读）"

LANE_ORDER = [LANE_BU_USER, LANE_SYS, LANE_BU_STEWARD, LANE_GC_STEWARD, LANE_ADMIN, LANE_AUDITOR]

NODE_APPLY = "APPLY"
NODE_BU_REVIEW = "BU_REVIEW"
NODE_GC_REVIEW = "GC_REVIEW"
NODE_END = "END"
NODE_START = "START"

MANUAL_REVIEW_NODES = {NODE_BU_REVIEW, NODE_GC_REVIEW}

FINAL_OK_STATUS = {"APPROVED", "COMPLETED"}
FINAL_STOP_STATUS = {"REJECTED", "CANCELLED"}
FINAL_STATUSES = FINAL_OK_STATUS | FINAL_STOP_STATUS

# 泳道图定义视图布局参数（阶段分列 × 泳道分行）
BASE_X = 300
COL_GAP = 168
BASE_Y = 70
LANE_GAP = 92
SUB_ROW_GAP = 46

SCENE_FLOW_CODE = {
    "CUSTOMER_CREATE": "cmd_customer_create",
    "CUSTOMER_CHANGE": "cmd_customer_change",
    "DEACTIVATE": "cmd_customer_deactivate",
    "HIER_RELATION": "cmd_hier_relation",
    "IMPORT_BATCH": "cmd_import_batch",
    "MERGE": "cmd_customer_merge",
    "DQ_RULE_CHANGE": "cmd_dq_rule_change",
    "MATCH_RULE_CHANGE": "cmd_match_rule_change",
    "INTEGRATION_FAIL": "cmd_integration_fail",
}

# 步骤模板：(phase, phaseName, lane, nodeCode, nodeName, nodeType, note)
_Tpl = tuple


def _create_scene() -> list[_Tpl]:
    return [
        (1, "发起", LANE_BU_USER, "APPLY", "创建客户申请", "MANUAL", "选择客户类型、BU、产品线与来源系统，保存草稿或提交"),
        (2, "数据准备", LANE_BU_USER, "INPUT", "录入与附件", "MANUAL", "填写 GC Core、BU 与来源系统字段，上传营业执照"),
        (2, "数据准备", LANE_SYS, "OCR", "OCR 与智能补全", "AUTO", "提取工商名称、信用代码和地址；底表检索与地址标准化"),
        (3, "自动校验", LANE_SYS, "DQ", "技术与业务 DQ", "AUTO", "必填、格式、值集、GC Core、层级与 Payer 校验"),
        (4, "匹配分流", LANE_SYS, "DUP", "Duplicate Check", "GATEWAY", "以信用代码和经营地址为主依据；名称仅作为辅助线索；SUSPECT 进入人工治理"),
        (5, "人工治理", LANE_BU_STEWARD, NODE_BU_REVIEW, "BU Scope 初审", "MANUAL", "查看申请与候选证据；确认 Same-BU 或升级 Cross-BU"),
        (5, "人工治理", LANE_GC_STEWARD, NODE_GC_REVIEW, "GC Scope 决策", "MANUAL", "核对跨 BU 证据；决定关联现有或创建新 One ID"),
        (6, "审批发布", LANE_SYS, "RESULT", "生成 / 关联结果", "AUTO", "关联已有 One ID；建立 BU 本地码映射并激活主档"),
        (6, "审批发布", LANE_ADMIN, "PUBLISH", "发布到下游", "MANUAL", "通过 API / 实时 / 批量发布；失败时 Retry / Resubmit"),
        (7, "追踪审计", LANE_ADMIN, "TRACE", "运行追踪", "AUTO", "查看任务状态、失败原因、重试与发布记录"),
        (7, "追踪审计", LANE_AUDITOR, "AUDIT", "审计查询", "AUTO", "记录谁、何时、做了什么及 Before / After 与审批证据"),
    ]


def _merge_scene() -> list[_Tpl]:
    return [
        (1, "发现候选", LANE_SYS, "CAND", "疑似重复发现", "AUTO",
         "单条创建 / 批量导入命中存量主档；治理中心发现存量疑似重复（信用代码 / 名称匹配）"),
        (2, "证据准备", LANE_BU_USER, "EVID", "补充业务证据", "MANUAL",
         "确认客户身份、上传附件并说明业务背景"),
        (2, "证据准备", LANE_SYS, "COMPARE", "候选对比准备", "AUTO",
         "展示信用代码、经营地址、名称、来源与层级"),
        (3, "BU 初审", LANE_BU_STEWARD, NODE_BU_REVIEW, "BU Scope 初审", "MANUAL",
         "核验本BU来源记录；确认升级、排除或退回"),
        (4, "GC 决策", LANE_GC_STEWARD, NODE_GC_REVIEW, "GC Scope 决策", "GATEWAY",
         "跨BU确认关联已有、创建新主档或退回修复"),
        (5, "合并 / 新建", LANE_SYS, "MERGE_EXEC", "执行合并 / 新建", "AUTO",
         "更新 Golden Record；One ID 保持稳定或新生成"),
        (6, "结果发布", LANE_SYS, "XREF", "建立交叉引用", "AUTO",
         "保留 Legacy Code 与 Source Snapshot（旧 One ID → 保留 One ID）"),
        (7, "追踪审计", LANE_ADMIN, "TRACE", "运行追踪", "AUTO",
         "合并任务状态、结果与失败原因追踪"),
        (7, "追踪审计", LANE_AUDITOR, "AUDIT", "审计查询", "AUTO",
         "记录合并前后快照与审批证据"),
    ]


def _dq_rule_scene() -> list[_Tpl]:
    return [
        (1, "规则草稿", LANE_BU_STEWARD, "DRAFT", "新增 / 编辑 DQ 规则", "MANUAL",
         "配置技术规则、业务规则、适用实体、BU、严重级别与提示（Draft 状态）"),
        (2, "模拟测试", LANE_BU_STEWARD, "DATASET", "选择测试数据集", "MANUAL",
         "选择 Customer Type、BU、Source System 和样例记录"),
        (2, "模拟测试", LANE_SYS, "SIMULATE", "执行规则模拟", "AUTO",
         "输出 Pass / Warning / Block 及字段级错误说明"),
        (3, "BU 验证", LANE_BU_STEWARD, NODE_BU_REVIEW, "BU Scope 业务验证", "MANUAL",
         "确认本 BU 业务语义、可修复性及 Blocking / Warning 设置"),
        (4, "GC 验证", LANE_GC_STEWARD, NODE_GC_REVIEW, "GC Scope 一致性验证", "MANUAL",
         "验证 GC Core、跨 BU 统一口径及重大规则影响"),
        (5, "影响评估", LANE_BU_STEWARD, "IMPACT", "影响评估", "MANUAL",
         "统计受影响 Active 客户、预计新增异常与 Score 变化"),
        (5, "影响评估", LANE_SYS, "CANDIDATE", "生成候选规则版本", "AUTO",
         "保留 Draft 与测试结果；等待正式发布"),
        (6, "发布 / 重评估", LANE_ADMIN, "PUBLISH", "发布 Rule Version", "MANUAL",
         "新任务引用新版本；旧结果不被静默覆盖"),
        (6, "发布 / 重评估", LANE_SYS, "REEVAL", "创建重评估任务", "AUTO",
         "按范围生成 Re-evaluation Job；保留旧分数和规则版本"),
        (7, "追踪审计", LANE_ADMIN, "TRACE", "记录规则与任务链", "AUTO",
         "保存版本、范围、旧分数、新分数和新增异常"),
        (7, "追踪审计", LANE_AUDITOR, "AUDIT", "规则审计", "AUTO",
         "Auditor 只读查看配置、验证、发布和重评估证据"),
    ]


def _match_rule_scene() -> list[_Tpl]:
    return [
        (1, "规则调整", LANE_BU_STEWARD, "ADJUST", "调整匹配字段与标准化", "MANUAL",
         "配置信用代码、经营地址、辅助名称、字段组合和空值策略"),
        (2, "样例模拟", LANE_BU_STEWARD, "THRESHOLD", "设置阈值与结果分层", "MANUAL",
         "定义 Exact / Suspected / New 阈值与 Same-BU / Cross-BU 路由"),
        (2, "样例模拟", LANE_SYS, "SIMULATE", "运行测试数据集", "AUTO",
         "选择已知重复与非重复样本；执行标准化和匹配并输出候选与解释"),
        (3, "BU 验证", LANE_BU_STEWARD, NODE_BU_REVIEW, "BU Scope 候选验证", "MANUAL",
         "检查 Same-BU 误匹配、漏匹配和业务可解释性"),
        (4, "GC 验证", LANE_GC_STEWARD, NODE_GC_REVIEW, "GC Scope 候选验证", "MANUAL",
         "检查 Cross-BU、多候选与重大误合并风险"),
        (5, "影响评估", LANE_BU_STEWARD, "IMPACT", "影响评估", "MANUAL",
         "比较新旧 Exact / Suspected / New 分布和任务数量"),
        (5, "影响评估", LANE_SYS, "KEEP_OLD", "保留原 Match Result", "AUTO",
         "历史任务继续引用原规则版本，不静默覆盖"),
        (6, "发布 / 重跑", LANE_ADMIN, "PUBLISH", "发布 Match Rule Version", "MANUAL",
         "新任务引用新版本；可选择指定范围重新执行"),
        (6, "发布 / 重跑", LANE_SYS, "RERUN", "生成新匹配任务", "AUTO",
         "按客户、BU、批次或时间范围重新执行并生成新结果"),
        (7, "追踪审计", LANE_ADMIN, "TRACE", "记录规则与任务链", "AUTO",
         "保存规则版本、测试数据、结果分布和重新执行范围"),
        (7, "追踪审计", LANE_AUDITOR, "AUDIT", "结果版本对比", "AUTO",
         "Auditor 查看新旧结果、人工决策和证据链"),
    ]


def _integration_scene() -> list[_Tpl]:
    return [
        (1, "任务触发", LANE_SYS, "RUN", "创建集成运行任务", "AUTO",
         "生成 Inbound / Outbound Run；记录对象、方向、模式和版本"),
        (2, "接口执行", LANE_SYS, "CALL", "调用外部系统", "AUTO",
         "通过 API / Batch / File 发送或接收数据；保存 Request 摘要"),
        (3, "失败检测", LANE_SYS, "DETECT", "检测失败与错误分类", "GATEWAY",
         "记录 HTTP / 文件 / Schema 错误、Attempt 与可重试标记"),
        (4, "告警与查看", LANE_BU_USER, "BIZ_VIEW", "业务状态可见", "MANUAL",
         "Business User 查看 Pending / Failed，不执行技术重试"),
        (4, "告警与查看", LANE_BU_STEWARD, "STEWARD_VIEW", "治理影响可见", "MANUAL",
         "Steward 查看受影响客户、审批和主档状态"),
        (4, "告警与查看", LANE_ADMIN, "ADMIN_VIEW", "管理员查看任务详情", "MANUAL",
         "查看错误、Payload 摘要、Request / Response 与已尝试次数"),
        (5, "技术重试", LANE_ADMIN, "RETRY", "Retry / Resubmit", "MANUAL",
         "按规则自动退避或人工重试；避免重复发布"),
        (5, "技术重试", LANE_SYS, "ALERT", "邮件告警与状态更新", "AUTO",
         "邮件仅作通知；更新 Failed / Retrying 状态"),
        (6, "同步完成", LANE_SYS, "ACK", "外部系统确认接收", "AUTO",
         "保存响应码、接收时间和目标系统业务回执"),
        (6, "同步完成", LANE_ADMIN, "MONITOR", "完成任务与监控", "MANUAL",
         "状态更新 Completed；展示耗时、记录数和失败原因"),
        (7, "追踪审计", LANE_BU_USER, "BIZ_RESULT", "同步业务结果", "AUTO",
         "业务角色查看已完成状态和 One ID / 属性结果"),
        (7, "追踪审计", LANE_AUDITOR, "AUDIT", "集成审计", "AUTO",
         "记录管理员重试、Attempt、错误和最终结果"),
    ]


def _generic_scene() -> list[_Tpl]:
    return [
        (1, "发起", LANE_BU_USER, "APPLY", "提交业务申请", "MANUAL", "Business User 发起申请"),
        (2, "数据准备", LANE_SYS, "INPUT", "数据装配", "AUTO", "装配申请数据与证据快照"),
        (3, "自动校验", LANE_SYS, "DQ", "自动校验", "AUTO", "DQ 规则与前置校验（Loop Check / 关联检查等）"),
        (4, "匹配分流", LANE_SYS, "DUP", "条件分流", "GATEWAY", "按规则变量路由（Same-BU / Cross-BU / 风险等级）"),
        (5, "人工治理", LANE_BU_STEWARD, NODE_BU_REVIEW, "BU Scope 初审", "MANUAL", "本 BU 数据管家初审"),
        (5, "人工治理", LANE_GC_STEWARD, NODE_GC_REVIEW, "GC Scope 决策", "MANUAL", "跨 BU 或高风险升级 GC 决策"),
        (6, "审批发布", LANE_SYS, "RESULT", "执行与生效", "AUTO", "审批通过后执行业务结果并生成版本"),
        (6, "审批发布", LANE_ADMIN, "PUBLISH", "发布下游", "MANUAL", "通知 API / 文件 / 批量发布；失败即 Retry / Resubmit"),
        (7, "追踪审计", LANE_ADMIN, "TRACE", "运行追踪", "AUTO", "任务状态与失败原因追踪"),
        (7, "追踪审计", LANE_AUDITOR, "AUDIT", "审计查询", "AUTO", "Before / After 证据审查"),
    ]


def build_swimlane(scene_code: str) -> list[dict]:
    """场景泳道步骤模板（status 初始为 PENDING），与 Java buildSwimlane 一致。"""
    if scene_code == "CUSTOMER_CREATE":
        tpl = _create_scene()
    elif scene_code == "MERGE":
        tpl = _merge_scene()
    elif scene_code == "DQ_RULE_CHANGE":
        tpl = _dq_rule_scene()
    elif scene_code == "MATCH_RULE_CHANGE":
        tpl = _match_rule_scene()
    elif scene_code == "INTEGRATION_FAIL":
        tpl = _integration_scene()
    else:
        tpl = _generic_scene()
    steps = []
    for i, (phase, phase_name, lane, code, name, ntype, note) in enumerate(tpl, start=1):
        steps.append({
            "order": i, "phase": phase, "phaseName": phase_name, "lane": lane,
            "nodeCode": code, "nodeName": name, "nodeType": ntype,
            "note": note, "status": "PENDING",
            "operator": None, "actionTime": None, "opinion": None, "assignee": None,
        })
    return steps


def resolve_current_node(task_status: Optional[str], current_node_name: Optional[str]) -> str:
    """任务状态 + 当前节点名 → 泳道模板节点编码（Java resolveCurrentNode）。"""
    name = current_node_name or ""
    status = task_status or ""
    if status in FINAL_OK_STATUS or "已完成" in name or "发布" in name:
        return "_DONE_"
    if "GC" in name:
        return NODE_GC_REVIEW
    if "BU" in name:
        return NODE_BU_REVIEW
    if status in FINAL_STOP_STATUS or "退回" in name:
        return "INPUT"
    return NODE_APPLY


def apply_step_status(steps: list[dict], task_status: Optional[str],
                      current_node_name: Optional[str], touched_nodes: Optional[set] = None) -> None:
    """Java applyStepStatus：终态全亮 / 终止后续 TERMINATED / 当前 CURRENT / 已过 COMPLETED。"""
    if not steps:
        return
    status = task_status or ""
    name = current_node_name or ""
    finished = status in FINAL_OK_STATUS or "已完成" in name
    stopped = status in FINAL_STOP_STATUS
    current_code = resolve_current_node(status, name)

    current_idx = -1
    for i, s in enumerate(steps):
        if s["nodeCode"] == current_code:
            current_idx = i
            break

    for i, s in enumerate(steps):
        touched = touched_nodes is not None and s["nodeCode"] in touched_nodes
        if finished:
            s["status"] = "COMPLETED"
        elif stopped and current_idx >= 0 and i > current_idx:
            s["status"] = "TERMINATED"
        elif i == current_idx:
            s["status"] = "CURRENT"
        elif current_idx >= 0 and (i < current_idx or touched):
            s["status"] = "COMPLETED"
        elif current_idx < 0 and touched:
            s["status"] = "COMPLETED"
        else:
            s["status"] = "PENDING"


def step_shape(node_type: str, index: int, size: int) -> str:
    """人工审核节点 → 泳道节点形状（首尾圆 / 网关菱形 / 其余矩形）。"""
    if index == 0 or index == size - 1:
        return "CIRCLE"
    if node_type == "GATEWAY":
        return "DIAMOND"
    return "RECT"


def normalize_scene_code(scene_code: Optional[str], biz_type: Optional[str]) -> str:
    """场景归一（Java normalizeSceneCode）：未知场景按 biz_type 兜底。"""
    if scene_code and scene_code in SCENE_FLOW_CODE:
        return scene_code
    bt = (biz_type or "").upper()
    if bt == "MERGE":
        return "MERGE"
    if bt in ("CHANGE", "CUSTOMER_CHANGE"):
        return "CUSTOMER_CHANGE"
    if bt == "IMPORT":
        return "IMPORT_BATCH"
    if bt == "CUSTOMER_CREATE":
        return "CUSTOMER_CREATE"
    return scene_code or "CUSTOMER_CREATE"

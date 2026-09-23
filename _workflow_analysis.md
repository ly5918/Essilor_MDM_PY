# 工作流技术分析报告（Essilor CMD POC · Python 版）

> 生成时间：2026-09-23 · 范围：后端工作流引擎 / 前端工作流页面

---

## 一、结论（一句话）

本项目的工作流引擎是 **SpiffWorkflow（Python 版 BPMN 2.0 引擎）**：
用一份手写的 **BPMN 2.0 XML 流程定义**（`backend/processes/cmd_approval.bpmn`）描述
「申请 → BU 初审 → 网关（跨BU升级/直接批准/驳回）→ GC 决策 → 结束」的主干审批流，
引擎实例状态以 **pickle + base64 序列化后存 MySQL 表 `cmd_py_flow_instance`**，
由审批服务驱动引擎推进，并在流程 END 时触发业务回调（发布主档 / 合并 / 变更同步）。

它是对原 Java 项目（RuoYi-Vue-Plus + Warm-Flow 的 `CmdFlowEngineServiceImpl`）的 Python 等价移植：
Warm-Flow 的「流程定义部署/版本管理」语义被重新实现为「BPMN 哈希版本登记」（`cmd_flow_def_version` 表）。

---

## 二、技术栈构成

| 层 | 技术 | 说明 |
|---|---|---|
| 引擎 | **SpiffWorkflow >= 0.21.0**（`backend/requirements.txt`） | 纯 Python 的 BPMN 2.0 引擎，解析 XML 定义、驱动 UserTask/排他网关 |
| 流程定义 | BPMN 2.0 XML（`cmd_approval.bpmn`） | 1 个流程 `CmdApproval`：Start → Activity_Apply → Activity_BUReview → Gateway_1 → Activity_GCReview → Gateway_2 → 2 个 EndEvent；网关条件表达式 `rejected == True` / `crossBu == True` |
| 状态持久化 | pickle + base64 → MySQL `cmd_py_flow_instance` | 整个 `BpmnWorkflow` 对象序列化存储；`data_json` 存流程变量（taskNo/buScope/crossBu/riskLevel/duplicateState/dqScore/bizType/rejected） |
| 业务接线 | FastAPI + SQLAlchemy(async) | 审批动作 API 驱动引擎，END 回调业务 |
| 展示层 | 前端自绘 SVG 泳道图 | **没有用 bpmn-js / AntV 等图库**，泳道图是后端算好布局坐标（`swimlane.py`）、前端用 `<svg>` 渲染 |

> 注意：`frontend/src/views/workflow/**` 和 `frontend/src/api/workflow/**` 是 RuoYi 框架脚手架自带的
> Warm-Flow 演示页（请假/流程定义设计器等），对接的 `/workflow/instance/*` 接口在本项目后端并不存在，
> **与 CMD 业务工作流无关**，勿混淆。

---

## 三、后端代码分布（按职责）

### 1. 引擎封装层 —— `backend/app/workflow/`

| 文件 | 职责 |
|---|---|
| **`engine.py`** | SpiffWorkflow 封装核心。`_get_spec()` 解析 BPMN（缓存 spec）；`start_instance()` 启动流程实例；`complete_current()` 完成当前 UserTask 并按动作（approve/reject/escalate）设置流程变量、驱动网关；`get_tasks()` 取待办；`reset_instance_node()` =「重建工作流 + 快进」实现流程退回（退回不是改镜像行，而是重开实例再 fast-forward 到目标节点）；`_persist/_load/_serialize/_deserialize` 负责 pickle↔base64↔MySQL。节点编码映射：Activity_Apply→APPLY / Activity_BUReview→BU_REVIEW / Activity_GCReview→GC_REVIEW，对应角色 APPLICANT / BU_STEWARD / GC_STEWARD |
| **`swimlane.py`** | 泳道图步骤模板与状态推导（1:1 复刻 Java `CmdFlowEngineServiceImpl`）：6 条泳道（Business User / 系统自动 / BU Steward / GC Steward / Admin / Auditor）、9 个场景模板（`SCENE_FLOW_CODE`：CUSTOMER_CREATE/MERGE/IMPORT_BATCH/DQ_RULE_CHANGE 等）、步骤状态机（COMPLETED/CURRENT/RETURNED/TERMINATED/PENDING）与布局常量 |

### 2. 审批业务接线 —— `backend/app/services/`

| 文件 | 职责 |
|---|---|
| **`approval.py`** | `do_action` 推进引擎 + 业务回调：首次动作懒启动流程（变更/合并场景）；流程 END 按 biz_type 回调（CUSTOMER_CREATE→`publish_customer` 发布主档、MERGE→合并执行、CUSTOMER_CHANGE→同步变更单）。含审批意见必填双闸门的服务端一侧、状态/节点中文文案、SLA 文案、决策标签 |
| **`customer.py`** | 新建客户提交时调 `start_instance` 启动流程；提供 `publish_customer`（END 回调） |
| **`rule_flow.py`** | 规则变更 / 集成失败场景接线：DQ_RULE_CHANGE / MATCH_RULE_CHANGE / INTEGRATION_FAIL 三场景此前只有 BPMN 定义没有触发点，此模块补齐 `start_rule_change_flow` / `start_integration_retry_flow` 及 END 回调（生效 / 回滚） |
| **`flow_def_service.py`** | 流程定义部署与版本管理（对应 Java `deployScene`）：BPMN sha256 哈希变更检测、幂等重部署、minor 版本递增（v1.0→v1.1），写 `cmd_flow_def_version` 表、回写 `cmd_flow_scene.definition_id` |
| **`step_detail.py`** | 流程跟踪「分步骤明细」服务（1:1 移植 Java `CmdFlowTraceServiceImpl#fillStepDetails`）：为泳道图每个步骤节点生成明细（INPUT/OCR/DQ/DUP/REVIEW/RESULT/PUBLISH/TRACE/AUDIT…） |

### 3. API 层 —— `backend/app/api/`

| 文件 | 路由 | 说明 |
|---|---|---|
| **`flow.py`** | `/cmd/flow/*`：`GET /scenes`、`GET /graph/scene/{code}`（泳道图数据）、`GET /instances`（实例列表）、`GET /trace/{taskNo}`（流程跟踪）、`POST /instance/{taskNo}/start`、`POST /deploy/{code}`、`GET /scene/{code}/versions`、`GET|PUT /scene/{code}/config`（场景级工作流配置，仅 GC_REVIEW 可配置） | 对齐 Java `CmdFlowTraceController` |
| **`approval.py`** | `/cmd/approval/*`：`GET /list`（待办）、`/stats`、`/kpi`、`GET /task/{taskNo}/detail`、`GET /instance/list`、`POST /action`（推进引擎的动作入口）、`GET /workflow-steps`（步骤日志） | 审批工作台数据源 |

### 4. 数据层 —— `backend/app/core/db.py`

定义 `flow_instance_table`（`cmd_py_flow_instance`：biz_no/scene_code/biz_type/state(pickle)/status/current_node/data_json）。
相关业务表：`cmd_approval_task`（任务/待办镜像）、`cmd_approval_action`（动作日志）、
`cmd_workflow_step_log`（步骤执行日志）、`cmd_flow_scene`（场景）、`cmd_flow_def_version`（定义版本）。

### 5. 流程定义 —— `backend/processes/cmd_approval.bpmn`

整个系统唯一的 BPMN 蓝图，全部 9 个场景共用这 5 节点主干，靠流程变量分流。

---

## 四、前端代码分布

全部集中在 CMD POC 业务页 `frontend/src/views/demo/cmd-poc/`，API 封装在 `frontend/src/api/demo/cmdPoc/`。

### 1. 页面装配

- **`index.vue`**：面板路由表 —— `approval`→ApprovalPanel（审批工作台）、
  `flowDefinition`→WorkflowDefinitionPanel（工作流定义）、`flowWorkitem`→FlowWorkitemPanel（工作项）、`flowDone`→FlowDonePanel（已完成流程）。
- **`components/DialogHost.vue`**：弹窗宿主 —— `flowTrace`→FlowTraceDialog（流程跟踪）、`flowGraph`→FlowGraphDialog（泳道图）。

### 2. 核心工作流组件

| 组件 | 体现的工作流能力 |
|---|---|
| **`components/FlowSwimlane.vue`** | **自绘 SVG 泳道图**（无 bpmn-js）：7 阶段 × 6 泳道，实例视图按实际进度点亮，含退回连线专用琥珀色箭头；头部直接标注「SpiffWorkflow 引擎已部署 / 定义 ID」 |
| **`components/FlowTraceDetail.vue`** | 流程跟踪详情：分步骤明细（与后端 `step_detail.py` 一一对应）、步骤执行日志 |
| **`components/panels/WorkflowDefinitionPanel.vue`** | 工作流定义管理：场景列表、部署状态、SpiffWorkflow 流程名称/流程编码、SLA、版本 |
| **`components/panels/FlowWorkitemPanel.vue` / `FlowDonePanel.vue` / `WorkflowViewTable.vue`** | 工作项待办 / 已完成流程列表（数据来自 `/cmd/flow/instances`） |
| **`components/panels/ApprovalPanel.vue`** | 审批工作台：待办列表、审批详情、动作按钮（批准/驳回/升级/退回），意见必填的前端禁用闸门 |
| **`components/dialogs/FlowGraphDialog.vue`** | 「查看泳道图」弹窗，包 FlowSwimlane（定义视图 / 实例视图两种模式） |
| **`components/dialogs/FlowTraceDialog.vue`** | 流程跟踪弹窗，包 FlowTraceDetail |
| **`components/dialogs/WorkflowDialog.vue`** | 工作流配置弹窗（场景级配置、流程节点页签） |

### 3. API 封装

- **`api/demo/cmdPoc/index.ts`**：全部工作流接口调用（`/cmd/approval/*`、`/cmd/flow/*`），
  USE_MOCK 开关切换 mock/真实后端。
- **`api/demo/cmdPoc/types.ts`**：FlowSceneVO / FlowInstanceVO / CmdFlowTraceRow 等类型定义。

### 4. 无关内容（提醒）

`src/views/workflow/**`（leave、processDefinition、task 等）与 `src/components/Process/*`（flowChart.vue 等）
是 RuoYi 框架自带 Warm-Flow 演示件，本项目后端无对应接口，属于脚手架遗留，不参与 CMD 工作流。

---

## 五、数据流（一次审批动作的完整链路）

```
前端 ApprovalPanel「确认批准」
  → POST /cmd/approval/action（taskNo + actionType + 意见）
  → services/approval.py::do_action
      ├─ 懒启动：引擎实例不存在 → workflow/engine.py::start_instance
      ├─ workflow/engine.py::complete_current：设流程变量(rejected/crossBu) → 推进网关
      ├─ 写 cmd_approval_task / cmd_approval_action / cmd_workflow_step_log
      └─ 引擎 END → 按 biz_type 回调（发布主档 / 合并 / 变更同步）
  ← HTTP 200 + 信封响应 → 前端刷新待办/角标/KPI
```

---

## 六、风险与注意点（现有备忘汇总）

1. **退回语义不依赖引擎走向**：跨 BU 单退回时引擎会按升级流走到 GC_REVIEW/RUNNING 而非 END，
   所以退回目标状态由 `reset_instance_node`（重建+快进）显式控制，crossBu 变量须保留。
2. **do_action 守卫**：发布分支必须带 `not is_return`（防 GC 退回误发布主档）；ESCALATE 仅限 BU_REVIEW。
3. **BPMN 文件读取必须二进制**（`engine.py` 已处理），Windows 下文本模式会 UnicodeDecodeError。
4. **修改 BPMN 后**：`flow_def_service` 会因哈希变化生成新版本；重启后端前务必清理 8000 端口残留实例。
5. 引擎状态是 **pickle 序列化**：引擎代码/SpiffWorkflow 升级后旧实例反序列化可能不兼容，
   清库重跑演示数据（`_reset_business_data.py`）即可。

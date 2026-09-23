# CMD POC · 页面 ↔ 数据库表 对照清单

> 生成时间：2026-09-23
> 核对方式：前端路由/面板源码 → 前端 API 函数 → 后端路由 → Service/Repository → SQLAlchemy 反射表名 / 原生 SQL
> 数据库：`ruoyi_plus` @ 127.0.0.1:3306（共 116 张表），表中行数为本次实际 `COUNT(*)` 结果

---

## 一、总体结论

| 项 | 数量 |
|---|---|
| 本项目**实际可达页面** | 16 个（另有 2 个已注册但无菜单入口） |
| 后端 API 模块 | 19 个（全部挂在 `/cmd/**`） |
| **页面实际读写的表** | **41 张**（现有库中的表） |
| 其中仅用原生 SQL 只读的表 | 3 张：`cmd_attachment` / `cmd_match_candidate` / `cmd_match_result` |
| Python 侧新建表（启动时创建） | 2 张：`cmd_py_flow_instance` / `cmd_py_seq` |
| 代码里声明但从未查询的表 | 9 张 |
| **代码引用、但当前库中缺失的表** | **1 张：`cmd_flow_def_version`** ⚠️ |

`frontend/src/router/index.ts` 只注册了 `/cmd-poc-py/**` 系列路由 + `/index`，
RuoYi-Plus 模板自带的 `system/*`、`monitor/*`、`tool/*` 页面**未注册任何路由**
（动态路由依赖 `getRouters` 接口，Python 后端未实现），因此这些页面在本项目中**不产生数据库访问**。

---

## 二、页面 → 数据表（正向清单）

### 1. 工作台（dash）
*Business User 工作台 / BU Scope 治理工作台 / GC Scope 全局治理工作台 / Platform Admin 工作台 / Auditor 工作台*

| 数据表 | 说明 |
|---|---|
| `cmd_customer` | 客户总数、生效中、待审批统计 |
| `cmd_customer_application` | 申请单统计 |
| `cmd_approval_task` | 待办任务、KPI、风险任务列表 |
| `cmd_governance_task` | 治理任务统计 |
| `cmd_hierarchy_node` | 层级节点数 |
| `cmd_notification` | 通知列表（当前 0 行） |
| `cmd_import_job` | 侧栏「批量治理」角标计数 |

接口：`/cmd/dashboard/stats`、`/cmd/dashboard/notifications`、`/cmd/approval/kpi`、`/cmd/approval/list`、`/cmd/nav/badge`

---

### 2. 客户主档（customers）
*客户管理 / 客户主档 / 全局客户主档 / 客户只读查询*

| 数据表 | 说明 |
|---|---|
| `cmd_customer` | 客户列表、客户详情（oneId 查询）、停用写回 |
| `cmd_customer_application` | 申请单列表 / 统计 |
| `cmd_approval_task` | 申请对应审批任务（在途重复提示） |
| `cmd_change_request` | 详情弹窗「变更版本」 |
| `cmd_hierarchy_node` | 详情弹窗层级节点 |
| `cmd_hierarchy_relation` | 详情弹窗层级关系 |
| `cmd_hierarchy_relation_hist` | 详情弹窗关系变更历史 |
| `oneid_event` | 详情弹窗 One ID 历史（当前 0 行） |
| `cmd_merge_record` | 详情弹窗合并记录 |
| `cmd_legacy_mapping` | 详情弹窗 Legacy 编码映射 |
| `md_field` | 新建客户表单字段定义 |

接口：`/cmd/customer/list`、`/cmd/customer/application/list`、`/cmd/customer/application/stats`、
`/cmd/customer/oneId/{oneId}`、`/cmd/customer`（新建）、`/cmd/customer/deactivate/{oneId}`、
`/cmd/change/versions/{oneId}`、`/cmd/hierarchy/node/{key}`、`/cmd/hierarchy/relations/{oneId}`、
`/cmd/hierarchy/relationHistory`、`/cmd/oneid/{oneId}/history`、`/cmd/oneid/{oneId}/mergeRecords`、
`/cmd/oneid/legacy/list`、`/cmd/metadata/field/list`、`/cmd/ocr/recognize`

---

### 3. 批量导入 / 批量治理（batch）

| 数据表 | 说明 |
|---|---|
| `cmd_import_job` | 导入任务列表、统计、上传建任务 |
| `cmd_import_row` | 导入明细行、行级治理动作 |
| `cmd_import_template` | 模板列表、模板下载 |
| `cmd_import_template_mapping` | 模板列映射增删改查 |
| `cmd_customer` | 行治理：信用代码/名称匹配已有主档、创建新主档 |
| `cmd_approval_task` | 行治理转审批、合并审批任务 |
| `audit_event` | 上传 / 治理动作留痕 |

接口：`/cmd/import/stats`、`/cmd/import/job/list`、`/cmd/import/job/{id}/result`、`/cmd/import/job/{id}/rows`、
`/cmd/import/row/{id}/action`、`/cmd/import/job`、`/cmd/import/job/upload`、
`/cmd/import/template/list`、`/cmd/import/template/{code}/download`、`/cmd/import/template/mapping`

---

### 4. 客户层级（hier）
*客户层级 / 层级只读查询*

| 数据表 | 说明 |
|---|---|
| `cmd_hierarchy_node` | 层级节点、根节点、新增子节点 |
| `cmd_hierarchy_relation` | 父子关系、新增/修改/关联 |
| `cmd_hierarchy_relation_hist` | 关系变更历史 |
| `cmd_customer` | 未分配节点（客户未挂层级） |
| `cmd_approval_task` | 层级关系变更转审批 |
| `cmd_loop_check_log` | 环路检测日志 |

接口：`/cmd/hierarchy/nodes`、`/node/{key}`、`/roots`、`/childrenPage/{parent}`、
`/relationByChild/{child}`、`/relations/{oneId}`、`/relationHistory`、`/relation`、`/child`、
`/relation/{id}`、`/validate`、`/unassigned`、`/assign`、`/loopCheck`

---

### 5. 变更与停用（change）

| 数据表 | 说明 |
|---|---|
| `cmd_change_request` | 变更申请列表 / KPI / 详情 / 版本 / 生效 / 取消 |
| `md_field` | 可变更字段清单 |
| `cmd_customer` | 变更生效后写回主档、停用写回 |
| `cmd_hierarchy_relation` | 停用影响面（被引用层级关系计数） |
| `cmd_approval_task` | 变更申请转审批任务 |

接口：`/cmd/change/list`、`/cmd/change`、`/cmd/change/fields`、`/cmd/change/kpi`、
`/cmd/change/versions/{oneId}`、`/cmd/change/{oneId}/deactivateResult`、`/cmd/change/{id}/detail`、
`/cmd/change/{code}/effect`、`/cmd/change/{code}/cancel`

---

### 6. 治理与审批 / 全局治理决策（approval）

| 数据表 | 说明 |
|---|---|
| `cmd_approval_task` | 审批队列、KPI、任务详情、审批动作落库 |
| `cmd_customer_application` | 客户申请审批的业务体 |
| `cmd_change_request` | 变更审批的业务体 |
| `cmd_hierarchy_relation` | 层级关系审批的业务体 |
| `cmd_customer` | 审批通过后主档发布 / 合并 |
| `cmd_merge_record` | 合并结果记录 |
| `cmd_workflow_step_log` | 步骤日志（工作流步骤查询） |
| `cmd_approval_action` | 审批动作轨迹（弹窗内决策动作表） |
| `cmd_py_flow_instance` | SpiffWorkflow 实例（审批流程弹窗） |
| `cmd_workflow_step_log` / `cmd_import_job` | 任务详情明细中的步骤/导入上下文 |
| `cmd_import_row` | 任务详情明细中的导入行 |
| `cmd_attachment`* | 任务详情「附件清单」（原生 SQL 只读） |
| `cmd_ocr_result` | 任务详情 OCR 识别结果 |
| `cmd_match_candidate`* / `cmd_match_result`* | 任务详情匹配候选对照（原生 SQL 只读） |
| `cmd_legacy_mapping` | 任务详情 Legacy 映射 |
| `int_run` | 任务详情关联集成批次 |
| `audit_event` | 任务详情审计留痕 |
| `cmd_flow_scene` | 场景信息（泳道/场景名） |
| `dq_rule` / `match_rule` | 规则变更审批通过后生效写回（按快照 `ruleTable` 动态选表） |

\* 仅 `services/step_detail.py` 用原生 SQL 只读

接口：`/cmd/approval/list`、`/cmd/approval/stats`、`/cmd/approval/kpi`、`/cmd/approval/task/{no}/detail`、
`/cmd/approval/action`、`/cmd/approval/flow/{key}`、`/cmd/approval/instance/list`、
`/cmd/approval/workflow-steps`、`/cmd/approval/{id}`

---

### 7. 流程中心 › 已激活工作流（flowWorkitem）

| 数据表 | 说明 |
|---|---|
| `cmd_approval_task` | 运行中实例列表（`flow_instance_id IS NULL` 口径） |
| `cmd_flow_scene` | 场景名 / 流程名 |
| `cmd_py_flow_instance` | SpiffWorkflow 实例绑定状态 |
| `cmd_approval_action` | 流程跟踪：动作轨迹 |
| `cmd_workflow_step_log` | 流程跟踪：步骤日志 |
| 以及「审批任务详情」全部表 | 流程跟踪弹窗内嵌分步骤明细 |

接口：`/cmd/flow/instances`、`/cmd/flow/trace/{taskNo}`、`/cmd/approval/task/{no}/detail`

---

### 8. 流程中心 › 已完成的工作流（flowDone）

同「已激活工作流」，差异仅在 `runState=DONE` 过滤（`cmd_approval_task.status IN 终态`）。
接口：`/cmd/flow/instances`、`/cmd/flow/trace/{taskNo}`

---

### 9. 治理审计 / 管理员日志 / 审计中心（audit）

| 数据表 | 说明 |
|---|---|
| `audit_event` | 审计事件列表、导出数据源 |
| `audit_export_log` | 导出任务登记 |

接口：`/cmd/audit/list`、`/cmd/audit/export`、`/cmd/audit/export/list`

---

### 10. 平台管理（admin）
9 张卡片：字段与值集 / One ID规则 / 角色与权限 / DQ规则 / 匹配规则 / 导入Template / Workflow / DQ Scorecard / 集成配置

| 数据表 | 说明 |
|---|---|
| `md_field` | 字段清单、新增/编辑/删除 |
| `md_value_set` | 值集清单、新增/删除 |
| `cmd_role` | 角色列表 / 策略列表 |
| `cmd_role_permission` | 角色权限矩阵 |
| `cmd_approval_task` | 「发布配置版本」→ 建审批任务 |
| `dq_rule` | DQ 规则（弹窗内管理） |
| `match_rule` | 匹配规则（弹窗内管理） |
| `cmd_import_template` / `cmd_import_template_mapping` | 导入模板与映射 |
| `dq_scorecard` | DQ 分数卡（卡片跳 DQ Scorecard 页） |

接口：`/cmd/metadata/field/list`、`/cmd/metadata/field`、`/cmd/metadata/valueset/list`、
`/cmd/metadata/valueset`、`/cmd/metadata/version/list`、`/cmd/metadata/version`、`/cmd/metadata/version/publish`、
`/cmd/permission/matrix`、`/cmd/permission/role/list`、`/cmd/permission/role`

---

### 11. 集成监控（integration）

| 数据表 | 说明 |
|---|---|
| `int_endpoint` | 端点列表、新增/删除/发布/连通测试 |
| `int_run` | 运行批次列表、Retry |
| `int_message` | 报文列表（当前 0 行） |
| `cmd_approval_task` | 重试触发集成失败审批（`biz_type=INTEGRATION_FAIL`） |
| `dq_rule` / `match_rule` | 集成规则审批回调写回 |

接口：`/cmd/integration/endpoint/list`、`/cmd/integration/endpoint`、`/cmd/integration/endpoint/{id}`、
`/cmd/integration/endpoint/{id}/test`、`/cmd/integration/endpoint/{id}/publish`、
`/cmd/integration/run/list`、`/cmd/integration/run/{id}/retry`、`/cmd/integration/message/list`

---

### 12. One ID 规则管理（oneid）
*无侧栏菜单项，入口＝平台管理 › One ID规则「管理」*

| 数据表 | 说明 |
|---|---|
| `oneid_rule` | 规则读取 / 保存 / 发布 / 复制 |
| `cmd_legacy_mapping` | Legacy 编码映射列表 |
| `oneid_event` | One ID 变更历史（弹窗） |
| `cmd_role` | 策略列表兜底数据源 |

接口：`/cmd/oneid/rule`、`/cmd/oneid/rule/publish`、`/cmd/oneid/rule/copy`、
`/cmd/oneid/policy/list`、`/cmd/oneid/{oneId}/history`、`/cmd/oneid/legacy/list`

---

### 13. DQ Scorecard（dqscore）
*无侧栏菜单项，入口＝平台管理 › DQ Scorecard「查看」*

| 数据表 | 说明 |
|---|---|
| `dq_scorecard` | 分数卡（当前 0 行） |
| `dq_rule` | 规则管理弹窗 |
| `dq_reeval_job` | 历史数据重评估任务登记 |

接口：`/cmd/dq/scorecard`、`/cmd/dq/rule/list`、`/cmd/dq/rule`、`/cmd/dq/simulate`、
`/cmd/dq/reEvaluate`、`/cmd/dq/reEvaluate/impact`

---

### 14. 工作流定义（flowDefinition）
*无侧栏菜单项，入口＝平台管理 › Workflow「管理」*

| 数据表 | 说明 |
|---|---|
| `cmd_flow_scene` | 场景清单 |
| `cmd_flow_def_version` | 部署版本登记 ⚠️ **当前库中不存在** |
| `cmd_flow_node_rule` | 场景配置：节点模板 / 路由条件 / SLA |
| `cmd_approval_task` / `cmd_approval_action` | 泳道图按任务点亮 |

接口：`/cmd/flow/scenes`、`/cmd/flow/scene/{code}/versions`、`/cmd/flow/scene/{code}/config`、
`/cmd/flow/deploy/{code}`、`/cmd/flow/graph/scene/{code}`

---

### 15. POC 覆盖检查（coverage）
*面板已注册，但 5 个角色的菜单配置里都没有入口，当前不可达*

| 数据表 | 说明 |
|---|---|
| `poc_coverage_topic` | 12 个 Demo Topic 清单 |

接口：`/cmd/coverage/list`

---

### 16. 治理任务（gov）
*面板已注册，但菜单配置里无入口，当前不可达*

| 数据表 | 说明 |
|---|---|
| `cmd_governance_task` | 治理任务列表 / 统计 / 合并发起 |
| `cmd_approval_task` | 治理转审批 |

接口：`/cmd/governance/list`、`/cmd/governance/stats`、`/cmd/governance/merge`

---

### 17. 全局（所有页面共享）

| 数据表 | 说明 |
|---|---|
| `cmd_customer` / `cmd_approval_task` | 顶部导航角标 `/cmd/nav/badge` |
| `cmd_py_seq` | 全站主键 / 业务编号生成计数器（Python 侧，启动时创建） |
| `cmd_customer` | 序列生成时读取现有 `GC-` 编号 |

---

## 三、数据表总清单（表 → 行数 → 所属页面）

| # | 数据表 | 当前行数 | 被哪些页面使用 |
|---|---|---|---|
| 1 | `cmd_customer` | 36 | 工作台、客户主档、批量导入、客户层级、变更停用、审批、流程中心 |
| 2 | `cmd_customer_application` | 22 | 工作台、客户主档、审批 |
| 3 | `cmd_approval_task` | 72 | 工作台、客户主档、批量导入、客户层级、变更停用、审批、流程中心、平台管理、集成监控、导航角标 |
| 4 | `cmd_approval_action` | 135 | 审批（详情弹窗）、流程中心 |
| 5 | `cmd_change_request` | 18 | 客户主档、变更与停用、审批 |
| 6 | `cmd_governance_task` | 18 | 工作台、治理任务（不可达） |
| 7 | `cmd_merge_record` | 3 | 客户主档（详情弹窗）、审批 |
| 8 | `cmd_hierarchy_node` | 23 | 工作台、客户主档、客户层级 |
| 9 | `cmd_hierarchy_relation` | 10 | 客户主档、客户层级、变更停用、审批 |
| 10 | `cmd_hierarchy_relation_hist` | 9 | 客户主档、客户层级 |
| 11 | `cmd_workflow_step_log` | 308 | 审批、流程中心 |
| 12 | `cmd_flow_scene` | 9 | 审批（泳道）、流程中心、工作流定义 |
| 13 | `cmd_flow_node_rule` | 10 | 工作流定义 |
| 14 | `cmd_flow_def_version` | ⚠️ 表不存在 | 工作流定义、流程中心 |
| 15 | `cmd_import_job` | 18 | 工作台、批量导入、导航角标、审批详情 |
| 16 | `cmd_import_row` | 80 | 批量导入、审批详情 |
| 17 | `cmd_import_template` | 2 | 批量导入、平台管理 |
| 18 | `cmd_import_template_mapping` | 10 | 批量导入、平台管理 |
| 19 | `oneid_rule` | 9 | One ID 规则管理 |
| 20 | `oneid_event` | 0 | 客户主档（详情弹窗）、One ID |
| 21 | `cmd_legacy_mapping` | 8 | 客户主档、One ID、审批详情 |
| 22 | `cmd_loop_check_log` | 51 | 客户层级 |
| 23 | `dq_rule` | 11 | 平台管理、DQ Scorecard、集成监控（审批回写） |
| 24 | `dq_scorecard` | 0 | DQ Scorecard |
| 25 | `dq_reeval_job` | 6 | DQ Scorecard |
| 26 | `match_rule` | 2 | 平台管理、集成监控（审批回写） |
| 27 | `md_field` | 150 | 客户主档、变更与停用、平台管理 |
| 28 | `md_value_set` | 7 | 平台管理 |
| 29 | `audit_event` | 186 | 批量导入、审批详情、审计中心 |
| 30 | `audit_export_log` | 1 | 审计中心 |
| 31 | `cmd_role` | 5 | 平台管理、One ID |
| 32 | `cmd_role_permission` | 25 | 平台管理 |
| 33 | `int_endpoint` | 5 | 集成监控 |
| 34 | `int_run` | 10 | 集成监控、审批详情 |
| 35 | `int_message` | 0 | 集成监控 |
| 36 | `cmd_ocr_result` | 0 | 审批详情（OCR 识别不落库，故为空） |
| 37 | `cmd_notification` | 0 | 工作台 |
| 38 | `poc_coverage_topic` | 12 | POC 覆盖检查（不可达） |
| 39 | `cmd_attachment` | 0 | 审批详情（原生 SQL 只读，非反射表） |
| 40 | `cmd_match_candidate` | 0 | 审批详情（原生 SQL 只读，非反射表） |
| 41 | `cmd_match_result` | 0 | 审批详情（原生 SQL 只读，非反射表） |
| 42 | `cmd_py_flow_instance` | ⚠️ 表不存在 | 审批、流程中心（后端启动时自动创建） |
| 43 | `cmd_py_seq` | ⚠️ 表不存在 | 全站（后端启动时自动创建） |

---

## 四、需要关注的问题

### ⚠️ 1. `cmd_flow_def_version` 表在当前库中缺失

- `backend/app/core/db.py` 的 `REFLECT_TABLES` 已声明该表，`flow_def_service.py` 明确查询它
  （`current_version` / `list_versions` / `deploy`）。
- 但当前 `ruoyi_plus` 库里 **没有这张表**（`SHOW TABLES LIKE 'cmd_flow\_%'` 只返回
  `cmd_flow_delegate` / `cmd_flow_node_rule` / `cmd_flow_scene`）。
- 根目录的 `_restore_py_tables.sql`（06:17 执行的那次「恢复为 Java 版表结构」）
  **也没有包含** `cmd_flow_def_version`，所以恢复后这张表就消失了。
- 影响：工作流定义页的「版本历史」「是否已部署」、`/cmd/flow/deploy/{code}` 部署动作
  会因 `table("cmd_flow_def_version")` 取不到表而报错。
  （`_be_walk.log` 里 `/cmd/flow/scenes` 曾返回 200，说明表存在时功能正常，是**环境回归**，不是代码 bug。）

### ⚠️ 2. `cmd_py_flow_instance` / `cmd_py_seq` 当前也不在库里

这两张是 Python 侧新增表，由 `init_db()` 在后端启动时自动创建。
当前库里没有 → 说明**那次恢复之后后端还没重新启动过**。
一旦启动，这两张表会自动建好，但 `cmd_flow_def_version` **不会被自动创建**，需要手工补。

### 3. 声明了但从未被查询的表（9 张）

`cmd_customer_field_value`(0行)、`cmd_change_diff`(18行)、`cmd_import_error`(0行)、
`md_model_version`(0行)、`sys_user`(3行)、`sys_role`(3行)、`sys_menu`(156行)、
`cmd_flow_delegate`(0行)、`cfg_sequence`(5行)

这些表在 `REFLECT_TABLES` 白名单里，占启动反射开销，但代码中无任何读写。
其中 `sys_menu` 有 156 行（RuoYi 菜单数据）、`cfg_sequence` 有 5 行，属于历史遗留。

### 4. 数据库中存在但本项目完全不用的表

`ruoyi_plus` 共 116 张表，本项目只用其中 41 张。剩余 75 张主要是：
- RuoYi-Plus 系统表：`sys_*`（31 张）、`gen_table*`
- SnailJob 调度表：`sj_*`（25 张）
- Flowable 工作流表：`flow_*`（11 张，本项目改用 SpiffWorkflow，未使用）
- 测试/其他：`test_*`、`md_model`、`md_value_set_item`、`dq_result*`、`match_rule_field`、`int_run_attempt`、`cfg_biz_rule`、`cfg_config`、`cmd_customer_version`

> 注：`cmd_customer_version`（41 行）只在 `step_detail.py` 的一句说明文案里被提及，**无实际查询**。

# ruoyi_plus_py 业务数据重置说明

> 执行时间：2026-09-23 09:44
> 目标：清空业务数据 / 日志数据 / 工作流流程数据，回到「刚上线、零业务数据」状态
> 数据库：`ruoyi_plus_py`（共 119 张表）

---

## 一、执行结果总览

| 分类 | 表数 | 行数（清理前） | 结果 |
|---|---:|---:|---|
| **清空** — 业务 / 日志 / 工作流运行时 | 74 | 2,909 | 全部归零 |
| **保留** — 系统配置与主数据 | 45 | 886 | 原样保留 |
| 合计 | 119 | 3,795 | — |

### 清空明细

| 分组 | 表数 | 行数 | 涉及表 |
|---|---:|---:|---|
| 客户主档 | 4 | 152 | `cmd_customer`、`cmd_customer_application`、`cmd_customer_field_value`、`cmd_customer_version` |
| 变更/合并/遗留映射 | 4 | 60 | `cmd_change_request`、`cmd_change_diff`、`cmd_merge_record`、`cmd_legacy_mapping` |
| 客户层级 | 4 | 92 | `cmd_hierarchy_node`、`cmd_hierarchy_relation`、`cmd_hierarchy_relation_hist`、`cmd_loop_check_log` |
| 批量导入运行数据 | 3 | 238 | `cmd_import_job`、`cmd_import_row`、`cmd_import_error` |
| 治理/查重/OCR/OneID/DQ 运行数据 | 11 | 26 | `cmd_governance_task`、`cmd_match_candidate`、`cmd_match_result`、`cmd_ocr_result`、`cmd_attachment`、`oneid_event`、`dq_result`、`dq_result_detail`、`dq_scorecard`、`dq_scorecard_dimension`、`dq_reeval_job` |
| 集成运行数据 | 3 | 13 | `int_run`、`int_run_attempt`、`int_message` |
| 工作流与审批运行时 | 17 | 1,538 | `cmd_approval_task`、`cmd_approval_action`、`cmd_workflow_step_log`、`cmd_py_flow_instance`、`cmd_flow_delegate`、`cmd_notification`、`cmd_py_seq` + 旧 Warm-Flow 残留 `flow_*` 共 10 张 |
| 审计与运行日志 | 6 | 764 | `audit_event`、`audit_export_log`、`sys_oper_log`、`sys_login_info`、`sys_message`、`sys_notice` |
| SnailJob 运行时残留 | 15 | 0 | `sj_job_*`、`sj_retry_*`、`sj_notify_*`、`sj_server_node` 等 |
| RuoYi 演示残留/附件 | 7 | 26 | `test_demo`、`test_tree`、`test_leave`、`gen_table`、`gen_table_column`、`sys_oss`、`sys_social` |

### 保留明细（45 张）

| 类别 | 表 |
|---|---|
| 用户/权限/菜单 | `sys_user`(3)、`sys_role`(3)、`sys_user_role`(3)、`sys_role_menu`(117)、`sys_role_dept`(0)、`sys_dept`(10)、`sys_post`(4)、`sys_user_post`(1)、`sys_menu`(156) |
| 字典与系统配置 | `sys_dict_type`(13)、`sys_dict_data`(55)、`sys_config`(3)、`sys_client`(2)、`sys_oss_config`(5) |
| 元数据模型 | `md_model`(3)、`md_field`(164)、`md_value_set`(7)、`md_value_set_item`(26)、`md_model_version`(0) |
| 规则配置 | `dq_rule`(26)、`dq_rule_field`(6)、`match_rule`(5)、`match_rule_field`(9)、`oneid_rule`(9) |
| 流程定义（非流程实例） | `cmd_flow_scene`(9)、`cmd_flow_node_rule`(10)、`cmd_flow_def_version`(9) |
| 权限矩阵 | `cmd_role`(5)、`cmd_role_permission`(25)、`cmd_user_role`(0) |
| 导入模板定义 | `cmd_import_template`(2)、`cmd_import_template_mapping`(17) |
| 集成/治理/配置 | `int_endpoint`(5)、`poc_coverage_topic`(12)、`cfg_config`(20)、`cfg_biz_rule`(0)、`cfg_sequence`(5) |
| 调度框架（未启用） | `sj_group_config`、`sj_job`、`sj_namespace`、`sj_system_user`、`sj_workflow*` 等 |

---

## 二、补充处理（非单纯清空）

1. **编号生成器复位**：`cfg_sequence` 保留定义，游标拉回初始值
   `UPDATE cfg_sequence SET current_value = init_value;`
   → 新业务编号从 1 重新开始（`GC-000001`、`AP-20260923-0001` …）
2. **运行时计数器清空**：`cmd_py_seq` 归零（含 `AE_*` / `APPROVAL_*` 等计数）
3. **自增游标重置**：`cmd_py_flow_instance`、`cmd_workflow_step_log` 的 AUTO_INCREMENT 归 1
4. **无外键约束**：全库 0 个 FOREIGN KEY，清理无需处理级联，直接 TRUNCATE

---

## 三、清理后验证

接口冒烟全部 200（404/405/422 为路径或请求方法不对，与数据无关）：

```
200  /cmd/dashboard/stats    → {"customerTotal":0, "customerActive":0, "hierarchyNodeCount":0 ...}
200  /cmd/customer/stats     → {"total":0, "activeCount":0, "duplicateCount":0, "avgDqScore":0}
200  /cmd/nav/badge          → {}                      侧栏角标全部消失
200  /cmd/metadata/field/list   → 109,967 B           164 个字段定义完好
200  /cmd/permission/matrix      → 2,729 B           权限矩阵完好
200  /cmd/flow/scenes            → 2,648 B           9 个场景 + 部署版本完好
200  /cmd/dq/rule/list           → 8,903 B           26 条 DQ 规则完好
200  /cmd/import/template/list   → 682 B             导入模板完好
```

---

## 四、回滚方式

全量备份在清理前生成（含全部结构与数据，2.9 MB）：

```
_db_backup/ruoyi_plus_py_before_reset_20260923_094435.sql
```

回滚（会覆盖当前所有变更）：

```bash
mysql -h127.0.0.1 -P3306 -uroot -proot \
  --default-character-set=utf8mb4 ruoyi_plus_py < _db_backup/ruoyi_plus_py_before_reset_20260923_094435.sql
```

---

## 五、从头创建业务数据时的注意点

1. **流程定义不需要重新部署**：`cmd_flow_def_version` 已保留 9 个场景的 BPMN 版本记录。
   它是从 `backend/processes/cmd_approval.bpmn` 部署登记的，即使丢失也可通过
   `POST /cmd/flow/deploy/{scene_code}` 重新生成；但审批引擎实际直接读取 BPMN 文件，
   不经该表。
2. **客户 One ID 从 1 开始**：首个客户得到 `GC-000001`。
3. **字段/值集/DQ/匹配/OneID 规则均为初始基线**：`md_field` 164 个字段、`dq_rule` 26 条等
   已就位，直接可用，无需先维护元数据。
4. **`sys_message`、`sys_notice` 已清空**：通知/公告列表为空，属预期。
5. **旧 Warm-Flow 表（`flow_*`）已清空**：本项目审批引擎为 SpiffWorkflow，这组表不被代码引用，
   保留空表仅为兼容库结构。

---

## 六、需要留意的环境细节（未修改，仅提示）

- 后端实际连接的库由 **`backend/.env`** 决定：`DB_NAME=ruoyi_plus_py`。
- `backend/app/core/config.py` 第 1 行注释与第 30 行默认值仍写作 `ruoyi_plus`（历史遗留），
  且仓库根目录没有 `.env`。正常情况下不生效，但若 `backend/.env` 被删除或未随部署分发，
  后端会静默回落到 `ruoyi_plus` 库 —— 该库结构不同（缺 `cmd_flow_def_version`），会引发
  「工作流定义页报错 / 部署失败」。建议后续把默认值改为 `ruoyi_plus_py` 或补充根目录 `.env`。
- **另一个库 `ruoyi_plus` 未做任何改动**（其中 `cmd_customer` 仍有 36 行等历史数据）。

---

## 七、产出文件

| 文件 | 说明 |
|---|---|
| `_db_backup/ruoyi_plus_py_before_reset_20260923_094435.sql` | 清理前全量备份 |
| `_reset_business_data.sql` | 本次实际执行的清理 SQL |
| `_reset_business_data.py` | 可复用重置脚本（含分类校验，支持干跑） |

重复使用：

```bash
python _reset_business_data.py          # 干跑：校验 119 张表归类无遗漏，不写库
python _reset_business_data.py --apply  # 执行清理并自动校验归零
```

脚本内置三重校验：表必须存在、不得同时出现在保留与清空清单、全部 119 张表必须被归类
（有未归类的表会直接拒绝执行），避免后续加表时漏清理。

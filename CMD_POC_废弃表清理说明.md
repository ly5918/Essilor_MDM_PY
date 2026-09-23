# ruoyi_plus_py 废弃表清理说明

> 执行时间：2026-09-23 10:09
> 目标：识别并删除由 RuoYi 框架（及 SnailJob / Warm-Flow 中间件）遗留、Python 项目已不再使用的表
> 结果：**119 张 → 64 张，删除 55 张**

---

## 一、分析方法

1. **全量引用扫描**：遍历 `backend/app`、`frontend/src` 共 **378 个源文件**（`.py/.ts/.vue/.js`），
   用整词正则统计每张表的命中位置 → 脚本 `_scan_table_usage.py`：42 张表零命中。
2. **剔除注释干扰**：`flow_instance` / `flow_node` / `flow_skip` 初判有引用，逐条核查后确认
   命中全部落在注释与文档字符串里（`types.ts:2168`、`mock.ts:1162`、`options.ts:255` 等，均为
   「引擎 flow_node / flow_skip 结构」这类旧引擎设计说明），并非真实读写 → 剔除注释后重判为零引用。
3. **动态表名排查**：`services/rule_flow.py:84` 有 `table(snapshot.get("ruleTable"))` 的动态拼接，
   追踪全部调用点确认实参只有 `dq_rule` 与 `match_rule`（均在反射清单内），不会误删。
4. **划定不可删除红线**：见下一节。
5. **三重护栏校验后执行**：删除脚本 `_drop_unused_tables.py` 内置拒绝机制（见第四节）。

---

## 二、关键发现：删除红线（决定了 sys_* 三张不能删）

`backend/app/core/db.py` 维护了一份**硬编码反射清单**：

```python
REFLECT_TABLES = [ ... 48 张 ... ]          # 含 "sys_user", "sys_role", "sys_menu"

async def init_db():
    metadata.reflect(sync_conn, only=REFLECT_TABLES)
    for name in REFLECT_TABLES:
        _tables[name] = metadata.tables[name]   # ← 表不存在会直接 KeyError
```

**清单内的表一旦删除，后端启动即崩溃**（`init_db()` 在第 96 行取不到该表）。
因此 `sys_user`(3 行)、`sys_role`(3 行)、`sys_menu`(156 行) 虽无业务读写，仍予以保留 ——
它们是被启动流程依赖的最小集合。

> 若日后确实想连这三张一起清掉，需**同步**修改 `db.py` 的 `REFLECT_TABLES`（删除脚本已实现该保护：
> 任何出现在清单里的表会被自动拒绝，不必担心误操作）。

---

## 三、删除清单（55 张）

| 分组 | 数量 | 表 |
|---|---:|---|
| **SnailJob 分布式调度框架**（未启用） | 23 | `sj_distributed_lock`、`sj_group_config`、`sj_job`、`sj_job_executor`、`sj_job_log_message`、`sj_job_summary`、`sj_job_task`、`sj_job_task_batch`、`sj_namespace`、`sj_notify_config`、`sj_notify_recipient`、`sj_retry`、`sj_retry_dead_letter`、`sj_retry_scene_config`、`sj_retry_summary`、`sj_retry_task`、`sj_retry_task_log_message`、`sj_server_node`、`sj_system_user`、`sj_system_user_permission`、`sj_workflow`、`sj_workflow_node`、`sj_workflow_task_batch` |
| **RuoYi 系统管理表** | 17 | `sys_client`、`sys_config`、`sys_dept`、`sys_dict_data`、`sys_dict_type`、`sys_login_info`、`sys_message`、`sys_notice`、`sys_oper_log`、`sys_oss`、`sys_oss_config`、`sys_post`、`sys_role_dept`、`sys_role_menu`、`sys_social`、`sys_user_post`、`sys_user_role` |
| **旧 Warm-Flow 工作流引擎表**（已被 SpiffWorkflow 取代） | 10 | `flow_category`、`flow_definition`、`flow_his_task`、`flow_instance`、`flow_instance_biz_ext`、`flow_node`、`flow_skip`、`flow_spel`、`flow_task`、`flow_user` |
| **RuoYi 代码生成器** | 2 | `gen_table`、`gen_table_column` |
| **RuoYi 内置演示表** | 3 | `test_demo`、`test_leave`、`test_tree` |

删前合计有数据的表：`sys_role_menu`(117)、`sys_dict_data`(55)、`sys_dict_type`(13)、`sys_dept`(10)、
`sys_oss_config`(5)、`sys_post`(4)、`sys_user_role`(3)、`sys_config`(3)、`sys_client`(2)、
`sj_group_config`(2)、`sj_namespace`(2)、`sj_job`(1)、`sj_system_user`(1)、`sys_user_post`(1) —— 已全部备份。

---

## 四、保留清单（64 张）

**CMD 业务表 61 张**（`cmd_*` / `md_*` / `dq_*` / `match_*` / `oneid_*` / `int_*` / `audit_*` / `poc_*` / `cfg_*`）

**RuoYi 框架表 3 张（反射依赖，必须留）**：`sys_user`、`sys_role`、`sys_menu`

### 保留但当前零引用的 CMD 表（9 张）— 建议保留

| 表 | 保留理由 |
|---|---|
| `md_model` | 元数据模型主表，`md_model_version` 的父实体，与 `md_field` 构成完整模型树 |
| `dq_result`、`dq_result_detail` | DQ 引擎评分产出的落库表，规则运行后写入 |
| `dq_rule_field` | 规则-字段关联，规则明细维度，与 `dq_rule` 配对 |
| `dq_scorecard_dimension` | 评分卡维度，`dq_scorecard` 的子表 |
| `match_rule_field` | 匹配规则字段权重，与 `match_rule` 配对 |
| `int_run_attempt` | 集成重试明细，`int_run` 的子表 |
| `cfg_biz_rule`、`cfg_config` | 规则/参数配置域，与 `cfg_sequence` 同族 |

这些虽暂时无代码读写，但**同属 CMD 业务数据模型且有父子关系**，删除会破坏模型完整性；
且不同于框架表，它们的存在不带来任何维护负担。

---

## 五、删除后的验证

```
✅ REFLECT_TABLES 48 张全部存在 → init_db() 不会因缺表崩溃（最重要）
✅ 库表数 119 → 64，与预期一致，无残留无少删
✅ 26 个核心接口全部 200：
   /cmd/dashboard/stats  /cmd/nav/badge  /cmd/customer/list  /cmd/customer/stats
   /cmd/customer/application/list  /cmd/metadata/field/list  /cmd/metadata/valueset/list
   /cmd/metadata/version/list  /cmd/permission/role/list  /cmd/permission/matrix
   /cmd/dq/rule/list  /cmd/dq/scorecard  /cmd/match/rule/list  /cmd/oneid/rule
   /cmd/oneid/policy/list  /cmd/flow/scenes  /cmd/flow/instances  /cmd/import/template/list
   /cmd/integration/endpoint/list  /cmd/coverage/list  /cmd/hierarchy/roots
   /cmd/hierarchy/nodes  /cmd/approval/list  /cmd/approval/stats  /cmd/audit/list
   /cmd/change/list
```

> 注：运行中的后端已缓存 metadata，本次删除不影响其在跑实例；上述反射校验等价于「下次重启」的启动前置检查。

---

## 六、回滚方式

已在删除前自动导出待删表的结构与数据：

```
_db_backup/_dropped_tables_backup_20260923_100929.sql     # 55 张被删表，含 CREATE TABLE + 数据（125 KB）
_db_backup/ruoyi_plus_py_schema_before_drop_20260923_100010.sql  # 删表前全库 119 张的结构快照
_db_backup/_ruoyi_sys_tables_withdata_20260923_100010.sql        # sys_* 等 25 张表单独导出
```

恢复单张表：

```bash
mysql -h127.0.0.1 -P3306 -uroot -proot ruoyi_plus_py < _db_backup/_dropped_tables_backup_20260923_100929.sql
```

---

## 七、产出文件

| 文件 | 说明 |
|---|---|
| `_scan_table_usage.py` | 表引用扫描器（可重复跑，输出每张表的命中文件与次数） |
| `_drop_unused_tables.py` | 清理脚本，三重护栏：① 禁止删除 `db.py` REFLECT_TABLES 内的表（实时解析源码）② 待删表必须剔除注释后零引用 ③ 删除前自动备份。默认干跑，`--apply` 才执行 |

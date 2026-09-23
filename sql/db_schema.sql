/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_event` (
  `id` bigint NOT NULL COMMENT '主键',
  `event_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '事件编号（对外展示）',
  `event_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '事件类型（LOGIN / LOGOUT / CREATE / UPDATE / DEACTIVATE / APPROVE / REJECT / ESCALATE / MERGE / EXPORT / CONFIG_CHANGE / PERMISSION_CHANGE / INTEGRATION / VIEW_SENSITIVE）',
  `event_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '事件名称',
  `biz_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '业务类型（CUSTOMER / HIERARCHY / IMPORT / CHANGE / RULE / ROLE）',
  `biz_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '业务主键',
  `one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '关联 One ID',
  `operator_id` bigint DEFAULT NULL COMMENT '操作人（sys_user.user_id）',
  `operator_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '操作人姓名（冗余，用户删除后仍可追溯）',
  `operator_role` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '操作角色（冗余）',
  `dept_id` bigint DEFAULT NULL COMMENT '操作部门',
  `event_time` datetime DEFAULT NULL COMMENT '事件时间',
  `client_ip` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户端 IP',
  `client_agent` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户端 UA',
  `request_url` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '请求地址',
  `request_method` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '请求方法',
  `before_json` json DEFAULT NULL COMMENT '变更前快照',
  `after_json` json DEFAULT NULL COMMENT '变更后快照',
  `changed_fields` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '变更字段列表',
  `result` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'SUCCESS' COMMENT '结果（SUCCESS / FAILED）',
  `error_message` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '错误信息',
  `duration_ms` bigint DEFAULT NULL COMMENT '耗时（毫秒）',
  `risk_level` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '风险等级（High / Medium / Low）',
  `sensitive_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否涉及敏感数据（Y是 N否）',
  `flow_instance_id` bigint DEFAULT NULL COMMENT '关联流程实例',
  `remark` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志（审计数据逻辑保留）',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_audit_event_id` (`event_id`),
  KEY `idx_audit_type_time` (`event_type`,`event_time`),
  KEY `idx_audit_biz` (`biz_type`,`biz_id`),
  KEY `idx_audit_operator` (`operator_id`,`event_time`),
  KEY `idx_audit_oneid` (`one_id`),
  KEY `idx_audit_risk` (`risk_level`,`event_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='统一审计事件表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_export_log` (
  `id` bigint NOT NULL COMMENT '主键',
  `export_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '导出编号',
  `export_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '导出类型（AUDIT_EVENT / CUSTOMER / CHANGE_REPORT）',
  `filter_json` json DEFAULT NULL COMMENT '导出筛选条件',
  `file_name` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '导出文件名',
  `file_path` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '文件路径',
  `oss_id` bigint DEFAULT NULL COMMENT '对象存储 ID',
  `row_count` int NOT NULL DEFAULT '0' COMMENT '导出行数',
  `export_status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'SUCCESS' COMMENT '导出状态（PROCESSING / SUCCESS / FAILED）',
  `export_time` datetime DEFAULT NULL COMMENT '导出时间',
  `operator_id` bigint DEFAULT NULL COMMENT '导出人',
  `operator_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '导出人姓名',
  `client_ip` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户端 IP',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_audit_export_code` (`export_code`),
  KEY `idx_audit_export_op` (`operator_id`,`export_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='审计导出记录表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cfg_biz_rule` (
  `id` bigint NOT NULL COMMENT '主键',
  `rule_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '规则编码（全局唯一）',
  `rule_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '规则名称',
  `scene` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '业务场景（MATCH / DQ / ROUTE / ESCALATE / SLA / NOTIFY）',
  `engine_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'SPEL' COMMENT '表达式引擎（SPEL / GROOVY / AVIATOR / JSON_COND）',
  `expression` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '规则表达式',
  `true_action` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '命中后动作（如 ESCALATE_TO_GC）',
  `false_action` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '未命中动作',
  `priority` int NOT NULL DEFAULT '0' COMMENT '优先级（数字越大越先执行）',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cfg_rule_code` (`rule_code`),
  KEY `idx_cfg_rule_scene` (`scene`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='通用业务规则表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cfg_config` (
  `id` bigint NOT NULL COMMENT '主键',
  `config_key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '参数键（全局唯一，如 cmd.match.threshold）',
  `config_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '参数名称',
  `config_value` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '参数值',
  `value_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'STRING' COMMENT '值类型（STRING/NUMBER/BOOLEAN/JSON/LIST）',
  `group_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '分组编码（MATCH/DQ/ONEID/WORKFLOW/IMPORT/INTEGRATION/UI）',
  `default_value` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '默认值（用于一键还原）',
  `is_system` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否系统内置（Y是 N否，Y不允许删除）',
  `is_visible` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'Y' COMMENT '是否在管理界面可见（Y是 N否）',
  `order_num` int NOT NULL DEFAULT '0' COMMENT '显示顺序',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注/说明',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志（0存在 1删除）',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cfg_config_key` (`config_key`),
  KEY `idx_cfg_config_group` (`group_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='系统参数配置表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cfg_sequence` (
  `id` bigint NOT NULL COMMENT '主键',
  `seq_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '规则编码（ONE_ID / APPROVAL_NO / IMPORT_BATCH ...）',
  `seq_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '规则名称',
  `prefix` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '固定前缀（如 GC）',
  `date_pattern` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '日期部分格式（yyyyMMdd / yyyy / 空）',
  `serial_length` int NOT NULL DEFAULT '6' COMMENT '流水号长度',
  `step` int NOT NULL DEFAULT '1' COMMENT '步长',
  `init_value` bigint NOT NULL DEFAULT '1' COMMENT '起始值',
  `current_value` bigint NOT NULL DEFAULT '0' COMMENT '当前值',
  `cycle_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'NONE' COMMENT '重置周期（NONE不重置 / DAY / MONTH / YEAR）',
  `separator` varchar(8) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '分隔符（如 - ）',
  `suffix` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '固定后缀',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cfg_seq_code` (`seq_code`),
  KEY `idx_cfg_seq_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='流水号生成规则表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_approval_action` (
  `id` bigint NOT NULL COMMENT '主键',
  `task_id` bigint NOT NULL COMMENT '待办任务 ID（cmd_approval_task.id）',
  `task_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '任务编号（冗余）',
  `one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户主数据标识（One ID）',
  `action_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '动作类型（SUBMIT 提交 / APPROVE 批准 / REJECT 拒绝 / RETURN 退回 / ESCALATE 升级 / TRANSFER 转办 / DELEGATE 委托 / ADD_SIGN 加签 / CLAIM 认领 / LINK 关联已有 / CREATE_NEW 确认新建 / EXCLUDE 排除 / MERGE 合并 / WITHDRAW 撤回 / COMMENT 评论）',
  `action_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '动作名称（展示用）',
  `from_node_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '源节点编码',
  `to_node_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '目标节点编码',
  `operator_id` bigint DEFAULT NULL COMMENT '操作人',
  `operator_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '操作人姓名（冗余）',
  `operator_role` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '操作角色（BU_STEWARD / GC_STEWARD）',
  `action_time` datetime DEFAULT NULL COMMENT '操作时间',
  `opinion` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '审批意见',
  `attach_ids` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '附件 ID 列表（逗号分隔）',
  `before_state` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '操作前状态',
  `after_state` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '操作后状态',
  `evidence_json` json DEFAULT NULL COMMENT '操作证据（决策依据快照）',
  `flow_task_id` bigint DEFAULT NULL COMMENT '关联 Warm-Flow 任务 ID',
  `flow_his_id` bigint DEFAULT NULL COMMENT '关联 Warm-Flow 历史任务 ID',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_cmd_act_task` (`task_id`,`action_time`),
  KEY `idx_cmd_act_operator` (`operator_id`),
  KEY `idx_cmd_act_type` (`action_type`),
  KEY `idx_action_one_id` (`one_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='审批动作轨迹表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_approval_task` (
  `id` bigint NOT NULL COMMENT '主键',
  `task_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '任务编号（页面"申请编号"列）',
  `task_category` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '任务分类（APPROVAL 审批 / GOVERNANCE 治理复核 / RETURNED 升级退回 / DONE 我已处理）',
  `biz_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '业务类型（CUSTOMER_CREATE / CUSTOMER_CHANGE / DEACTIVATE / HIER_RELATION / IMPORT_BATCH / MERGE）',
  `biz_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '业务主键',
  `biz_title` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '业务标题（客户主题）',
  `one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '关联 One ID',
  `scene_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '业务场景（cmd_flow_scene.scene_code）',
  `applicant_id` bigint DEFAULT NULL COMMENT '申请人',
  `applicant_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '申请人姓名（冗余）',
  `bu_scope` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '归属 BU（数据权限维度）',
  `scope` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'BU' COMMENT '审批 Scope（BU / GC / CROSS_BU）',
  `current_node_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '当前流程节点编码',
  `current_node_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '当前节点名称（页面"当前节点"）',
  `assignee_id` bigint DEFAULT NULL COMMENT '当前处理人',
  `assignee_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '当前处理人姓名（冗余）',
  `assignee_role` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '当前处理角色（BU_STEWARD / GC_STEWARD / ...）',
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'PENDING' COMMENT '状态（DRAFT / PENDING 待审批 / APPROVED 通过 / REJECTED 拒绝 / RETURNED 退回 / ESCALATED 已升级 / CANCELLED 撤销 / COMPLETED 完成）',
  `risk_level` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'Medium' COMMENT '风险等级（High / Medium / Low）',
  `dq_score` decimal(5,2) DEFAULT NULL COMMENT '质量分（页面 DQ 列）',
  `duplicate_state` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '重复状态（页面 Duplicate 列：EXACT / SUSPECTED / NEW / NONE）',
  `cross_bu_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否跨 BU',
  `submit_time` datetime DEFAULT NULL COMMENT '提交时间',
  `sla_due` datetime DEFAULT NULL COMMENT 'SLA 应完成时间',
  `sla_state` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'NORMAL' COMMENT 'SLA 状态（NORMAL 正常 / DUE_SOON 临近 / OVERDUE 已超时）',
  `finish_time` datetime DEFAULT NULL COMMENT '完成时间',
  `duration_hours` decimal(10,2) DEFAULT NULL COMMENT '实际处理时长（小时）',
  `opinion` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '最新审批意见',
  `evidence_json` json DEFAULT NULL COMMENT '证据快照（自动检查结果 / 治理证据 / Before-After）',
  `biz_snapshot_json` json DEFAULT NULL COMMENT '业务数据快照（避免二次查询）',
  `flow_instance_id` bigint DEFAULT NULL COMMENT 'Warm-Flow 流程实例 ID（flow_instance.id）',
  `flow_task_id` bigint DEFAULT NULL COMMENT 'Warm-Flow 待办任务 ID（flow_task.id）',
  `flow_definition_id` bigint DEFAULT NULL COMMENT '流程定义 ID（flow_definition.id）',
  `flow_status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '流程状态镜像（0待提交 1审批中 2通过 4终止 5作废 6撤销 8完成 9退回）',
  `remark` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cmd_appr_no` (`task_no`),
  KEY `idx_cmd_appr_cat_status` (`task_category`,`status`),
  KEY `idx_cmd_appr_assignee` (`assignee_id`,`status`),
  KEY `idx_cmd_appr_scope` (`scope`,`status`),
  KEY `idx_cmd_appr_sla` (`sla_state`,`sla_due`),
  KEY `idx_cmd_appr_biz` (`biz_type`,`biz_id`),
  KEY `idx_cmd_appr_risk` (`risk_level`),
  KEY `idx_cmd_appr_flow` (`flow_instance_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='统一待办/审批任务表（治理与审批合并）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_attachment` (
  `id` bigint NOT NULL COMMENT '主键',
  `biz_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '业务类型（CUSTOMER / HIERARCHY / IMPORT / CHANGE）',
  `biz_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '业务主键（如 one_id / 申请编号）',
  `file_name` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '原始文件名',
  `file_path` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '存储路径',
  `file_size` bigint DEFAULT NULL COMMENT '文件大小（字节）',
  `file_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '文件类型（pdf / jpg / png / xlsx）',
  `file_md5` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '文件 MD5（用于重复检测）',
  `oss_id` bigint DEFAULT NULL COMMENT '对象存储 ID（对接 RuoYi sys_oss）',
  `category` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '附件分类（BUSINESS_LICENSE 营业执照 / TAX 税务 / OTHER）',
  `ocr_status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'OCR 状态（NONE / PROCESSING / DONE / FAILED）',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_cmd_attach_biz` (`biz_type`,`biz_id`),
  KEY `idx_cmd_attach_md5` (`file_md5`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='附件表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_change_diff` (
  `id` bigint NOT NULL COMMENT '主键',
  `request_id` bigint NOT NULL COMMENT '变更申请 ID（cmd_change_request.id）',
  `request_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '申请编号（冗余）',
  `field_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '字段编码',
  `field_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '字段名称',
  `before_value` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '变更前值',
  `after_value` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '变更后值',
  `is_key_field` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否关键字段（Y：单独审批）',
  `is_sensitive` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否敏感字段',
  `change_flag` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'MODIFY' COMMENT '变化类型（ADD 新增 / MODIFY 修改 / DELETE 删除 / SAME 未变）',
  `dq_impact` decimal(5,2) DEFAULT NULL COMMENT '对质量分的影响',
  `order_num` int NOT NULL DEFAULT '0' COMMENT '显示顺序',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_cmd_diff_req` (`request_id`),
  KEY `idx_cmd_diff_field` (`field_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='变更字段差异明细表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_change_request` (
  `id` bigint NOT NULL COMMENT '主键',
  `request_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '申请编号',
  `one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'One ID',
  `legal_name` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户名称（冗余）',
  `change_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '变更类型（UPDATE 属性变更 / DEACTIVATE 逻辑停用 / RESTORE 恢复启用 / MERGE 合并 / LEVEL_CHANGE 层级调整）',
  `target_status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '目标状态（停用场景：inactive / archived）',
  `is_key_change` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否关键属性变更（Y：需高级别审批）',
  `bu_scope` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '归属 BU',
  `change_reason` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '变更原因',
  `effective_date` datetime DEFAULT NULL COMMENT '期望生效日期',
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'DRAFT' COMMENT '状态（DRAFT / PENDING / APPROVED / REJECTED / EFFECTIVE / CANCELLED）',
  `impact_json` json DEFAULT NULL COMMENT '影响分析（关联层级、下游系统、存量单据）',
  `relation_check` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '关联关系检查（PASS / WARN / FAIL，停用时检查是否被引用）',
  `relation_msg` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '关系检查说明',
  `flow_instance_id` bigint DEFAULT NULL COMMENT '关联流程实例',
  `approval_id` bigint DEFAULT NULL COMMENT '关联待办 ID',
  `approved_by` bigint DEFAULT NULL COMMENT '审批人',
  `approved_time` datetime DEFAULT NULL COMMENT '审批时间',
  `effective_time` datetime DEFAULT NULL COMMENT '实际生效时间',
  `remark` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cmd_change_code` (`request_code`),
  KEY `idx_cmd_change_oneid` (`one_id`),
  KEY `idx_cmd_change_type` (`change_type`,`status`),
  KEY `idx_cmd_change_bu` (`bu_scope`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='客户变更与停用申请表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_customer` (
  `id` bigint NOT NULL COMMENT '主键',
  `one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'One ID（全局唯一，生成后永不变更）',
  `legal_name` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '客户法定名称',
  `legal_name_en` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户英文名称',
  `short_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户简称',
  `credit_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '统一社会信用代码（关键匹配字段）',
  `tax_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '税号',
  `customer_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户类型（SoldTo / ShipTo / Payer / BillTo）',
  `customer_level` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户层级（A1 / A2 / A3）',
  `product_line` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '产品线(High End/Mainstream)',
  `bu_scope` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '归属 BU（数据权限隔离维度，如 High End）',
  `gc_scope_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否跨 BU 全局可见（Y是 N否）',
  `country` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '国家/地区',
  `province` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '省份',
  `city` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '城市',
  `address` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '注册地址',
  `payer_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'Payer编码',
  `postal_code` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '邮编',
  `contact_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '联系人',
  `contact_phone` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '联系电话',
  `contact_email` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '邮箱',
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'draft' COMMENT '状态（draft / pending / active / inactive / archived / rejected）',
  `source_system` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '来源系统（OCR / EXCEL / SAP / CRM / MANUAL）',
  `source_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '来源系统主键',
  `dq_score` decimal(5,2) DEFAULT NULL COMMENT '数据质量总分（冗余自 dq_scorecard，避免列表 JOIN）',
  `dq_grade` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '质量等级（A / B / C / D）',
  `match_state` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '匹配状态（EXACT / SUSPECTED / NEW / REVIEW / INVALID）',
  `duplicate_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '疑似重复标记（Y是 N否）',
  `merged_to_one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '合并到哪个 One ID（被合并后指向主记录）',
  `version_no` int NOT NULL DEFAULT '1' COMMENT '当前版本号（对应 cmd_customer_version）',
  `effective_from` datetime DEFAULT NULL COMMENT '生效时间',
  `effective_to` datetime DEFAULT NULL COMMENT '失效时间（逻辑停用写入）',
  `approved_by` bigint DEFAULT NULL COMMENT '审批人',
  `approved_time` datetime DEFAULT NULL COMMENT '审批时间',
  `flow_instance_id` bigint DEFAULT NULL COMMENT '关联 Warm-Flow 流程实例（flow_instance.id）',
  `flow_status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '工作流实例状态（Warm-Flow flow_instance.flow_status 镜像）',
  `remark` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性（未建模字段统一放这里）',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志（0存在 1删除）',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cmd_customer_oneid` (`one_id`),
  KEY `idx_cmd_customer_status` (`status`,`bu_scope`),
  KEY `idx_cmd_customer_credit` (`credit_code`),
  KEY `idx_cmd_customer_name` (`legal_name`(191)),
  KEY `idx_cmd_customer_source` (`source_system`,`source_id`),
  KEY `idx_cmd_customer_dq` (`dq_score`),
  KEY `idx_cmd_customer_flow` (`flow_instance_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='客户主档表（Golden Record）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_customer_application` (
  `id` bigint NOT NULL COMMENT '主键（沿用原 cmd_customer.id，审批任务 biz_id 无需改写）',
  `app_no` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '申请编号（AP-yyyyMMdd-####，与 cmd_approval_task.task_no 同值同源）',
  `one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'One ID（提交时预分配；发布主档沿用此号，拒绝/关联已有则作废保留）',
  `legal_name` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '客户法定名称',
  `legal_name_en` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户英文名称',
  `short_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户简称',
  `credit_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '统一社会信用代码（关键匹配字段）',
  `tax_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '税号',
  `customer_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户类型（SoldTo / ShipTo / Payer / BillTo）',
  `customer_level` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户层级（A1 / A2 / A3）',
  `product_line` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '产品线(High End/Mainstream)',
  `bu_scope` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '归属 BU（数据权限隔离维度）',
  `gc_scope_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否跨 BU 全局可见（Y是 N否）',
  `country` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '国家/地区',
  `province` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '省份',
  `city` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '城市',
  `address` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '注册地址',
  `payer_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'Payer编码',
  `postal_code` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '邮编',
  `contact_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '联系人',
  `contact_phone` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '联系电话',
  `contact_email` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '邮箱',
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'pending' COMMENT '申请状态（draft / pending / returned / rejected / approved）',
  `source_system` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '来源系统（OCR / EXCEL / SAP / CRM / MANUAL）',
  `source_id` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '来源系统主键',
  `dq_score` decimal(5,2) DEFAULT NULL COMMENT '数据质量总分（提交时自动检查写入）',
  `dq_grade` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '质量等级（A / B / C / D）',
  `match_state` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '匹配状态（EXACT / SUSPECTED / NEW）',
  `duplicate_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '疑似重复标记（Y是 N否）',
  `merged_to_one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '关联到的既有 One ID（EXACT / SUSPECTED 批准合并时回填）',
  `effective_from` datetime DEFAULT NULL COMMENT '生效时间（发布主档时写入）',
  `approved_by` bigint DEFAULT NULL COMMENT '审批人（发布 / 终态写入）',
  `approved_time` datetime DEFAULT NULL COMMENT '审批时间',
  `flow_instance_id` bigint DEFAULT NULL COMMENT '关联 Warm-Flow 流程实例（flow_instance.id）',
  `flow_status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '工作流实例状态（Warm-Flow flow_instance.flow_status 镜像）',
  `remark` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性（未建模字段统一放这里）',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志（0存在 1删除）',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cmd_customer_application_oneid` (`one_id`),
  KEY `idx_app_credit_code` (`credit_code`),
  KEY `idx_app_status_bu` (`status`,`bu_scope`),
  KEY `idx_app_app_no` (`app_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='客户新建申请单（申请态与主档分离；主档表只存审批通过后的 Golden Record）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_customer_field_value` (
  `id` bigint NOT NULL COMMENT '主键',
  `one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'One ID',
  `model_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'CUSTOMER' COMMENT '模型编码（支持未来扩展实体）',
  `field_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '字段编码（对应 md_field.field_code）',
  `field_value` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '字段值（统一文本存储，按 data_type 解析）',
  `value_number` decimal(20,6) DEFAULT NULL COMMENT '数值型冗余（便于范围查询与排序）',
  `value_date` datetime DEFAULT NULL COMMENT '日期型冗余（便于时间范围查询）',
  `version_no` int NOT NULL DEFAULT '1' COMMENT '所属客户版本号',
  `scope_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'GC' COMMENT '字段归属范围（GC / BU / SOURCE）',
  `owner_bu` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '归属 BU',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cmd_field_val` (`one_id`,`model_code`,`field_code`,`version_no`),
  KEY `idx_cmd_field_val_code` (`field_code`,`field_value`(100)),
  KEY `idx_cmd_field_val_num` (`field_code`,`value_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='客户扩展字段值表（EAV）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_customer_version` (
  `id` bigint NOT NULL COMMENT '主键',
  `one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'One ID',
  `version_no` int NOT NULL COMMENT '版本号（同一 one_id 内递增）',
  `change_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '变更类型（CREATE / UPDATE / DEACTIVATE / MERGE / RESTORE）',
  `change_reason` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '变更原因',
  `snapshot_json` json DEFAULT NULL COMMENT '变更后完整快照',
  `before_json` json DEFAULT NULL COMMENT '变更前快照（首版本为空）',
  `changed_fields` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '本次变更的字段编码列表（逗号分隔）',
  `rule_version` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '当时生效的元数据版本',
  `dq_score` decimal(5,2) DEFAULT NULL COMMENT '该版本的质量总分',
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '版本状态（effective 生效中 / history 历史）',
  `source_system` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '来源系统',
  `flow_instance_id` bigint DEFAULT NULL COMMENT '触发该版本的流程实例',
  `change_request_id` bigint DEFAULT NULL COMMENT '关联变更申请（cmd_change_request.id）',
  `remark` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cmd_cust_ver` (`one_id`,`version_no`),
  KEY `idx_cmd_cust_ver_type` (`change_type`),
  KEY `idx_cmd_cust_ver_flow` (`flow_instance_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='客户版本快照表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_flow_def_version` (
  `id` bigint NOT NULL,
  `scene_code` varchar(64) NOT NULL COMMENT '场景编码',
  `flow_code` varchar(64) NOT NULL COMMENT '流程编码',
  `version_no` varchar(16) NOT NULL COMMENT '版本号 v1.0 起',
  `definition_id` varchar(64) NOT NULL COMMENT '定义ID（flow_code#版本）',
  `process_id` varchar(64) DEFAULT NULL COMMENT 'BPMN process id',
  `node_count` int DEFAULT '0' COMMENT '泳道节点数',
  `bpmn_hash` varchar(64) DEFAULT NULL COMMENT 'BPMN 文件 sha256（变更检测）',
  `bpmn_xml` longtext COMMENT 'BPMN 快照',
  `status` char(1) DEFAULT '1' COMMENT '0=当前版本 1=历史',
  `deployed_by` varchar(64) DEFAULT NULL,
  `deployed_at` datetime DEFAULT NULL,
  `remark` varchar(255) DEFAULT NULL,
  `del_flag` char(1) DEFAULT '0',
  `create_time` datetime DEFAULT NULL,
  `update_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_scene_ver` (`scene_code`,`version_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='CMD 流程定义版本登记（SpiffWorkflow 部署历史）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_flow_delegate` (
  `id` bigint NOT NULL COMMENT '主键',
  `delegator_id` bigint NOT NULL COMMENT '委托人（原审批人）',
  `delegatee_id` bigint NOT NULL COMMENT '被委托人（实际审批人）',
  `scene_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '适用业务场景（为空表示全部）',
  `bu_scope` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '适用 BU（为空表示全部）',
  `start_time` datetime NOT NULL COMMENT '生效开始时间',
  `end_time` datetime NOT NULL COMMENT '生效结束时间',
  `reason` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '委托原因',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0生效 1已失效）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_cmd_dele_from` (`delegator_id`,`status`),
  KEY `idx_cmd_dele_to` (`delegatee_id`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='审批委托代理表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_flow_node_rule` (
  `id` bigint NOT NULL COMMENT '主键',
  `scene_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '业务场景编码',
  `node_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'Warm-Flow 节点编码（flow_node.node_code）',
  `node_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '节点名称（冗余）',
  `condition_expr` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '命中条件表达式（如 risk_level == "High" || cross_bu == true）',
  `assignee_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'ROLE' COMMENT '审批人类型（ROLE 角色 / USER 指定人 / DEPT_LEADER 部门主管 / SPEL 表达式 / INITIATOR_LEADER 发起人上级）',
  `assignee_value` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '审批人值（角色编码 / 用户ID / SpEL 表达式）',
  `scope_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '适用范围（GC / BU / CROSS_BU）',
  `bu_scope` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '适用 BU（为空表示全部）',
  `multi_mode` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'ALL' COMMENT '多审批人模式（ALL 会签 / ANY 或签 / SEQUENCE 依次）',
  `allow_transfer` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'Y' COMMENT '允许转办（Y是 N否）',
  `allow_add_sign` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'Y' COMMENT '允许加签（Y是 N否）',
  `sla_hours` int DEFAULT NULL COMMENT '节点 SLA 时长（小时）',
  `priority` int NOT NULL DEFAULT '0' COMMENT '优先级（同节点多规则按优先级命中）',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_cmd_node_scene` (`scene_code`,`node_code`),
  KEY `idx_cmd_node_status` (`status`,`priority`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='节点审批人规则表（可配置路由）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_flow_scene` (
  `id` bigint NOT NULL COMMENT '主键',
  `scene_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '业务场景编码（CUSTOMER_CREATE / CUSTOMER_CHANGE / DEACTIVATE / HIER_ADD / IMPORT / MERGE）',
  `scene_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '场景名称',
  `biz_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '关联业务类型（对应业务表 biz_type）',
  `flow_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'Warm-Flow 流程编码（flow_definition.flow_code）',
  `flow_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '流程名称（冗余展示）',
  `definition_id` bigint DEFAULT NULL COMMENT '当前生效的流程定义 ID（flow_definition.id）',
  `start_conditions` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '启动条件表达式（满足条件才走流程，否则直接生效）',
  `biz_title_expr` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '业务标题表达式（写入 flow_instance_biz_ext）',
  `form_key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '审批表单标识（前端动态表单路由）',
  `sla_hours` int DEFAULT NULL COMMENT '整体 SLA 时长（小时）',
  `escalate_rule` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '超时升级规则（如 TO_GC / NOTIFY_LEADER）',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `order_num` int NOT NULL DEFAULT '0' COMMENT '显示顺序',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cmd_scene_code` (`scene_code`),
  KEY `idx_cmd_scene_flow` (`flow_code`),
  KEY `idx_cmd_scene_biz` (`biz_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='业务场景-工作流映射表（对接 Warm-Flow）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_governance_task` (
  `id` bigint NOT NULL COMMENT '主键',
  `task_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '任务编号',
  `task_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '任务类型（SUSPECT 疑似重复 / REVIEW 待复核 / NEW 新建确认 / CROSS_BU 跨BU决策）',
  `biz_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'CUSTOMER' COMMENT '业务类型',
  `biz_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '业务主键',
  `one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '相关 One ID',
  `subject` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '任务主题（客户名称）',
  `bu_scope` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '归属 BU',
  `cross_bu_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否跨 BU（Y：需 GC Scope）',
  `risk_level` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'Medium' COMMENT '风险等级（High / Medium / Low）',
  `match_result_id` bigint DEFAULT NULL COMMENT '关联匹配结果（cmd_match_result.id）',
  `match_state` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '匹配结论快照',
  `match_score` decimal(5,2) DEFAULT NULL COMMENT '匹配分',
  `dq_score` decimal(5,2) DEFAULT NULL COMMENT '质量分',
  `priority` int NOT NULL DEFAULT '0' COMMENT '优先级（数字越大越优先）',
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'OPEN' COMMENT '状态（OPEN / CLAIMED / RESOLVED / CLOSED / ESCALATED）',
  `resolution` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '处理结论（LINK_EXISTING / CREATE_NEW / EXCLUDE / MERGE / RETURN）',
  `assignee_id` bigint DEFAULT NULL COMMENT '当前处理人',
  `claimed_time` datetime DEFAULT NULL COMMENT '认领时间',
  `resolved_time` datetime DEFAULT NULL COMMENT '解决时间',
  `due_time` datetime DEFAULT NULL COMMENT '应完成时间（SLA）',
  `flow_instance_id` bigint DEFAULT NULL COMMENT '关联流程实例（flow_instance.id）',
  `evidence_json` json DEFAULT NULL COMMENT '治理证据（候选对比、规则命中）',
  `remark` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cmd_gov_code` (`task_code`),
  KEY `idx_cmd_gov_type_status` (`task_type`,`status`),
  KEY `idx_cmd_gov_bu` (`bu_scope`,`status`),
  KEY `idx_cmd_gov_assignee` (`assignee_id`,`status`),
  KEY `idx_cmd_gov_cross` (`cross_bu_flag`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='治理任务表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_hierarchy_node` (
  `id` bigint NOT NULL COMMENT '主键',
  `node_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '节点编码',
  `one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '关联客户 One ID',
  `legal_name` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户名称',
  `hierarchy_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'LEGAL' COMMENT '层级类型（LEGAL 法人 / SALES 销售 / PAYER 付款）',
  `level` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '层级级别（A1 / A2 / A3）',
  `parent_one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '父节点 One ID（根节点为空）',
  `full_path` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '完整路径（/A3-001/A2-0188/A1-000128，冗余加速）',
  `path_names` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '路径名称串（展示用）',
  `depth` int NOT NULL DEFAULT '1' COMMENT '层级深度（A3=1, A2=2, A1=3）',
  `payer_one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'Payer 节点 One ID',
  `bu_scope` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '归属 BU',
  `children_count` int NOT NULL DEFAULT '0' COMMENT '直接子节点数（Lazy Load 分页用）',
  `descendants` int NOT NULL DEFAULT '0' COMMENT '后代节点总数',
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'active' COMMENT '状态（active / inactive / pending）',
  `effective_from` datetime DEFAULT NULL COMMENT '生效时间',
  `effective_to` datetime DEFAULT NULL COMMENT '失效时间',
  `sort_order` int NOT NULL DEFAULT '0' COMMENT '同级排序',
  `remark` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cmd_hier_node` (`hierarchy_type`,`node_code`),
  UNIQUE KEY `uk_cmd_hier_oneid` (`hierarchy_type`,`one_id`),
  KEY `idx_cmd_hier_parent` (`parent_one_id`),
  KEY `idx_cmd_hier_level` (`level`,`bu_scope`),
  KEY `idx_cmd_hier_path` (`full_path`(191)),
  KEY `idx_cmd_hier_payer` (`payer_one_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='客户层级节点表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_hierarchy_relation` (
  `id` bigint NOT NULL COMMENT '主键',
  `relation_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '关系编号',
  `hierarchy_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'LEGAL' COMMENT '层级类型',
  `relation_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '关系类型（A3_A2 / A2_A1 / MAIN_DOOR / PAYER_LINK）',
  `parent_one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '父节点 One ID',
  `child_one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '子节点 One ID',
  `payer_one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'Payer One ID',
  `bu_scope` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '归属 BU',
  `cross_bu_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否跨 BU（Y：需 GC Scope 审批）',
  `effective_from` datetime NOT NULL COMMENT '生效时间',
  `effective_to` datetime DEFAULT NULL COMMENT '失效时间',
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'Pending' COMMENT '状态（Pending 待审批 / Effective 已生效 / Expired 已失效 / Rejected 已拒绝）',
  `change_reason` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '变更原因',
  `source_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'MANUAL' COMMENT '来源（MANUAL 手工 / IMPORT 导入 / REQUEST 业务申请 / API）',
  `applicant_id` bigint DEFAULT NULL COMMENT '申请人（业务申请场景）',
  `approved_by` bigint DEFAULT NULL COMMENT '审批人',
  `approved_time` datetime DEFAULT NULL COMMENT '审批时间',
  `flow_instance_id` bigint DEFAULT NULL COMMENT '关联流程实例',
  `approval_id` bigint DEFAULT NULL COMMENT '关联待办 ID',
  `remark` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cmd_hier_rel` (`hierarchy_type`,`parent_one_id`,`child_one_id`,`effective_from`),
  KEY `idx_cmd_hier_rel_child` (`child_one_id`,`status`),
  KEY `idx_cmd_hier_rel_status` (`status`),
  KEY `idx_cmd_hier_rel_eff` (`effective_from`,`effective_to`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='客户层级关系表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_hierarchy_relation_hist` (
  `id` bigint NOT NULL COMMENT '主键',
  `relation_id` bigint NOT NULL COMMENT '关系 ID（cmd_hierarchy_relation.id）',
  `relation_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '关系编号（冗余）',
  `version_no` int NOT NULL DEFAULT '1' COMMENT '关系版本号',
  `operation` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '操作类型（CREATE / UPDATE / DELETE / EXPIRE / APPROVE / REJECT）',
  `hierarchy_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '层级类型',
  `relation_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '关系类型',
  `parent_one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '父节点',
  `child_one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '子节点',
  `payer_one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'Payer',
  `effective_from` datetime DEFAULT NULL COMMENT '生效时间',
  `effective_to` datetime DEFAULT NULL COMMENT '失效时间',
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '操作后状态',
  `snapshot_json` json DEFAULT NULL COMMENT '关系快照',
  `change_reason` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '变更原因',
  `flow_instance_id` bigint DEFAULT NULL COMMENT '关联流程实例',
  `remark` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_cmd_hier_hist_rel` (`relation_id`,`version_no`),
  KEY `idx_cmd_hier_hist_child` (`child_one_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='客户层级关系历史表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_import_error` (
  `id` bigint NOT NULL COMMENT '主键',
  `row_id` bigint NOT NULL COMMENT '导入行 ID（cmd_import_row.id）',
  `job_id` bigint NOT NULL COMMENT '导入任务 ID',
  `row_no` int DEFAULT NULL COMMENT '行号（冗余）',
  `error_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '错误码（REQUIRED / FORMAT / LENGTH / DUPLICATE_IN_FILE / DUPLICATE_IN_DB / VALUE_SET / DQ_BLOCK）',
  `error_level` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'ERROR' COMMENT '错误级别（ERROR / WARNING）',
  `field_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '出错字段编码',
  `column_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '出错列名',
  `field_value` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '出错值',
  `error_message` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '错误描述',
  `suggest_value` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '建议修正值',
  `fixed` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否已修复（Y是 N否）',
  `fixed_by` bigint DEFAULT NULL COMMENT '修复人',
  `fixed_time` datetime DEFAULT NULL COMMENT '修复时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_cmd_err_row` (`row_id`),
  KEY `idx_cmd_err_job` (`job_id`,`error_level`),
  KEY `idx_cmd_err_code` (`error_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='导入行错误明细表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_import_job` (
  `id` bigint NOT NULL COMMENT '主键',
  `job_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '任务编号',
  `job_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '任务名称',
  `scene` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '业务场景',
  `template_id` bigint DEFAULT NULL COMMENT '使用模板 ID',
  `template_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '模板编码',
  `template_version` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '模板版本',
  `bu_scope` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '归属 BU',
  `file_name` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '上传文件名',
  `file_path` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '文件存储路径',
  `file_size` bigint DEFAULT NULL COMMENT '文件大小',
  `file_md5` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '文件 MD5（重复文件检测）',
  `oss_id` bigint DEFAULT NULL COMMENT '对象存储 ID',
  `error_strategy` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'REJECT_ROW' COMMENT '错误策略（REJECT_ROW 跳过错误行 / ABORT_ALL 全部回滚）',
  `duplicate_strategy` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'GOVERNANCE' COMMENT '重复策略（GOVERNANCE 转治理 / SKIP 跳过 / OVERWRITE 覆盖 / CREATE_NEW 强制新建）',
  `precheck_status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '文件预检状态（PASS / FAIL）',
  `precheck_msg` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '预检信息',
  `total_count` int NOT NULL DEFAULT '0' COMMENT '总行数',
  `success_count` int NOT NULL DEFAULT '0' COMMENT '成功数',
  `exact_count` int NOT NULL DEFAULT '0' COMMENT 'Exact 数（精确匹配已有）',
  `suspected_count` int NOT NULL DEFAULT '0' COMMENT 'Suspected 数（疑似重复）',
  `new_count` int NOT NULL DEFAULT '0' COMMENT 'New 数（全新客户）',
  `review_count` int NOT NULL DEFAULT '0' COMMENT 'Review 数（需人工复核）',
  `invalid_count` int NOT NULL DEFAULT '0' COMMENT 'Invalid 数（校验失败）',
  `job_status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'DRAFT' COMMENT '任务状态（DRAFT / UPLOADING / PRECHECKING / PROCESSING / DONE / PARTIAL / FAILED / CANCELLED）',
  `progress` int NOT NULL DEFAULT '0' COMMENT '进度百分比',
  `start_time` datetime DEFAULT NULL COMMENT '开始时间',
  `end_time` datetime DEFAULT NULL COMMENT '结束时间',
  `error_message` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '错误信息',
  `flow_instance_id` bigint DEFAULT NULL COMMENT '关联流程实例（部分场景需审批）',
  `remark` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `submit_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '提交人(页面展示)',
  `submit_time` datetime DEFAULT NULL COMMENT '提交时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cmd_job_code` (`job_code`),
  KEY `idx_cmd_job_status` (`job_status`),
  KEY `idx_cmd_job_scene` (`scene`,`bu_scope`),
  KEY `idx_cmd_job_md5` (`file_md5`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='批量导入任务表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_import_row` (
  `id` bigint NOT NULL COMMENT '主键',
  `job_id` bigint NOT NULL COMMENT '导入任务 ID',
  `job_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '任务编号（冗余）',
  `row_no` int NOT NULL COMMENT '行号（Excel 实际行号）',
  `row_status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'PENDING' COMMENT '行状态（PENDING / PROCESSING / SUCCESS / FAILED / SKIPPED / GOVERNANCE）',
  `result_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '结果分流（EXACT / SUSPECTED / NEW / REVIEW / INVALID）',
  `one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '生成/关联的 One ID',
  `legal_name` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户名称',
  `credit_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '统一社会信用代码',
  `bu_scope` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '归属 BU',
  `dq_score` decimal(5,2) DEFAULT NULL COMMENT '质量分',
  `match_state` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '匹配结论',
  `match_score` decimal(5,2) DEFAULT NULL COMMENT '匹配分',
  `match_result_id` bigint DEFAULT NULL COMMENT '关联匹配结果',
  `governance_id` bigint DEFAULT NULL COMMENT '转治理任务 ID（cmd_governance_task.id）',
  `approval_id` bigint DEFAULT NULL COMMENT '关联待办 ID（cmd_approval_task.id）',
  `raw_json` json DEFAULT NULL COMMENT '原始行数据（列名 → 值）',
  `parsed_json` json DEFAULT NULL COMMENT '解析后数据（字段编码 → 值）',
  `error_count` int NOT NULL DEFAULT '0' COMMENT '错误数',
  `error_summary` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '错误摘要',
  `handling` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '处理策略（RETRY 重试 / FIX 修复 / GOVERNANCE 转治理 / IGNORE 忽略）',
  `handled_by` bigint DEFAULT NULL COMMENT '处理人',
  `handled_time` datetime DEFAULT NULL COMMENT '处理时间',
  `remark` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门（BaseEntity 基础列）',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cmd_row` (`job_id`,`row_no`),
  KEY `idx_cmd_row_result` (`result_type`),
  KEY `idx_cmd_row_status` (`row_status`),
  KEY `idx_cmd_row_job_result` (`job_id`,`result_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='批量导入行明细表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_import_template` (
  `id` bigint NOT NULL COMMENT '主键',
  `template_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '模板编码',
  `template_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '模板名称',
  `scene` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '业务场景（CUSTOMER_CREATE / CUSTOMER_UPDATE / HIERARCHY / CONTACT）',
  `bu_scope` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '适用 BU（为空表示通用）',
  `customer_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户类型（Door / Payer / A1 / A2 / A3），下载模板筛选项',
  `product_line` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '产品线（Lens / Frame / Sunglasses），下载模板筛选项',
  `source_system` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '来源系统（DMS+ / Cloud / SAP），下载模板筛选项',
  `version_no` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'v1' COMMENT '模板版本',
  `file_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'XLSX' COMMENT '文件类型（XLSX / CSV）',
  `header_row` int NOT NULL DEFAULT '1' COMMENT '表头所在行',
  `data_start_row` int NOT NULL DEFAULT '2' COMMENT '数据起始行',
  `sheet_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'Sheet 名称',
  `file_path` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '模板文件存储路径',
  `oss_id` bigint DEFAULT NULL COMMENT '对象存储 ID',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0草稿 1已发布 2已停用）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cmd_tpl` (`template_code`,`version_no`),
  KEY `idx_cmd_tpl_scene` (`scene`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='导入模板定义表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_import_template_mapping` (
  `id` bigint NOT NULL COMMENT '主键',
  `template_id` bigint NOT NULL COMMENT '模板 ID',
  `template_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '模板编码（冗余）',
  `column_index` int NOT NULL COMMENT 'Excel 列序号（从 1 开始）',
  `column_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'Excel 表头名称',
  `field_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '目标字段编码（md_field.field_code）',
  `field_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '目标字段名称',
  `data_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'STRING' COMMENT '数据类型',
  `is_required` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否必填',
  `default_value` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '默认值',
  `convert_rule` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '转换规则（值集映射 / 日期格式 / 去空格）',
  `value_set_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '校验值集',
  `order_num` int NOT NULL DEFAULT '0' COMMENT '顺序',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cmd_tpl_map` (`template_code`,`column_index`),
  KEY `idx_cmd_tpl_map_field` (`field_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='导入模板字段映射表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_legacy_mapping` (
  `id` bigint NOT NULL COMMENT '主键',
  `one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'One ID',
  `source_system` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '来源系统（SAP / CRM / EXCEL / OCR / EC）',
  `source_code` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '来源系统编码',
  `source_name` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '来源系统名称（冗余，便于搜索）',
  `bu_scope` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '归属 BU',
  `mapping_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'MAIN' COMMENT '映射类型（MAIN 主映射 / ALIAS 别名 / HISTORY 历史）',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0有效 1失效）',
  `effective_from` datetime DEFAULT NULL COMMENT '生效时间',
  `effective_to` datetime DEFAULT NULL COMMENT '失效时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cmd_legacy` (`source_system`,`source_code`),
  KEY `idx_cmd_legacy_oneid` (`one_id`),
  KEY `idx_cmd_legacy_status` (`status`,`bu_scope`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='源系统编码映射表（Cross Reference）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_loop_check_log` (
  `id` bigint NOT NULL COMMENT '主键',
  `check_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '检测编号',
  `hierarchy_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'LEGAL' COMMENT '层级类型',
  `parent_one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '待校验父节点',
  `child_one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '待校验子节点',
  `check_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '检测类型（SELF_REF 父子相同 / LEVEL_RULE 层级约束 / MULTI_PARENT 多父冲突 / CYCLE 路径循环 / VALIDITY 有效期重叠）',
  `check_result` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '检测结果（PASS 通过 / FAIL 不通过 / WARN 警告）',
  `conflict_path` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '冲突路径（如 A1-000128 → A2-0188 → A1-000128）',
  `conflict_nodes` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '冲突节点列表',
  `message` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '检测信息',
  `suggestion` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '修正建议',
  `execute_time` datetime DEFAULT NULL COMMENT '执行时间',
  `duration_ms` bigint DEFAULT NULL COMMENT '耗时（毫秒）',
  `relation_id` bigint DEFAULT NULL COMMENT '关联关系 ID（提交前校验时）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_cmd_loop_result` (`check_result`,`check_type`),
  KEY `idx_cmd_loop_child` (`child_one_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='层级环路检测日志表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_match_candidate` (
  `id` bigint NOT NULL COMMENT '主键',
  `match_id` bigint NOT NULL COMMENT '匹配结果 ID（cmd_match_result.id）',
  `candidate_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '候选类型（INCOMING 待判定 / EXISTING 已有记录）',
  `one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'One ID（EXISTING 时有值）',
  `legal_name` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户名称',
  `credit_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '统一社会信用代码',
  `bu_scope` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '归属 BU',
  `customer_level` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户层级',
  `dq_score` decimal(5,2) DEFAULT NULL COMMENT '质量分',
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '记录状态',
  `total_score` decimal(5,2) DEFAULT NULL COMMENT '该候选综合分',
  `is_best` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否最优候选（Y是 N否）',
  `field_compare_json` json DEFAULT NULL COMMENT '字段级对比（字段名/值/相似度/权重/贡献分）',
  `snapshot_json` json DEFAULT NULL COMMENT '记录快照',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_cmd_cand_match` (`match_id`),
  KEY `idx_cmd_cand_oneid` (`one_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='匹配候选明细表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_match_result` (
  `id` bigint NOT NULL COMMENT '主键',
  `biz_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '业务类型（CUSTOMER / IMPORT_ROW）',
  `biz_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '业务主键',
  `incoming_one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '待判定记录标识（新建时为临时编码）',
  `rule_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '匹配规则编码',
  `rule_version` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '规则版本',
  `match_state` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '匹配结论（EXACT / SUSPECTED / NEW / REVIEW / INVALID）',
  `total_score` decimal(5,2) DEFAULT NULL COMMENT '综合匹配分',
  `candidate_count` int NOT NULL DEFAULT '0' COMMENT '候选数量',
  `best_candidate_id` bigint DEFAULT NULL COMMENT '最优候选（cmd_match_candidate.id）',
  `cross_bu_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否跨 BU 命中（Y：需 GC Scope 决策）',
  `conclusion` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '最终结论（LINK_EXISTING / CREATE_NEW / EXCLUDE / MERGE / PENDING）',
  `handled_by` bigint DEFAULT NULL COMMENT '处理人',
  `handled_time` datetime DEFAULT NULL COMMENT '处理时间',
  `execute_time` datetime DEFAULT NULL COMMENT '匹配执行时间',
  `result_json` json DEFAULT NULL COMMENT '匹配明细 JSON',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_cmd_match_biz` (`biz_type`,`biz_id`),
  KEY `idx_cmd_match_state` (`match_state`),
  KEY `idx_cmd_match_cross` (`cross_bu_flag`,`match_state`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='匹配结果表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_merge_record` (
  `id` bigint NOT NULL COMMENT '主键',
  `merge_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '合并编号',
  `survivor_one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '保留方 One ID（主记录）',
  `merged_one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '被合并方 One ID',
  `merge_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'MANUAL' COMMENT '合并类型（AUTO 自动 / MANUAL 手工 / CROSS_BU 跨BU）',
  `merge_strategy` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '字段合并策略（SURVIVOR / LATEST / HIGHEST_DQ / MANUAL）',
  `field_json` json DEFAULT NULL COMMENT '字段级取值来源（字段名 → 取自哪一方 / 原值）',
  `before_json` json DEFAULT NULL COMMENT '合并前快照（双方）',
  `after_json` json DEFAULT NULL COMMENT '合并后快照',
  `reason` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '合并原因',
  `can_rollback` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'Y' COMMENT '是否可回滚（Y是 N否）',
  `rollback_time` datetime DEFAULT NULL COMMENT '回滚时间',
  `rollback_by` bigint DEFAULT NULL COMMENT '回滚人',
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'EFFECTIVE' COMMENT '状态（EFFECTIVE 生效 / ROLLED_BACK 已回滚）',
  `flow_instance_id` bigint DEFAULT NULL COMMENT '关联流程实例',
  `remark` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cmd_merge_code` (`merge_code`),
  KEY `idx_cmd_merge_surv` (`survivor_one_id`),
  KEY `idx_cmd_merge_merged` (`merged_one_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='客户合并记录表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_notification` (
  `id` bigint NOT NULL COMMENT '主键',
  `receiver_id` bigint NOT NULL COMMENT '接收人（sys_user.user_id）',
  `notice_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '通知类型（TODO 待办 / SLA 预警 / ESCALATE 升级 / RESULT 结果通知 / SYSTEM 系统 / INTEGRATION 集成告警）',
  `title` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '通知标题',
  `content` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '通知内容',
  `biz_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '业务类型',
  `biz_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '业务主键',
  `task_id` bigint DEFAULT NULL COMMENT '关联待办 ID（点击直达）',
  `link_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '跳转链接',
  `priority` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'NORMAL' COMMENT '优先级（HIGH / NORMAL / LOW）',
  `is_read` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否已读（Y是 N否）',
  `read_time` datetime DEFAULT NULL COMMENT '阅读时间',
  `send_time` datetime DEFAULT NULL COMMENT '发送时间',
  `expire_time` datetime DEFAULT NULL COMMENT '过期时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_cmd_notice_receiver` (`receiver_id`,`is_read`),
  KEY `idx_cmd_notice_type` (`notice_type`,`send_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='站内通知表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_ocr_result` (
  `id` bigint NOT NULL COMMENT '主键',
  `attachment_id` bigint DEFAULT NULL COMMENT '关联附件（cmd_attachment.id）',
  `biz_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '业务主键（客户草稿 ID / one_id）',
  `field_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '识别字段编码',
  `field_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '字段名称',
  `ocr_value` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '识别值',
  `confirmed_value` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '人工确认后的值',
  `confidence` decimal(5,2) DEFAULT NULL COMMENT '置信度（0-100）',
  `needs_review` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否需要人工复核（Y是 N否，置信度低于阈值自动置 Y）',
  `reviewed_by` bigint DEFAULT NULL COMMENT '复核人',
  `reviewed_time` datetime DEFAULT NULL COMMENT '复核时间',
  `ocr_engine` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'OCR 引擎',
  `raw_json` json DEFAULT NULL COMMENT '识别原始结果',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_cmd_ocr_biz` (`biz_id`),
  KEY `idx_cmd_ocr_attach` (`attachment_id`),
  KEY `idx_cmd_ocr_review` (`needs_review`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='OCR识别结果表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_py_flow_instance` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `biz_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '业务编号（= task_no）',
  `scene_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '场景编码',
  `biz_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '业务类型',
  `state` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'base64(pickle 序列化的 BpmnWorkflow)',
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'RUNNING / COMPLETED',
  `current_node` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '当前节点编码',
  `data_json` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '流程变量快照（JSON 字符串）',
  `create_time` datetime DEFAULT NULL,
  `update_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_py_seq` (
  `name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '序号名（表名或编号名）',
  `current` bigint NOT NULL COMMENT '当前值',
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_role` (
  `id` bigint NOT NULL COMMENT '主键',
  `role_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '角色编码（BUSINESS_USER / BU_STEWARD / GC_STEWARD / PLATFORM_ADMIN / AUDITOR）',
  `role_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '角色名称',
  `role_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'BUSINESS' COMMENT '角色类型（BUSINESS 业务角色 / TECHNICAL 技术角色 / DATA 数据角色）',
  `scope_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'BU' COMMENT '数据范围（BU / GC / CROSS_BU / ALL）',
  `default_bu` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '默认 BU',
  `description` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '角色描述',
  `order_num` int NOT NULL DEFAULT '0' COMMENT '显示顺序',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cmd_role_code` (`role_code`),
  KEY `idx_cmd_role_type` (`role_type`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='CMD业务角色表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_role_permission` (
  `id` bigint NOT NULL COMMENT '主键',
  `role_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '角色编码',
  `perm_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '权限类型（PAGE 页面 / ACTION 操作按钮 / FIELD 字段 / SCOPE 数据范围）',
  `resource_code` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '资源编码（页面 ID / 按钮编码 / 字段编码 / BU 编码）',
  `resource_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '资源名称',
  `access_mode` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'VIEW' COMMENT '访问模式（VIEW 查看 / EDIT 编辑 / HIDE 隐藏 / APPROVE 审批）',
  `bu_scope` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '适用 BU（为空表示全部）',
  `condition_expr` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '附加条件表达式（动态权限）',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cmd_perm` (`role_code`,`perm_type`,`resource_code`,`bu_scope`),
  KEY `idx_cmd_perm_type` (`perm_type`,`resource_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='角色权限配置表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_user_role` (
  `id` bigint NOT NULL COMMENT '主键',
  `user_id` bigint NOT NULL COMMENT '用户 ID（sys_user.user_id）',
  `user_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '用户名（冗余）',
  `role_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '角色编码',
  `bu_scope` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '该角色下的数据范围 BU',
  `is_default` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否默认角色（Y是 N否）',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cmd_user_role` (`user_id`,`role_code`),
  KEY `idx_cmd_user_role_code` (`role_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户业务角色关联表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cmd_workflow_step_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `one_id` varchar(64) NOT NULL COMMENT '客户主数据标识（One ID），全链路追溯主键',
  `task_no` varchar(100) NOT NULL COMMENT '审批任务编号（AP-yyyyMMdd-####）',
  `flow_instance_id` bigint DEFAULT NULL COMMENT 'Warm-Flow 流程实例 ID',
  `step_seq` int NOT NULL DEFAULT '0' COMMENT '步骤序号（同一 one_id 内从 1 递增）',
  `step_type` varchar(20) NOT NULL COMMENT '步骤类型：SUBMIT=提交 / SYSTEM=系统自动 / BUSINESS=人工决策 / ENGINE=引擎节点推进',
  `node_code` varchar(100) DEFAULT NULL COMMENT '节点编码（APPLY/INPUT/OCR/DQ/DUP/BU_REVIEW/GC_REVIEW/END）',
  `node_name` varchar(200) DEFAULT NULL COMMENT '节点名称',
  `action_type` varchar(32) DEFAULT NULL COMMENT '动作类型（SUBMIT/APPROVE/REJECT/RETURN/ESCALATE）',
  `action_name` varchar(100) DEFAULT NULL COMMENT '动作名称（提交申请/审批通过/审批拒绝/退回补充/升级GC）',
  `operator_id` bigint DEFAULT NULL COMMENT '操作人 ID',
  `operator_name` varchar(100) DEFAULT NULL COMMENT '操作人姓名',
  `operator_role` varchar(64) DEFAULT NULL COMMENT '操作角色（BU_STEWARD/GC_STEWARD/Business User）',
  `from_status` varchar(64) DEFAULT NULL COMMENT '业务状态（操作前）',
  `to_status` varchar(64) DEFAULT NULL COMMENT '业务状态（操作后）',
  `opinion` varchar(2000) DEFAULT NULL COMMENT '审批意见 / 升级原因',
  `create_dept` bigint DEFAULT NULL,
  `create_by` bigint DEFAULT NULL,
  `create_time` datetime DEFAULT NULL,
  `update_by` bigint DEFAULT NULL,
  `update_time` datetime DEFAULT NULL,
  `del_flag` char(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `idx_step_one_id` (`one_id`),
  KEY `idx_step_task_no` (`task_no`),
  KEY `idx_step_instance` (`flow_instance_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工作流步骤执行日志（按客户 One ID 串联每一步）';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dq_reeval_job` (
  `id` bigint NOT NULL COMMENT '主键',
  `job_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '任务编号',
  `job_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '任务名称',
  `from_version` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '原规则版本',
  `to_version` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '目标规则版本',
  `scope_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'ALL' COMMENT '评估范围（ALL 全量 / BU / ONE_ID 指定）',
  `scope_value` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '范围值（BU 编码或 one_id 列表）',
  `execute_mode` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'SIMULATE' COMMENT '执行模式（SIMULATE 模拟 / FORMAL 正式）',
  `job_status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'PENDING' COMMENT '任务状态（PENDING / RUNNING / SUCCESS / FAILED / CANCELLED）',
  `total_count` int NOT NULL DEFAULT '0' COMMENT '待评估总数',
  `processed_count` int NOT NULL DEFAULT '0' COMMENT '已处理数',
  `changed_count` int NOT NULL DEFAULT '0' COMMENT '分数变化数',
  `start_time` datetime DEFAULT NULL COMMENT '开始时间',
  `end_time` datetime DEFAULT NULL COMMENT '结束时间',
  `error_message` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '错误信息',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_dq_job_code` (`job_code`),
  KEY `idx_dq_job_status` (`job_status`),
  KEY `idx_dq_job_ver` (`to_version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='质量历史重评估任务表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dq_result` (
  `id` bigint NOT NULL COMMENT '主键',
  `biz_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '业务类型（CUSTOMER / IMPORT_ROW / CHANGE / HIERARCHY）',
  `biz_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '业务主键（one_id / import_row_id / change_id）',
  `model_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'CUSTOMER' COMMENT '模型编码',
  `rule_version` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '执行时的规则版本',
  `total_score` decimal(5,2) DEFAULT NULL COMMENT '总分',
  `grade` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '等级（A / B / C / D）',
  `pass_count` int NOT NULL DEFAULT '0' COMMENT '通过规则数',
  `warning_count` int NOT NULL DEFAULT '0' COMMENT '警告数',
  `error_count` int NOT NULL DEFAULT '0' COMMENT '错误数',
  `blocked` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否阻断提交（Y是 N否，存在 ERROR 级时为 Y）',
  `execute_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'AUTO' COMMENT '执行类型（AUTO 自动 / SIMULATE 模拟测试 / REEVAL 重评估 / MANUAL 手工）',
  `job_id` bigint DEFAULT NULL COMMENT '关联重评估任务（dq_reeval_job.id）',
  `execute_time` datetime DEFAULT NULL COMMENT '执行时间',
  `duration_ms` bigint DEFAULT NULL COMMENT '耗时（毫秒）',
  `result_json` json DEFAULT NULL COMMENT '结果汇总 JSON',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_dq_result_biz` (`biz_type`,`biz_id`),
  KEY `idx_dq_result_score` (`total_score`),
  KEY `idx_dq_result_ver` (`rule_version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='数据质量校验结果表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dq_result_detail` (
  `id` bigint NOT NULL COMMENT '主键',
  `result_id` bigint NOT NULL COMMENT '结果 ID（dq_result.id）',
  `rule_id` bigint DEFAULT NULL COMMENT '规则 ID',
  `rule_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '规则编码',
  `rule_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '规则名称',
  `dimension` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '质量维度',
  `severity` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '严重级别',
  `field_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '命中字段',
  `field_value` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '字段实际值',
  `passed` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否通过（Y是 N否）',
  `deduct_score` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '扣分值',
  `message` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '校验信息',
  `suggest_value` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '建议修正值',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_dq_detail_result` (`result_id`),
  KEY `idx_dq_detail_rule` (`rule_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='数据质量校验明细表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dq_rule` (
  `id` bigint NOT NULL COMMENT '主键',
  `rule_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '规则编码',
  `rule_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '规则名称',
  `rule_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '规则类型（TECHNICAL 技术 / BUSINESS 业务）',
  `dimension` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '质量维度（COMPLETENESS 完整性 / VALIDITY 有效性 / CONSISTENCY 一致性 / UNIQUENESS 唯一性 / TIMELINESS 及时性）',
  `model_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'CUSTOMER' COMMENT '作用模型',
  `field_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '主校验字段（多字段见 dq_rule_field）',
  `check_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '校验类型（NOT_NULL / REGEX / LENGTH / RANGE / ENUM / UNIQUE / CROSS_FIELD / CUSTOM）',
  `expression` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '校验表达式（正则 / SpEL / SQL 片段）',
  `severity` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'WARNING' COMMENT '严重级别（ERROR 阻断 / WARNING 警告 / INFO 提示）',
  `score_weight` decimal(5,2) NOT NULL DEFAULT '10.00' COMMENT '扣分权重',
  `error_message` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '失败提示文案',
  `version_no` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'v1' COMMENT '规则版本号',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0草稿 1已发布 2已停用）',
  `is_preset` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否系统预置（Y是 N否，Y不可删除）',
  `order_num` int NOT NULL DEFAULT '0' COMMENT '显示顺序',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_dq_rule` (`rule_code`,`version_no`),
  KEY `idx_dq_rule_dim` (`dimension`,`status`),
  KEY `idx_dq_rule_model` (`model_code`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='数据质量规则表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dq_rule_field` (
  `id` bigint NOT NULL COMMENT '主键',
  `rule_id` bigint NOT NULL COMMENT '规则 ID（dq_rule.id）',
  `rule_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '规则编码（冗余）',
  `field_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '字段编码',
  `field_role` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'MAIN' COMMENT '字段角色（MAIN 主字段 / COMPARE 对比字段 / CONDITION 条件字段）',
  `param_json` json DEFAULT NULL COMMENT '字段级参数（最小长度、正则、比较符等）',
  `order_num` int NOT NULL DEFAULT '0' COMMENT '顺序',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_dq_rule_field` (`rule_code`,`field_code`,`field_role`),
  KEY `idx_dq_rule_field_code` (`field_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='数据质量规则字段关联表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dq_scorecard` (
  `id` bigint NOT NULL COMMENT '主键',
  `one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'One ID',
  `rule_version` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '评分所用规则版本',
  `overall_score` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '综合总分',
  `grade` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '等级（A / B / C / D）',
  `trend` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '较上次变化（UP / DOWN / FLAT）',
  `score_diff` decimal(5,2) DEFAULT NULL COMMENT '较上次分差',
  `is_current` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'Y' COMMENT '是否当前有效分（Y是 N否，同一 one_id 仅一条为 Y）',
  `eval_time` datetime DEFAULT NULL COMMENT '评分时间',
  `eval_source` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'AUTO' COMMENT '评分来源（AUTO 自动 / REEVAL 重评估 / MANUAL 手工）',
  `job_id` bigint DEFAULT NULL COMMENT '来源重评估任务',
  `detail_json` json DEFAULT NULL COMMENT '维度分明细（冗余快照）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_dq_score_ver` (`one_id`,`rule_version`),
  KEY `idx_dq_score_oneid` (`one_id`,`is_current`),
  KEY `idx_dq_score_value` (`overall_score`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='数据质量评分卡表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dq_scorecard_dimension` (
  `id` bigint NOT NULL COMMENT '主键',
  `scorecard_id` bigint NOT NULL COMMENT '评分卡 ID（dq_scorecard.id）',
  `one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'One ID（冗余）',
  `dimension` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '维度编码（COMPLETENESS / VALIDITY / CONSISTENCY ...）',
  `dimension_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '维度名称',
  `dimension_score` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '维度得分',
  `weight` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '维度权重（百分比）',
  `weighted_score` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '加权得分',
  `rule_count` int NOT NULL DEFAULT '0' COMMENT '参与规则数',
  `failed_count` int NOT NULL DEFAULT '0' COMMENT '失败规则数',
  `order_num` int NOT NULL DEFAULT '0' COMMENT '显示顺序',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_dq_dim` (`scorecard_id`,`dimension`),
  KEY `idx_dq_dim_oneid` (`one_id`,`dimension`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='质量评分维度表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `flow_category` (
  `category_id` bigint NOT NULL COMMENT '流程分类ID',
  `parent_id` bigint DEFAULT '0' COMMENT '父流程分类id',
  `ancestors` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '祖级列表',
  `category_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '流程分类名称',
  `order_num` int DEFAULT '0' COMMENT '显示顺序',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '删除标志（0代表存在 1代表删除）',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`category_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='流程分类';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `flow_definition` (
  `id` bigint NOT NULL COMMENT '主键id',
  `flow_code` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '流程编码',
  `flow_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '流程名称',
  `model_value` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'CLASSICS' COMMENT '设计器模型（CLASSICS经典模型 MIMIC仿钉钉模型）',
  `category` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '流程类别',
  `version` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '流程版本',
  `is_publish` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否发布（0未发布 1已发布 9失效）',
  `form_custom` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'N' COMMENT '审批表单是否自定义（Y是 N否）',
  `form_path` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '审批表单路径',
  `activity_status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '流程激活状态（0挂起 1激活）',
  `listener_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '监听器类型',
  `listener_path` varchar(400) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '监听器路径',
  `ext` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '业务详情 存业务表对象json字符串',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '创建人',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '更新人',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '删除标志',
  `tenant_id` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '租户id',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='流程定义表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `flow_his_task` (
  `id` bigint NOT NULL COMMENT '主键id',
  `definition_id` bigint NOT NULL COMMENT '对应flow_definition表的id',
  `instance_id` bigint NOT NULL COMMENT '对应flow_instance表的id',
  `task_id` bigint NOT NULL COMMENT '对应flow_task表的id',
  `node_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '开始节点编码',
  `node_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '开始节点名称',
  `node_type` tinyint(1) DEFAULT NULL COMMENT '开始节点类型（0开始节点 1中间节点 2结束节点 3互斥网关 4并行网关）',
  `target_node_code` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '目标节点编码',
  `target_node_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '结束节点名称',
  `approver` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '审批人',
  `cooperate_type` tinyint(1) NOT NULL DEFAULT '0' COMMENT '协作方式(1审批 2转办 3委派 4会签 5票签 6加签 7减签)',
  `collaborator` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '协作人',
  `skip_type` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '流转类型（PASS通过 REJECT退回 NONE无动作）',
  `flow_status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '流程状态（0待提交 1审批中 2审批通过 4终止 5作废 6撤销 8已完成 9已退回 10失效 11拿回）',
  `form_custom` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'N' COMMENT '审批表单是否自定义（Y是 N否）',
  `form_path` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '审批表单路径',
  `message` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '审批意见',
  `variable` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '任务变量',
  `ext` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '业务详情 存业务表对象json字符串',
  `create_time` datetime DEFAULT NULL COMMENT '任务开始时间',
  `update_time` datetime DEFAULT NULL COMMENT '审批完成时间',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '删除标志',
  `tenant_id` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '租户id',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='历史任务记录表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `flow_instance` (
  `id` bigint NOT NULL COMMENT '主键id',
  `definition_id` bigint NOT NULL COMMENT '对应flow_definition表的id',
  `business_id` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '业务id',
  `node_type` tinyint(1) NOT NULL COMMENT '节点类型（0开始节点 1中间节点 2结束节点 3互斥网关 4并行网关）',
  `node_code` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '流程节点编码',
  `node_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '流程节点名称',
  `variable` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '任务变量',
  `flow_status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '流程状态（0待提交 1审批中 2审批通过 4终止 5作废 6撤销 8已完成 9已退回 10失效 11拿回）',
  `activity_status` tinyint(1) NOT NULL DEFAULT '1' COMMENT '流程激活状态（0挂起 1激活）',
  `def_json` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '流程定义json',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '创建人',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '更新人',
  `ext` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '扩展字段，预留给业务系统使用',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '删除标志',
  `tenant_id` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '租户id',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='流程实例表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `flow_instance_biz_ext` (
  `id` bigint NOT NULL COMMENT '主键id',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `business_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '业务编码',
  `business_title` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '业务标题',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '删除标志（0代表存在 1代表删除）',
  `instance_id` bigint DEFAULT NULL COMMENT '流程实例Id',
  `business_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '业务Id',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='流程实例业务扩展表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `flow_node` (
  `id` bigint NOT NULL COMMENT '主键id',
  `node_type` tinyint(1) NOT NULL COMMENT '节点类型（0开始节点 1中间节点 2结束节点 3互斥网关 4并行网关）',
  `definition_id` bigint NOT NULL COMMENT '流程定义id',
  `node_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '流程节点编码',
  `node_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '流程节点名称',
  `permission_flag` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '权限标识（权限类型:权限标识，可以多个，用@@隔开)',
  `node_ratio` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '流程签署比例值',
  `coordinate` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '坐标',
  `any_node_skip` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '任意结点跳转',
  `listener_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '监听器类型',
  `listener_path` varchar(400) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '监听器路径',
  `form_custom` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'N' COMMENT '审批表单是否自定义（Y是 N否）',
  `form_path` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '审批表单路径',
  `version` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '版本',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '创建人',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '更新人',
  `ext` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '节点扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '删除标志',
  `tenant_id` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '租户id',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='流程节点表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `flow_skip` (
  `id` bigint NOT NULL COMMENT '主键id',
  `definition_id` bigint NOT NULL COMMENT '流程定义id',
  `now_node_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '当前流程节点的编码',
  `now_node_type` tinyint(1) DEFAULT NULL COMMENT '当前节点类型（0开始节点 1中间节点 2结束节点 3互斥网关 4并行网关）',
  `next_node_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '下一个流程节点的编码',
  `next_node_type` tinyint(1) DEFAULT NULL COMMENT '下一个节点类型（0开始节点 1中间节点 2结束节点 3互斥网关 4并行网关）',
  `skip_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '跳转名称',
  `skip_type` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '跳转类型（PASS审批通过 REJECT退回）',
  `skip_condition` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '跳转条件',
  `coordinate` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '坐标',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '创建人',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '更新人',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '删除标志',
  `tenant_id` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '租户id',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='节点跳转关联表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `flow_spel` (
  `id` bigint NOT NULL COMMENT '主键id',
  `component_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '组件名称',
  `method_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '方法名',
  `method_params` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '参数',
  `view_spel` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '预览spel表达式',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='流程spel表达式定义表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `flow_task` (
  `id` bigint NOT NULL COMMENT '主键id',
  `definition_id` bigint NOT NULL COMMENT '对应flow_definition表的id',
  `instance_id` bigint NOT NULL COMMENT '对应flow_instance表的id',
  `node_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '节点编码',
  `node_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '节点名称',
  `node_type` tinyint(1) NOT NULL COMMENT '节点类型（0开始节点 1中间节点 2结束节点 3互斥网关 4并行网关）',
  `flow_status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '流程状态（0待提交 1审批中 2审批通过 4终止 5作废 6撤销 8已完成 9已退回 10失效 11拿回）',
  `form_custom` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'N' COMMENT '审批表单是否自定义（Y是 N否）',
  `form_path` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '审批表单路径',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '创建人',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '更新人',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '删除标志',
  `tenant_id` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '租户id',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='待办任务表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `flow_user` (
  `id` bigint NOT NULL COMMENT '主键id',
  `type` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '人员类型（1待办任务的审批人权限 2待办任务的转办人权限 3待办任务的委托人权限）',
  `processed_by` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '权限人',
  `associated` bigint NOT NULL COMMENT '任务表id',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `update_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '创建人',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '删除标志',
  `tenant_id` varchar(40) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '租户id',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `user_processed_type` (`processed_by`,`type`),
  KEY `user_associated` (`associated`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='流程用户表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `gen_table` (
  `table_id` bigint NOT NULL COMMENT '编号',
  `data_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '数据源名称',
  `table_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '表名称',
  `table_comment` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '表描述',
  `class_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '实体类名称',
  `tpl_category` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'crud' COMMENT '使用的模板（crud单表操作 tree树表操作）',
  `frontend_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'vue' COMMENT '前端模板类型，对应 vm 下的模板目录',
  `package_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '生成包路径',
  `module_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '生成模块名',
  `business_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '生成业务名',
  `function_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '生成功能名',
  `function_author` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '生成功能作者',
  `gen_type` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '生成代码方式（0zip压缩包 1自定义路径）',
  `gen_path` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '/' COMMENT '生成路径（不填默认项目路径）',
  `options` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '其它生成选项',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`table_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='代码生成业务表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `gen_table_column` (
  `column_id` bigint NOT NULL COMMENT '编号',
  `table_id` bigint DEFAULT NULL COMMENT '归属表编号',
  `column_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '列名称',
  `column_comment` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '列描述',
  `column_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '列类型',
  `java_type` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'JAVA类型',
  `java_field` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'JAVA字段名',
  `is_pk` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '是否主键（1是）',
  `is_increment` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '是否自增（1是）',
  `is_required` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '是否必填（1是）',
  `is_insert` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '是否为插入字段（1是）',
  `is_edit` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '是否编辑字段（1是）',
  `is_list` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '是否列表字段（1是）',
  `is_query` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '是否查询字段（1是）',
  `query_type` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'EQ' COMMENT '查询方式（等于、不等于、大于、小于、范围）',
  `html_type` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '显示类型（文本框、文本域、下拉框、复选框、单选框、日期控件）',
  `dict_type` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '字典类型',
  `sort` int DEFAULT NULL COMMENT '排序',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`column_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='代码生成业务表字段';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `int_endpoint` (
  `id` bigint NOT NULL COMMENT '主键',
  `endpoint_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '端点编码',
  `endpoint_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '端点名称',
  `direction` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '方向（INBOUND 入站 / OUTBOUND 出站）',
  `protocol` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'HTTP' COMMENT '协议（HTTP / HTTPS / SFTP / KAFKA / JDBC / FILE）',
  `target_system` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '目标系统（SAP / CRM / EC / DW）',
  `endpoint_url` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '端点地址',
  `auth_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '认证方式（NONE / BASIC / TOKEN / OAUTH2 / CERT）',
  `auth_config` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '认证配置（加密存储）',
  `biz_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '关联业务类型（CUSTOMER / HIERARCHY / DQ_RESULT）',
  `message_format` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'JSON' COMMENT '报文格式（JSON / XML / CSV / IDOC）',
  `mapping_id` bigint DEFAULT NULL COMMENT '关联导入模板映射 ID',
  `max_retry` int NOT NULL DEFAULT '3' COMMENT '最大重试次数',
  `retry_interval` int NOT NULL DEFAULT '60' COMMENT '重试间隔（秒）',
  `timeout_ms` int NOT NULL DEFAULT '30000' COMMENT '超时时间（毫秒）',
  `fail_notify` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'Y' COMMENT '失败是否邮件通知（Y是 N否）',
  `notify_emails` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '通知邮箱（多个逗号分隔）',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性（自定义 header、加解密配置等）',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_int_endpoint_code` (`endpoint_code`),
  KEY `idx_int_endpoint_dir` (`direction`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='集成端点配置表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `int_message` (
  `id` bigint NOT NULL COMMENT '主键',
  `message_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '报文唯一 ID（幂等键）',
  `endpoint_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '端点编码',
  `direction` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '方向',
  `biz_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '业务类型',
  `biz_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '业务主键',
  `one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '关联 One ID',
  `payload` json DEFAULT NULL COMMENT '报文内容',
  `raw_payload` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '原始报文',
  `headers` json DEFAULT NULL COMMENT '报文头',
  `payload_size` bigint DEFAULT NULL COMMENT '报文大小',
  `status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'RECEIVED' COMMENT '状态（RECEIVED / PROCESSING / SUCCESS / FAILED / IGNORED）',
  `error_message` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '错误信息',
  `receive_time` datetime DEFAULT NULL COMMENT '接收时间',
  `process_time` datetime DEFAULT NULL COMMENT '处理时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_int_msg_id` (`message_id`),
  KEY `idx_int_msg_endpoint` (`endpoint_code`,`status`),
  KEY `idx_int_msg_biz` (`biz_type`,`biz_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='集成报文表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `int_run` (
  `id` bigint NOT NULL COMMENT '主键',
  `run_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '运行编号（Run ID）',
  `endpoint_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '端点编码',
  `endpoint_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '端点名称（冗余）',
  `direction` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '方向',
  `target_system` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '目标系统',
  `biz_type` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '业务类型',
  `trigger_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'AUTO' COMMENT '触发方式（AUTO 自动 / MANUAL 手工 / RETRY 重试 / RESUBMIT 重提）',
  `run_status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'RUNNING' COMMENT '运行状态（RUNNING / SUCCESS / FAILED / PARTIAL / CANCELLED）',
  `total_count` int NOT NULL DEFAULT '0' COMMENT '总记录数',
  `success_count` int NOT NULL DEFAULT '0' COMMENT '成功数',
  `failed_count` int NOT NULL DEFAULT '0' COMMENT '失败数',
  `attempt_count` int NOT NULL DEFAULT '0' COMMENT '尝试次数',
  `max_attempt` int NOT NULL DEFAULT '3' COMMENT '最大尝试次数',
  `error_message` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '错误信息',
  `start_time` datetime DEFAULT NULL COMMENT '开始时间',
  `end_time` datetime DEFAULT NULL COMMENT '结束时间',
  `duration_ms` bigint DEFAULT NULL COMMENT '耗时（毫秒）',
  `parent_run_id` bigint DEFAULT NULL COMMENT '父运行 ID（重试/重提场景）',
  `message_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '关联报文 ID',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_int_run_code` (`run_code`),
  KEY `idx_int_run_status` (`run_status`,`start_time`),
  KEY `idx_int_run_endpoint` (`endpoint_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='集成运行实例表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `int_run_attempt` (
  `id` bigint NOT NULL COMMENT '主键',
  `run_id` bigint NOT NULL COMMENT '运行 ID（int_run.id）',
  `run_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '运行编号（冗余）',
  `attempt_no` int NOT NULL COMMENT '尝试序号（从 1 开始）',
  `attempt_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'INITIAL' COMMENT '尝试类型（INITIAL 首次 / RETRY 重试 / RESUBMIT 重提）',
  `attempt_status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '尝试状态（SUCCESS / FAILED）',
  `request_json` json DEFAULT NULL COMMENT '请求内容',
  `response_json` json DEFAULT NULL COMMENT '响应内容',
  `http_status` int DEFAULT NULL COMMENT 'HTTP 状态码',
  `error_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '错误码',
  `error_message` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '错误信息',
  `start_time` datetime DEFAULT NULL COMMENT '开始时间',
  `end_time` datetime DEFAULT NULL COMMENT '结束时间',
  `duration_ms` bigint DEFAULT NULL COMMENT '耗时（毫秒）',
  `operator_id` bigint DEFAULT NULL COMMENT '操作人（手工重试时）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_int_att_run` (`run_id`,`attempt_no`),
  KEY `idx_int_att_status` (`attempt_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='集成运行尝试记录表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `match_rule` (
  `id` bigint NOT NULL COMMENT '主键',
  `rule_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '规则编码',
  `rule_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '规则名称',
  `model_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'CUSTOMER' COMMENT '作用模型',
  `scene` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'CREATE' COMMENT '应用场景（CREATE 新建查重 / IMPORT 批量 / BATCH 存量扫描 / MERGE 合并）',
  `algorithm` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'WEIGHTED' COMMENT '算法（WEIGHTED 加权 / EXACT 精确 / FUZZY 模糊 / ML 模型）',
  `normalize_rule` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '标准化规则（去空格/全半角/繁简/公司后缀）',
  `exact_threshold` decimal(5,2) NOT NULL DEFAULT '95.00' COMMENT 'Exact Match 阈值',
  `suspect_threshold` decimal(5,2) NOT NULL DEFAULT '70.00' COMMENT 'Suspected 阈值（低于则为 New）',
  `auto_merge_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '超阈值是否自动合并（Y是 N否）',
  `cross_bu_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'Y' COMMENT '是否参与跨 BU 匹配（Y是 N否）',
  `version_no` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'v1' COMMENT '规则版本号',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0草稿 1已发布 2已停用）',
  `is_preset` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否系统预置',
  `order_num` int NOT NULL DEFAULT '0' COMMENT '显示顺序',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_match_rule` (`rule_code`,`version_no`),
  KEY `idx_match_rule_scene` (`scene`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='匹配规则表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `match_rule_field` (
  `id` bigint NOT NULL COMMENT '主键',
  `rule_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '规则编码',
  `field_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '字段编码',
  `field_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '字段名称',
  `weight` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '字段权重',
  `match_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'EQUAL' COMMENT '匹配方式（EQUAL 相等 / FUZZY 模糊 / CONTAINS 包含 / NUMERIC 数值 / PHONETIC 音似）',
  `fuzzy_threshold` decimal(5,2) DEFAULT NULL COMMENT '模糊匹配阈值（0-100）',
  `is_blocking` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否阻断字段（Y：该字段不一致直接判非重复）',
  `is_required` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否必比字段',
  `order_num` int NOT NULL DEFAULT '0' COMMENT '顺序',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_match_field` (`rule_code`,`field_code`),
  KEY `idx_match_field_code` (`field_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='匹配规则字段权重表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `md_field` (
  `id` bigint NOT NULL COMMENT '主键',
  `model_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '所属模型编码',
  `field_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '字段编码（如 credit_code / bu_scope）',
  `field_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '字段名称（中文）',
  `field_name_en` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '字段名称（英文）',
  `data_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'STRING' COMMENT '数据类型（STRING/NUMBER/DATE/DATETIME/BOOLEAN/ENUM/JSON）',
  `value_set_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '关联值集编码（data_type=ENUM 时使用）',
  `default_value` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '默认值',
  `is_required` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否必填（Y是 N否）',
  `is_unique` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否唯一（Y是 N否，用于匹配与查重）',
  `is_key_field` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否关键字段（Y：变更需审批）',
  `is_match_field` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否参与匹配（Y是 N否）',
  `is_dq_field` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否参与 DQ 校验（Y是 N否）',
  `is_sensitive` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否敏感字段（Y：受字段级权限控制）',
  `is_physical` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否物理列（Y：主表列；N：存 EAV 表）',
  `physical_column` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '物理列名（is_physical=Y 时有效）',
  `min_length` int DEFAULT NULL COMMENT '最小长度',
  `max_length` int DEFAULT NULL COMMENT '最大长度',
  `regex_pattern` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '正则校验',
  `scope_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'GC' COMMENT '归属范围（GC 全局 / BU 业务单元 / SOURCE 来源）',
  `owner_bu` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '归属 BU（scope_type=BU 时有效）',
  `version_no` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'v1' COMMENT '字段版本号',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0草稿 1已发布 2已停用）',
  `order_num` int NOT NULL DEFAULT '0' COMMENT '显示顺序',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性（UI 控件、联动规则等）',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_md_field` (`model_code`,`field_code`,`version_no`),
  KEY `idx_md_field_model` (`model_code`,`status`),
  KEY `idx_md_field_match` (`is_match_field`),
  KEY `idx_md_field_dq` (`is_dq_field`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='元数据-字段定义表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `md_model` (
  `id` bigint NOT NULL COMMENT '主键',
  `model_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '模型编码（CUSTOMER / HIERARCHY / CONTACT ...）',
  `model_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '模型名称',
  `table_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '主表表名（物理表，扩展实体时可登记）',
  `owner_domain` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '归属域（GC_CORE / BU_EXT / SOURCE）',
  `description` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '模型描述',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `order_num` int NOT NULL DEFAULT '0' COMMENT '显示顺序',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_md_model_code` (`model_code`),
  KEY `idx_md_model_domain` (`owner_domain`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='元数据-数据模型定义表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `md_model_version` (
  `id` bigint NOT NULL COMMENT '主键',
  `model_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '模型编码',
  `version_no` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '版本号',
  `version_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '版本名称',
  `change_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'ADD_FIELD' COMMENT '变更类型（ADD_FIELD / EDIT_FIELD / DISABLE_FIELD / VALUE_SET）',
  `snapshot_json` json DEFAULT NULL COMMENT '发布时字段快照（审计对比用）',
  `impact_note` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '影响说明（新增字段 X，影响页面 Y）',
  `publish_status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '发布状态（0未发布 1已发布 2已回滚）',
  `publish_time` datetime DEFAULT NULL COMMENT '发布时间',
  `publish_by` bigint DEFAULT NULL COMMENT '发布人',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_md_version` (`model_code`,`version_no`),
  KEY `idx_md_version_status` (`publish_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='元数据-模型版本发布表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `md_value_set` (
  `id` bigint NOT NULL COMMENT '主键',
  `set_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '值集编码（如 BU_LIST / COUNTRY / CUSTOMER_STATUS）',
  `set_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '值集名称',
  `set_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'STATIC' COMMENT '值集类型（STATIC静态 / DYNAMIC动态SQL / DICT字典）',
  `source_sql` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '动态值集来源 SQL / 字典类型',
  `scope_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'GC' COMMENT '归属范围（GC / BU / SOURCE）',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_md_set_code` (`set_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='元数据-值集定义表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `md_value_set_item` (
  `id` bigint NOT NULL COMMENT '主键',
  `set_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '值集编码',
  `item_value` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '选项值',
  `item_label` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '选项显示名',
  `item_label_en` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '英文显示名',
  `parent_value` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '父级选项值（支持级联）',
  `is_default` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否默认项（Y是 N否）',
  `order_num` int NOT NULL DEFAULT '0' COMMENT '显示顺序',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_md_item` (`set_code`,`item_value`),
  KEY `idx_md_item_set` (`set_code`,`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='元数据-值集项表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `oneid_event` (
  `id` bigint NOT NULL COMMENT '主键',
  `one_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'One ID',
  `event_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '事件类型（GENERATE 生成 / STABLE 保持稳定 / MAP 映射新增 / REMAP 映射变更 / DEACTIVATE 停用 / MERGE 合并 / RESTORE 恢复）',
  `event_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '事件名称',
  `event_desc` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '事件描述',
  `rule_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '当时使用的规则编码',
  `old_value` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '变更前值',
  `new_value` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '变更后值',
  `source_system` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '来源系统',
  `event_time` datetime DEFAULT NULL COMMENT '事件时间',
  `operator_id` bigint DEFAULT NULL COMMENT '操作人',
  `biz_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '关联业务 ID',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_oneid_event_id` (`one_id`,`event_time`),
  KEY `idx_oneid_event_type` (`event_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='One ID生命周期事件表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `oneid_rule` (
  `id` bigint NOT NULL COMMENT '主键',
  `rule_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '规则编码',
  `rule_name` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '规则名称',
  `pattern` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '编码模式（如 GC-{yyyy}{seq6}，支持占位符）',
  `prefix` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '固定前缀',
  `separator` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '-' COMMENT '分隔符',
  `serial_length` int NOT NULL DEFAULT '6' COMMENT '流水长度',
  `seq_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '关联流水号规则（cfg_sequence.seq_code）',
  `gen_strategy` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'ON_APPROVE' COMMENT '生成时机（ON_CREATE 创建即生成 / ON_APPROVE 审批通过后生成 / MANUAL 手工）',
  `stable_policy` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'NEVER_CHANGE' COMMENT '稳定性策略（NEVER_CHANGE 永不变更 / CHANGE_ON_MERGE 合并时变更）',
  `reuse_policy` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'NEVER_REUSE' COMMENT '复用策略（NEVER_REUSE 停用后不复用）',
  `scope_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'GC' COMMENT '适用范围（GC 全局 / BU 按 BU 分段）',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `is_default` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'N' COMMENT '是否默认规则（Y是 N否）',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_oneid_rule_code` (`rule_code`),
  KEY `idx_oneid_rule_status` (`status`,`is_default`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='One ID生成规则表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `poc_coverage_topic` (
  `id` bigint NOT NULL COMMENT '主键',
  `topic_no` int NOT NULL COMMENT 'Topic 序号',
  `topic_name` varchar(300) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'Topic 名称',
  `topic_desc` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'Topic 描述',
  `demo_status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'PENDING' COMMENT '演示状态（DONE 已完成 / PARTIAL 部分 / PENDING 待演示 / NA 不涉及）',
  `related_pages` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '关联页面（逗号分隔）',
  `related_tables` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '关联数据表（逗号分隔）',
  `evidence_json` json DEFAULT NULL COMMENT '证据（截图 / 数据示例）',
  `verified_by` bigint DEFAULT NULL COMMENT '验证人',
  `verified_time` datetime DEFAULT NULL COMMENT '验证时间',
  `order_num` int NOT NULL DEFAULT '0' COMMENT '显示顺序',
  `remark` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  `ext_json` json DEFAULT NULL COMMENT '扩展属性',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '删除标志',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_poc_topic_no` (`topic_no`),
  KEY `idx_poc_topic_status` (`demo_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='POC演示Topic覆盖检查表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_distributed_lock` (
  `name` varchar(64) NOT NULL COMMENT '锁名称',
  `lock_until` timestamp(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '锁定时长',
  `locked_at` timestamp(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '锁定时间',
  `locked_by` varchar(255) NOT NULL COMMENT '锁定者',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='锁定表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_group_config` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `namespace_id` varchar(64) NOT NULL DEFAULT '764d604ec6fc45f68cd92514c40e9e1a' COMMENT '命名空间id',
  `group_name` varchar(64) NOT NULL DEFAULT '' COMMENT '组名称',
  `description` varchar(256) NOT NULL DEFAULT '' COMMENT '组描述',
  `token` varchar(64) NOT NULL DEFAULT 'SJ_cKqBTPzCsWA3VyuCfFoccmuIEGXjr5KT' COMMENT 'token',
  `group_status` tinyint NOT NULL DEFAULT '0' COMMENT '组状态 0、未启用 1、启用',
  `version` int NOT NULL COMMENT '版本号',
  `group_partition` int NOT NULL COMMENT '分区',
  `id_generator_mode` tinyint NOT NULL DEFAULT '1' COMMENT '唯一id生成模式 默认号段模式',
  `init_scene` tinyint NOT NULL DEFAULT '0' COMMENT '是否初始化场景 0:否 1:是',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_namespace_id_group_name` (`namespace_id`,`group_name`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='组配置';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_job` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `namespace_id` varchar(64) NOT NULL DEFAULT '764d604ec6fc45f68cd92514c40e9e1a' COMMENT '命名空间id',
  `biz_id` varchar(64) NOT NULL COMMENT '业务ID',
  `group_name` varchar(64) NOT NULL COMMENT '组名称',
  `job_name` varchar(64) NOT NULL COMMENT '名称',
  `args_str` text COMMENT '执行方法参数',
  `args_type` tinyint NOT NULL DEFAULT '1' COMMENT '参数类型 ',
  `next_trigger_at` bigint NOT NULL COMMENT '下次触发时间',
  `job_status` tinyint NOT NULL DEFAULT '1' COMMENT '任务状态 0、关闭、1、开启',
  `task_type` tinyint NOT NULL DEFAULT '1' COMMENT '任务类型 1、集群 2、广播 3、切片',
  `route_key` tinyint NOT NULL DEFAULT '4' COMMENT '路由策略',
  `executor_type` tinyint NOT NULL DEFAULT '1' COMMENT '执行器类型',
  `executor_info` varchar(255) DEFAULT NULL COMMENT '执行器名称',
  `trigger_type` tinyint NOT NULL COMMENT '触发类型 1.CRON 表达式 2. 固定时间',
  `trigger_interval` varchar(255) NOT NULL COMMENT '间隔时长',
  `block_strategy` tinyint NOT NULL DEFAULT '1' COMMENT '阻塞策略 1、丢弃 2、覆盖 3、并行 4、恢复',
  `executor_timeout` int NOT NULL DEFAULT '0' COMMENT '任务执行超时时间，单位秒',
  `max_retry_times` int NOT NULL DEFAULT '0' COMMENT '最大重试次数',
  `parallel_num` int NOT NULL DEFAULT '1' COMMENT '并行数',
  `retry_interval` int NOT NULL DEFAULT '0' COMMENT '重试间隔(s)',
  `bucket_index` int NOT NULL DEFAULT '0' COMMENT 'bucket',
  `resident` tinyint NOT NULL DEFAULT '0' COMMENT '是否是常驻任务',
  `notify_ids` varchar(128) NOT NULL DEFAULT '' COMMENT '通知告警场景配置id列表',
  `owner_id` bigint DEFAULT NULL COMMENT '负责人id',
  `labels` varchar(512) DEFAULT '' COMMENT '标签',
  `description` varchar(256) NOT NULL DEFAULT '' COMMENT '描述',
  `ext_attrs` varchar(256) DEFAULT '' COMMENT '扩展字段',
  `deleted` tinyint NOT NULL DEFAULT '0' COMMENT '逻辑删除 1、删除',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sj_job_01` (`namespace_id`,`biz_id`),
  KEY `idx_namespace_id_group_name` (`namespace_id`,`group_name`),
  KEY `idx_job_status_bucket_index` (`job_status`,`bucket_index`),
  KEY `idx_create_dt` (`create_dt`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='任务信息';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_job_executor` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `namespace_id` varchar(64) NOT NULL DEFAULT '764d604ec6fc45f68cd92514c40e9e1a' COMMENT '命名空间id',
  `group_name` varchar(64) NOT NULL COMMENT '组名称',
  `executor_info` varchar(256) NOT NULL COMMENT '任务执行器名称',
  `executor_type` varchar(3) NOT NULL COMMENT '1:java 2:python 3:go',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  KEY `idx_namespace_id_group_name` (`namespace_id`,`group_name`),
  KEY `idx_create_dt` (`create_dt`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='任务执行器信息';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_job_log_message` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `namespace_id` varchar(64) NOT NULL DEFAULT '764d604ec6fc45f68cd92514c40e9e1a' COMMENT '命名空间id',
  `group_name` varchar(64) NOT NULL COMMENT '组名称',
  `job_id` bigint NOT NULL COMMENT '任务信息id',
  `task_batch_id` bigint NOT NULL COMMENT '任务批次id',
  `task_id` bigint NOT NULL COMMENT '调度任务id',
  `message` longtext NOT NULL COMMENT '调度信息',
  `log_num` int NOT NULL DEFAULT '1' COMMENT '日志数量',
  `real_time` bigint NOT NULL DEFAULT '0' COMMENT '上报时间',
  `ext_attrs` varchar(256) DEFAULT '' COMMENT '扩展字段',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_task_batch_id_task_id` (`task_batch_id`,`task_id`),
  KEY `idx_create_dt` (`create_dt`),
  KEY `idx_namespace_id_group_name` (`namespace_id`,`group_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='调度日志';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_job_summary` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `namespace_id` varchar(64) NOT NULL DEFAULT '764d604ec6fc45f68cd92514c40e9e1a' COMMENT '命名空间id',
  `group_name` varchar(64) NOT NULL DEFAULT '' COMMENT '组名称',
  `business_id` bigint NOT NULL COMMENT '业务id (job_id或workflow_id)',
  `system_task_type` tinyint NOT NULL DEFAULT '3' COMMENT '任务类型 3、JOB任务 4、WORKFLOW任务',
  `trigger_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '统计时间',
  `success_num` int NOT NULL DEFAULT '0' COMMENT '执行成功-日志数量',
  `fail_num` int NOT NULL DEFAULT '0' COMMENT '执行失败-日志数量',
  `fail_reason` varchar(512) NOT NULL DEFAULT '' COMMENT '失败原因',
  `stop_num` int NOT NULL DEFAULT '0' COMMENT '执行失败-日志数量',
  `stop_reason` varchar(512) NOT NULL DEFAULT '' COMMENT '失败原因',
  `cancel_num` int NOT NULL DEFAULT '0' COMMENT '执行失败-日志数量',
  `cancel_reason` varchar(512) NOT NULL DEFAULT '' COMMENT '失败原因',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_trigger_at_system_task_type_business_id` (`trigger_at`,`system_task_type`,`business_id`) USING BTREE,
  KEY `idx_namespace_id_group_name_business_id` (`namespace_id`,`group_name`,`business_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='DashBoard_Job';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_job_task` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `namespace_id` varchar(64) NOT NULL DEFAULT '764d604ec6fc45f68cd92514c40e9e1a' COMMENT '命名空间id',
  `group_name` varchar(64) NOT NULL COMMENT '组名称',
  `job_id` bigint NOT NULL COMMENT '任务信息id',
  `task_batch_id` bigint NOT NULL COMMENT '调度任务id',
  `parent_id` bigint NOT NULL DEFAULT '0' COMMENT '父执行器id',
  `task_status` tinyint NOT NULL DEFAULT '0' COMMENT '执行的状态 0、失败 1、成功',
  `retry_count` int NOT NULL DEFAULT '0' COMMENT '重试次数',
  `mr_stage` tinyint DEFAULT NULL COMMENT '动态分片所处阶段 1:map 2:reduce 3:mergeReduce',
  `leaf` tinyint NOT NULL DEFAULT '1' COMMENT '叶子节点',
  `task_name` varchar(255) NOT NULL DEFAULT '' COMMENT '任务名称',
  `client_info` varchar(128) DEFAULT NULL COMMENT '客户端地址 clientId#ip:port',
  `wf_context` text COMMENT '工作流全局上下文',
  `result_message` text NOT NULL COMMENT '执行结果',
  `args_str` text COMMENT '执行方法参数',
  `args_type` tinyint NOT NULL DEFAULT '1' COMMENT '参数类型 ',
  `ext_attrs` varchar(256) DEFAULT '' COMMENT '扩展字段',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  KEY `idx_task_batch_id_task_status` (`task_batch_id`,`task_status`),
  KEY `idx_create_dt` (`create_dt`),
  KEY `idx_namespace_id_group_name` (`namespace_id`,`group_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='任务实例';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_job_task_batch` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `namespace_id` varchar(64) NOT NULL DEFAULT '764d604ec6fc45f68cd92514c40e9e1a' COMMENT '命名空间id',
  `group_name` varchar(64) NOT NULL COMMENT '组名称',
  `job_id` bigint NOT NULL COMMENT '任务id',
  `workflow_node_id` bigint NOT NULL DEFAULT '0' COMMENT '工作流节点id',
  `parent_workflow_node_id` bigint NOT NULL DEFAULT '0' COMMENT '工作流任务父批次id',
  `workflow_task_batch_id` bigint NOT NULL DEFAULT '0' COMMENT '工作流任务批次id',
  `task_batch_status` tinyint NOT NULL DEFAULT '0' COMMENT '任务批次状态 0、失败 1、成功',
  `operation_reason` tinyint NOT NULL DEFAULT '0' COMMENT '操作原因',
  `execution_at` bigint NOT NULL DEFAULT '0' COMMENT '任务执行时间',
  `system_task_type` tinyint NOT NULL DEFAULT '3' COMMENT '任务类型 3、JOB任务 4、WORKFLOW任务',
  `parent_id` varchar(64) NOT NULL DEFAULT '' COMMENT '父节点',
  `ext_attrs` varchar(256) DEFAULT '' COMMENT '扩展字段',
  `deleted` tinyint NOT NULL DEFAULT '0' COMMENT '逻辑删除 1、删除',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  KEY `idx_job_id_task_batch_status` (`job_id`,`task_batch_status`),
  KEY `idx_create_dt` (`create_dt`),
  KEY `idx_namespace_id_group_name` (`namespace_id`,`group_name`),
  KEY `idx_workflow_task_batch_id_workflow_node_id` (`workflow_task_batch_id`,`workflow_node_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='任务批次';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_namespace` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` varchar(64) NOT NULL COMMENT '名称',
  `unique_id` varchar(64) NOT NULL COMMENT '唯一id',
  `description` varchar(256) NOT NULL DEFAULT '' COMMENT '描述',
  `deleted` tinyint NOT NULL DEFAULT '0' COMMENT '逻辑删除 1、删除',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_unique_id` (`unique_id`),
  KEY `idx_name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='命名空间';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_notify_config` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `namespace_id` varchar(64) NOT NULL DEFAULT '764d604ec6fc45f68cd92514c40e9e1a' COMMENT '命名空间id',
  `group_name` varchar(64) NOT NULL COMMENT '组名称',
  `notify_name` varchar(64) NOT NULL DEFAULT '' COMMENT '通知名称',
  `system_task_type` tinyint NOT NULL DEFAULT '3' COMMENT '任务类型 1. 重试任务 2. 重试回调 3、JOB任务 4、WORKFLOW任务',
  `notify_status` tinyint NOT NULL DEFAULT '0' COMMENT '通知状态 0、未启用 1、启用',
  `recipient_ids` varchar(128) NOT NULL COMMENT '接收人id列表',
  `notify_threshold` int NOT NULL DEFAULT '0' COMMENT '通知阈值',
  `notify_scene` tinyint NOT NULL DEFAULT '0' COMMENT '通知场景',
  `rate_limiter_status` tinyint NOT NULL DEFAULT '0' COMMENT '限流状态 0、未启用 1、启用',
  `rate_limiter_threshold` int NOT NULL DEFAULT '0' COMMENT '每秒限流阈值',
  `description` varchar(256) NOT NULL DEFAULT '' COMMENT '描述',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  KEY `idx_namespace_id_group_name_scene_name` (`namespace_id`,`group_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='通知配置';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_notify_recipient` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `namespace_id` varchar(64) NOT NULL DEFAULT '764d604ec6fc45f68cd92514c40e9e1a' COMMENT '命名空间id',
  `recipient_name` varchar(64) NOT NULL COMMENT '接收人名称',
  `notify_type` tinyint NOT NULL DEFAULT '0' COMMENT '通知类型 1、钉钉 2、邮件 3、企业微信 4 飞书 5 webhook',
  `notify_attribute` varchar(512) NOT NULL COMMENT '配置属性',
  `description` varchar(256) NOT NULL DEFAULT '' COMMENT '描述',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  KEY `idx_namespace_id` (`namespace_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='告警通知接收人';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_retry` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `namespace_id` varchar(64) NOT NULL DEFAULT '764d604ec6fc45f68cd92514c40e9e1a' COMMENT '命名空间id',
  `group_name` varchar(64) NOT NULL COMMENT '组名称',
  `group_id` bigint NOT NULL COMMENT '组Id',
  `scene_name` varchar(64) NOT NULL COMMENT '场景名称',
  `scene_id` bigint NOT NULL COMMENT '场景ID',
  `idempotent_id` varchar(64) NOT NULL COMMENT '幂等id',
  `biz_no` varchar(64) NOT NULL DEFAULT '' COMMENT '业务编号',
  `executor_name` varchar(512) NOT NULL DEFAULT '' COMMENT '执行器名称',
  `args_str` text NOT NULL COMMENT '执行方法参数',
  `ext_attrs` text NOT NULL COMMENT '扩展字段',
  `serializer_name` varchar(32) NOT NULL DEFAULT 'jackson' COMMENT '执行方法参数序列化器名称',
  `next_trigger_at` bigint NOT NULL COMMENT '下次触发时间',
  `retry_count` int NOT NULL DEFAULT '0' COMMENT '重试次数',
  `retry_status` tinyint NOT NULL DEFAULT '0' COMMENT '重试状态 0、重试中 1、成功 2、最大重试次数',
  `task_type` tinyint NOT NULL DEFAULT '1' COMMENT '任务类型 1、重试数据 2、回调数据',
  `bucket_index` int NOT NULL DEFAULT '0' COMMENT 'bucket',
  `parent_id` bigint NOT NULL DEFAULT '0' COMMENT '父节点id',
  `deleted` bigint NOT NULL DEFAULT '0' COMMENT '逻辑删除',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_scene_tasktype_idempotentid_deleted` (`scene_id`,`task_type`,`idempotent_id`,`deleted`),
  KEY `idx_biz_no` (`biz_no`),
  KEY `idx_idempotent_id` (`idempotent_id`),
  KEY `idx_retry_status_bucket_index` (`retry_status`,`bucket_index`),
  KEY `idx_parent_id` (`parent_id`),
  KEY `idx_create_dt` (`create_dt`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='重试信息表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_retry_dead_letter` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `namespace_id` varchar(64) NOT NULL DEFAULT '764d604ec6fc45f68cd92514c40e9e1a' COMMENT '命名空间id',
  `group_name` varchar(64) NOT NULL COMMENT '组名称',
  `group_id` bigint NOT NULL COMMENT '组Id',
  `scene_name` varchar(64) NOT NULL COMMENT '场景名称',
  `scene_id` bigint NOT NULL COMMENT '场景ID',
  `idempotent_id` varchar(64) NOT NULL COMMENT '幂等id',
  `biz_no` varchar(64) NOT NULL DEFAULT '' COMMENT '业务编号',
  `executor_name` varchar(512) NOT NULL DEFAULT '' COMMENT '执行器名称',
  `serializer_name` varchar(32) NOT NULL DEFAULT 'jackson' COMMENT '执行方法参数序列化器名称',
  `args_str` text NOT NULL COMMENT '执行方法参数',
  `ext_attrs` text NOT NULL COMMENT '扩展字段',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_namespace_id_group_name_scene_name` (`namespace_id`,`group_name`,`scene_name`),
  KEY `idx_idempotent_id` (`idempotent_id`),
  KEY `idx_biz_no` (`biz_no`),
  KEY `idx_create_dt` (`create_dt`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='死信队列表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_retry_scene_config` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `namespace_id` varchar(64) NOT NULL DEFAULT '764d604ec6fc45f68cd92514c40e9e1a' COMMENT '命名空间id',
  `scene_name` varchar(64) NOT NULL COMMENT '场景名称',
  `group_name` varchar(64) NOT NULL COMMENT '组名称',
  `scene_status` tinyint NOT NULL DEFAULT '0' COMMENT '组状态 0、未启用 1、启用',
  `max_retry_count` int NOT NULL DEFAULT '5' COMMENT '最大重试次数',
  `back_off` tinyint NOT NULL DEFAULT '1' COMMENT '1、默认等级 2、固定间隔时间 3、CRON 表达式',
  `trigger_interval` varchar(16) NOT NULL DEFAULT '' COMMENT '间隔时长',
  `notify_ids` varchar(128) NOT NULL DEFAULT '' COMMENT '通知告警场景配置id列表',
  `deadline_request` bigint unsigned NOT NULL DEFAULT '60000' COMMENT 'Deadline Request 调用链超时 单位毫秒',
  `executor_timeout` int unsigned NOT NULL DEFAULT '5' COMMENT '任务执行超时时间，单位秒',
  `route_key` tinyint NOT NULL DEFAULT '4' COMMENT '路由策略',
  `block_strategy` tinyint NOT NULL DEFAULT '1' COMMENT '阻塞策略 1、丢弃 2、覆盖 3、并行',
  `cb_status` tinyint NOT NULL DEFAULT '0' COMMENT '回调状态 0、不开启 1、开启',
  `cb_trigger_type` tinyint NOT NULL DEFAULT '1' COMMENT '1、默认等级 2、固定间隔时间 3、CRON 表达式',
  `cb_max_count` int NOT NULL DEFAULT '16' COMMENT '回调的最大执行次数',
  `cb_trigger_interval` varchar(16) NOT NULL DEFAULT '' COMMENT '回调的最大执行次数',
  `owner_id` bigint DEFAULT NULL COMMENT '负责人id',
  `labels` varchar(512) DEFAULT '' COMMENT '标签',
  `description` varchar(256) NOT NULL DEFAULT '' COMMENT '描述',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_namespace_id_group_name_scene_name` (`namespace_id`,`group_name`,`scene_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='场景配置';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_retry_summary` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `namespace_id` varchar(64) NOT NULL DEFAULT '764d604ec6fc45f68cd92514c40e9e1a' COMMENT '命名空间id',
  `group_name` varchar(64) NOT NULL DEFAULT '' COMMENT '组名称',
  `scene_name` varchar(64) NOT NULL DEFAULT '' COMMENT '场景名称',
  `trigger_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '统计时间',
  `running_num` int NOT NULL DEFAULT '0' COMMENT '重试中-日志数量',
  `finish_num` int NOT NULL DEFAULT '0' COMMENT '重试完成-日志数量',
  `max_count_num` int NOT NULL DEFAULT '0' COMMENT '重试到达最大次数-日志数量',
  `suspend_num` int NOT NULL DEFAULT '0' COMMENT '暂停重试-日志数量',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_scene_name_trigger_at` (`namespace_id`,`group_name`,`scene_name`,`trigger_at`) USING BTREE,
  KEY `idx_trigger_at` (`trigger_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='DashBoard_Retry';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_retry_task` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `namespace_id` varchar(64) NOT NULL DEFAULT '764d604ec6fc45f68cd92514c40e9e1a' COMMENT '命名空间id',
  `group_name` varchar(64) NOT NULL COMMENT '组名称',
  `scene_name` varchar(64) NOT NULL COMMENT '场景名称',
  `retry_id` bigint NOT NULL COMMENT '重试信息Id',
  `ext_attrs` text NOT NULL COMMENT '扩展字段',
  `task_status` tinyint NOT NULL DEFAULT '1' COMMENT '重试状态',
  `task_type` tinyint NOT NULL DEFAULT '1' COMMENT '任务类型 1、重试数据 2、回调数据',
  `operation_reason` tinyint NOT NULL DEFAULT '0' COMMENT '操作原因',
  `client_info` varchar(128) DEFAULT NULL COMMENT '客户端地址 clientId#ip:port',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  KEY `idx_group_name_scene_name` (`namespace_id`,`group_name`,`scene_name`),
  KEY `task_status` (`task_status`),
  KEY `idx_create_dt` (`create_dt`),
  KEY `idx_retry_id` (`retry_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='重试任务表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_retry_task_log_message` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `namespace_id` varchar(64) NOT NULL DEFAULT '764d604ec6fc45f68cd92514c40e9e1a' COMMENT '命名空间id',
  `group_name` varchar(64) NOT NULL COMMENT '组名称',
  `retry_id` bigint NOT NULL COMMENT '重试信息Id',
  `retry_task_id` bigint NOT NULL COMMENT '重试任务Id',
  `message` longtext NOT NULL COMMENT '异常信息',
  `log_num` int NOT NULL DEFAULT '1' COMMENT '日志数量',
  `real_time` bigint NOT NULL DEFAULT '0' COMMENT '上报时间',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_namespace_id_group_name_retry_task_id` (`namespace_id`,`group_name`,`retry_task_id`),
  KEY `idx_create_dt` (`create_dt`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='任务调度日志信息记录表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_server_node` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `namespace_id` varchar(64) NOT NULL DEFAULT '764d604ec6fc45f68cd92514c40e9e1a' COMMENT '命名空间id',
  `group_name` varchar(64) NOT NULL COMMENT '组名称',
  `host_id` varchar(64) NOT NULL COMMENT '主机id',
  `host_ip` varchar(64) NOT NULL COMMENT '机器ip',
  `host_port` int NOT NULL COMMENT '机器端口',
  `expire_at` datetime NOT NULL COMMENT '过期时间',
  `node_type` tinyint NOT NULL COMMENT '节点类型 1、客户端 2、是服务端',
  `ext_attrs` varchar(256) DEFAULT '' COMMENT '扩展字段',
  `labels` varchar(512) DEFAULT '' COMMENT '标签',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_host_id_host_ip` (`host_id`,`host_ip`),
  KEY `idx_namespace_id_group_name` (`namespace_id`,`group_name`),
  KEY `idx_expire_at_node_type` (`expire_at`,`node_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='服务器节点';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_system_user` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `username` varchar(64) NOT NULL COMMENT '账号',
  `password` varchar(128) NOT NULL COMMENT '密码',
  `role` tinyint NOT NULL DEFAULT '0' COMMENT '角色：1-普通用户、2-管理员',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='系统用户表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_system_user_permission` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `group_name` varchar(64) NOT NULL COMMENT '组名称',
  `namespace_id` varchar(64) NOT NULL DEFAULT '764d604ec6fc45f68cd92514c40e9e1a' COMMENT '命名空间id',
  `system_user_id` bigint NOT NULL COMMENT '系统用户id',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_namespace_id_group_name_system_user_id` (`namespace_id`,`group_name`,`system_user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='系统用户权限表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_workflow` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `workflow_name` varchar(64) NOT NULL COMMENT '工作流名称',
  `namespace_id` varchar(64) NOT NULL DEFAULT '764d604ec6fc45f68cd92514c40e9e1a' COMMENT '命名空间id',
  `biz_id` varchar(64) NOT NULL COMMENT '业务ID',
  `group_name` varchar(64) NOT NULL COMMENT '组名称',
  `workflow_status` tinyint NOT NULL DEFAULT '1' COMMENT '工作流状态 0、关闭、1、开启',
  `trigger_type` tinyint NOT NULL COMMENT '触发类型 1.CRON 表达式 2. 固定时间',
  `trigger_interval` varchar(255) NOT NULL COMMENT '间隔时长',
  `next_trigger_at` bigint NOT NULL COMMENT '下次触发时间',
  `block_strategy` tinyint NOT NULL DEFAULT '1' COMMENT '阻塞策略 1、丢弃 2、覆盖 3、并行',
  `executor_timeout` int NOT NULL DEFAULT '0' COMMENT '任务执行超时时间，单位秒',
  `description` varchar(256) NOT NULL DEFAULT '' COMMENT '描述',
  `flow_info` text COMMENT '流程信息',
  `wf_context` text COMMENT '上下文',
  `notify_ids` varchar(128) NOT NULL DEFAULT '' COMMENT '通知告警场景配置id列表',
  `bucket_index` int NOT NULL DEFAULT '0' COMMENT 'bucket',
  `version` int NOT NULL COMMENT '版本号',
  `owner_id` bigint DEFAULT NULL COMMENT '负责人id',
  `ext_attrs` varchar(256) DEFAULT '' COMMENT '扩展字段',
  `deleted` tinyint NOT NULL DEFAULT '0' COMMENT '逻辑删除 1、删除',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sj_workflow_01` (`namespace_id`,`biz_id`),
  KEY `idx_create_dt` (`create_dt`),
  KEY `idx_namespace_id_group_name` (`namespace_id`,`group_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工作流';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_workflow_node` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `namespace_id` varchar(64) NOT NULL DEFAULT '764d604ec6fc45f68cd92514c40e9e1a' COMMENT '命名空间id',
  `node_name` varchar(64) NOT NULL COMMENT '节点名称',
  `group_name` varchar(64) NOT NULL COMMENT '组名称',
  `job_id` bigint NOT NULL COMMENT '任务信息id',
  `workflow_id` bigint NOT NULL COMMENT '工作流ID',
  `node_type` tinyint NOT NULL DEFAULT '1' COMMENT '1、任务节点 2、条件节点',
  `expression_type` tinyint NOT NULL DEFAULT '0' COMMENT '1、SpEl、2、Aviator 3、QL',
  `fail_strategy` tinyint NOT NULL DEFAULT '1' COMMENT '失败策略 1、跳过 2、阻塞',
  `workflow_node_status` tinyint NOT NULL DEFAULT '1' COMMENT '工作流节点状态 0、关闭、1、开启',
  `priority_level` int NOT NULL DEFAULT '1' COMMENT '优先级',
  `node_info` text COMMENT '节点信息 ',
  `version` int NOT NULL COMMENT '版本号',
  `ext_attrs` varchar(256) DEFAULT '' COMMENT '扩展字段',
  `deleted` tinyint NOT NULL DEFAULT '0' COMMENT '逻辑删除 1、删除',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  KEY `idx_create_dt` (`create_dt`),
  KEY `idx_namespace_id_group_name` (`namespace_id`,`group_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工作流节点';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sj_workflow_task_batch` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `namespace_id` varchar(64) NOT NULL DEFAULT '764d604ec6fc45f68cd92514c40e9e1a' COMMENT '命名空间id',
  `group_name` varchar(64) NOT NULL COMMENT '组名称',
  `workflow_id` bigint NOT NULL COMMENT '工作流任务id',
  `task_batch_status` tinyint NOT NULL DEFAULT '0' COMMENT '任务批次状态 0、失败 1、成功',
  `operation_reason` tinyint NOT NULL DEFAULT '0' COMMENT '操作原因',
  `flow_info` text COMMENT '流程信息',
  `wf_context` text COMMENT '全局上下文',
  `execution_at` bigint NOT NULL DEFAULT '0' COMMENT '任务执行时间',
  `ext_attrs` varchar(256) DEFAULT '' COMMENT '扩展字段',
  `version` int NOT NULL DEFAULT '1' COMMENT '版本号',
  `deleted` tinyint NOT NULL DEFAULT '0' COMMENT '逻辑删除 1、删除',
  `create_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_dt` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '修改时间',
  PRIMARY KEY (`id`),
  KEY `idx_job_id_task_batch_status` (`workflow_id`,`task_batch_status`),
  KEY `idx_create_dt` (`create_dt`),
  KEY `idx_namespace_id_group_name` (`namespace_id`,`group_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工作流批次';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_client` (
  `id` bigint NOT NULL COMMENT 'id',
  `client_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户端id',
  `client_key` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户端key',
  `client_secret` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '客户端秘钥',
  `grant_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '授权类型',
  `device_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '设备类型',
  `access_path` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '允许访问路径',
  `ip_whitelist` varchar(1000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'IP白名单',
  `active_timeout` int DEFAULT '1800' COMMENT 'token活跃超时时间',
  `timeout` int DEFAULT '604800' COMMENT 'token固定超时',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '状态（0正常 1停用）',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '删除标志（0代表存在 1代表删除）',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='系统授权表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_config` (
  `config_id` bigint NOT NULL COMMENT '参数主键',
  `config_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '参数名称',
  `config_key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '参数键名',
  `config_value` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '参数键值',
  `config_type` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'N' COMMENT '系统内置（Y是 N否）',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`config_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='参数配置表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_dept` (
  `dept_id` bigint NOT NULL COMMENT '部门id',
  `parent_id` bigint DEFAULT '0' COMMENT '父部门id',
  `ancestors` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '祖级列表',
  `dept_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '部门名称',
  `dept_category` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '部门类别编码',
  `order_num` int DEFAULT '0' COMMENT '显示顺序',
  `leader` bigint DEFAULT NULL COMMENT '负责人',
  `phone` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '联系电话',
  `email` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '邮箱',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '部门状态（0正常 1停用）',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '删除标志（0代表存在 1代表删除）',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`dept_id`),
  KEY `idx_sys_dept_parent_id` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='部门表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_dict_data` (
  `dict_code` bigint NOT NULL COMMENT '字典编码',
  `dict_sort` int DEFAULT '0' COMMENT '字典排序',
  `dict_label` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '字典标签',
  `dict_value` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '字典键值',
  `dict_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '字典类型',
  `css_class` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '样式属性（其他样式扩展）',
  `list_class` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '表格回显样式',
  `is_default` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'N' COMMENT '是否默认（Y是 N否）',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`dict_code`),
  KEY `idx_sys_dict_data_type` (`dict_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='字典数据表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_dict_type` (
  `dict_id` bigint NOT NULL COMMENT '字典主键',
  `dict_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '字典名称',
  `dict_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '字典类型',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`dict_id`),
  UNIQUE KEY `dict_type` (`dict_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='字典类型表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_login_info` (
  `info_id` bigint NOT NULL COMMENT '访问ID',
  `user_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '用户账号',
  `client_key` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '客户端',
  `device_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '设备类型',
  `ipaddr` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '登录IP地址',
  `login_location` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '登录地点',
  `browser` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '浏览器类型',
  `os` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '操作系统',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '登录状态（0正常 1异常）',
  `msg` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '提示消息',
  `login_time` datetime DEFAULT NULL COMMENT '访问时间',
  PRIMARY KEY (`info_id`),
  KEY `idx_sys_login_info_s` (`status`),
  KEY `idx_sys_login_info_lt` (`login_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='系统访问记录';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_menu` (
  `menu_id` bigint NOT NULL COMMENT '菜单ID',
  `menu_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '菜单名称',
  `parent_id` bigint DEFAULT '0' COMMENT '父菜单ID',
  `order_num` int DEFAULT '0' COMMENT '显示顺序',
  `path` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '路由地址',
  `component` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '组件路径',
  `query_param` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '路由参数',
  `is_frame` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'N' COMMENT '是否为外链（Y是 N否）',
  `is_cache` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'Y' COMMENT '是否缓存（Y缓存 N不缓存）',
  `menu_type` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '菜单类型（M目录 C菜单 F按钮）',
  `visible` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '显示状态（0显示 1隐藏）',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '菜单状态（0正常 1停用）',
  `perms` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '权限标识',
  `icon` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '#' COMMENT '菜单图标',
  `active_menu` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '激活菜单路径',
  `ext` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '扩展字段',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '备注',
  PRIMARY KEY (`menu_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='菜单权限表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_message` (
  `message_id` bigint NOT NULL COMMENT '消息ID',
  `category` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '消息分组(system/notice/workflow)',
  `type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '消息类型',
  `source` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '消息来源',
  `title` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '标题',
  `message` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '摘要消息',
  `content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '详细内容',
  `data_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '扩展数据JSON',
  `path` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '前端跳转路径',
  `send_user_ids` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '0' COMMENT '目标用户ID串，0表示全局',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`message_id`),
  KEY `idx_sys_message_category_time` (`category`,`create_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='消息记录表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_notice` (
  `notice_id` bigint NOT NULL COMMENT '公告ID',
  `notice_title` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '公告标题',
  `notice_type` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '公告类型（1通知 2公告）',
  `notice_content` longblob COMMENT '公告内容',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '公告状态（0正常 1关闭）',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`notice_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='通知公告表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_oper_log` (
  `oper_id` bigint NOT NULL COMMENT '日志主键',
  `title` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '模块标题',
  `business_type` int DEFAULT '0' COMMENT '业务类型（0其它 1新增 2修改 3删除）',
  `method` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '方法名称',
  `request_method` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '请求方式',
  `operator_type` int DEFAULT '0' COMMENT '操作类别（0其它 1后台用户 2手机端用户）',
  `oper_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '操作人员',
  `user_id` bigint DEFAULT NULL COMMENT '操作用户ID',
  `dept_id` bigint DEFAULT NULL COMMENT '操作部门ID',
  `dept_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '部门名称',
  `client_key` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '客户端',
  `device_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '设备类型',
  `browser` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '浏览器类型',
  `os` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '操作系统',
  `oper_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '请求URL',
  `oper_ip` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '主机地址',
  `oper_location` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '操作地点',
  `oper_param` varchar(4000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '请求参数',
  `json_result` varchar(4000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '返回参数',
  `status` int DEFAULT '0' COMMENT '操作状态（0正常 1异常）',
  `error_msg` varchar(4000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '错误消息',
  `oper_time` datetime DEFAULT NULL COMMENT '操作时间',
  `cost_time` bigint DEFAULT '0' COMMENT '消耗时间',
  PRIMARY KEY (`oper_id`),
  KEY `idx_sys_oper_log_bt` (`business_type`),
  KEY `idx_sys_oper_log_uid` (`user_id`),
  KEY `idx_sys_oper_log_s` (`status`),
  KEY `idx_sys_oper_log_ot` (`oper_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='操作日志记录';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_oss` (
  `oss_id` bigint NOT NULL COMMENT '对象存储主键',
  `file_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '文件名',
  `original_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '原名',
  `file_suffix` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '文件后缀名',
  `url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT 'URL地址',
  `ext1` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci COMMENT '扩展字段',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `create_by` bigint DEFAULT NULL COMMENT '上传人',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新人',
  `service` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT 'minio' COMMENT '服务商',
  PRIMARY KEY (`oss_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='OSS对象存储表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_oss_config` (
  `oss_config_id` bigint NOT NULL COMMENT '主键',
  `config_key` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '' COMMENT '配置key',
  `access_key` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT 'accessKey',
  `secret_key` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '秘钥',
  `bucket_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '桶名称',
  `prefix` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '前缀',
  `endpoint` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '访问站点',
  `domain_url` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '自定义域名',
  `is_https` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'N' COMMENT '是否https（Y=是,N=否）',
  `region` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '域',
  `access_policy` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL DEFAULT '1' COMMENT '桶权限类型(0=private 1=public 2=custom)',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'N' COMMENT '是否默认（Y=是,N=否）',
  `ext1` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '扩展字段',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`oss_config_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='对象存储配置表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_post` (
  `post_id` bigint NOT NULL COMMENT '岗位ID',
  `dept_id` bigint NOT NULL COMMENT '部门id',
  `post_code` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '岗位编码',
  `post_category` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '岗位类别编码',
  `post_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '岗位名称',
  `post_sort` int NOT NULL COMMENT '显示顺序',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '状态（0正常 1停用）',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '删除标志（0代表存在 1代表删除）',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`post_id`),
  KEY `idx_sys_post_dept_id` (`dept_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='岗位信息表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_role` (
  `role_id` bigint NOT NULL COMMENT '角色ID',
  `role_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '角色名称',
  `role_key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '角色权限字符串',
  `role_sort` int NOT NULL COMMENT '显示顺序',
  `data_scope` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '1' COMMENT '数据范围（1：全部数据权限 2：自定数据权限 3：本部门数据权限 4：本部门及以下数据权限 5：仅本人数据权限 6：部门及以下或本人数据权限）',
  `menu_check_strictly` tinyint(1) DEFAULT '1' COMMENT '菜单树选择项是否关联显示',
  `dept_check_strictly` tinyint(1) DEFAULT '1' COMMENT '部门树选择项是否关联显示',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '角色状态（0正常 1停用）',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '删除标志（0代表存在 1代表删除）',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`role_id`),
  KEY `idx_sys_role_create_dept` (`create_dept`),
  KEY `idx_sys_role_create_by` (`create_by`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='角色信息表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_role_dept` (
  `role_id` bigint NOT NULL COMMENT '角色ID',
  `dept_id` bigint NOT NULL COMMENT '部门ID',
  PRIMARY KEY (`role_id`,`dept_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='角色和部门关联表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_role_menu` (
  `role_id` bigint NOT NULL COMMENT '角色ID',
  `menu_id` bigint NOT NULL COMMENT '菜单ID',
  PRIMARY KEY (`role_id`,`menu_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='角色和菜单关联表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_social` (
  `id` bigint NOT NULL COMMENT '主键',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `auth_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '平台+平台唯一id',
  `source` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '用户来源',
  `open_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '平台编号唯一id',
  `user_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '登录账号',
  `nick_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '用户昵称',
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '用户邮箱',
  `avatar` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '头像地址',
  `access_token` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '用户的授权令牌',
  `expire_in` int DEFAULT NULL COMMENT '用户的授权令牌的有效期，部分平台可能没有',
  `refresh_token` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '刷新令牌，部分平台可能没有',
  `access_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '平台的授权信息，部分平台可能没有',
  `union_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '用户的 unionid',
  `scope` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '授予的权限，部分平台可能没有',
  `token_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '个别平台的授权信息，部分平台可能没有',
  `id_token` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'id token，部分平台可能没有',
  `mac_algorithm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '小米平台用户的附带属性，部分平台可能没有',
  `mac_key` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '小米平台用户的附带属性，部分平台可能没有',
  `code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '用户的授权code，部分平台可能没有',
  `oauth_token` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'Twitter平台用户的附带属性，部分平台可能没有',
  `oauth_token_secret` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'Twitter平台用户的附带属性，部分平台可能没有',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '删除标志（0代表存在 1代表删除）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='社会化关系表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_user` (
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `dept_id` bigint DEFAULT NULL COMMENT '部门ID',
  `user_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '用户账号',
  `nick_name` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '用户昵称',
  `user_type` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT 'sys_user' COMMENT '用户类型（sys_user系统用户）',
  `email` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '用户邮箱',
  `phone_number` varchar(11) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '手机号码',
  `gender` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '用户性别（0男 1女 2未知）',
  `avatar` bigint DEFAULT NULL COMMENT '头像地址',
  `password` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '密码',
  `status` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '账号状态（0正常 1停用）',
  `del_flag` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '删除标志（0代表存在 1代表删除）',
  `login_ip` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT '' COMMENT '最后登录IP',
  `login_date` datetime DEFAULT NULL COMMENT '最后登录时间',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `remark` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (`user_id`),
  KEY `idx_sys_user_dept_id` (`dept_id`),
  KEY `idx_sys_user_create_by` (`create_by`),
  KEY `idx_sys_user_user_name` (`user_name`),
  KEY `idx_sys_user_phone` (`phone_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户信息表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_user_post` (
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `post_id` bigint NOT NULL COMMENT '岗位ID',
  PRIMARY KEY (`user_id`,`post_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户与岗位关联表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_user_role` (
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `role_id` bigint NOT NULL COMMENT '角色ID',
  PRIMARY KEY (`user_id`,`role_id`),
  KEY `idx_sys_user_role_rid` (`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户和角色关联表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `test_demo` (
  `id` bigint NOT NULL COMMENT '主键',
  `dept_id` bigint DEFAULT NULL COMMENT '部门id',
  `user_id` bigint DEFAULT NULL COMMENT '用户id',
  `order_num` int DEFAULT '0' COMMENT '排序号',
  `test_key` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'key键',
  `value` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '值',
  `version` int DEFAULT '0' COMMENT '版本',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `create_by` bigint DEFAULT NULL COMMENT '创建人',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新人',
  `del_flag` int DEFAULT '0' COMMENT '删除标志',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='测试单表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `test_leave` (
  `id` bigint NOT NULL COMMENT 'id',
  `apply_code` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '申请编号',
  `leave_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '请假类型',
  `start_date` datetime NOT NULL COMMENT '开始时间',
  `end_date` datetime NOT NULL COMMENT '结束时间',
  `leave_days` int NOT NULL COMMENT '请假天数',
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '请假原因',
  `status` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '状态',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_by` bigint DEFAULT NULL COMMENT '创建者',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新者',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='请假申请表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `test_tree` (
  `id` bigint NOT NULL COMMENT '主键',
  `parent_id` bigint DEFAULT '0' COMMENT '父id',
  `dept_id` bigint DEFAULT NULL COMMENT '部门id',
  `user_id` bigint DEFAULT NULL COMMENT '用户id',
  `tree_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '值',
  `version` int DEFAULT '0' COMMENT '版本',
  `create_dept` bigint DEFAULT NULL COMMENT '创建部门',
  `create_time` datetime DEFAULT NULL COMMENT '创建时间',
  `create_by` bigint DEFAULT NULL COMMENT '创建人',
  `update_time` datetime DEFAULT NULL COMMENT '更新时间',
  `update_by` bigint DEFAULT NULL COMMENT '更新人',
  `del_flag` int DEFAULT '0' COMMENT '删除标志',
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='测试树表';
/*!40101 SET character_set_client = @saved_cs_client */;

"""数据库层：异步引擎 + 反射现有 ruoyi_plus 表（1:1 复用原表与原数据）。

设计要点：
- 用 SQLAlchemy Core 反射（autoload）现有表，保证列结构与原库完全一致，零手写模型风险。
- 仅反射本后端实际读写的表，避免一次性反射 116 张表。
- 新增一张 cmd_py_flow_instance 保存 SpiffWorkflow 流程实例的序列化状态（Python 侧新增状态表）。
"""
from __future__ import annotations

from typing import Dict

from sqlalchemy import (
    MetaData, Table, Column, BigInteger, String, Text, JSON,
    DateTime, Integer, create_engine, text,
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncConnection

from .config import settings

# 业务读写涉及的现有表（与前端 /cmd/** 接口一一对应）
REFLECT_TABLES = [
    "cmd_customer", "cmd_customer_application", "cmd_customer_field_value",
    "cmd_approval_task", "cmd_change_request", "cmd_change_diff",
    "cmd_governance_task", "cmd_merge_record", "cfg_sequence", "md_field",
    "md_value_set", "sys_user", "sys_role", "sys_menu",
    # 工作流配置 / 步骤日志
    "cmd_flow_scene", "cmd_flow_node_rule", "cmd_flow_delegate",
    "cmd_workflow_step_log",
    # DQ / 匹配
    "dq_rule", "dq_reeval_job", "dq_scorecard", "match_rule",
    # 导入
    "cmd_import_job", "cmd_import_row", "cmd_import_template",
    "cmd_import_template_mapping", "cmd_import_error",
    # 层级 / OneID
    "cmd_hierarchy_node", "cmd_hierarchy_relation", "cmd_hierarchy_relation_hist",
    "oneid_rule", "oneid_event",
    # 审计 / 权限 / 覆盖 / OCR / 集成
    "audit_event", "audit_export_log", "cmd_role_permission", "cmd_user_role",
    "poc_coverage_topic", "cmd_ocr_result",
    "int_endpoint", "int_run", "int_message",
    "cmd_legacy_mapping", "cmd_loop_check_log", "cmd_notification",
    "cmd_role", "md_model_version",
    "cmd_flow_def_version",
    "cmd_approval_action", "cmd_flow_scene", "cmd_flow_node_rule", "cmd_workflow_step_log",
]

metadata = MetaData()

# Python 侧新增：SpiffWorkflow 流程实例持久化表
flow_instance_table = Table(
    "cmd_py_flow_instance", metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("biz_no", String(100), nullable=False, comment="业务编号（= task_no）"),
    Column("scene_code", String(64), nullable=False, comment="场景编码"),
    Column("biz_type", String(64), nullable=False, comment="业务类型"),
    Column("state", Text, nullable=False, comment="base64(pickle 序列化的 BpmnWorkflow)"),
    Column("status", String(20), nullable=False, default="RUNNING", comment="RUNNING / COMPLETED"),
    Column("current_node", String(100), nullable=True, comment="当前节点编码"),
    # 用 Text 存 JSON 字符串，规避 aiomysql + pymysql2.x 对 JSON 类型的转义不兼容
    Column("data_json", Text, nullable=True, comment="流程变量快照（JSON 字符串）"),
    Column("create_time", DateTime, nullable=True),
    Column("update_time", DateTime, nullable=True),
)

# Python 侧新增：自增序号表（原库无 AUTO_INCREMENT、cfg_sequence 为空，用于生成 id 与业务编号）
seq_table = Table(
    "cmd_py_seq", metadata,
    Column("name", String(64), primary_key=True, comment="序号名（表名或编号名）"),
    Column("current", BigInteger, nullable=False, default=0, comment="当前值"),
)

_engine: AsyncEngine | None = None
_tables: Dict[str, Table] = {}


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            connect_args={"autocommit": False},
        )
    return _engine


async def init_db() -> None:
    """反射现有表 + 创建 Python 侧流程实例表。"""
    engine = get_engine()
    async with engine.connect() as conn:
        # 反射现有表
        def _reflect(sync_conn):
            metadata.reflect(sync_conn, only=REFLECT_TABLES)
        await conn.run_sync(_reflect)
        for name in REFLECT_TABLES:
            _tables[name] = metadata.tables[name]
        # 创建 Python 侧新增表（若不存在）
        await conn.run_sync(lambda sc: metadata.create_all(sc, tables=[flow_instance_table, seq_table]))
        await conn.commit()


def table(name: str) -> Table:
    t = _tables.get(name)
    if t is None:
        raise KeyError(f"表 {name} 尚未反射，请确认已在 REFLECT_TABLES 中登记")
    return t

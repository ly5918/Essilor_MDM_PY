"""导入域数据访问层（对应 Java CmdImportJobMapper / CmdImportRowMapper /
CmdImportTemplateMapper / CmdImportTemplateMappingMapper）。

约定：
- 只做 SQL/表操作，不含业务判断；
- 全部函数显式接收 conn（事务边界由调用方控制），不自行 commit；
- 返回 dict（mappings），由上层决定如何加工。
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy import desc, func, select

from ..core.db import table
from ..core.query import dynamic_insert

# ============================ 导入任务（cmd_import_job） ============================


async def get_job_by_id(conn, job_id: int) -> Optional[dict]:
    row = (await conn.execute(
        table("cmd_import_job").select()
        .where(table("cmd_import_job").c.id == job_id))).mappings().first()
    return dict(row) if row else None


async def get_job_by_code(conn, job_code: str) -> Optional[dict]:
    row = (await conn.execute(
        table("cmd_import_job").select()
        .where(table("cmd_import_job").c.job_code == job_code))).mappings().first()
    return dict(row) if row else None


async def insert_job(conn, vals: dict) -> dict:
    """插入任务并回读（job_code 唯一键由本层生成）。"""
    await dynamic_insert(conn, table("cmd_import_job"), vals)
    return await get_job_by_code(conn, vals["job_code"])


async def update_job(conn, job_id: int, patch: dict) -> None:
    if patch:
        await conn.execute(table("cmd_import_job").update()
                           .where(table("cmd_import_job").c.id == job_id).values(**patch))


async def list_jobs(conn, page: int, size: int,
                    job_status_list: Optional[List[str]] = None) -> dict:
    """任务分页列表；job_status_list 为 Java 口径的「待处置」状态聚合。"""
    t = table("cmd_import_job")
    stmt = select(t)
    count_stmt = select(func.count()).select_from(t)
    if job_status_list:
        stmt = stmt.where(t.c.job_status.in_(job_status_list))
        count_stmt = count_stmt.where(t.c.job_status.in_(job_status_list))
    rows = (await conn.execute(
        stmt.order_by(desc(t.c.create_time)).limit(size).offset((page - 1) * size))).mappings().all()
    total = (await conn.execute(count_stmt)).scalar() or 0
    return {"rows": [dict(r) for r in rows], "total": int(total)}


async def aggregate_job_stats(conn) -> dict:
    """导入中心全局统计（全量口径：跨全部任务 SUM，对应 Java selectStats）。"""
    t = table("cmd_import_job")
    row = (await conn.execute(
        select(
            func.count().label("job_count"),
            func.coalesce(func.sum(t.c.total_count), 0).label("total_rows"),
            func.coalesce(func.sum(t.c.exact_count), 0).label("exact_count"),
            func.coalesce(func.sum(t.c.suspected_count), 0).label("suspected_count"),
            func.coalesce(func.sum(t.c.new_count), 0).label("new_count"),
            func.coalesce(func.sum(t.c.review_count), 0).label("review_count"),
            func.coalesce(func.sum(t.c.invalid_count), 0).label("invalid_count"),
        ))).mappings().first()
    return dict(row)


# ============================ 导入行（cmd_import_row） ============================


async def list_rows_by_job(conn, job_id: int,
                           result_type: Optional[str] = None) -> List[dict]:
    stmt = select(table("cmd_import_row")).where(
        table("cmd_import_row").c.job_id == job_id)
    if result_type:
        stmt = stmt.where(table("cmd_import_row").c.result_type == result_type.upper())
    rows = (await conn.execute(
        stmt.order_by(table("cmd_import_row").c.row_no))).mappings().all()
    out: List[dict] = []
    for r in rows:
        d = dict(r)
        # raw_json 是 JSON 列，SQLAlchemy 反序列化为 dict；Java 实体与前端契约是
        # JSON 字符串（前端 parseRaw 按 JSON.parse 处理），此处统一序列化回字符串
        v = d.get("raw_json")
        if isinstance(v, (dict, list)):
            d["raw_json"] = json.dumps(v, ensure_ascii=False)
        out.append(d)
    return out


async def get_row(conn, row_id: int) -> Optional[dict]:
    row = (await conn.execute(
        table("cmd_import_row").select()
        .where(table("cmd_import_row").c.id == row_id))).mappings().first()
    return dict(row) if row else None


async def insert_row(conn, vals: dict) -> None:
    return await dynamic_insert(conn, table("cmd_import_row"), vals)


async def update_row(conn, row_id: int, patch: dict) -> None:
    if patch:
        await conn.execute(table("cmd_import_row").update()
                           .where(table("cmd_import_row").c.id == row_id).values(**patch))


# ============================ 模板与映射（cmd_import_template / _mapping） ============================


async def list_templates(conn) -> List[dict]:
    rows = (await conn.execute(
        select(table("cmd_import_template"))
        .order_by(table("cmd_import_template").c.id))).mappings().all()
    return [dict(r) for r in rows]


async def get_template_by_code(conn, template_code: str) -> Optional[dict]:
    row = (await conn.execute(
        table("cmd_import_template").select()
        .where(table("cmd_import_template").c.template_code == template_code))).mappings().first()
    return dict(row) if row else None


async def get_template_by_id(conn, template_id: int) -> Optional[dict]:
    row = (await conn.execute(
        table("cmd_import_template").select()
        .where(table("cmd_import_template").c.id == template_id))).mappings().first()
    return dict(row) if row else None


async def count_mappings(conn, template_code: str) -> int:
    return (await conn.execute(
        select(func.count()).select_from(table("cmd_import_template_mapping"))
        .where(table("cmd_import_template_mapping").c.template_code == template_code)
        .where(table("cmd_import_template_mapping").c.del_flag == "0"))).scalar() or 0


async def list_mappings(conn, template_code: Optional[str] = None) -> List[dict]:
    stmt = select(table("cmd_import_template_mapping")).where(
        table("cmd_import_template_mapping").c.del_flag == "0")
    if template_code:
        stmt = stmt.where(table("cmd_import_template_mapping").c.template_code == template_code)
    rows = (await conn.execute(
        stmt.order_by(table("cmd_import_template_mapping").c.column_index))).mappings().all()
    return [dict(r) for r in rows]


async def max_column_index(conn, template_code: str) -> int:
    """含软删行的最大列序号（唯一键 uk_cmd_tpl_map 不区分 del_flag，必须越过已删列号）。"""
    return (await conn.execute(
        select(func.max(table("cmd_import_template_mapping").c.column_index))
        .where(table("cmd_import_template_mapping").c.template_code == template_code))).scalar() or 0


async def insert_mapping(conn, vals: dict) -> dict:
    return await dynamic_insert(conn, table("cmd_import_template_mapping"), vals)


async def update_mapping(conn, mapping_id: int, patch: dict) -> None:
    if patch:
        await conn.execute(table("cmd_import_template_mapping").update()
                           .where(table("cmd_import_template_mapping").c.id == mapping_id)
                           .values(**patch))


async def soft_delete_mapping(conn, mapping_id: int) -> None:
    await conn.execute(table("cmd_import_template_mapping").update()
                       .where(table("cmd_import_template_mapping").c.id == mapping_id)
                       .values(del_flag="1"))


# ============================ 存量主档匹配（cmd_customer） ============================


async def find_active_by_credit_code(conn, credit_code: str) -> Optional[dict]:
    """存量精确匹配：信用代码 + active 主档。"""
    row = (await conn.execute(
        select(table("cmd_customer")).where(
            table("cmd_customer").c.credit_code == credit_code,
            table("cmd_customer").c.status == "active",
            table("cmd_customer").c.del_flag == "0").limit(1))).mappings().first()
    return dict(row) if row else None


async def find_by_legal_name(conn, legal_name: str) -> Optional[dict]:
    """存量名称匹配：名称相同（不限状态，作为疑似候选证据）。"""
    row = (await conn.execute(
        select(table("cmd_customer")).where(
            table("cmd_customer").c.legal_name == legal_name,
            table("cmd_customer").c.del_flag == "0").limit(1))).mappings().first()
    return dict(row) if row else None


async def find_active_by_one_id(conn, one_id: str) -> Optional[dict]:
    """按 One ID 查 active 主档（行治理 LINK 跨BU判定用）。"""
    row = (await conn.execute(
        select(table("cmd_customer")).where(
            table("cmd_customer").c.one_id == one_id,
            table("cmd_customer").c.status == "active",
            table("cmd_customer").c.del_flag == "0")
        .order_by(desc(table("cmd_customer").c.create_time)).limit(1))).mappings().first()
    return dict(row) if row else None


# ============================ 审计留痕（audit_event） ============================


async def insert_audit_event(conn, vals: dict) -> None:
    await dynamic_insert(conn, table("audit_event"), vals)


def now() -> datetime:
    return datetime.now()

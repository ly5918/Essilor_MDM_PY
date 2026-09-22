"""通用表查询助手：对反射表做安全分页/关键字/过滤查询，供各 /cmd/** 列表接口复用。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select, func, or_
from sqlalchemy.sql import Select

# 常见关键字检索列（存在才用）
_KEYWORD_COLS = (
    "legal_name", "short_name", "name", "task_no", "request_code", "task_code",
    "merge_code", "code", "title", "biz_title", "subject", "one_id", "credit_code",
    "credit_no", "rule_name", "endpoint_name", "file_name", "template_name",
    "event_type", "node_key", "role_name", "topic", "status", "remark", "content",
)


def _build_conditions(table_obj, *, filters, keyword, keyword_cols, extra_where):
    conds = []
    if filters:
        for k, v in filters.items():
            if v is None:
                continue
            col = getattr(table_obj.c, k, None)
            if col is not None:
                conds.append(col == v)
    if keyword:
        cols = [c for c in (keyword_cols or _KEYWORD_COLS) if hasattr(table_obj.c, c)]
        if cols:
            conds.append(or_(*[getattr(table_obj.c, c).like(f"%{keyword}%") for c in cols]))
    if extra_where is not None:
        conds.append(extra_where)
    return conds


async def list_table(
    conn,
    table_obj,
    *,
    page: int = 1,
    size: int = 20,
    filters: Optional[Dict[str, Any]] = None,
    keyword: Optional[str] = None,
    keyword_cols: Optional[Sequence[str]] = None,
    order_by: Optional[Any] = None,
    extra_where: Optional[Any] = None,
) -> Dict[str, Any]:
    """返回 {'total': int, 'rows': [dict, ...]}（对齐前端 PageResult 契约）。"""
    conds = _build_conditions(
        table_obj, filters=filters, keyword=keyword,
        keyword_cols=keyword_cols, extra_where=extra_where,
    )
    base = select(table_obj)
    if conds:
        base = base.where(*conds)

    total = (await conn.execute(
        select(func.count()).select_from(table_obj).where(*conds)
    )).scalar() or 0

    data_stmt = base
    if order_by is not None:
        data_stmt = data_stmt.order_by(order_by)
    data_stmt = data_stmt.limit(size).offset((max(page, 1) - 1) * size)
    rows = (await conn.execute(data_stmt)).mappings().all()
    return {"total": total, "rows": [dict(r) for r in rows]}


async def get_row(conn, table_obj, pk_value, pk_col: str = "id"):
    row = (await conn.execute(
        select(table_obj).where(getattr(table_obj.c, pk_col) == pk_value)
    )).mappings().first()
    return dict(row) if row is not None else None


async def dynamic_insert(conn, table_obj, data: Dict[str, Any]):
    """按反射表的真实列过滤 payload，自动补 id 与 del_flag，执行插入。"""
    from ..services import sequence as seq
    cols = set(table_obj.c.keys())
    vals = {k: v for k, v in data.items() if k in cols}
    if "del_flag" in cols and "del_flag" not in vals:
        vals["del_flag"] = "0"
    pk = table_obj.primary_key.columns.keys()[0]
    if pk in cols and pk not in vals:
        vals[pk] = await seq.next_id(conn, table_obj.name)
    await conn.execute(table_obj.insert().values(**vals))
    return vals


async def dynamic_update(conn, table_obj, pk_value, data: Dict[str, Any], pk_col: str = "id"):
    cols = set(table_obj.c.keys())
    vals = {k: v for k, v in data.items() if k in cols and k != pk_col}
    if not vals:
        return
    await conn.execute(
        table_obj.update().where(getattr(table_obj.c, pk_col) == pk_value).values(**vals)
    )

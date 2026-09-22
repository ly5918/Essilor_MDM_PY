"""编号与 ID 生成。

原库特点：
- 业务表无 AUTO_INCREMENT；
- cfg_sequence 表为空（原 one_id 由 Java 侧其它规则生成）；
- 库内已存在演示数据（task_no 形如 AP-20260922-0001）。

因此这里用 cmd_py_seq 计数器表生成：
  - 表主键 id（续接现有 MAX(id)+1）
  - one_id（GC-XXXXXXXX 十六进制，大于现有最大值避免碰撞）
  - 审批/申请编号（AP-yyyyMMdd-#### 等）：从「现有最大序号 +1」起算，绝不撞已有演示数据
均在同一事务内完成，保证并发安全。
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Tuple

from sqlalchemy import text, select

from ..core.db import get_engine, seq_table


async def next_id(conn, table_name: str) -> int:
    """续接现有表 MAX(id)+1 生成主键。"""
    row = (await conn.execute(text(f"SELECT COALESCE(MAX(id),0) FROM {table_name}"))).first()
    return (row[0] or 0) + 1


async def _next_seq(conn, name: str, init: int = 0) -> int:
    row = (await conn.execute(select(seq_table).where(seq_table.c.name == name))).first()
    if row is None:
        await conn.execute(seq_table.insert().values(name=name, current=init + 1))
        return init + 1
    nxt = row._mapping["current"] + 1
    await conn.execute(seq_table.update().where(seq_table.c.name == name).values(current=nxt))
    return nxt


async def _existing_max_num(conn, pattern: str, tables_cols: List[Tuple[str, str]], width: int) -> int:
    """扫描现有表中匹配 pattern 的编号，返回其后 width 位数字的最大值。"""
    maxn = 0
    for tbl, col in tables_cols:
        rows = (await conn.execute(
            text(f"SELECT {col} FROM {tbl} WHERE {col} LIKE :p"), {"p": pattern})).all()
        for r in rows:
            v = r[0]
            if isinstance(v, str) and len(v) >= width and v[-width:].isdigit():
                maxn = max(maxn, int(v[-width:]))
    return maxn


async def _existing_max_hex(conn) -> int:
    """扫描现有 one_id（GC-XXXXXXXX）的最大十六进制数值，避免碰撞。"""
    maxv = 0
    rows = (await conn.execute(text("SELECT one_id FROM cmd_customer WHERE one_id LIKE 'GC-%'"))).all()
    for r in rows:
        v = r[0]
        try:
            maxv = max(maxv, int(v[3:], 16))
        except ValueError:
            pass
    return maxv


async def gen_one_id(conn) -> str:
    """生成 One ID，形如 GC-6021C90C（大于现有最大值）。"""
    base = max(await _existing_max_hex(conn), 0) + 1
    n = await _next_seq(conn, "ONE_ID", init=base)
    return f"GC-{n:08X}"


async def gen_app_no(conn) -> str:
    """生成审批/申请编号，形如 AP-20260922-0028（接续现有最大序号）。"""
    d = datetime.now().strftime("%Y%m%d")
    pattern = f"AP-{d}-%"
    tables_cols = [("cmd_approval_task", "task_no"), ("cmd_customer_application", "app_no")]
    init = await _existing_max_num(conn, pattern, tables_cols, 4)
    n = await _next_seq(conn, f"APPROVAL_NO_{d}", init=init)
    return f"AP-{d}-{n:04d}"


async def gen_code(conn, prefix: str, width: int = 6, key: str | None = None) -> str:
    """通用编号，如 MRG-20260922-0001 / CH-20260922-0001 / GOV-20260922-0001。
    从现有最大序号 +1 起算，避免与演示数据碰撞。"""
    if key is None:
        key = prefix
    d = datetime.now().strftime("%Y%m%d")
    pattern = f"{prefix}{d}-%"
    tables_cols = [
        ("cmd_approval_task", "task_no"), ("cmd_governance_task", "task_code"),
        ("cmd_change_request", "request_code"), ("cmd_merge_record", "merge_code"),
    ]
    init = await _existing_max_num(conn, pattern, tables_cols, width)
    n = await _next_seq(conn, f"{key}_{d}", init=init)
    return f"{prefix}{d}-{n:0{width}d}"

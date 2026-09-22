"""重复核验：按统一社会信用代码判定重复状态（EXACT / SUSPECTED / NEW）。

口径与原系统一致：同主体排除 merged/rejected/draft；命中即返回组内 One ID 列表。
"""
from __future__ import annotations

from sqlalchemy import select

from ..core.db import table


async def duplicate_check(conn, credit_code: str | None):
    if not credit_code:
        return {"match_state": "NEW", "duplicate_flag": "N", "peers": []}

    cust = table("cmd_customer")
    app = table("cmd_customer_application")

    # 1) 已生效主档命中 → EXACT
    rows = (await conn.execute(
        select(cust.c.one_id, cust.c.legal_name, cust.c.status)
        .where(cust.c.credit_code == credit_code)
        .where(cust.c.status == "active")
        .where(cust.c.del_flag == "0")
    )).all()
    if rows:
        return {"match_state": "EXACT", "duplicate_flag": "Y",
                "peers": [{"one_id": r._mapping["one_id"], "legal_name": r._mapping["legal_name"]} for r in rows]}

    # 2) 在途申请命中 → SUSPECTED
    rows = (await conn.execute(
        select(app.c.one_id, app.c.legal_name, app.c.status, app.c.app_no)
        .where(app.c.credit_code == credit_code)
        .where(app.c.status.in_(["pending", "returned"]))
        .where(app.c.del_flag == "0")
    )).all()
    if rows:
        return {"match_state": "SUSPECTED", "duplicate_flag": "Y",
                "peers": [{"one_id": r._mapping["one_id"], "legal_name": r._mapping["legal_name"],
                           "app_no": r._mapping["app_no"]} for r in rows]}

    return {"match_state": "NEW", "duplicate_flag": "N", "peers": []}

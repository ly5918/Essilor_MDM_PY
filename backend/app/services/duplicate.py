"""重复核验：判定重复状态（EXACT / SUSPECTED / NEW）。

口径对齐 Java CmdCustomerServiceImpl.matchExisting：
1) 统一社会信用代码 vs 已发布主档（active）→ EXACT（精准重复）；
2) 客户名称 vs 已发布主档（规范化相等或 bigram Dice 相似度 ≥ 0.85）→ SUSPECTED（疑似重复）；
3) 同信用代码在途申请（pending/returned）→ SUSPECTED + 在途标记（上一单未审完时不判 NEW）。

同主体口径：排除 merged/rejected/draft；命中即返回组内 One ID 列表（含回执富化字段）。
"""
from __future__ import annotations

import re
from sqlalchemy import select, desc

from ..core.db import table

_NAME_SUFFIXES = ("股份有限公司", "有限责任公司", "有限公司", "集团公司", "集团", "分公司", "分店", "总部", "中心", "工厂", "公司")
_BRACKET_RE = re.compile(r"[（(【\[].*?[）)】\]]")


def normalize_customer_name(name: str | None) -> str:
    """对齐 Java normalizeCustomerName：去括号及其中内容，去常见法律/组织后缀（长后缀优先）。"""
    s = (name or "").strip()
    s = _BRACKET_RE.sub("", s)
    for suf in _NAME_SUFFIXES:
        if s.endswith(suf):
            s = s[: -len(suf)]
            break
    return s.strip()


def _bigrams(s: str) -> set[str]:
    return {s[i:i + 2] for i in range(len(s) - 1)}


def dice_similarity(a: str, b: str) -> float:
    """bigram Dice 相似度（0~1），对齐 Java diceSimilarity（名称模糊比对兜底）。"""
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    ba, bb = _bigrams(a), _bigrams(b)
    overlap = len(ba & bb)
    return (2.0 * overlap) / (len(ba) + len(bb))


async def duplicate_check(conn, credit_code: str | None, legal_name: str | None = None):
    if not credit_code and not legal_name:
        return {"match_state": "NEW", "duplicate_flag": "N", "peers": []}

    cust = table("cmd_customer")
    app = table("cmd_customer_application")

    def _peer(row) -> dict:
        return {
            "one_id": row._mapping["one_id"],
            "legal_name": row._mapping["legal_name"],
            "credit_code": row._mapping.get("credit_code"),
            "bu_scope": row._mapping.get("bu_scope"),
            "status": row._mapping.get("status"),
            "in_flight": False,
        }

    # 1) 主依据：信用代码 vs 已发布主档 → EXACT
    if credit_code:
        rows = (await conn.execute(
            select(cust.c.one_id, cust.c.legal_name, cust.c.credit_code, cust.c.bu_scope, cust.c.status)
            .where(cust.c.credit_code == credit_code)
            .where(cust.c.status == "active")
            .where(cust.c.del_flag == "0")
            .order_by(desc(cust.c.create_time))
        )).all()
        if rows:
            return {"match_state": "EXACT", "duplicate_flag": "Y", "peers": [_peer(r) for r in rows]}

    # 2) 辅助线索：客户名称 vs 已发布主档（规范化相等或 Dice ≥ 0.85）→ SUSPECTED
    #    （对齐 Java：仅名称同值/相近命中时信用代码不同，判疑似重复而非精准重复）
    if legal_name:
        norm_new = normalize_customer_name(legal_name)
        if norm_new:
            rows = (await conn.execute(
                select(cust.c.one_id, cust.c.legal_name, cust.c.credit_code, cust.c.bu_scope, cust.c.status)
                .where(cust.c.status == "active")
                .where(cust.c.del_flag == "0")
                .order_by(desc(cust.c.create_time))
            )).all()
            hits = []
            for r in rows:
                exist_name = r._mapping["legal_name"]
                if not exist_name:
                    continue
                norm_exist = normalize_customer_name(exist_name)
                if norm_new == norm_exist or dice_similarity(norm_new, norm_exist) >= 0.85:
                    hits.append(r)
            if hits:
                return {"match_state": "SUSPECTED", "duplicate_flag": "Y", "peers": [_peer(r) for r in hits]}

    # 3) 同信用代码在途申请 → SUSPECTED + in_flight 标记（上一单未审完时依然判重复）
    if credit_code:
        rows = (await conn.execute(
            select(app.c.one_id, app.c.legal_name, app.c.credit_code, app.c.bu_scope,
                   app.c.status, app.c.app_no)
            .where(app.c.credit_code == credit_code)
            .where(app.c.status.in_(["pending", "returned"]))
            .where(app.c.del_flag == "0")
            .order_by(desc(app.c.create_time))
        )).all()
        if rows:
            peers = []
            for r in rows:
                p = _peer(r)
                p["in_flight"] = True
                p["app_no"] = r._mapping["app_no"]
                peers.append(p)
            return {"match_state": "SUSPECTED", "duplicate_flag": "Y", "peers": peers}

    return {"match_state": "NEW", "duplicate_flag": "N", "peers": []}

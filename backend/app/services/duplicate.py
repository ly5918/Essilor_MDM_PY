"""重复核验：对齐《Essilor CMD POC 总体设计方案 V6.1》场景一 Duplicate Check 节点口径。

设计口径（文档原文）：
- Duplicate Check 节点：『以信用代码和经营地址为主依据；名称仅作为辅助线索』；
- 匹配规则页：『配置信用代码、经营地址、辅助名称、字段组合和空值策略』
  + 『定义 Exact / Suspected / New 阈值与 Same-BU / Cross-BU 路由』；
- 输出候选与解释：『展示字段贡献、相似度、候选 One ID 和结果分类』。

实现要点：
1) 主依据 = 统一社会信用代码 + 经营地址；客户名称仅作辅助线索——
   主依据都不像时，名称再像也不单独判重复（避免同名不同主体的误判）；
2) 阈值与标准化策略取 match_rule（按 scene：CREATE / IMPORT），缺规则时用内置默认，
   不再像此前那样把 0.85 写死在代码里（改规则页的阈值此前根本不生效）；
3) 结果三档 EXACT / SUSPECTED / NEW，并回传得分与字段贡献供审批端展示；
4) 保留「同信用代码在途申请」判定：防止同一主体重复发单、审批后产生两个 One ID。
"""
from __future__ import annotations

import re
from sqlalchemy import select, desc

from ..core.db import table

# ---- 归一化 ----
_NAME_SUFFIXES = ("股份有限公司", "有限责任公司", "有限公司", "集团公司", "集团", "分公司", "分店", "总部", "中心", "工厂", "公司")
_BRACKET_RE = re.compile(r"[（(【\[].*?[）)】\]]")
_ADDR_NOISE_RE = re.compile(r"[\s,，.。、;；:：\-—_/\\|#'\"“”()（）]+")

# 匹配规则缺省值（match_rule 无可用记录时的兜底）
DEFAULT_NORMALIZE_RULE = "trim|upper|removeSuffix(公司,有限公司,Co.,Ltd)|fullToHalf"
DEFAULT_EXACT_THRESHOLD = 95.0
DEFAULT_SUSPECT_THRESHOLD = 70.0

# 权重：主依据（信用代码 / 经营地址）为主，客户名称为辅助线索
W_PRIMARY = 0.75
W_AUX = 0.25
# 主依据门槛：主依据相似度低于此值时，名称不得单独把总分推过疑似线
PRIMARY_GATE = 50.0


def _full_to_half(s: str) -> str:
    """全角转半角（对齐 match_rule.normalize_rule 的 fullToHalf）。"""
    out = []
    for ch in s or "":
        code = ord(ch)
        if code == 0x3000:
            out.append(" ")
        elif 0xFF01 <= code <= 0xFF5E:
            out.append(chr(code - 0xFEE0))
        else:
            out.append(ch)
    return "".join(out)


def parse_normalize_rule(rule: str | None) -> dict:
    """解析 match_rule.normalize_rule，如 trim|upper|removeSuffix(公司,有限公司)|fullToHalf。"""
    ops = {"trim": True, "upper": True, "fullToHalf": False, "suffixes": list(_NAME_SUFFIXES)}
    if not rule:
        return ops
    for part in str(rule).split("|"):
        p = part.strip()
        if not p:
            continue
        low = p.lower()
        if low == "trim":
            ops["trim"] = True
        elif low == "upper":
            ops["upper"] = True
        elif low == "fulltohalf":
            ops["fullToHalf"] = True
        elif low.startswith("removesuffix"):
            inner = p[p.find("(") + 1: p.rfind(")")] if "(" in p and ")" in p else ""
            suffixes = [x.strip() for x in inner.split(",") if x.strip()]
            if suffixes:
                # 长后缀优先：否则「有限公司」会先被「公司」截成「…有限」
                ops["suffixes"] = sorted(suffixes, key=len, reverse=True)
    return ops


def normalize(value: str | None, ops: dict | None = None) -> str:
    """按匹配规则做标准化：全角转半角 → 去括号内容 → trim → upper → 去法律/组织后缀。"""
    ops = ops or parse_normalize_rule(None)
    s = _full_to_half(value or "") if ops.get("fullToHalf") else (value or "")
    s = _BRACKET_RE.sub("", s)
    if ops.get("trim", True):
        s = s.strip()
    if ops.get("upper", True):
        s = s.upper()
    for suf in ops.get("suffixes") or []:
        target = suf.upper() if ops.get("upper", True) else suf
        if target and s.endswith(target):
            s = s[: -len(target)].strip()
            break
    return s.strip()


def normalize_customer_name(name: str | None, ops: dict | None = None) -> str:
    """客户名称标准化（对齐 Java normalizeCustomerName）。"""
    return normalize(name, ops)


def normalize_address(address: str | None, ops: dict | None = None) -> str:
    """经营地址标准化：在通用规则之上再剔除空格与标点，便于省市门牌的近似比对。"""
    s = normalize(address, ops)
    return _ADDR_NOISE_RE.sub("", s)


def _bigrams(s: str) -> set[str]:
    return {s[i:i + 2] for i in range(len(s) - 1)}


def dice_similarity(a: str, b: str) -> float:
    """bigram Dice 相似度（0~1），对齐 Java diceSimilarity。"""
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    ba, bb = _bigrams(a), _bigrams(b)
    if not ba or not bb:
        return 0.0
    return (2.0 * len(ba & bb)) / (len(ba) + len(bb))


def similarity(a: str, b: str) -> float:
    """0~100 的相似度：相等 100，包含关系取 80 与 Dice 的较大者，其余按 Dice。"""
    if not a or not b:
        return 0.0
    if a == b:
        return 100.0
    if a in b or b in a:
        return max(80.0, dice_similarity(a, b) * 100)
    return dice_similarity(a, b) * 100


def score_candidate(new: dict, exist: dict, ops: dict,
                    suspect_threshold: float = DEFAULT_SUSPECT_THRESHOLD) -> tuple[float, dict, str]:
    """按「主依据 = 信用代码 + 经营地址，名称 = 辅助线索」计算匹配得分（0~100）。

    返回 (score, 字段贡献, 判定依据说明)。空值策略：主依据双方均无值可比时，
    名称作为唯一可用线索按 100% 权重兜底（否则两张都不填地址的申请永远无法查重）。
    """
    nc = normalize(new.get("credit_code"), ops)
    ec = normalize(exist.get("credit_code"), ops)
    na = normalize_address(new.get("address"), ops)
    ea = normalize_address(exist.get("address"), ops)
    nn = normalize_customer_name(new.get("legal_name"), ops)
    en = normalize_customer_name(exist.get("legal_name"), ops)

    c_credit = 100.0 if (nc and ec and nc == ec) else 0.0
    c_addr = similarity(na, ea)
    c_name = similarity(nn, en)

    comparable_primary = bool(nc and ec) or bool(na and ea)
    if not comparable_primary:
        # 空值策略：主依据缺失 → 名称兜底为主依据
        score, basis = c_name, "名称兜底（信用代码与经营地址双方均无值可比）"
    else:
        primary = max(c_credit, c_addr)
        score = W_PRIMARY * primary + W_AUX * c_name
        basis = "信用代码 + 经营地址为主依据，客户名称为辅助线索"
        if primary < PRIMARY_GATE and score >= suspect_threshold:
            # 名称仅作辅助线索：主依据都不像时不允许仅凭名称判重复
            score = suspect_threshold - 1.0
            basis = "主依据（信用代码/经营地址）相似度不足，客户名称仅作辅助线索，不单独判重复"

    contributions = {
        "信用代码": round(c_credit, 1),
        "经营地址": round(c_addr, 1),
        "客户名称": round(c_name, 1),
    }
    return round(score, 1), contributions, basis


async def load_match_rule(conn, scene: str = "CREATE") -> dict:
    """读取匹配规则（阈值 + 标准化策略）；无可用规则时用内置默认。"""
    fallback = {
        "rule_code": "DEFAULT",
        "exact": DEFAULT_EXACT_THRESHOLD,
        "suspect": DEFAULT_SUSPECT_THRESHOLD,
        "ops": parse_normalize_rule(DEFAULT_NORMALIZE_RULE),
    }
    try:
        t = table("match_rule")
        row = (await conn.execute(
            select(t)
            .where(t.c.scene == scene)
            .where(t.c.status == 1)
            .where(t.c.del_flag == "0")
            .order_by(t.c.order_num)
            .limit(1)
        )).mappings().first()
    except Exception:
        return fallback
    if not row:
        return fallback
    return {
        "rule_code": row.get("rule_code") or "DEFAULT",
        "exact": float(row.get("exact_threshold") or DEFAULT_EXACT_THRESHOLD),
        "suspect": float(row.get("suspect_threshold") or DEFAULT_SUSPECT_THRESHOLD),
        "ops": parse_normalize_rule(row.get("normalize_rule")),
    }


def _peer_from_master(row, score: float, contributions: dict, basis: str) -> dict:
    m = row._mapping
    return {
        "one_id": m["one_id"],
        "legal_name": m.get("legal_name"),
        "credit_code": m.get("credit_code"),
        "bu_scope": m.get("bu_scope"),
        "status": m.get("status"),
        "address": m.get("address"),
        "in_flight": False,
        "source": "MASTER",
        "score": score,
        "contributions": contributions,
        "basis": basis,
    }


async def duplicate_check(conn, credit_code: str | None, legal_name: str | None = None,
                          address: str | None = None, scene: str = "CREATE") -> dict:
    """重复核验：EXACT / SUSPECTED / NEW。

    peers 中 source=MASTER 表示命中已发布主档，source=IN_FLIGHT 表示命中在途申请。
    """
    rule = await load_match_rule(conn, scene)
    ops = rule["ops"]
    new = {"credit_code": credit_code, "legal_name": legal_name, "address": address}

    if not credit_code and not legal_name and not address:
        return {"match_state": "NEW", "duplicate_flag": "N", "peers": [],
                "score": 0.0, "rule": rule, "basis": "无匹配依据"}

    cust = table("cmd_customer")
    rows = (await conn.execute(
        select(cust.c.one_id, cust.c.legal_name, cust.c.credit_code,
               cust.c.bu_scope, cust.c.status, cust.c.address)
        .where(cust.c.status == "active")
        .where(cust.c.del_flag == "0")
        .order_by(desc(cust.c.create_time))
    )).all()

    # 1) 主依据优先：统一社会信用代码完全相同 → EXACT（文档『信用代码优先』）
    if credit_code:
        nc = normalize(credit_code, ops)
        for r in rows:
            ec = normalize(r._mapping.get("credit_code"), ops)
            if nc and ec and nc == ec:
                peer = _peer_from_master(r, 100.0, {
                    "信用代码": 100.0,
                    "经营地址": similarity(normalize_address(address, ops),
                                          normalize_address(r._mapping.get("address"), ops)),
                    "客户名称": similarity(normalize_customer_name(legal_name, ops),
                                          normalize_customer_name(r._mapping.get("legal_name"), ops)),
                }, "统一社会信用代码完全相同（主依据）")
                return {"match_state": "EXACT", "duplicate_flag": "Y", "peers": [peer],
                        "score": 100.0, "rule": rule, "basis": peer["basis"]}

    # 2) 加权匹配：经营地址为主依据，客户名称为辅助线索
    best: tuple[float, dict, dict, str] | None = None
    for r in rows:
        m = r._mapping
        score, contrib, basis = score_candidate(
            new,
            {"credit_code": m.get("credit_code"), "legal_name": m.get("legal_name"),
             "address": m.get("address")},
            ops, rule["suspect"],
        )
        if best is None or score > best[0]:
            best = (score, r, contrib, basis)
    if best:
        state = "EXACT" if best[0] >= rule["exact"] else (
            "SUSPECTED" if best[0] >= rule["suspect"] else "NEW")
        # 硬约束：双方信用代码都有值却不相等 → 是两个不同法人主体
        # （同址同名的总/分公司场景），最多只能判疑似，交由人工治理，绝不自动合并
        ec = normalize(best[1]._mapping.get("credit_code"), ops)
        nc = normalize(credit_code, ops)
        if state == "EXACT" and nc and ec and nc != ec:
            state = "SUSPECTED"
            best = (best[0], best[1], best[2],
                    "经营地址 / 名称高度相似，但双方信用代码不同（不同法人主体），需人工治理确认")
        if state in ("EXACT", "SUSPECTED"):
            peer = _peer_from_master(best[1], best[0], best[2], best[3])
            return {"match_state": state, "duplicate_flag": "Y", "peers": [peer],
                    "score": best[0], "rule": rule, "basis": best[3]}

    # 3) 同信用代码在途申请 → SUSPECTED + in_flight（上一单未审完时不判 NEW，
    #    否则两条申请各自审批通过会产生两个 One ID）
    if credit_code:
        app = table("cmd_customer_application")
        arows = (await conn.execute(
            select(app.c.one_id, app.c.legal_name, app.c.credit_code, app.c.bu_scope,
                   app.c.status, app.c.app_no, app.c.address)
            .where(app.c.credit_code == credit_code)
            .where(app.c.status.in_(["pending", "returned"]))
            .where(app.c.del_flag == "0")
            .order_by(desc(app.c.create_time))
        )).all()
        if arows:
            peers = []
            for r in arows:
                m = r._mapping
                peers.append({
                    "one_id": m["one_id"],
                    "legal_name": m.get("legal_name"),
                    "credit_code": m.get("credit_code"),
                    "bu_scope": m.get("bu_scope"),
                    "status": m.get("status"),
                    "address": m.get("address"),
                    "in_flight": True,
                    "source": "IN_FLIGHT",
                    "app_no": m.get("app_no"),
                    "score": 100.0,
                    "contributions": {"信用代码": 100.0, "经营地址": 0.0, "客户名称": 0.0},
                    "basis": "同一统一社会信用代码存在尚未审批完成的在途申请",
                })
            return {"match_state": "SUSPECTED", "duplicate_flag": "Y", "peers": peers,
                    "score": 100.0, "rule": rule, "basis": peers[0]["basis"]}

    return {"match_state": "NEW", "duplicate_flag": "N", "peers": [],
            "score": best[0] if best else 0.0, "rule": rule,
            "basis": (best[3] if best else "未命中任何已发布主档或在途申请")}

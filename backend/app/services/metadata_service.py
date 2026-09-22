"""元数据模型版本服务层。

对应 Java 端 CmdPlatformServiceImpl 中的版本域逻辑：
- selectVersionList()  → list_versions：从 md_field 按版本号分组推导 VO（不依赖登记表）
- createVersion()      → create_version：克隆当前已发布版本全部字段为一条新 Draft 版本
- publishVersion()     → publish_version：目标版本字段置发布、其余版本退役为 Draft

口径说明（与 Java 对齐）：
- 版本的「发布状态」实际记录在 md_field.status 上（0=已发布 / 1=Draft），
  md_model_version 仅作登记，不作为状态源。
- 版本 VO 的差异文本基于字段签名（fieldName|dataType|isRequired|valueSetCode|scopeType|ownerBu）
  与版本号顺序上的上一版本对比得出。
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from ..core.db import table
from ..core.query import dynamic_insert

# 核心主数据字段保护清单（对应 Java PROTECTED_FIELDS，field_code → 不可删原因）
PROTECTED_FIELDS = {
    "legal_name": "客户法定名称，主档主键属性",
    "credit_code": "总设计 DESIGN BOUNDARIES：主要匹配依据",
    "address": "总设计 DESIGN BOUNDARIES：主要匹配依据 + DQ 必评项",
    "province": "DQ 必评维度（地址）",
    "city": "DQ 必评维度（地址）",
    "contact_name": "DQ 必评维度（联系人）",
    "contact_phone": "DQ 必评维度（联系电话）",
    "customer_type": "主档必填属性（客户分层维度）",
    "bu_scope": "主档必填属性（数据权限维度）",
    "country": "主档必填属性",
    "status": "生命周期状态，逻辑停用依赖",
}


def protected_reason(field: Dict[str, Any]) -> Optional[str]:
    """字段「不可删原因」：保护清单优先，其次主键/匹配/DQ 标记（对应 Java protectedReason）。"""
    by_code = PROTECTED_FIELDS.get(field.get("field_code") or "")
    if by_code:
        return by_code
    if field.get("is_key_field") == "Y":
        return "已标记为主键字段 is_key_field=Y"
    if field.get("is_match_field") == "Y":
        return "已标记为匹配字段 is_match_field=Y"
    if field.get("is_dq_field") == "Y":
        return "已标记为 DQ 评分字段 is_dq_field=Y"
    return None


async def list_fields(conn, keyword: Optional[str] = None,
                      model_code: Optional[str] = None) -> List[Dict[str, Any]]:
    """字段目录：已删除不进目录，可选 keyword/model_code 过滤，回填 deleteGuard。"""
    f = table("md_field")
    q = select(f).where(f.c.del_flag == "0")
    if model_code not in (None, ""):
        q = q.where(f.c.model_code == model_code)
    if keyword not in (None, ""):
        like = f"%{keyword}%"
        q = q.where(f.c.field_code.like(like) | f.c.field_name.like(like))
    q = q.order_by(f.c.order_num)
    rows = [dict(r) for r in (await conn.execute(q)).mappings().all()]
    for r in rows:
        r["deleteGuard"] = protected_reason(r)
    return rows


async def delete_field(conn, field_id: int) -> None:
    """逻辑删除字段；核心主数据字段拒绝删除（对应 Java deleteField）。"""
    f = table("md_field")
    row = (await conn.execute(
        select(f).where(f.c.id == field_id))).mappings().first()
    if row is None:
        raise ValueError("字段不存在或已被删除")
    d = dict(row)
    guard = protected_reason(d)
    if guard:
        raise ValueError(f"「{d.get('field_name')}」是核心主数据字段（{guard}），不允许删除")
    await conn.execute(
        f.update().where(f.c.id == field_id).values(del_flag="1"))  # @TableLogic 等价：仅置 del_flag

# 字段签名参与对比的列（与 Java fieldSignatures 逐一对应）
_SIG_COLS = ("field_name", "data_type", "is_required", "value_set_code", "scope_type", "owner_bu")

_VERSION_RE = re.compile(r"v(\d+)\.(\d+)")


def _blank_to_default(v: Optional[str]) -> str:
    """Java StringUtils.blankToDefault 等价实现。"""
    return v if v not in (None, "") else ""


def field_signatures(fields: List[Dict[str, Any]]) -> Dict[str, str]:
    """字段签名：fieldCode → 属性拼接串，用于版本间差异对比。"""
    sig: Dict[str, str] = {}
    for f in fields:
        sig[f["field_code"]] = "|".join(_blank_to_default(f.get(c)) for c in _SIG_COLS)
    return sig


def next_version(current: Optional[str]) -> str:
    """生成下一个版本号：解析 v{major}.{minor}，minor+1；minor 越界(>9)则 major+1、minor 归零。"""
    major, minor = 1, 0
    if current:
        m = _VERSION_RE.search(current)
        if m:
            major, minor = int(m.group(1)), int(m.group(2))
    minor += 1
    if minor > 9:
        major, minor = major + 1, 0
    return f"v{major}.{minor}"


def _version_sort_key(version: str):
    """版本号排序键：v1.10 应排在 v1.9 之后，按数值比较。"""
    m = _VERSION_RE.search(version)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 0, 0


async def _load_fields_by_version(conn) -> Dict[str, List[Dict[str, Any]]]:
    """拉取全部字段（含软删行，与 Java 不过滤一致），按 version_no 分组、组内保持稳定顺序。"""
    f = table("md_field")
    rows = (await conn.execute(select(f).order_by(f.c.id))).mappings().all()
    by_version: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        d = dict(r)
        by_version.setdefault(_blank_to_default(d.get("version_no")) or "v1.0", []).append(d)
    return by_version


async def list_versions(conn) -> List[Dict[str, Any]]:
    """版本列表 VO：状态/差异/草稿创建时间/发布时间全部由 md_field 推导（对应 selectVersionList）。"""
    by_version = await _load_fields_by_version(conn)
    ordered = sorted(by_version.keys(), key=_version_sort_key)

    # 按版本号升序计算差异（第一个版本为基线）
    diff_text: Dict[str, str] = {}
    for i, version in enumerate(ordered):
        if i == 0:
            diff_text[version] = "基线"
            continue
        prev_sig = field_signatures(by_version[ordered[i - 1]])
        added = changed = 0
        for code, sig in field_signatures(by_version[version]).items():
            prev = prev_sig.get(code)
            if prev is None:
                added += 1
            elif prev != sig:
                changed += 1
        if added == 0 and changed == 0:
            diff_text[version] = "无变更"
        else:
            parts = []
            if added:
                parts.append(f"新增 {added}")
            if changed:
                parts.append(f"变更 {changed}")
            diff_text[version] = " · ".join(parts)

    fmt = "%Y-%m-%d %H:%M:%S"
    result: List[Dict[str, Any]] = []
    for version in ordered:
        fields = by_version[version]
        has_published = any(f.get("status") == "0" for f in fields)
        created = [f["create_time"] for f in fields if f.get("create_time")]
        published_at = [
            f["update_time"] for f in fields
            if f.get("status") == "0" and f.get("update_time")
        ]
        result.append({
            "version": version,
            "status": "Current" if has_published else "Draft",
            "diff": diff_text.get(version, "—"),
            "draftCreatedAt": min(created).strftime(fmt) if created else None,
            "publishedAt": max(published_at).strftime(fmt) if published_at else None,
        })

    # 稳定排序：Current 优先、组内版本号倒序（与 Java compareTo 降序一致，保证
    # current_published_version 取到最新的 Current，避免旧版本克隆撞唯一键）
    currents = sorted((v for v in result if v["status"] == "Current"),
                      key=lambda v: v["version"], reverse=True)
    drafts = sorted((v for v in result if v["status"] != "Current"),
                    key=lambda v: v["version"], reverse=True)
    return currents + drafts


async def current_published_version(conn) -> Optional[str]:
    """取当前已发布版本号（存在 status='0' 字段的版本）；无则取版本列表首个。"""
    versions = await list_versions(conn)
    if not versions:
        return None
    for vo in versions:
        if vo["status"] == "Current":
            return vo["version"]
    return versions[0]["version"]


async def create_version(conn) -> str:
    """基于当前已发布版本克隆出一条新 Draft 版本，返回新版本号（对应 createVersion）。"""
    f = table("md_field")
    source = await current_published_version(conn)
    if not source:
        # 无任何版本时兜底 v1.0（与 Java 一致）
        source = "v1.0"
    source_fields = (await conn.execute(
        select(f).where(f.c.version_no == source))).mappings().all()

    target = next_version(source)
    # 防御：目标版本号若已存在字段（历史脏数据），顺延版本号直到不与
    # uk_md_field(model_code, field_code, version_no) 冲突
    existing = set((await conn.execute(
        select(f.c.version_no).distinct())).scalars())
    while target in existing:
        target = next_version(target)
    # 克隆字段清单：与 Java createVersion 逐列对齐
    clone_cols = ("model_code", "field_code", "field_name", "field_name_en", "data_type",
                  "value_set_code", "default_value", "is_required", "is_unique",
                  "is_key_field", "is_match_field", "is_dq_field", "is_sensitive",
                  "is_physical", "physical_column", "min_length", "max_length",
                  "regex_pattern", "scope_type", "owner_bu", "order_num", "remark")
    now = datetime.now()
    for src in source_fields:
        payload = {c: src[c] for c in clone_cols if src.get(c) is not None}
        payload["version_no"] = target
        payload["status"] = "1"       # 新版本整体为 Draft
        payload["create_time"] = now  # 作为版本草稿创建时间
        await dynamic_insert(conn, f, payload)
    return target


async def publish_version(conn, version: Optional[str]) -> str:
    """发布目标版本：其余版本字段退役为 Draft（status='1'），目标版本全部置发布（status='0'）。

    对应 Java publishVersion；返回提示文案由路由层组装进 R.ok。
    """
    f = table("md_field")
    target = version if version not in (None, "") else await current_published_version(conn)
    if not target:
        raise ValueError("版本号不能为空")
    now = datetime.now()
    # 退役其余版本（保证单一 Current）
    await conn.execute(
        f.update().where(f.c.version_no != target)
        .values(status="1", update_time=now))
    # 发布目标版本全部字段
    await conn.execute(
        f.update().where(f.c.version_no == target)
        .values(status="0", update_time=now))
    return f"模型版本 {target} 已发布，其余版本已退役为 Draft"

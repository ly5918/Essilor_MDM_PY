"""流程定义部署 / 版本管理服务。

对应原 CmdFlowEngineServiceImpl.deployScene（Warm-Flow 定义登记 + 发布），
Python 侧引擎为 SpiffWorkflow：部署 = 将 BPMN 蓝图登记为一条版本记录
（cmd_flow_def_version），含 BPMN 哈希变更检测与幂等重部署：

- 首次部署：登记 v1.0（当前版本 status='0'），回写 cmd_flow_scene.definition_id；
- 重复部署（BPMN 未变化）：幂等返回现有版本，与 Java「已发布且完整 → 直接返回」一致；
- BPMN 变更后重部署：版本号 minor+1（v1.1 / v1.2 …），旧版本转为历史（status='1'）。
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime
from typing import Optional

from sqlalchemy import select

from ..core.db import get_engine, table
from ..core.query import dynamic_insert, dynamic_update

# BPMN 蓝图路径（与 workflow/engine.py 共用同一份）
BPMN_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "processes", "cmd_approval.bpmn"))


def _bpmn_snapshot() -> tuple[str, str]:
    """读取 BPMN 蓝图 → (xml 文本, sha256)。"""
    with open(BPMN_PATH, "rb") as f:
        raw = f.read()
    return raw.decode("utf-8"), hashlib.sha256(raw).hexdigest()


def _next_version(current: Optional[str]) -> str:
    """版本号进位：无当前版本 → v1.0；v1.N → v1.(N+1)；v9.9 → v2.0。"""
    if not current:
        return "v1.0"
    major, minor = current.lstrip("v").split(".")
    minor_num = int(minor) + 1
    if minor_num > 9:
        return f"v{int(major) + 1}.0"
    return f"v{major}.{minor_num}"


async def current_version(conn, scene_code: str) -> Optional[dict]:
    """查询场景当前部署版本（status='0'）。"""
    v = table("cmd_flow_def_version")
    row = (await conn.execute(
        select(v).where(v.c.scene_code == scene_code)
        .where(v.c.status == "0").where(v.c.del_flag == "0")
        .order_by(v.c.id.desc()))).mappings().first()
    return dict(row) if row else None


async def list_versions(conn, scene_code: str) -> list[dict]:
    """版本历史（倒序）：版本号 / 定义ID / 节点数 / 部署人 / 部署时间 / 状态。"""
    v = table("cmd_flow_def_version")
    rows = (await conn.execute(
        select(v.c.version_no, v.c.definition_id, v.c.node_count, v.c.bpmn_hash,
               v.c.status, v.c.deployed_by, v.c.deployed_at, v.c.remark)
        .where(v.c.scene_code == scene_code).where(v.c.del_flag == "0")
        .order_by(v.c.id.desc()))).mappings().all()
    return [dict(r) for r in rows]


async def deploy(scene_code: str, operator: str = "admin") -> dict:
    """部署场景到 SpiffWorkflow（幂等，按 BPMN 哈希检测变更）。

    返回 {definitionId, versionNo, created}：created=False 表示 BPMN 未变化、
    幂等复用现有版本（对齐 Java deployScene 的「已发布且完整 → 直接返回」分支）。
    """
    scene_t = table("cmd_flow_scene")
    engine = get_engine()
    async with engine.begin() as conn:
        scene = (await conn.execute(
            select(scene_t).where(scene_t.c.scene_code == scene_code))).mappings().first()
        if scene is None:
            raise ValueError(f"流程场景不存在：{scene_code}")
        flow_code = scene["flow_code"]
        xml, bpmn_hash = _bpmn_snapshot()

        cur = await current_version(conn, scene_code)
        if cur and cur.get("bpmn_hash") == bpmn_hash:
            # 幂等：蓝图未变化，直接复用现有版本
            return {"definitionId": cur["definition_id"], "versionNo": cur["version_no"],
                    "created": False}

        # BPMN 变化（或首次部署）：旧当前版本转历史，登记新版本
        if cur:
            v_t = table("cmd_flow_def_version")
            await conn.execute(v_t.update()
                               .where(v_t.c.scene_code == scene_code)
                               .where(v_t.c.status == "0")
                               .values(status="1", update_time=datetime.now()))

        from ..workflow.swimlane import build_swimlane
        node_count = len(build_swimlane(scene_code))
        version_no = _next_version(cur["version_no"] if cur else None)
        definition_id = f"{flow_code}#{version_no}"
        now = datetime.now()
        inserted = await dynamic_insert(conn, table("cmd_flow_def_version"), {
            "scene_code": scene_code, "flow_code": flow_code,
            "version_no": version_no, "definition_id": definition_id,
            "process_id": "cmd_approval", "node_count": node_count,
            "bpmn_hash": bpmn_hash, "bpmn_xml": xml, "status": "0",
            "deployed_by": operator, "deployed_at": now, "create_time": now,
            "remark": f"SpiffWorkflow 部署（{node_count} 节点）",
        })
        # 回写场景：definition_id 用版本记录数字主键（cmd_flow_scene 该列为 INT），
        # 展示层用版本表的 definition_id 字符串（flow_code#版本）
        await dynamic_update(conn, scene_t, scene["id"], {
            "definition_id": inserted["id"], "status": "0", "update_time": now,
        })
        return {"definitionId": definition_id, "versionNo": version_no, "created": True}

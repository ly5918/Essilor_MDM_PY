"""侧边导航角标 API。

返回**扁平键 = 菜单 id**（approval / batch），与前端 `badgeMap[menu.id]`
直接对应——此前返回嵌套对象（approval:{pending} 等），前端
`Number({pending:N})` 得 NaN，角标永不渲染（与 Java 侧同病）。

口径对齐 Java CmdNavServiceImpl.selectMenuBadges：
- approval：审批队列待办数（PENDING + RETURNED；bu→scope=BU，gc→scope=GC）
- batch：批量导入「待处置」任务数（WAIT_REVIEW / RUNNING / PARTIAL_SUCCESS）
- 无审批职责的角色（business/admin/audit）返回空对象 → 前端不渲染角标
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import select, func

from ..core.db import get_engine, table
from ..schemas import R
from ..services.import_service import PENDING_JOB_STATUSES

router = APIRouter(prefix="/cmd/nav", tags=["导航"])

# 审批队列「待办」口径：PENDING + RETURNED（与列表页 ALL 页签一致）
_OPEN_TASK_STATUSES = ("PENDING", "RETURNED")


@router.get("/badge")
async def nav_badge(role: str = Query("ALL")):
    """返回各菜单角标计数（扁平键 = 菜单 id，数字全部来自数据库实时聚合）。"""
    r = (role or "").strip().lower()
    if r not in ("bu", "gc"):
        # Business / Admin / Auditor 无审批职责：不给角标
        return R.ok({})

    task = table("cmd_approval_task")
    job = table("cmd_import_job")
    conn = await get_engine().connect()
    try:
        approval = (await conn.execute(
            select(func.count()).select_from(task).where(
                task.c.scope == r.upper(),
                task.c.status.in_(_OPEN_TASK_STATUSES),
                task.c.del_flag == "0"))).scalar() or 0
        batch = (await conn.execute(
            select(func.count()).select_from(job).where(
                job.c.job_status.in_(PENDING_JOB_STATUSES),
                job.c.del_flag == "0"))).scalar() or 0
    finally:
        await conn.close()
    return R.ok({"approval": int(approval), "batch": int(batch)})

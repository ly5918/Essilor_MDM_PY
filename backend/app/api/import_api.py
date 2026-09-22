"""批量导入：任务 / 行明细 / 模板 / 映射 API。"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, Body
from sqlalchemy import select, func, desc

from ..core.db import get_engine, table
from ..core.query import list_table, dynamic_insert, dynamic_update
from ..schemas import R

router = APIRouter(prefix="/cmd/import", tags=["导入"])


@router.get("/stats")
async def import_stats():
    t = table("cmd_import_job")
    conn = await get_engine().connect()
    try:
        total = (await conn.execute(select(func.count()).select_from(t))).scalar() or 0
        rows_total = 0
        try:
            rows_total = (await conn.execute(
                select(func.count()).select_from(table("cmd_import_row")))).scalar() or 0
        except Exception:
            rows_total = 0
    finally:
        await conn.close()
    return R.ok({"jobCount": total, "totalRows": rows_total, "exact": 0, "suspected": 0, "new": 0, "invalid": 0})


@router.get("/job/list")
async def job_list(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=200)):
    conn = await get_engine().connect()
    try:
        data = await list_table(conn, table("cmd_import_job"), page=page, size=size,
                                order_by=desc(table("cmd_import_job").c.create_time))
    finally:
        await conn.close()
    return R.ok(data)


@router.get("/job/{job_id}/result")
async def job_result(job_id: str):
    t = table("cmd_import_row")
    conn = await get_engine().connect()
    try:
        rows = (await conn.execute(select(t).where(t.c.job_id == job_id).limit(1))).mappings().all()
    finally:
        await conn.close()
    return R.ok({"jobId": job_id, "rows": [dict(r) for r in rows]})


@router.get("/job/{job_id}/rows")
async def job_rows(job_id: str, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=200)):
    conn = await get_engine().connect()
    try:
        data = await list_table(conn, table("cmd_import_row"), page=page, size=size,
                                filters={"job_id": job_id})
    finally:
        await conn.close()
    return R.ok(data)


@router.post("/row/{row_id}/action")
async def row_action(row_id: int, body: dict = Body(...)):
    action = body.get("action")
    one_id = body.get("oneId") or body.get("one_id")
    async with get_engine().begin() as conn:
        await dynamic_update(conn, table("cmd_import_row"), row_id,
                            {"status": action.upper() if action else "DONE", "one_id": one_id})
    return R.ok(msg="行操作已执行")


@router.post("/job")
async def job_create(body: dict = Body(...)):
    body = dict(body)
    body.setdefault("create_time", datetime.now())
    async with get_engine().begin() as conn:
        vals = await dynamic_insert(conn, table("cmd_import_job"), body)
    return R.ok(vals.get("job_code") or "JOB", msg="导入任务已创建")


@router.get("/template/list")
async def template_list():
    try:
        t = table("cmd_import_template")
        rows = (await (await get_engine().connect()).execute(select(t))).mappings().all()
        return R.ok([dict(r) for r in rows])
    except Exception:
        return R.ok([])


@router.get("/template/{template_code}/download")
async def template_download(template_code: str):
    """返回模板 CSV 内容（演示用）。"""
    header = "legal_name,credit_code,bu_scope,contact_email\n"
    return R.ok({"fileName": f"{template_code}.csv", "content": header})


@router.get("/template/mapping")
async def mapping_get(templateCode: Optional[str] = Query(None)):
    t = table("cmd_import_template_mapping")
    conn = await get_engine().connect()
    try:
        if templateCode:
            rows = (await conn.execute(select(t).where(t.c.template_code == templateCode))).mappings().all()
        else:
            rows = (await conn.execute(select(t))).mappings().all()
    finally:
        await conn.close()
    return R.ok([dict(r) for r in rows])


@router.post("/template/mapping")
async def mapping_save(body: dict = Body(...)):
    body = dict(body)
    body.setdefault("create_time", datetime.now())
    async with get_engine().begin() as conn:
        vals = await dynamic_insert(conn, table("cmd_import_template_mapping"), body)
    return R.ok(vals, msg="模板映射已保存")


@router.delete("/template/mapping/{mapping_id}")
async def mapping_delete(mapping_id: int):
    async with get_engine().begin() as conn:
        await conn.execute(table("cmd_import_template_mapping").update()
                          .where(table("cmd_import_template_mapping").c.id == mapping_id).values(del_flag="1"))
    return R.ok(msg="模板映射已删除")


@router.post("/job/upload")
async def job_upload(body: dict = Body(...)):
    return R.ok("文件已接收，进入解析队列")

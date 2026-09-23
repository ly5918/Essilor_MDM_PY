"""导入域 Router 层（对应 Java CmdImportController）。

只做 HTTP 关注点：参数解析、调用 import_service、包装 R.ok/R.fail、
文件上传/下载的 HTTP 细节（multipart / xlsx 流响应）。业务规则全部在 service。

事务约定：写操作统一经 _run_tx 在显式事务中执行——
业务错误（ImportBizError）回滚并翻译为 R.fail；其余异常原样抛出（全局 500 处理）。
"""
from __future__ import annotations

import io
from typing import Callable, Optional, Tuple

from fastapi import APIRouter, Body, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse

from ..core.db import get_engine
from ..repositories import import_repo
from ..schemas import R
from ..services import import_service
from ..services.import_service import ImportBizError

router = APIRouter(prefix="/cmd/import", tags=["导入"])


async def _run_tx(fn: Callable, *args, **kwargs) -> Tuple[object, Optional[str]]:
    """在事务中执行业务函数：成功 commit 返回 (result, None)；
    ImportBizError 回滚返回 (None, 错误文案)；其余异常回滚后原样抛出。"""
    engine = get_engine()
    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            result = await fn(conn, *args, **kwargs)
        except ImportBizError as e:
            await trans.rollback()
            return None, str(e)
        except Exception:
            await trans.rollback()
            raise
        else:
            await trans.commit()
            return result, None
        finally:
            await conn.close()


@router.get("/stats")
async def import_stats():
    """导入中心全局统计（服务端全量聚合，7 张 KPI 卡数据源）。"""
    conn = await get_engine().connect()
    try:
        stats = await import_service.get_job_stats(conn)
    finally:
        await conn.close()
    return R.ok({
        "jobCount": int(stats.get("job_count") or 0),
        "totalRows": int(stats.get("total_rows") or 0),
        "exactCount": int(stats.get("exact_count") or 0),
        "suspectedCount": int(stats.get("suspected_count") or 0),
        "newCount": int(stats.get("new_count") or 0),
        "reviewCount": int(stats.get("review_count") or 0),
        "invalidCount": int(stats.get("invalid_count") or 0),
    })


@router.get("/job/list")
async def job_list(pageNum: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=200),
                   jobStatusList: Optional[str] = Query(None)):
    """任务分页列表；jobStatusList 为逗号分隔状态聚合（「仅看待处置」口径）。"""
    status_list = [s.strip().upper() for s in jobStatusList.split(",") if s.strip()] \
        if jobStatusList else None
    conn = await get_engine().connect()
    try:
        data = await import_service.list_jobs(conn, pageNum, pageSize,
                                              job_status_list=status_list)
    finally:
        await conn.close()
    return R.ok(data)


@router.get("/job/{job_id}/result")
async def job_result(job_id: str):
    """任务分流结果（五分流 routes 卡 + 计数，前端 getBatchResult 数据源）。"""
    conn = await get_engine().connect()
    try:
        job = await import_service.get_job_or_fail(conn, job_id)
        vo = import_service.build_result_vo(job)
    except ImportBizError as e:
        return R.fail(str(e))
    finally:
        await conn.close()
    return R.ok(vo)


@router.get("/job/{job_id}/rows")
async def job_rows(job_id: str, resultType: Optional[str] = Query(None),
                   pageNum: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=200)):
    """行明细分页（分流下钻「查看 N 条」；job_id 为 jobCode，支持 resultType 过滤）。"""
    conn = await get_engine().connect()
    try:
        job = await import_service.get_job_or_fail(conn, job_id)
        rows = await import_repo.list_rows_by_job(conn, job["id"], result_type=resultType)
    except ImportBizError as e:
        return R.fail(str(e))
    finally:
        await conn.close()
    start = (pageNum - 1) * pageSize
    return R.ok({"rows": rows[start:start + pageSize], "total": len(rows)})


@router.post("/row/{row_id}/action")
async def row_action(row_id: int, body: dict = Body(...)):
    """行级治理：LINK 关联已有（跨BU自动升级 MERGE）/ EXCLUDE 排除 / RETURN 退回修复。"""
    message, err = await _run_tx(
        import_service.row_action, row_id, body.get("action") or "",
        body.get("oneId") or body.get("one_id"))
    if err:
        return R.fail(err)
    return R.ok(message, msg=message)


@router.post("/job")
async def job_create(body: dict = Body(...)):
    """新建导入任务（Java createJob：仅登记任务，不解析文件）。"""
    file_name = (body.get("fileName") or body.get("file_name") or "").strip()
    if not file_name:
        return R.fail("文件名不能为空")
    job_code, err = await _run_tx(import_service.create_job_registration,
                                  file_name=file_name, body=body)
    if err:
        return R.fail(err)
    return R.ok(job_code, msg="导入任务已创建")


@router.get("/template/list")
async def template_list(status: Optional[str] = Query(None)):
    """模板清单（Published/Draft + 字段数，前端下载模板弹窗数据源）。

    status=Published 只回已发布模板：业务侧（新建导入任务 / 下载模板）只能选已发布版本；
    平台管理的模板管理不传该参数，取全量以便编辑草稿。
    """
    conn = await get_engine().connect()
    try:
        rows = await import_service.list_templates(conn, status)
    finally:
        await conn.close()
    return R.ok(rows)


@router.get("/template/{template_code}/download")
async def template_download(template_code: str):
    """按字段映射动态生成「仅表头」xlsx（前端以 blob 下载真实文件）。"""
    conn = await get_engine().connect()
    try:
        template, wb = await import_service.build_template_workbook(conn, template_code)
    except ImportBizError as e:
        return R.fail(str(e))
    finally:
        await conn.close()
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{template_code}.xlsx"'})


@router.get("/template/mapping")
async def mapping_get(templateCode: Optional[str] = Query(None)):
    """字段映射清单（错误策略与必填同口径：必填→Reject Row / 选填→Warning Row）。"""
    conn = await get_engine().connect()
    try:
        rows = await import_service.list_mappings(conn, templateCode)
    finally:
        await conn.close()
    return R.ok(rows)


@router.post("/template/mapping")
async def mapping_save(body: dict = Body(...)):
    """新增/编辑上传字段（唯一性校验 + 主键保护；即时生效到下载/预检/行级DQ）。"""
    message, err = await _run_tx(import_service.save_mapping, body)
    if err:
        return R.fail(err)
    return R.ok(message, msg=message)


@router.delete("/template/mapping/{mapping_id}")
async def mapping_delete(mapping_id: int):
    """删除映射（主键字段拒绝删除）。"""
    message, err = await _run_tx(import_service.delete_mapping, mapping_id)
    if err:
        return R.fail(err)
    return R.ok(message, msg=message)


@router.post("/template")
async def template_save(body: dict = Body(...)):
    """新建 / 编辑导入模板（业务上下文：场景 / BU / 客户类型 / 产品线 / 来源系统）。

    全新部署（无模板数据）时管理员可直接在「平台管理 › 导入Template」建模板，
    不再依赖开发预置 SQL；模板编码留空时按业务上下文自动生成。
    """
    message, err = await _run_tx(import_service.save_template, body)
    if err:
        return R.fail(err)
    return R.ok(message, msg=message)


@router.post("/template/core-mapping")
async def template_fill_core_mapping(body: dict = Body(...)):
    """一键补齐主键字段映射（客户法定名称 / 统一社会信用代码）——发布的前置条件。

    新建模板已自动带上；此接口用于历史模板或列被删过的模板，避免手输字段编码。
    """
    message, err = await _run_tx(
        import_service.fill_core_mappings,
        template_code=(body.get("templateCode") or body.get("template_code") or ""))
    if err:
        return R.fail(err)
    return R.ok(message, msg=message)


@router.post("/template/status")
async def template_status(body: dict = Body(...)):
    """发布 / 停用导入模板（发布前后端校验主键字段映射 legal_name / credit_code）。"""
    message, err = await _run_tx(
        import_service.set_template_status,
        template_code=(body.get("templateCode") or body.get("template_code") or ""),
        status=(body.get("status") or ""))
    if err:
        return R.fail(err)
    return R.ok(message, msg=message)


@router.post("/job/upload")
async def job_upload(file: UploadFile = File(...),
                     templateCode: str = Form(...),
                     errorStrategy: Optional[str] = Form(None),
                     duplicateStrategy: Optional[str] = Form(None),
                     scene: Optional[str] = Form(None),
                     buScope: Optional[str] = Form(None),
                     sourceSystem: Optional[str] = Form(None)):
    """上传主流程：预检 → 四类分流 → 提交审批（文件级预检不过整批退回）。"""
    file_bytes = await file.read()
    result, err = await _run_tx(
        import_service.create_job_from_upload,
        template_code=templateCode, file_name=file.filename or "upload.xlsx",
        file_bytes=file_bytes, error_strategy=errorStrategy,
        duplicate_strategy=duplicateStrategy, scene=scene, bu_scope=buScope,
        source_system=sourceSystem)
    if err:
        return R.fail(err)
    # create_job_from_upload 返回 (job_code, result_vo)；按前端契约只回 jobCode，
    # 分流结果走 GET /job/{id}/result。
    job_code = result[0] if isinstance(result, tuple) else result
    return R.ok(job_code, msg="导入任务已创建")


# ============================ 兼容别名 ============================
# 早期联调脚本 / 旧前端构建会用 /cmd/template/list 读模板清单（真实路径为
# /cmd/import/template/list）。保留一个只读别名，避免联调时把它误判成 404。
compat_router = APIRouter(prefix="/cmd", tags=["导入"], include_in_schema=False)


@compat_router.get("/template/list")
async def template_list_compat(status: Optional[str] = Query(None)):
    """兼容别名：等价于 GET /cmd/import/template/list（同样支持 status 过滤）。"""
    return await template_list(status)

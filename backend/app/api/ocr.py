"""OCR 识别 API（Router 层，薄 HTTP 壳）— 识别逻辑在 services/ocr_service.py。

与 Java 版 CmdOcrController 对齐：
- POST /cmd/ocr/recognize：识别营业执照，返回执照原件信息 + 字段识别值，
  纯预置结果、**不落库**（cmd_ocr_result 为空是 POC 预期行为）。
- GET /cmd/ocr/results、PUT /cmd/ocr/result/{id}/confirm：识别结果查询 / 人工确认
  （预留的真实 OCR 落库链路，status 列为 char(1)，取值 0正常 / 1停用）。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from ..core.db import get_engine, table
from ..core.query import dynamic_update
from ..schemas import R
from ..services import ocr_service

router = APIRouter(prefix="/cmd/ocr", tags=["OCR"])


class RecognizeReq(BaseModel):
    """识别入参：前端传 {fileName}，SnakeCaseBodyMiddleware 会补 file_name 别名。"""

    attachment_id: Optional[int] = None
    biz_id: Optional[str] = None
    file_name: Optional[str] = None


@router.post("/recognize")
async def recognize(payload: Optional[RecognizeReq] = None):
    """识别营业执照（文件名可为空 → 返回默认演示识别结果，与 Java 版一致）。"""
    file_name = payload.file_name if payload is not None else None
    return R.ok(ocr_service.recognize(file_name), msg="OCR 识别完成")


@router.get("/results")
async def ocr_results(bizId: Optional[str] = Query(None), page: int = Query(1, ge=1),
                      size: int = Query(20, ge=1, le=200)):
    """识别结果分页查询（真实 OCR 落库后的数据链路，POC 阶段通常为空）。"""
    conn = await get_engine().connect()
    try:
        stmt = select(table("cmd_ocr_result")).where(table("cmd_ocr_result").c.del_flag == "0")
        if bizId:
            stmt = stmt.where(table("cmd_ocr_result").c.biz_id == bizId)
        total = (await conn.execute(select(func.count()).select_from(
            table("cmd_ocr_result")).where(table("cmd_ocr_result").c.del_flag == "0"))).scalar() or 0
        rows = (await conn.execute(stmt.limit(size).offset((page - 1) * size))).mappings().all()
    finally:
        await conn.close()
    return R.ok({"total": int(total), "rows": [dict(r) for r in rows]})


class ConfirmReq(BaseModel):
    confirmed_value: str


@router.put("/result/{result_id}/confirm")
async def confirm_result(result_id: int, payload: ConfirmReq):
    """人工确认识别结果（status 为 char(1)：0正常 1停用；needs_review 置 N 表示已复核）。"""
    async with get_engine().begin() as conn:
        await dynamic_update(conn, table("cmd_ocr_result"), result_id, {
            "confirmed_value": payload.confirmed_value,
            "status": "0",
            "reviewed_by": 1,
            "reviewed_time": datetime.now(),
            "needs_review": "N",
        })
    return R.ok(msg="识别结果已确认")

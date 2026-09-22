"""OCR 识别 API（cmd_ocr_result）— 与原系统一致，模拟识别并落库供确认。"""
from __future__ import annotations

import json
import random
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select

from ..core.db import get_engine, table
from ..core.query import dynamic_insert, dynamic_update
from ..schemas import R

router = APIRouter(prefix="/cmd/ocr", tags=["OCR"])

# 营业执照字段 → 模拟识别结果
_MOCK_FIELDS = [
    ("legal_name", "企业名称", 0.97),
    ("credit_code", "统一社会信用代码", 0.95),
    ("legal_name_en", "英文名称", 0.88),
    ("registered_address", "注册地址", 0.90),
    ("legal_representative", "法定代表人", 0.93),
]


class RecognizeReq(BaseModel):
    attachment_id: Optional[int] = None
    biz_id: Optional[str] = None
    file_name: Optional[str] = None


@router.post("/recognize")
async def recognize(payload: RecognizeReq):
    results = []
    async with get_engine().begin() as conn:
        for field_code, field_name, base_conf in _MOCK_FIELDS:
            conf = round(min(0.99, base_conf + random.uniform(-0.03, 0.03)), 2)
            vals = await dynamic_insert(conn, table("cmd_ocr_result"), {
                "attachment_id": payload.attachment_id,
                "biz_id": payload.biz_id,
                "field_code": field_code,
                "field_name": field_name,
                "ocr_value": f"{field_name}-OCR样例",
                "confidence": conf,
                "needs_review": "N" if conf >= 0.9 else "Y",
                "ocr_engine": "MOCK-ENGINE",
                "raw_json": json.dumps({"field": field_code, "conf": conf}, ensure_ascii=False),
                "status": "PENDING_REVIEW",
            })
            results.append({"id": vals.get("id"), "fieldCode": field_code,
                            "fieldName": field_name, "ocrValue": vals.get("ocr_value"),
                            "confidence": conf, "needsReview": vals.get("needs_review")})
    return R.ok(results, msg="OCR 识别完成")


@router.get("/results")
async def ocr_results(bizId: Optional[str] = Query(None), page: int = Query(1, ge=1),
                      size: int = Query(20, ge=1, le=200)):
    conn = await get_engine().connect()
    try:
        stmt = select(table("cmd_ocr_result")).where(table("cmd_ocr_result").c.del_flag == "0")
        if bizId:
            stmt = stmt.where(table("cmd_ocr_result").c.biz_id == bizId)
        from sqlalchemy import func
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
    async with get_engine().begin() as conn:
        await dynamic_update(conn, table("cmd_ocr_result"), result_id, {
            "confirmed_value": payload.confirmed_value,
            "status": "CONFIRMED",
            "reviewed_by": 1,
            "reviewed_time": datetime.now(),
            "needs_review": "N",
        })
    return R.ok(msg="识别结果已确认")

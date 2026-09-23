"""FastAPI 应用入口：复用现有 ruoyi_plus 数据库，SpiffWorkflow 驱动审批流。

合同兼容层（对齐 Java 版 RuoYi 的序列化口径）：
- 响应：所有 JSON key 由 snake_case 转 camelCase（Java VO 序列化行为）。
- 请求体：前端发 camelCase JSON，为每个 key 额外补一份 snake_case 别名
  （原 key 保留，Pydantic 模型按 snake_case 字段名取值）。
"""
from __future__ import annotations

import json
import re
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from .core.db import init_db
from .api import (
    customer, approval, dashboard, metadata as metadata_api, duplication,
    change, governance, nav, flow, oneid, dq, match_api, import_api,
    hierarchy, audit, permission, coverage, ocr, integration,
)

_CAMEL_1 = re.compile(r"_([a-zA-Z])")
_CAMEL_2 = re.compile(r"_([0-9])")


def _to_camel(key: str) -> str:
    """one_id -> oneId；dq_score_100 -> dqScore100；已是 camelCase 的 key 原样返回。"""
    if "_" not in key:
        return key
    head, *rest = key.split("_")
    return head + "".join(w[:1].upper() + w[1:] for w in rest if w)


def _to_snake(key: str) -> str:
    """legalName -> legal_name；已是 snake_case 的 key 原样返回。"""
    if "_" in key or not re.search(r"[A-Z]", key):
        return key
    return re.sub(r"(?<=[a-z0-9])([A-Z])", lambda m: "_" + m.group(1).lower(), key)


def _convert_keys(obj: Any, fn) -> Any:
    if isinstance(obj, dict):
        return {fn(str(k)): _convert_keys(v, fn) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_keys(v, fn) for v in obj]
    return obj


# JS Number.MAX_SAFE_INTEGER：超过此范围的整数（19 位雪花 id）在浏览器 JSON.parse 时
# 会丢失精度（如 ...030 被 parse 成 ...000），前端拿它回传（删除/详情/审批动作）就会打错行。
# Java 端 RuoYi-Vue-Plus 的 BigNumberSerializer 对超范围 Long 按字符串下发，这里对齐该口径。
_JS_SAFE_MAX = 2 ** 53 - 1


def _serialize_compat(obj: Any) -> Any:
    """camelCase key 转换 + 超出 JS 安全范围的整数转字符串，单次遍历完成。"""
    if isinstance(obj, dict):
        return {_to_camel(str(k)): _serialize_compat(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_compat(v) for v in obj]
    if isinstance(obj, int) and not isinstance(obj, bool) and abs(obj) > _JS_SAFE_MAX:
        return str(obj)
    return obj


class CamelCaseResponseMiddleware(BaseHTTPMiddleware):
    """把 JSON 响应体的 key 统一转成 camelCase（对齐 Java 后端）。"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        ctype = response.headers.get("content-type", "")
        if "application/json" not in ctype:
            return response
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        try:
            data = json.loads(body)
            new_body = json.dumps(
                _serialize_compat(data),
                ensure_ascii=False, default=str,
            ).encode("utf-8")
        except Exception:
            return Response(
                content=body, status_code=response.status_code,
                media_type=response.media_type or "application/json",
                headers={k: v for k, v in response.headers.items()
                         if k.lower() not in ("content-length",)},
            )
        headers = {k: v for k, v in response.headers.items()
                   if k.lower() not in ("content-length",)}
        return Response(
            content=new_body, status_code=response.status_code,
            media_type="application/json", headers=headers,
        )


class QueryAliasMiddleware(BaseHTTPMiddleware):
    """查询参数别名：前端统一发 pageNum/pageSize，后端签名是 page/size，这里改写 query_string。"""

    _ALIASES = {b"pageNum": b"page", b"pageSize": b"size"}

    async def dispatch(self, request: Request, call_next):
        qs = request.scope.get("query_string", b"")
        if qs:
            pairs = []
            changed = False
            for pair in qs.split(b"&"):
                k, _, v = pair.partition(b"=")
                if k in self._ALIASES:
                    pairs.append(self._ALIASES[k] + b"=" + v)
                    changed = True
                else:
                    pairs.append(pair)
            if changed:
                request.scope["query_string"] = b"&".join(pairs)
        return await call_next(request)


class SnakeCaseBodyMiddleware(BaseHTTPMiddleware):
    """请求体 JSON key：保留原 key，同时补 snake_case 别名，两种风格都能命中。"""

    async def dispatch(self, request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            ctype = request.headers.get("content-type", "")
            if "application/json" in ctype:
                raw = await request.body()
                try:
                    data = json.loads(raw) if raw else None
                except Exception:
                    data = None
                if isinstance(data, (dict, list)):
                    converted = _convert_keys(data, _to_snake)
                    if isinstance(data, dict) and isinstance(converted, dict):
                        merged = {**converted, **data}
                        new_raw = json.dumps(merged, ensure_ascii=False, default=str).encode("utf-8")
                    else:
                        new_raw = json.dumps(converted, ensure_ascii=False, default=str).encode("utf-8")
                    # 替换请求体供后续 handler 读取
                    request._body = new_raw  # noqa: SLF001
        return await call_next(request)


app = FastAPI(title="Essilor CMD POC (Python)", version="1.0.0")

app.add_middleware(CamelCaseResponseMiddleware)
app.add_middleware(SnakeCaseBodyMiddleware)
app.add_middleware(QueryAliasMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

for _m in (customer, approval, dashboard, metadata_api, duplication, change,
           governance, nav, flow, oneid, dq, match_api, import_api,
           hierarchy, audit, permission, coverage, ocr, integration):
    app.include_router(_m.router)

# 兼容别名路由（如 /cmd/template/list → /cmd/import/template/list），不进入 OpenAPI 文档
if getattr(import_api, "compat_router", None) is not None:
    app.include_router(import_api.compat_router)


@app.on_event("startup")
async def _startup():
    await init_db()


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    from .core.config import settings
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=False)

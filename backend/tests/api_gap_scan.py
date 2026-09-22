# -*- coding: utf-8 -*-
"""前端 API 调用 vs 后端路由 全量差集：找出前端调用但后端缺失/方法不匹配的接口"""
import re, sys, json

sys.path.insert(0, r"D:/Code/2026AI/AIA_MDM/Essilor_MDM_PY/backend")
FE = "D:/Code/2026AI/AIA_MDM/Essilor_MDM_PY/frontend/src/api/demo/cmdPoc/index.ts"
t = open(FE, encoding="utf-8").read()

# ---- 1. 前端全部请求：method + url 模板 ----
calls = {}
# request({ url: '...', method: 'get'|'post', data/params ... })
for m in re.finditer(r"request\(\{[^}]*?url:\s*'([^']+)'[^}]*?method:\s*'(\w+)'", t, re.S):
    url, method = m.group(1), m.group(2).lower()
    calls.setdefault(url, set()).add(method)
# 反向：method 在前 url 在后
for m in re.finditer(r"request\(\{[^}]*?method:\s*'(\w+)'[^}]*?url:\s*'([^']+)'", t, re.S):
    url, method = m.group(2), m.group(1).lower()
    calls.setdefault(url, set()).add(method)
# 还有模板字符串 url: `/xxx/${...}`
for m in re.finditer(r"url:\s*`([^`]+)`", t):
    url = m.group(1)
    url_norm = re.sub(r"\$\{[^}]+\}", "{var}", url)
    # method 猜测：getBy 默认 get；找同一函数上下文
    seg = t[max(0, m.start()-300):m.start()]
    mm = re.search(r"method:\s*'(\w+)'", seg)
    method = mm.group(1).lower() if mm else "get"
    calls.setdefault(url_norm, set()).add(method)

# ---- 2. 后端全部路由（经 OpenAPI）----
import asyncio
from httpx import AsyncClient, ASGITransport

async def _routes():
    from app.core import db
    await db.init_db()
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/openapi.json")
        return r.json()["paths"]

spec = asyncio.run(_routes())
backend = set()  # (method, path)
for path, ops in spec.items():
    if not path.startswith("/cmd"):
        continue
    for me in ops:
        if me in ("get", "post", "put", "delete", "patch"):
            backend.add((me, path))

def match(fe_url, method):
    """把前端 url 模板与后端路由匹配"""
    fe_pat = re.sub(r"\{[^}]+\}", "{var}", fe_url)
    fe_pat = re.sub(r"\$\{[^}]+\}", "{var}", fe_pat)
    for bm, bp in backend:
        bp_pat = re.sub(r"\{[^}]+\}", "{var}", bp)
        if bp_pat == fe_pat and bm == method:
            return True
        # 前端无参数占位但后端有路径参数（如前端 /cmd/hierarchy/node/CODE）粗匹配已覆盖
    return False

missing = []
for url, methods in sorted(calls.items()):
    for me in sorted(methods):
        if not match(url, me):
            missing.append((me.upper(), url))

print("frontend call urls:", len(calls))
print("backend /cmd routes:", len(backend))
print("\n=== MISSING / MISMATCH ===")
for me, url in missing:
    print(f"  {me:6} {url}")

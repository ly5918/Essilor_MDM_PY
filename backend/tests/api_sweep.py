"""全端点扫描：覆盖前端调用的 /cmd/** 端点（GET 为主 + 关键 POST），验证 R 信封 code==200。"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from httpx import AsyncClient, ASGITransport  # noqa: E402


GETS = [
    "/cmd/dashboard/stats",
    "/cmd/dashboard/notifications",
    "/cmd/customer/list",
    "/cmd/customer/stats",
    "/cmd/customer/application/list",
    "/cmd/customer/application/stats",
    "/cmd/approval/list",
    "/cmd/approval/stats",
    "/cmd/approval/kpi",
    "/cmd/approval/instance/list",
    "/cmd/approval/workflow-steps?taskNo=AP-20260922-0025",
    "/cmd/change/list",
    "/cmd/change/kpi",
    "/cmd/change/fields",
    "/cmd/governance/list",
    "/cmd/governance/stats",
    "/cmd/metadata/field/list",
    "/cmd/metadata/valueset/list",
    "/cmd/metadata/version/list",
    "/cmd/dq/rule/list",
    "/cmd/dq/scorecard",
    "/cmd/match/rule/list",
    "/cmd/nav/badge",
    "/cmd/flow/scenes",
    "/cmd/flow/instances",
    "/cmd/oneid/rule",
    "/cmd/oneid/policy/list",
    "/cmd/oneid/legacy/list",
    "/cmd/import/stats",
    "/cmd/import/job/list",
    "/cmd/import/template/list",
    "/cmd/import/template/mapping",
    "/cmd/hierarchy/nodes",
    "/cmd/hierarchy/roots",
    "/cmd/hierarchy/unassigned",
    "/cmd/hierarchy/relationHistory",
    "/cmd/audit/list",
    "/cmd/permission/matrix",
    "/cmd/permission/role/list",
    "/cmd/coverage/list",
    "/cmd/integration/endpoint/list",
    "/cmd/integration/run/list",
    "/cmd/integration/message/list",
]

POSTS = [
    ("/cmd/dq/simulate", {"fields": ["legal_name", "credit_code"]}),
    ("/cmd/dq/reEvaluate", {}),
    ("/cmd/match/simulate", {"legalName": "南京视界"}),
    ("/cmd/hierarchy/validate", {"parentOneId": "GC-6021C90C", "childOneId": "GC-D46D0939"}),
    ("/cmd/hierarchy/loopCheck", None),
]


async def main():
    from app.core import db
    await db.init_db()

    ok, bad = 0, []
    transport = ASGITransport(app=app)  # noqa: F821
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        for path in GETS:
            try:
                r = await c.get(path)
                body = r.json()
                if r.status_code == 200 and str(body.get("code")) in ("200", "0"):
                    ok += 1
                else:
                    bad.append(("GET", path, r.status_code, str(body)[:200]))
            except Exception as ex:
                bad.append(("GET", path, "EXC", f"{type(ex).__name__}: {str(ex)[:150]}"))

        for path, payload in POSTS:
            try:
                if payload is None:
                    r = await c.get(path)
                else:
                    r = await c.post(path, json=payload)
                body = r.json()
                if r.status_code == 200 and str(body.get("code")) in ("200", "0"):
                    ok += 1
                else:
                    bad.append(("POST", path, r.status_code, str(body)[:200]))
            except Exception as ex:
                bad.append(("POST", path, "EXC", f"{type(ex).__name__}: {str(ex)[:150]}"))

    print(f"SWEEP OK: {ok} endpoints passed")
    for b in bad:
        print("FAIL:", *b)
    print("ALL SWEEP CHECKS PASSED ✅" if not bad else f"{len(bad)} FAILURES")


if __name__ == "__main__":
    from app.main import app
    asyncio.run(main())

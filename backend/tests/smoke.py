"""端到端集成测试：通过 ASGITransport 在进程内驱动 FastAPI 应用，
绕过沙箱网络代理（仅放行 GET），完整覆盖 路由→服务→SpiffWorkflow→MySQL。
"""
import asyncio
import sys
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, "D:/Code/2026AI/AIA_MDM/Essilor_MDM_PY/backend")
from app.main import app  # noqa: E402
from app.core.db import init_db  # noqa: E402

BASE = "http://test"


async def approve_until_done(c, task_no, actors=("bu1", "gc1")):
    """持续推进审批流直到 COMPLETED（统一流程可能需 BU、GC 两步）。"""
    last = None
    for i in range(5):
        r = await c.post("/cmd/approval/action",
                         json={"taskNo": task_no, "action": "approve", "actor": actors[i % len(actors)]})
        j = r.json()
        if j["code"] != 200:
            print("  approve error:", j); break
        print("  approve:", j["data"])
        last = j
        if j["data"]["status"] == "COMPLETED":
            return j
    return last


async def main():
    await init_db()  # 触发表反射（ASGITransport 不会自动跑 startup 事件）
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        r = await c.get("/health"); print("health:", r.json())

        r = await c.get("/cmd/metadata/field/list"); print("metadata fields:", len(r.json()["data"] or []), "fields")

        payload = {"legal_name": "Python重建测试客户A", "credit_code": "PYTEST0001XYZ",
                   "bu_scope": "High End", "cross_bu": False, "contact_email": "a@test.com"}
        r = await c.post("/cmd/customer", json=payload); j = r.json()
        print("submit:", j["code"], j.get("data"))
        assert j["code"] == 200, j
        app_no = j["data"]["appNo"]; one_id = j["data"]["oneId"]

        r = await c.get("/cmd/approval/list", params={"size": 200}); tasks = r.json()["data"]["rows"]
        print("approval pending total:", r.json()["data"]["total"], "| our task present:", any(t["taskNo"] == app_no for t in tasks))

        r = await c.post("/cmd/approval/action", json={"taskNo": app_no, "action": "approve", "actor": "bu1"})
        print("approve:", r.json()["data"])
        assert r.json()["data"]["status"] == "COMPLETED"
        assert r.json()["data"]["outcome"] == "approved"

        r = await c.get(f"/cmd/customer/oneId/{one_id}"); cust = r.json()["data"]
        print("golden record status:", cust["status"], "| one_id:", cust["oneId"])
        assert cust["status"] == "active"

        r = await c.get("/cmd/duplication/candidate", params={"creditCode": "PYTEST0001XYZ"})
        print("dup candidate:", r.json()["data"])

        r = await c.post("/cmd/customer", json={"legal_name": "Python重建测试客户B", "credit_code": "PYTEST0001XYZ", "bu_scope": "High End"})
        print("dup submit:", r.json()["data"]["matchState"], r.json()["data"]["duplicateFlag"])
        assert r.json()["data"]["matchState"] in ("SUSPECTED", "EXACT")

        r0 = await c.get("/cmd/customer/list"); survivor = r0.json()["data"]["rows"][0]["oneId"]
        r = await c.post("/cmd/governance/merge", json={"survivorOneId": survivor, "mergedOneId": one_id})
        mno = r.json()["data"]["mergeApprovalNo"]; print("merge launched:", r.json()["data"])
        r = await approve_until_done(c, mno)
        assert r["data"]["status"] == "COMPLETED"

        r = await c.get(f"/cmd/customer/oneId/{one_id}"); print("merged record status:", r.json()["data"]["status"])
        assert r.json()["data"]["status"] == "inactive"

        r = await c.post("/cmd/change", json={"one_id": survivor, "change_type": "UPDATE", "change_reason": "test"})
        chg = r.json()["data"]["requestCode"]; print("change submitted:", chg)
        r = await approve_until_done(c, chg)
        assert r["data"]["status"] == "COMPLETED"

        r = await c.get("/cmd/dashboard/stats"); print("dashboard:", r.json()["data"])

        print("\nALL SMOKE CHECKS PASSED ✅")


asyncio.run(main())

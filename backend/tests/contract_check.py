# 验证合同兼容层：camelCase 响应 / rows+total 分页 / pageNum+pageSize 入参 / 关键端点契约
import asyncio
import sys

sys.path.insert(0, 'D:/Code/2026AI/AIA_MDM/Essilor_MDM_PY/backend')
from httpx import AsyncClient, ASGITransport

NOISE_SUB = None


async def main():
    from app.core import db
    await db.init_db()
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://t') as c:
        # 1. camelCase + rows/total + pageNum/pageSize
        r = await c.get('/cmd/customer/list', params={'pageNum': 1, 'pageSize': 3})
        j = r.json()
        d = j.get('data') or {}
        row0 = (d.get('rows') or [{}])[0]
        print('customer/list keys ok:',
              'rows' in d, 'total' in d,
              'oneId' in row0, 'legalName' in row0, 'buScope' in row0,
              '| total =', d.get('total'), '| rows =', len(d.get('rows') or []))

        # 2. stats 契约（CustomerStats）
        r = await c.get('/cmd/customer/stats')
        s = r.json()['data']
        print('customer/stats:', {k: s.get(k) for k in
              ('total', 'activeCount', 'pendingCount', 'crossBuCount', 'duplicateCount', 'avgDqScore')})

        # 3. approval list（scope/taskCategory/pageNum）+ dupPeerInFlight
        r = await c.get('/cmd/approval/list',
                        params={'scope': 'BU', 'taskCategory': 'ALL', 'pageNum': 1, 'pageSize': 5})
        d = r.json()['data']
        row0 = (d.get('rows') or [{}])[0]
        print('approval/list total =', d.get('total'),
              '| taskNo =', row0.get('taskNo'),
              '| dupPeerInFlight =', row0.get('dupPeerInFlight'))

        # 4. approval stats（myTodo 口径）
        r = await c.get('/cmd/approval/stats')
        print('approval/stats:', r.json()['data'])

        # 5. kpi 数组契约
        r = await c.get('/cmd/approval/kpi', params={'scope': 'BU'})
        k = r.json()['data']
        print('approval/kpi is array:', isinstance(k, list), '| first =', k[0] if k else None)

        # 6. application list（toApplicationVO 契约）
        r = await c.get('/cmd/customer/application/list', params={'pageNum': 1, 'pageSize': 3})
        d = r.json()['data']
        row0 = (d.get('rows') or [{}])[0]
        print('application/list total =', d.get('total'),
              '| appNo =', row0.get('appNo'),
              '| taskNo =', row0.get('taskNo'),
              '| currentNodeName =', row0.get('currentNodeName'))

        # 7. dashboard stats（camelCase）
        r = await c.get('/cmd/dashboard/stats')
        s = r.json()['data']
        print('dashboard/stats:', {k: s.get(k) for k in ('customerTotal', 'customerActive', 'customerPending')})

        # 8. 通知
        r = await c.get('/cmd/dashboard/notifications')
        n = r.json()['data']
        row0 = (n or [{}])[0] if isinstance(n, list) else {}
        print('notifications is array:', isinstance(n, list),
              '| keys:', sorted(row0.keys())[:8] if row0 else 'EMPTY')

        # 9. POST 请求体 camelCase（提交客户）
        r = await c.post('/cmd/customer', json={
            'legalName': '合同层验证客户', 'creditCode': '91320100TESTCONTRACT01',
            'customerType': '直供', 'customerLevel': 'A1', 'productLine': '镜架',
            'buScope': 'High End', 'gcScopeFlag': 'N', 'country': '中国',
            'province': '江苏省', 'city': '南京市', 'address': '合同层测试地址',
            'contactName': '测试联系人', 'contactPhone': '13800000000',
            'contactEmail': 't@t.com', 'sourceSystem': 'MANUAL',
        })
        body = r.json()
        print('submit customer (camel body):', 'code =', body.get('code'), '| msg =', body.get('msg'))
        submitted = (body.get('data') or {})
        print('  -> appNo =', submitted.get('appNo'), '| oneId =', submitted.get('oneId'),
              '| matchState =', submitted.get('matchState'))

        # 10. 审批动作（body camel: taskNo/action/actor）
        app_no = submitted.get('appNo')
        if app_no:
            r = await c.post('/cmd/approval/action', json={'taskNo': app_no, 'action': 'approve',
                                                           'actor': 'bu1', 'opinion': '合同层验证'})
            print('approval action (camel body):', 'code =', r.json().get('code'),
              '| status =', (r.json().get('data') or {}).get('status'))


asyncio.run(main())

"""流程中心端点验证：scenes / instances / graph / trace / workflow-steps。"""
import asyncio
import sys

sys.path.insert(0, 'D:/Code/2026AI/AIA_MDM/Essilor_MDM_PY/backend')
from httpx import AsyncClient, ASGITransport


async def main():
    from app.core import db
    await db.init_db()
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://t') as c:
        # 1. 场景列表
        r = await c.get('/cmd/flow/scenes')
        scenes = r.json()['data']
        print('scenes:', len(scenes), '| first:', {k: scenes[0].get(k) for k in
              ('sceneCode', 'sceneName', 'flowCode', 'deployed', 'nodeCount')} if scenes else None)

        # 2. 实例列表（RUNNING / DONE）
        for run in ('RUNNING', 'DONE', None):
            params = {'pageNum': 1, 'pageSize': 5}
            if run:
                params['runState'] = run
            r = await c.get('/cmd/flow/instances', params=params)
            d = r.json()['data']
            row0 = (d.get('rows') or [{}])[0]
            print(f'instances[{run or "ALL"}] total =', d.get('total'),
                  '| taskNo =', row0.get('taskNo'),
                  '| bizType =', row0.get('bizType'),
                  '| sceneName =', row0.get('sceneName'),
                  '| progress =', f"{row0.get('completedSteps')}/{row0.get('totalSteps')}",
                  '| engineBound =', row0.get('engineBound'))

        # 3. 泳道图（定义视图 + 实例视图）
        r = await c.get('/cmd/flow/graph/scene/CUSTOMER_CREATE')
        g = r.json()['data']
        print('graph def: nodes =', len(g.get('nodes') or []),
              '| lanes =', len(g.get('lanes') or []),
              '| edges =', len(g.get('edges') or []),
              '| node0 =', {k: (g['nodes'][0] or {}).get(k) for k in ('nodeCode', 'shape', 'x', 'y', 'status')})
        # 找一个真实任务
        r = await c.get('/cmd/flow/instances', params={'pageNum': 1, 'pageSize': 1})
        tno = r.json()['data']['rows'][0]['taskNo']
        r = await c.get('/cmd/flow/graph/scene/CUSTOMER_CREATE', params={'taskNo': tno})
        g = r.json()['data']
        st = [n['status'] for n in g['nodes']]
        print(f'graph instance[{tno}]:', {s: st.count(s) for s in set(st)})

        # 4. 流程跟踪
        r = await c.get(f'/cmd/flow/trace/{tno}')
        vo = r.json()['data']
        print('trace:', vo.get('taskNo'), '| status =', vo.get('status'),
              '| steps =', len(vo.get('steps') or []),
              '| progress =', vo.get('progressPercent'),
              '| contextVars =', len(vo.get('contextVars') or []),
              '| actions =', len(vo.get('actions') or []),
              '| graph =', (vo.get('graph') or {}).get('flowCode'),
              '| step1 =', (vo.get('steps') or [{}])[0].get('nodeName'),
              (vo.get('steps') or [{}])[0].get('status'))

        # 5. workflow-steps（数组契约）
        r = await c.get('/cmd/approval/workflow-steps', params={'taskNo': tno})
        steps = r.json()['data']
        print('workflow-steps:', type(steps).__name__, 'len =', len(steps) if isinstance(steps, list) else '-',
              '| first =', {k: (steps[0] or {}).get(k) for k in ('stepSeq', 'stepType', 'nodeName', 'actionType')}
              if isinstance(steps, list) and steps else None)


asyncio.run(main())

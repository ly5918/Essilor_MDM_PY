"""工作流中心 API：场景 / 实例 / 泳道图 / 流程跟踪（对齐 Java CmdFlowTraceController）。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query, Body
from sqlalchemy import select, func, desc

from ..core.db import get_engine, table, flow_instance_table
from ..core.query import dynamic_insert, dynamic_update
from ..schemas import R
from ..workflow import swimlane as sl
from ..services import flow_def_service as flow_def

router = APIRouter(prefix="/cmd/flow", tags=["工作流"])

# biz_type → 中文业务名（前端 FlowInstanceVO.bizType 直接展示中文）
BIZ_TYPE_CN = {
    "CUSTOMER_CREATE": "客户创建",
    "CUSTOMER_CHANGE": "客户变更",
    "MERGE": "跨BU合并",
    "IMPORT": "批量导入确认",
    "DEACTIVATE": "客户停用",
    "HIER_RELATION": "层级关系变更",
    "DQ_RULE_CHANGE": "DQ规则变更",
    "MATCH_RULE_CHANGE": "匹配规则变更",
    "INTEGRATION_FAIL": "集成失败处理",
}

# 平台固定 / 可配置节点判定（与 mock / Java CmdFlowSceneConfigServiceImpl 同一口径）：
# 只有 GC 决策可按场景停用/增删（V6.1 待确认项：High End 必经 GC，Mainstream 可只走 BU 初审），
# 其余节点为业务入口 / 系统自动 / 主干审批 / 审计链，平台固定不可删除。
CONFIGURABLE_NODES = {"GC_REVIEW"}
LOCKED_NODE_CONSTRAINT = {
    "APPLY": "业务入口：Business User 发起，平台固定不可删除",
    "INPUT": "申请数据录入与附件，平台固定不可删除",
    "OCR": "系统自动：OCR 与地址标准化，规则驱动不可删除",
    "DQ": "系统自动：DQ 打分，结果写入实例变量驱动路由，不可删除",
    "DUP": "系统自动：Duplicate Check（信用代码 + 经营地址为主依据），不可删除",
    "BU_REVIEW": "主干审批节点：BU Scope 初审，不可停用；命中条件与办理角色可配置",
    "RESULT": "系统自动：One ID 生成 / 关联，One ID 稳定不重新生成，不可删除",
    "PUBLISH": "发布下游与 Retry / Resubmit 由平台统一执行，不可删除",
    "TRACE": "运行追踪：任务状态与失败原因，平台固定",
    "AUDIT": "审计证据链：Who / When / What 与 Before / After，只读保留不可删除",
}


def _node_config_of(node_code: str) -> dict:
    """节点约束标注（FlowSceneNodeVO.locked/configurable/constraint）。"""
    configurable = node_code in CONFIGURABLE_NODES
    if configurable:
        constraint = "可配置：可停用（Mainstream 可只走 BU 初审）或调整升级命中条件（V6.1 待确认项）"
    else:
        constraint = LOCKED_NODE_CONSTRAINT.get(node_code, "平台固定节点，不可删除")
    return {"locked": not configurable, "configurable": configurable, "constraint": constraint}


async def _scene_map(conn) -> dict[str, dict]:
    """scene_code → 场景行（cmd_flow_scene）。"""
    try:
        sf = table("cmd_flow_scene")
        rows = (await conn.execute(select(sf).where(sf.c.del_flag == "0"))).mappings().all()
        return {r["scene_code"]: dict(r) for r in rows}
    except Exception:
        return {}


def _progress(steps: list[dict]) -> tuple[int, int, int]:
    done = sum(1 for s in steps if s["status"] == "COMPLETED")
    total = len(steps)
    pct = round(done * 100 / total) if total else 0
    return done, total, pct


@router.get("/scenes")
async def flow_scenes():
    """场景列表（FlowSceneVO[]）：cmd_flow_scene + 部署版本登记（cmd_flow_def_version）。"""
    conn = await get_engine().connect()
    try:
        smap = await _scene_map(conn)
        vmap: dict[str, dict] = {}
        for code in smap:
            vmap[code] = await flow_def.current_version(conn, code) or {}
    finally:
        await conn.close()
    result = []
    for code, row in smap.items():
        ver = vmap.get(code) or {}
        node_count = ver.get("node_count") or len(sl.build_swimlane(code))
        result.append({
            "sceneCode": code,
            "sceneName": row.get("scene_name"),
            "flowCode": row.get("flow_code"),
            "flowName": row.get("flow_name"),
            "slaHours": row.get("sla_hours"),
            # 已部署 = 场景正常且登记了当前版本（SpiffWorkflow 部署记录）
            "deployed": row.get("status") == "0" and bool(ver),
            "definitionId": (ver.get("definition_id") or row.get("definition_id")
                             or None),
            "version": ver.get("version_no") or None,
            "deployedAt": ver.get("deployed_at"),
            "nodeCount": node_count,
        })
    return R.ok(result)


@router.get("/graph/scene/{scene_code}")
async def flow_graph(scene_code: str, taskNo: Optional[str] = Query(None)):
    """泳道图（FlowGraphVO）：定义视图 + 实例视图（taskNo 按实际进度点亮）。"""
    steps = sl.build_swimlane(scene_code)
    touched: set = set()
    task = None
    returned = False
    return_src: Optional[str] = None
    current_code = ""
    if taskNo:
        conn = await get_engine().connect()
        try:
            t = table("cmd_approval_task")
            task = (await conn.execute(
                t.select().where(t.c.task_no == taskNo))).mappings().first()
            if task is not None:
                # 真实轨迹：cmd_approval_action 的 to / from 两端都算「到过」——
                # 只取 to 会漏掉升级动作的起节点（BU_REVIEW → GC_REVIEW 时 BU 初审不会被点亮）
                act = table("cmd_approval_action")
                actions = [dict(a) for a in (await conn.execute(
                    act.select().where(act.c.task_id == task["id"])
                    .order_by(act.c.action_time))).mappings().all()]
                act_by_node: dict[str, dict] = {}
                for a in actions:
                    for key in (a.get("to_node_code"), a.get("from_node_code")):
                        if key:
                            act_by_node[key] = a          # 后发生的动作覆盖先发生的
                touched = set(act_by_node.keys())
                returned = sl.is_returned(task["status"], task["current_node_name"], actions)
                return_src = sl.return_source_node(actions)
                current_code = sl.apply_step_status(
                    steps, task["status"], task["current_node_name"], touched,
                    current_node_code=task["current_node_code"], returned=returned)
        finally:
            await conn.close()

    nodes = []
    sub_row: dict[str, int] = {}
    for i, s in enumerate(steps):
        lane_idx = sl.LANE_ORDER.index(s["lane"]) if s["lane"] in sl.LANE_ORDER else 0
        sub = sub_row.get(f"{lane_idx}#{s['phase']}", 0)
        sub_row[f"{lane_idx}#{s['phase']}"] = sub + 1
        nodes.append({
            "nodeCode": s["nodeCode"], "nodeName": s["nodeName"],
            "shape": sl.step_shape(s["nodeType"], i, len(steps)),
            "nodeType": 4 if s["nodeType"] == "GATEWAY" else 1,
            "lane": s["lane"], "phase": s["phase"], "phaseName": s["phaseName"],
            "note": s["note"],
            "x": sl.BASE_X + (s["phase"] - 1) * sl.COL_GAP,
            "y": sl.BASE_Y + lane_idx * sl.LANE_GAP + sub * sl.SUB_ROW_GAP,
            "status": s["status"],
            "approver": s.get("operator"),
            "actionTime": s.get("actionTime"),
        })
    edges = []
    for k in range(len(nodes) - 1):
        edges.append({
            "from": nodes[k]["nodeCode"], "to": nodes[k + 1]["nodeCode"],
            "label": "", "skipType": "PASS",
            "passed": nodes[k]["status"] == "COMPLETED",
        })
    # 退回连线：从退回发起的节点指回当前停留节点（泳道图上的「退回」回溯箭头）。
    # 主流程连线只表达「往前走」，退回是逆方向的一跳，必须单独画出来，
    # 否则图上完全看不出这一单已经被打回。
    if returned and return_src and current_code and return_src != current_code:
        codes = {n["nodeCode"] for n in nodes}
        if return_src in codes and current_code in codes:
            edges.append({"from": return_src, "to": current_code,
                          "label": "退回", "skipType": "RETURN", "passed": False})
    graph = {"definitionId": scene_code, "flowCode": sl.SCENE_FLOW_CODE.get(scene_code, ""),
             "lanes": sl.LANE_ORDER, "nodes": nodes, "edges": edges}
    return R.ok(graph)


@router.get("/instances")
async def flow_instances(
    keyword: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    bizType: Optional[str] = Query(None),
    runState: Optional[str] = Query(None),
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(100, ge=1, le=200),
):
    """流程实例记录（FlowInstanceVO 分页）：源 = cmd_approval_task，Java listInstances 口径。"""
    t = table("cmd_approval_task")
    conds = [t.c.del_flag == "0"]
    if status:
        conds.append(t.c.status == status)
    if bizType:
        conds.append(t.c.biz_type == bizType)
    if keyword:
        like = f"%{keyword}%"
        conds.append(t.c.task_no.like(like) | t.c.biz_title.like(like) | t.c.one_id.like(like))
    run = (runState or "").upper()
    if run == "RUNNING":
        conds.append(t.c.status.notin_(sl.FINAL_STATUSES))
    elif run == "DONE":
        conds.append(t.c.status.in_(sl.FINAL_STATUSES))
    elif run == "NEW":
        conds.append(t.c.flow_instance_id.is_(None))

    conn = await get_engine().connect()
    try:
        rows = [dict(r) for r in (await conn.execute(
            select(t).where(*conds)
            # 历史数据可能缺 create_time（旧导入链路未写），NULL 在 DESC 排序中沉底会导致
            # 实例「看不见」——用 COALESCE 回退到 update_time/submit_time，再按 id 稳定排序
            .order_by(func.coalesce(t.c.create_time, t.c.update_time, t.c.submit_time).desc(),
                      t.c.id.desc())
            .limit(pageSize).offset((pageNum - 1) * pageSize))).mappings().all()]
        total = (await conn.execute(
            select(func.count()).select_from(t).where(*conds))).scalar() or 0
        smap = await _scene_map(conn)
        # SpiffWorkflow 引擎实例（Python 侧）
        py_flows: dict[str, dict] = {}
        py_ids = [r["task_no"] for r in rows if r.get("task_no")]
        if py_ids:
            for f in (await conn.execute(
                flow_instance_table.select().where(flow_instance_table.c.biz_no.in_(py_ids))
            )).mappings().all():
                py_flows[f["biz_no"]] = dict(f)
    finally:
        await conn.close()

    result = []
    for r in rows:
        scene_code = sl.normalize_scene_code(r.get("scene_code"), r.get("biz_type"))
        scene = smap.get(scene_code, {})
        steps = sl.build_swimlane(scene_code)
        sl.apply_step_status(steps, r.get("status"), r.get("current_node_name"),
                             current_node_code=r.get("current_node_code"))
        done, total_steps, pct = _progress(steps)
        py = py_flows.get(r.get("task_no"))
        flow_instance_id = py["id"] if py else r.get("flow_instance_id")
        result.append({
            "id": r["id"], "taskNo": r.get("task_no"), "oneId": r.get("one_id"),
            "bizTitle": r.get("biz_title"),
            "bizType": BIZ_TYPE_CN.get(r.get("biz_type") or "", r.get("biz_type")),
            "sceneCode": scene_code,
            "sceneName": scene.get("scene_name"),
            "flowName": scene.get("flow_name"),
            "flowCode": scene.get("flow_code"),
            "flowInstanceId": flow_instance_id,
            "engineBound": py is not None or r.get("flow_instance_id") is not None,
            "applicantName": r.get("applicant_name"),
            "assigneeName": r.get("assignee_name"),
            "assigneeRole": r.get("assignee_role"),
            "priority": r.get("risk_level"),
            "status": r.get("status"),
            "currentNodeName": r.get("current_node_name"),
            "completedSteps": done, "totalSteps": total_steps,
            "progressPercent": pct,
            "slaState": r.get("sla_state"),
            "submitTime": r.get("submit_time"),
            "finishTime": r.get("finish_time"),
            "durationHours": r.get("duration_hours"),
            "createTime": r.get("create_time"),
        })
    return R.ok({"total": int(total), "rows": result})


@router.get("/trace/{task_no}")
async def flow_trace(task_no: str):
    """流程跟踪（FlowTraceVO）：步骤条 + 泳道图 + 动作轨迹 + 上下文变量 + 分步骤明细。"""
    conn = await get_engine().connect()
    try:
        t = table("cmd_approval_task")
        task = (await conn.execute(
            t.select().where(t.c.task_no == task_no))).mappings().first()
        if task is None:
            return R.fail("流程实例不存在", code=404)
        task = dict(task)
        smap = await _scene_map(conn)
        act = table("cmd_approval_action")
        actions = [dict(a) for a in (await conn.execute(
            act.select().where(act.c.task_id == task["id"])
            .order_by(act.c.action_time))).mappings().all()]
        py_flow = (await conn.execute(
            flow_instance_table.select().where(flow_instance_table.c.biz_no == task_no))).mappings().first()

        scene_code = sl.normalize_scene_code(task.get("scene_code"), task.get("biz_type"))
        scene = smap.get(scene_code, {})
        steps = sl.build_swimlane(scene_code)

        # 轨迹按节点归并（人工节点由审批动作写入，自动节点由系统轨迹写入）。
        # to / from 两端都登记：升级动作 from=BU_REVIEW、to=GC_REVIEW，
        # 只取一端会让「谁在哪个节点做了什么」丢一半。
        act_by_node: dict[str, dict] = {}
        for a in actions:
            for key in (a.get("to_node_code"), a.get("from_node_code")):
                if key:
                    act_by_node[key] = a          # 后发生的动作覆盖先发生的
        for s in steps:
            a = act_by_node.get(s["nodeCode"])
            if a:
                s["operator"] = a.get("operator_name")
                s["actionTime"] = a.get("action_time")
                s["opinion"] = a.get("opinion")
            if s["nodeCode"] in sl.MANUAL_REVIEW_NODES:
                s["assignee"] = "GC_STEWARD" if s["nodeCode"] == sl.NODE_GC_REVIEW else "BU_STEWARD"
        sl.apply_step_status(steps, task.get("status"), task.get("current_node_name"),
                             set(act_by_node.keys()),
                             current_node_code=task.get("current_node_code"),
                             returned=sl.is_returned(task.get("status"),
                                                     task.get("current_node_name"), actions))
        done, total_steps, pct = _progress(steps)

        # 分步骤明细（1:1 移植 Java fillStepDetails：每个节点都有内容，点步骤条即切）
        from ..services.step_detail import build_step_details
        step_details = await build_step_details(conn, task, steps, actions)
    finally:
        await conn.close()

    # 泳道图（实例视图）
    graph = None
    try:
        graph_resp = await flow_graph(scene_code, taskNo=task_no)
        graph = graph_resp.data if graph_resp is not None else None
    except Exception:
        graph = None

    # 上下文变量（SpiffWorkflow 实例变量快照）
    context_vars = []
    if py_flow is not None and py_flow["data_json"]:
        raw = py_flow["data_json"]
        if isinstance(raw, str):
            import json as _json
            try:
                raw = _json.loads(raw)
            except Exception:
                raw = {}
        for k, v in (raw or {}).items():
            context_vars.append({"name": k, "value": "" if v is None else str(v)})

    action_traces = [{
        "actionType": a.get("action_type"), "actionName": a.get("action_name"),
        "operatorName": a.get("operator_name"), "operatorRole": a.get("operator_role"),
        "actionTime": a.get("action_time"), "opinion": a.get("opinion"),
    } for a in actions]

    vo = {
        "engineBound": py_flow is not None or task.get("flow_instance_id") is not None,
        "graph": graph,
        "taskNo": task.get("task_no"),
        "bizTitle": task.get("biz_title"),
        "bizType": BIZ_TYPE_CN.get(task.get("biz_type") or "", task.get("biz_type")),
        "sceneCode": scene_code,
        "sceneName": scene.get("scene_name"),
        "flowCode": scene.get("flow_code"),
        "flowName": scene.get("flow_name"),
        "status": task.get("status"),
        # 已退回：前端据此提示「本单被打回、下游节点需重做」（琥珀色标记）
        "returned": sl.is_returned(task.get("status"), task.get("current_node_name"), actions),
        "currentNodeName": task.get("current_node_name"),
        "assigneeName": task.get("assignee_name"),
        "assigneeRole": task.get("assignee_role"),
        "buScope": task.get("bu_scope"),
        "riskLevel": task.get("risk_level"),
        "slaState": task.get("sla_state"),
        "submitTime": task.get("submit_time"),
        "slaDue": task.get("sla_due"),
        "flowInstanceId": py_flow["id"] if py_flow else task.get("flow_instance_id"),
        "flowTaskId": task.get("flow_task_id"),
        "flowDefinitionId": task.get("flow_definition_id"),
        "flowStatus": task.get("flow_status"),
        "totalSteps": total_steps, "completedSteps": done, "progressPercent": pct,
        "bypass": {"lane": sl.LANE_ADMIN, "nodeName": "规则与参数配置",
                   "note": "配置 DQ 规则、匹配规则和审批试验，参数配置不打断主流程"},
        "steps": steps,
        "stepDetails": step_details,
        "contextVars": context_vars,
        "actions": action_traces,
    }
    return R.ok(vo)


@router.post("/instance/{task_no}/start")
async def flow_instance_start(task_no: str):
    """启动流程实例（统一流程在提交/首次审批时已启动，此处幂等返回）。"""
    row = (await (await get_engine().connect()).execute(
        flow_instance_table.select().where(flow_instance_table.c.biz_no == task_no))).mappings().first()
    if row is None:
        return R.fail("流程实例尚未创建（请先提交或发起审批）", code=404)
    return R.ok({"biz_no": task_no, "status": row["status"], "current_node": row["current_node"]})


@router.post("/deploy/{scene_code}")
async def flow_deploy(scene_code: str):
    """部署场景到 SpiffWorkflow：登记版本记录（幂等，BPMN 变更时版本号进位）。"""
    try:
        result = await flow_def.deploy(scene_code)
    except ValueError as e:
        return R.fail(str(e), code=404)
    msg = ("流程已部署为 " + result["versionNo"]) if result["created"] \
        else f"已是最新版本 {result['versionNo']}（BPMN 未变化，幂等复用）"
    return R.ok(result, msg=msg)


@router.get("/scene/{scene_code}/versions")
async def flow_scene_versions(scene_code: str):
    """场景版本历史（FlowSceneVersionVO[]）：版本号 / 定义ID / 节点数 / 部署人 / 时间。"""
    conn = await get_engine().connect()
    try:
        rows = await flow_def.list_versions(conn, scene_code)
    finally:
        await conn.close()
    return R.ok(rows)


@router.get("/scene/{scene_code}/config")
async def scene_config_get(scene_code: str):
    """场景配置（FlowSceneConfigVO）：场景头 + 节点模板 + cmd_flow_node_rule 规则。

    V6.1 设计 16「Workflow配置」要求配置弹窗呈现：流程节点、路由条件（启动条件/表单标识）、
    SLA、超时升级和邮件通知。此前只返回 nodes/rules，导致弹窗头部
    「业务场景 — / 流程编码 — / 版本 v— / 未部署」与实际部署状态不符。
    """
    steps = sl.build_swimlane(scene_code)
    conn = await get_engine().connect()
    try:
        smap = await _scene_map(conn)
        scene = smap.get(scene_code, {})
        ver = await flow_def.current_version(conn, scene_code) or {}
        nr = table("cmd_flow_node_rule")
        try:
            rules = [dict(r) for r in (await conn.execute(
                nr.select().where(nr.c.scene_code == scene_code))).mappings().all()]
            # 主干 BU 初审规则锁定启用状态（与 mock / 弹窗「启用」开关禁用口径一致）
            for r in rules:
                r["locked"] = (r.get("node_code") or "").lower() == "bu_review"
        except Exception:
            rules = []
    finally:
        await conn.close()

    # ext_json（json 列）：变更说明 / 通知方式 / 通知对象 / 超时动作（平台初始化写入）
    ext = scene.get("ext_json")
    if isinstance(ext, str):
        import json as _json
        try:
            ext = _json.loads(ext)
        except Exception:
            ext = {}
    ext = ext or {}

    return R.ok({
        "sceneCode": scene_code,
        "sceneName": scene.get("scene_name"),
        "flowCode": scene.get("flow_code"),
        "flowName": scene.get("flow_name"),
        "slaHours": scene.get("sla_hours"),
        "escalateRule": scene.get("escalate_rule"),
        "startConditions": scene.get("start_conditions"),
        "formKey": scene.get("form_key"),
        # 已部署 = 场景正常且登记了当前版本（与 /scenes 列表同一口径）
        "deployed": scene.get("status") == "0" and bool(ver),
        "version": ver.get("version_no"),          # 'v1.0' 字符串（展示层不再拼 v）
        "deployedAt": ver.get("deployed_at"),
        "changeNote": ext.get("changeNote"),
        "timeoutAction": ext.get("timeoutAction"),
        "notifyMode": ext.get("notifyMode"),
        "notifyTargets": ext.get("notifyTargets") or [],
        "nodes": [dict({"nodeCode": s["nodeCode"], "nodeName": s["nodeName"],
                        "nodeType": s["nodeType"], "lane": s["lane"],
                        "slaHours": None, "note": s["note"]}, **_node_config_of(s["nodeCode"]))
                  for s in steps],
        "rules": rules,
    })


@router.put("/scene/{scene_code}/config")
async def scene_config_save(scene_code: str, body: dict = Body(...)):
    try:
        nr = table("cmd_flow_node_rule")
        async with get_engine().begin() as conn:
            rules = body.get("rules") or []
            for rule in rules:
                rid = rule.get("id")
                if rid:
                    await dynamic_update(conn, nr, rid, rule)
                elif rule.get("nodeCode"):
                    await dynamic_insert(conn, nr, {
                        "scene_code": scene_code, "node_code": rule.get("nodeCode"),
                        "node_name": rule.get("nodeName"), "assignee_type": rule.get("assigneeType"),
                        "assignee_value": rule.get("assigneeValue"),
                        "sla_hours": rule.get("slaHours"), "status": "0",
                    })
    except Exception as e:
        return R.fail(f"保存场景配置失败: {e}", code=500)
    return R.ok(msg="场景配置已保存")

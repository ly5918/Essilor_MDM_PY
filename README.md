# Essilor CMD MDM (Python 版)

> 依视路（Essilor）客户主数据管理（Customer Master Data）POC 项目 — Python 后端 + Vue3 前端实现。
>
> 后端用 **FastAPI** 重写，复用原 RuoYi-Vue-Plus 的 `ruoyi_plus` 数据库表结构与数据；前端基于 [plus-ui](https://gitee.com/JavaLionLi/plus-ui) 6.X（Vue3 + Element Plus + Vite）改造，新增 CMD POC 业务模块。

---

## 一、技术栈

| 层 | 技术 | 说明 |
| --- | --- | --- |
| 后端 | Python 3.10+ / FastAPI / SQLAlchemy 2.x (async) / aiomysql | 异步 API，复用 ruoyi_plus 库 |
| 工作流 | SpiffWorkflow | 驱动客户审批/变更流程，BPMN 定义见 `backend/processes/` |
| 前端 | Vue 3.5 + TypeScript + Element Plus 2.14 + Vite 8 | 基于 plus-ui 6.X |
| 数据库 | MySQL 8.x（utf8mb4） | 116 张表（RuoYi 基础表 + CMD 业务表） |
| 包管理 | pip（后端）/ pnpm 10（前端） | |

### 合同兼容层

后端在 `app/main.py` 实现了三中间件，对齐 Java 版 RuoYi 的序列化口径，前端无需改造即可对接：

- `CamelCaseResponseMiddleware`：响应 JSON key 统一转 camelCase
- `SnakeCaseBodyMiddleware`：请求体补 snake_case 别名
- `QueryAliasMiddleware`：`pageNum/pageSize` → `page/size`

---

## 二、仓库目录

```
Essilor_MDM_PY/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── main.py             # 应用入口 + 中间件
│   │   ├── api/                # 18 个业务路由（customer/approval/dashboard/...）
│   │   ├── core/               # config / db / query
│   │   ├── services/           # 业务服务（approval/customer/duplicate/sequence）
│   │   ├── workflow/           # SpiffWorkflow 引擎封装
│   │   └── schemas.py          # Pydantic 模型
│   ├── processes/              # BPMN 流程定义（cmd_approval.bpmn）
│   ├── tests/                  # 冒烟与契约测试（smoke.py / contract_check.py）
│   ├── requirements.txt        # Python 依赖
│   ├── .env.example            # 配置模板（请复制为 .env）
│   └── .env                    # 本地配置（已 gitignore，不上传）
├── frontend/                   # Vue3 前端（plus-ui 6.X 改造）
│   ├── src/
│   │   ├── views/demo/cmd-poc/ # CMD POC 业务模块（客户/层级/变更/审批/...）
│   │   ├── api/                # 接口封装
│   │   ├── layout/             # 布局
│   │   ├── store/              # Pinia 状态
│   │   └── ...
│   ├── docs/                   # 操作手册
│   ├── gen/                    # 代码生成模板（.ftl）
│   ├── vite/                   # vite 插件
│   ├── .env.development        # 开发环境配置
│   ├── .env.production         # 生产环境配置
│   └── package.json
├── sql/                        # 数据库 schema（仅结构，无数据）
│   ├── db_schema.sql           # 全库 119 张表 DDL（与本地开发库一致，推荐）
│   └── cmd_schema_subset.sql   # CMD 业务相关 93 张表子集 DDL
├── .gitignore
└── README.md
```

> **不上传的内容**（见 `.gitignore`）：`node_modules/`、`__pycache__/`、`.venv/`、`backend/.env`（含密码）、数据库 dump、运行日志、临时调试脚本（`tests/_*.py`）、截图、IDE 配置、`.codeartsdoer/` 等。

---

## 三、CMD POC 业务功能

前端 `src/views/demo/cmd-poc/` 下按角色组织（admin / bu / gc / business / audit），核心能力：

| 模块 | 能力 |
| --- | --- |
| 客户管理 | 新建 / 详情 / 停用 / 合并（OneID） |
| 层级管理 | 层级新增 / 分配 |
| 变更管理 | 变更请求 / 详情 / 审批流 |
| 审批流 | BPMN 驱动，HE/MS 节点，流程图与轨迹 |
| 数据质量 | DQ 规则模拟 |
| 匹配去重 | 匹配模拟 / 循环检查 / 重新评估 |
| 导入 | 批量上传 / 模板 / 字段映射 |
| OCR | 营业执照识别 |
| OneID | 主数据归并历史 |
| 集成 | 外部系统集成连接 |
| 治理 | 字段级权限 |
| 审计 | 审计事件导出 |

后端对应 18 个路由：`customer / approval / dashboard / metadata / duplication / change / governance / nav / flow / oneid / dq / match / import / hierarchy / audit / permission / coverage / ocr / integration`。

---

## 四、环境准备

### 4.1 基础环境

| 软件 | 版本要求 |
| --- | --- |
| Node.js | ≥ 20.19 |
| pnpm | ≥ 10.0 |
| Python | ≥ 3.10（推荐 3.12/3.13） |
| MySQL | ≥ 8.0 |

### 4.2 数据库初始化

```bash
# 1) 登录 MySQL，创建数据库
mysql -uroot -p -e "CREATE DATABASE IF NOT EXISTS ruoyi_plus_py DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_general_ci;"

# 2) 导入 schema（仅表结构，无数据；推荐全量 119 表）
mysql -uroot -p ruoyi_plus_py < sql/db_schema.sql
```

> **重要**：
> - `sql/db_schema.sql` 为全库 119 张表，与本地开发库完全一致，**必须使用它**导入。
>   `cmd_flow_def_version`、`cmd_py_flow_instance`、`cmd_py_seq` 三张表已包含——
>   `cmd_py_flow_instance` / `cmd_py_seq` 后端启动时也会自动创建（`create_all`），但 schema 中已有确保最稳。
> - 如仅需 CMD 业务相关表，可改用 `sql/cmd_schema_subset.sql`（93 表），已含上述 3 张必需表。
> - schema 不含业务数据。首次启动后登录系统，通过「客户新建 / 批量导入」等页面录入即可；
>   系统配置类表（`sys_dict_*`、`cmd_role`、`cmd_flow_scene`、`md_model` 等）为保留主数据，初始为空，若前端依赖字典选项展示异常，可参考
>   `CMD_POC_页面-数据表清单.md` 中各表的常用字典值手工补录。

---

## 五、后端启动

```bash
cd backend

# 1) 创建虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 2) 安装依赖
pip install -r requirements.txt

# 3) 配置本地环境变量（从模板复制后修改数据库密码）
cp .env.example .env
#   然后编辑 .env，填写 DB_PASSWORD 等

# 4) 启动服务（默认 0.0.0.0:8000）
python -m app.main
# 或
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

健康检查：浏览器打开 <http://localhost:8000/health>，返回 `{"status":"ok"}` 即成功。

交互式 API 文档：<http://localhost:8000/docs>

---

## 六、前端启动

```bash
cd frontend

# 1) 安装依赖（国内可加镜像）
pnpm install --registry=https://registry.npmmirror.com

# 2) 启动开发服务（默认 http://localhost:80）
pnpm dev

# 3) 构建生产包
pnpm build:prod
```

前端通过 `vite.config.ts` 的 proxy 把 `/dev-api` 代理到 `http://localhost:8000`，故**先启后端再启前端**。

### Mock 开关

`frontend/.env.development` 中：

```bash
VITE_CMD_POC_MOCK = false              # 全局 Mock 开关
VITE_CMD_POC_LIVE_MODULES = customer,hierarchy,dashboard,...  # 走真实后端的模块白名单
```

设为 `true` 可在前端纯演示模式下运行（无需后端）。

---

## 七、测试

```bash
cd backend
# 冒烟测试
python tests/smoke.py
# 契约检查（校验 camelCase / 字段契约）
python tests/contract_check.py
```

---

## 八、默认账号

POC 演示为 mock 登录，前端登录页可直接进入，无需真实账号。如需对接 RuoYi 标准登录路径，请配置 `backend/.env` 的 `JWT_SECRET` 并启用鉴权中间件。

---

## 九、相关项目

| 项目 | 地址 |
| --- | --- |
| 前端基座 plus-ui | <https://gitee.com/JavaLionLi/plus-ui> |
| 后端基座 RuoYi-Vue-Plus | <https://gitee.com/dromara/RuoYi-Vue-Plus> |

本项目在 plus-ui 基础上新增 CMD POC 业务模块，后端用 Python 重写并对齐 Java 版序列化口径，复用 ruoyi_plus 数据库。

---

## 十、License

MIT（继承自 plus-ui）。
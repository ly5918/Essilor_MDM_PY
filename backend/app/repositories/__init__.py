"""Repository 层（数据访问层）。

对应 Java 三层架构中的 Mapper/DAO 层（如 CmdImportJobMapper）。

分层规范（与 Java 后端对齐，写新代码必须遵守）：

    HTTP 请求
      │
      ▼
    app/api/*_api.py        Router 层（≈ Controller）
                            只做：参数解析/校验、调用 service、包装 R.ok/R.fail、
                            异常翻译、文件上传/下载的 HTTP 细节。禁止写业务规则与 SQL。
      │
      ▼
    app/services/*_service.py  业务层（≈ ServiceImpl）
                            只做：业务规则编排（预检、分流、状态推导、审批联动）。
                            不直接拼 SQL，数据读写一律调 repository。
      │
      ▼
    app/repositories/*_repo.py  数据访问层（≈ Mapper/DAO）
                            只做：全部 SQL / 表操作（select/insert/update/聚合统计）。
                            函数粒度与 Java Mapper 方法对应，一个业务表一个 repo 模块。

辅助约定：
- 请求/响应模型放 app/schemas.py（≈ domain/bo/vo）；
- 引擎、反射表、发号器等基础设施放 app/core/（≈ 框架 starter）；
- repo 函数全部显式接收 conn（调用方控制事务边界），不自行 commit。
"""

# Drun 学习课程目录

## 学习收获（可落地验收）
1. 搭建运行与产物：独立完成安装与运行，输出 HTML 报告、JSON 报告与控制台/文件日志（`drun run testcases --html reports/report.html --report reports/report.json --env-file .env`）。
2. 业务回归测试套件：基于现有 `testcases/*` 与 `testsuites/*` 交付冒烟/回归/权限三层测试套件；验收标准：冒烟测试套件稳定全绿且用时 <5 分钟（示例：运行 `testsuites/testsuite_smoke.yaml`）。
3. 标签治理与筛选：按 `smoke/regression/permissions` 标签组织并能用 `-k` 表达式精确筛选（如 `drun run testcases -k "smoke and not slow"`）。
4. 参数化覆盖：使用压缩参数化覆盖多环境与边界场景（`examples/test_params_zipped.yaml`），验证实例数与期望一致。
5. 鉴权与会话复用：完成登录→带 token 访问链路（`testcases/test_auth.yaml`、`examples/test_login_whoami.yaml`），并验证无需显式设置 `Authorization` 头也能通过（自动注入生效）。
6. 报告与最小复现：能从 HTML 报告中获取 cURL 并在终端复现实验结果；可生成 Allure 结果并本地渲染（`--allure-results allure-results`）。
7. SQL 数据一致性：配置 MySQL 连接（环境变量 `MYSQL_HOST/PORT/USER/PASSWORD/DB` 或 `MYSQL_DSN`），运行 `examples/test_sql_validate.yaml` 与 `examples/test_sql_store_reuse.yaml` 完成金额/库存校验与变量复用。
8. 性能阈值：在关键接口为 `$elapsed_ms` 设置断言阈值（参考 `examples/test_perf_timing.yaml`），确保核心路径在目标预算内。
9. 规范化校验：用 `drun check` 校验用例通过、`drun fix` 一键修复常见风格问题；提交前通过本地校验脚本。
10. 通知闭环：完成至少一种渠道（飞书/钉钉/邮件）配置并在失败时自动推送摘要（命令示例：`--notify feishu --notify-only failed`；可用环境变量：`FEISHU_WEBHOOK`、`DINGTALK_WEBHOOK`、`SMTP_HOST` 等）。
11. 安全与合规：启用 `--mask-secrets` 进行日志与报告脱敏；密钥通过 `.env` 注入；报告与日志不包含敏感明文。
12. 理解框架架构设计：掌握 CLI→Loader→Runner→Engine→Reporter→Notifier 调用链与数据流，能据此定位问题模块（参考 `drun/cli.py`、`drun/loader/*`、`drun/runner/runner.py`）。
13. 阅读和修改源码：完成一次小型修复或优化（<50 行），`drun check` 通过且示例回归全绿（提交修改文件与验证命令）。
14. 添加新功能：在断言/通知/Reporter 任一处新增一个可用扩展，配套 `examples/*.yaml` 用例与报告产物（如扩展 `drun/runner/assertions.py` 或 `drun/notifier/*`）。
15. 性能优化：针对模板/提取/报告任一热点编写基准脚本，优化后 p95 延迟下降≥20%（参考 `drun/templating/*`、`drun/runner/extractors.py`、`drun/reporter/*`）。
16. 技术选型：完成一次鉴权/通知/报告/SQL 驱动的对比选型并落地到配置/代码；产出 1 页 ADR（方案/权衡/回滚）。
17. 推动企业落地：在 CI 中运行测试套件并启用门禁阈值（通过率/时延），失败自动通知责任人；产出报告链接、通知截图与示例 CI 片段（如 `drun run testsuites/testsuite_regression.yaml --notify feishu --notify-only failed`）。

## 阶段 1｜前置与方法论（必修）
1. Python 知识点：语法/数据结构/函数与装饰器/面向对象/异常/上下文管理器/类型注解/异步 async-await。
2. Python 工程与生态：虚拟环境/venv、包管理/pip、打包/pyproject，`pydantic`/`typer`/`httpx` 基础。
3. 接口测试与自动化测试方法论：金字塔、等价类/边界、幂等/重试、错误码与安全。
4. HTTP/REST 与鉴权：方法/状态码/头/缓存、HMAC/签名、cURL 调试。
5. YAML/JSON/JMESPath：表达式/过滤/提取的高频模式与陷阱。
6. SQL 与数据准备：查询/事务/隔离，断言场景与数据构造。
7. CLI/Git 与工具链：shell、git 分支/PR、Postman/Insomnia、日志溯源。

## 阶段 2｜Drun 速通与基础
1. 结构速览与安装运行：README、命令行入口（`drun/cli.py`）。
2. YAML DSL 入门：Case/Step/Request/Validate/Extract。
3. 变量与模板：作用域优先级、`$var`/`${expr}`、ENV 与内置函数。
4. 运行与报告：标签过滤、HTML/JSON/Allure 基础。

## 阶段 3｜核心能力
1. 数据提取与断言：JMESPath 常用模式与断言可读性。
2. 参数化与复用：压缩模式，片段与组织策略。
3. HTTP 引擎与稳定性：超时/重试/幂等/cURL 诊断（`drun/engine/http.py`）。
4. Hooks 与签名鉴权：`drun_hooks.py`、时间戳/HMAC、会话变量。
5. SQL 校验与结果复用：查询断言/变量存储（`examples/test_sql_*.yaml`）。

## 阶段 4｜业务实战
1. 契约驱动用例：`spec/openapi/ecommerce_api.json` 到 YAML。
   - 更多格式转换与导入实战详见：`docs/CLI.md#format-conversion`（cURL/Postman/HAR/OpenAPI，导入期脱敏与测试套件（Testsuite）生成）。
2. 健康检查与可用性：`testcases/test_health.yaml`。
3. 注册与登录会话：`testcases/test_register.yaml`、`testcases/test_auth.yaml`、`examples/test_register_and_login.yaml`。
4. 身份校验与自检：`examples/test_login_whoami.yaml`。
5. 目录与类目详情：`testcases/test_catalog.yaml`、`testcases/test_category_detail.yaml`。
6. 商品详情与库存一致性（含 SQL 对照）：`examples/test_sql_store_reuse.yaml`。
7. 购物车流程与边界：`testcases/test_cart.yaml`。
8. 订单创建与金额校核：`testcases/test_orders.yaml`。
9. 订单列表与筛选：`testcases/test_orders_list.yaml`。
10. 用户信息与资料：`testcases/test_user_profile.yaml`。
11. 权限与负向矩阵：`testcases/test_admin_negative.yaml`、`examples/test_negative_auth.yaml`。
12. 端到端下单链路：`testcases/test_e2e_purchase.yaml`。
13. 接口性能阈值与时延预算：`examples/test_perf_timing.yaml`。
14. 请求体与编码场景：`examples/test_form_urlencoded.yaml`、`examples/test_multipart_upload.yaml`、`examples/test_headers_merge.yaml`。
15. 鉴权策略示例：`examples/test_static_bearer.yaml`、`examples/test_hmac_sign.yaml`。
16. 重试与跳过策略：`examples/test_skip_and_retry.yaml`。
17. 参数化覆盖策略：`examples/test_params_zipped.yaml`。
18. SQL 连接与覆盖：`examples/test_sql_validate.yaml`、`examples/test_sql_dsn_override.yaml`。
19. 测试套件与标签治理：`testsuites/testsuite_smoke.yaml`、`testsuites/testsuite_regression.yaml`、`testsuites/testsuite_permissions.yaml`。

## 阶段 5｜工程落地
1. 报告产物与定位：HTML 报告（`drun/reporter/html_reporter.py`）、JSON 结果（`drun/reporter/json_reporter.py`）。
2. Allure 集成与历史：结果生成与附件（`drun/reporter/allure_reporter.py`）。
3. 通知集成与失败聚合：飞书/钉钉/邮件（`drun/notifier/{feishu,dingtalk,emailer}.py`、`drun/notifier/{base,format}.py`）。
4. 结构化日志与脱敏：`drun/utils/logging.py`、`drun/utils/mask.py`。
5. cURL 生成与最小复现：`drun/utils/curl.py`。
6. 环境与密钥管理：`.env` 注入与覆盖（`drun/loader/env.py`）。
7. CLI 规范化工具：`drun check`/`drun fix` 规则与一键修复（`drun/cli.py`）。
8. 性能计时与基线：`drun/utils/timeit.py`、`examples/test_perf_timing.yaml`。
9. SQL 校验落地：`drun/db/sql_validate.py`、`drun/models/sql_validate.py`。
10. 测试套件化运行与筛选：标签表达式与测试套件产物（`testsuites/*`）。
11. 提交流程与本地校验：打包与脚本（`pyproject.toml`）。
 
### CI 中的批量转换示例

提示：`drun convert` 要求“文件在前，选项在后”，且不支持无选项转换（至少提供一个选项，如 `--outfile`/`--split-output`/`--redact`/`--placeholders`）。

```bash
# 将存量资产（cURL/Postman）转换为用例，启用导入期脱敏与变量占位
drun convert assets/requests.curl \
  --into testcases/imported.yaml \
  --redact Authorization,Cookie \
  --placeholders

## 如有 Postman 环境文件，可加 --postman-env assets/postman_env.json；否则可省略
drun convert assets/postman.json \
  --split-output \
  --suite-out testsuites/testsuite_postman.yaml \
  --redact Authorization \
  --placeholders

# 运行回归测试套件
drun run testsuites/testsuite_regression.yaml \
  --report reports/run.json \
  --html reports/report.html \
  --env-file .env
```

## 阶段 6｜源码拆解与扩展
1. CLI 与命令体系：`drun/cli.py`（run/check/fix、过滤/报告/通知参数）。
2. 加载器 Loader：`drun/loader/{yaml_loader,collector,env,hooks}.py`（发现/解析/ENV 注入/Hooks 发现）。
3. 数据模型 Models：`drun/models/{config,case,step,request,validators,sql_validate,report}.py`（Pydantic 建模与校验）。
4. 模板引擎：`drun/templating/{engine,builtins,context}.py`（Dollar 表达式、安全求值、内置函数）。
5. 运行器 Runner：`drun/runner/{runner,assertions,extractors}.py`（变量作用域、执行与重试、断言与提取）。
6. HTTP 引擎：`drun/engine/http.py`（httpx 客户端、超时/重试/上传、Authorization 注入）。
7. SQL 与数据校验：`drun/db/sql_validate.py`、`drun/models/sql_validate.py`（DSN、查询与断言、存储复用）。
8. 报告子系统：`drun/reporter/{json_reporter,html_reporter,allure_reporter}.py`（结构化结果、附件与掩码、历史）。
9. 通知子系统：`drun/notifier/{base,format,feishu,dingtalk,emailer}.py`（消息格式化、多渠道与失败聚合）。
10. 工具与基础设施：`drun/utils/{logging,mask,curl,errors,timeit}.py`。
11. Hooks 扩展点：`drun_hooks.py`、`drun/loader/hooks.py`。
12. 规范与自动修复：`drun check/fix` 实现与规则。
13. 示例与用例映射：`examples/*.yaml`、`testcases/*`、`testsuites/*`。
14. 规范与打包：`pyproject.toml`。
15. 规格与资产：`spec/openapi/ecommerce_api.json`。

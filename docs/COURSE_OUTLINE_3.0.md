# Drun 学习课程目录 3.0

## 学习收获（可落地验收）
1. 搭建运行与产物：独立完成安装与运行，输出 HTML 报告、JSON 报告、Allure 结果与结构化日志（示例：`drun run testcases --env-file .env --html reports/report.html --report reports/run.json --allure-results allure-results --log-file logs/run.log --mask-secrets`），说明脱敏效果。
2. 业务回归测试套件：基于现有 `testcases/*` 与 `testsuites/*` 交付冒烟/回归/权限三层测试套件；验收标准：冒烟测试套件稳定全绿且用时 <5 分钟（示例：运行 `testsuites/testsuite_smoke.yaml`）。
3. 标签治理与筛选：按 `smoke/regression/permissions` 标签组织并能用 `-k` 表达式精确筛选（示例：`drun run testcases -k "smoke and not slow"`）。
4. 参数化覆盖：使用压缩参数化覆盖多环境与边界场景（示例：`examples/test_params_zipped.yaml`），验证实例数与期望一致。
5. 鉴权与会话复用：完成登录→带 token 访问链路，验证自动 Authorization 注入与 `auth` 字段生效（示例：`testcases/test_auth.yaml`、`examples/test_login_whoami.yaml`）。
6. 报告与最小复现：从 HTML/JSON/Allure 报告中定位失败，利用 `drun export curl` 生成脱敏、多行/单行可选的 cURL（`--with-comments/--redact/--steps/--shell`）。
7. 资产迁移（格式转换）：使用 `drun convert` 将 cURL/HAR/Postman/OpenAPI 导入（`--split-output/--into/--case-name/--base-url/--tags/--redact/--placeholders`），形成脚本化导入方案。（提示：`drun convert` 要求“文件在前，选项在后”，且不支持无选项转换。）
8. 环境与优先级：通过 `DRUN_ENV` + `env/<name>.yaml` + `.env` + `--vars` 构建多层环境合并，梳理冲突与覆盖策略。
9. 模板与内置函数：熟练 `$var`/`${expr}`、`ENV()` 与 `now/uuid/random_int/base64_encode/hmac_sha256` 等的常见用法与陷阱。
10. Hooks 与签名：掌握 Case/Suite/Step hooks 的调用栈与 `hook_ctx`，实现时间戳/HMAC 签名与上下文注入（示例：`examples/test_hmac_sign.yaml`）。
11. SQL 数据一致性：配置 MySQL 连接（`MYSQL_*` 或 `MYSQL_DSN`），运行 `examples/test_sql_validate.yaml` 与 `examples/test_sql_store_reuse.yaml` 完成金额/库存校验与变量复用。
12. 性能阈值：在关键接口为 `$elapsed_ms` 设置断言阈值（参考 `examples/test_perf_timing.yaml`），形成基线与优化记录。
13. 通知闭环：完成至少一种渠道（飞书/钉钉/邮件）配置并在失败时自动推送摘要（示例：`--notify feishu --notify-only failed --notify-attach-html`）。
14. 安全与合规：启用 `--mask-secrets` 进行日志与报告脱敏；密钥通过 `.env`/环境变量注入；产物不包含敏感明文。
15. 规范化校验：用 `drun check` 校验用例通过、`drun fix` 一键修复常见风格问题；提交前通过本地校验脚本。
16. 阅读和修改源码：完成一次小型修复或扩展（<50 行），`drun check` 通过且示例回归全绿（提交修改文件与验证命令）。
17. CI 门禁：在 CI 运行 `testsuites/testsuite_regression.yaml`，设定通过率/时延门槛并联动通知；产出报告链接与配置片段。

## 阶段 1｜前置与方法论（必修）
1. Python 知识点：语法/数据结构/函数与装饰器/面向对象/异常/上下文管理器/类型注解/异步 async‑await。
2. Python 工程与生态：虚拟环境/venv、包管理/pip、打包/pyproject，`pydantic`/`typer`/`httpx` 基础。
3. 接口测试与自动化测试方法论：金字塔、等价类/边界、幂等/重试、错误码与安全。
4. HTTP/REST 与鉴权：方法/状态码/头/缓存、HMAC/签名、cURL 调试。
5. YAML/JSON/JMESPath：表达式/过滤/提取的高频模式与陷阱。
6. SQL 与数据准备：查询/事务/隔离，断言场景与数据构造。
7. CLI/Git 与工具链：shell、git 分支/PR、Postman/Insomnia、日志溯源。

## 阶段 2｜Drun 速通与基础
1. 结构速览与目录约定：`testcases/`、`testsuites/`、`examples/`、`docs/`、`spec/` 作用与边界；文件命名建议（`test_*.yaml`、`testsuite_*.yaml`），推荐一案一档便于复用。
2. 安装与环境准备：`pip install -e .`、`drun --help`；创建 `.env`、`reports/`、`logs/`；确认 Python 版本与依赖。
3. 首次运行与产物：`drun run testcases --env-file .env --html reports/report.html --report reports/run.json`，认识默认产物与路径（`reports/`、`logs/`）。
4. YAML DSL 入门：`config/steps/request`（`method/url/headers/query/body`）/`extract/validate`；常用比较器 `eq/contains/gt/regex`。
5. 变量与模板基础：`$var` 与 `${expr}` 的区别；作用域优先级（环境 < config.variables < config.parameters < step < CLI）；`ENV()` 读取环境变量与默认值。
6. 环境加载与覆盖：`DRUN_ENV` + `env/<name>.yaml` 的合并策略；`--vars` 临时覆盖；冲突识别与定位思路。
7. 标签与筛选：`config.tags` 用法；`-k` 表达式 `and/or/not` 组合（示例：`-k "smoke and not slow"`）。
8. 失败与重试控制：`--failfast` 行为；Step 级 `timeout/retry`（如场景需要）；失败快照与最小复现建议。
9. 日志与脱敏：`--log-level`、`--log-file`、`--httpx-logs`；`--mask-secrets` 与 `--reveal-secrets` 的适用场景（本地/CI）。
10. 报告阅读与定位：HTML/JSON/Allure 的差异与使用顺序；从报告定位失败步骤与断言，配合 cURL 导出快速复现。
11. 规范化工具：`drun check` 校验（语法/提取前缀/断言目标/Hook 命名/空行），`drun fix` 自动修复（`--only-spacing/--only-hooks`）。
12. 最小用例模板：建议包含 `name/base_url/tags/steps`（提取 + 断言），优先增加状态码与关键字段断言，逐步补充提取与参数化。
13. 常见错误与排查：YAML 缩进/引号、数字与字符串类型混淆、漏写 `$`/花括号、JMESPath 路径不匹配、缺少 `base_url`、大小写不一致。
14. 资产转换引导：先导 `drun convert` 基本用法，明确导入后需手动补充断言/提取与变量占位。
15. 参考与路径：优先阅读 `docs/CLI.md`、`docs/EXAMPLES.md`、`docs/REFERENCE.md`，对照示例快速复制落地。

## 阶段 3｜核心能力
1. 数据提取与断言：JMESPath 常用模式（数组/对象/嵌套），断言可读性与命名（`drun/runner/{extractors,assertions}.py`）。
2. 断言集合与失败定位：多断言分组/短路；错误信息优化与报告阅读顺序（HTML/JSON/Allure）。
3. 变量作用域与生命周期：环境/config.variables/config.parameters/step/CLI 覆盖顺序；同名冲突与临时变量复用。
4. 参数化深化：压缩模式的适用场景与实例数预估；条目级 `parameters` 覆盖（`testsuites/*`）。
5. 模板与渲染：`$var/${expr}`；`ENV()` 默认值；内置函数 `now/uuid/random_int/base64_encode/hmac_sha256`；渲染失败排查。
6. HTTP 稳定性：超时/重试/重定向/证书校验；最小复现 cURL（`drun/utils/curl.py`）。
7. 会话与鉴权：`auth` 字段与自动 Authorization 注入；登录 token 提取与复用；Cookie/跨请求头合并策略（`drun/engine/http.py`）。
8. Hooks 机制：`setup_hooks/teardown_hooks` 调用顺序；`hook_ctx` 可用信息；HMAC/时间戳签名示例（`drun_hooks.py`、`drun/loader/hooks.py`）。
9. 跳过与重试策略：条件跳过与重试边界；避免掩盖真实失败（`examples/test_skip_and_retry.yaml`）。
10. 错误定位与追踪：从报告到日志的定位路径；在 `teardown_hook` 捕获 `request_id` 并回填上下文。
11. 性能阈值与基线：`$elapsed_ms` 阈值设计、P95 监控与回归比对（`drun/utils/timeit.py`）。
12. SQL 校验与结果复用：查询断言、金额/库存等典型场景；变量存储与后续步骤复用（`drun/db/sql_validate.py`、`examples/test_sql_*`）。

## 阶段 4｜业务实战
1. 契约驱动用例：`spec/openapi/ecommerce_api.json` 到 YAML（更多格式转换与导入实战见 `docs/CLI.md` 的 convert 章节，覆盖 OpenAPI/cURL/Postman/HAR，导入期脱敏与 Testsuite 生成）。
2. 健康检查与可用性：`testcases/test_health.yaml`。
3. 注册与登录会话：`testcases/test_register.yaml`、`testcases/test_auth.yaml`、`examples/test_register_and_login.yaml`。
4. 身份校验与自检：`examples/test_login_whoami.yaml`。
5. 目录与类目详情：`testcases/test_catalog.yaml`、`testcases/test_category_detail.yaml`。
6. 商品与库存一致性（含 SQL 对照）：`examples/test_sql_store_reuse.yaml`。
7. 购物车流程与边界：`testcases/test_cart.yaml`。
8. 订单创建与金额校核：`testcases/test_orders.yaml`。
9. 订单列表与筛选：`testcases/test_orders_list.yaml`。
10. 用户信息与资料：`testcases/test_user_profile.yaml`。
11. 权限与负向矩阵：`testcases/test_admin_negative.yaml`、`examples/test_negative_auth.yaml`。
12. 端到端下单链路：`testcases/test_e2e_purchase.yaml`。
13. 接口性能阈值与时延预算：`examples/test_perf_timing.yaml`。
14. 编码与边界场景：`examples/test_form_urlencoded.yaml`、`examples/test_multipart_upload.yaml`、`examples/test_headers_merge.yaml`。
15. 鉴权策略示例：`examples/test_static_bearer.yaml`、`examples/test_hmac_sign.yaml`。
16. 重试与跳过策略：`examples/test_skip_and_retry.yaml`。
17. 参数化覆盖策略：`examples/test_params_zipped.yaml`。
18. SQL 连接与覆盖：`examples/test_sql_validate.yaml`、`examples/test_sql_dsn_override.yaml`。
19. 测试套件与标签治理：`testsuites/testsuite_smoke.yaml`、`testsuites/testsuite_regression.yaml`、`testsuites/testsuite_permissions.yaml`。

## 阶段 5｜工程落地
1. 报告产物与定位：HTML 报告（`drun/reporter/html_reporter.py`）、JSON 结果（`drun/reporter/json_reporter.py`）。
2. Allure 集成与历史：结果生成与附件（`drun/reporter/allure_reporter.py`）。
3. 通知集成与失败聚合：飞书/钉钉/邮件（`drun/notifier/{feishu,dingtalk,emailer}.py`、`drun/notifier/{base,format}.py`）。
4. 结构化日志与脱敏：`drun/utils/logging.py`、`drun/utils/mask.py`（`--mask-secrets` 与 `reveal_secrets`）。
5. cURL 生成与最小复现：`drun/utils/curl.py`。
6. 环境与密钥管理：`.env` 注入与覆盖（`drun/loader/env.py`）。
7. CLI 规范化工具：`drun check`/`drun fix` 规则与一键修复（`drun/cli.py`）。
8. 性能计时与基线：`drun/utils/timeit.py`、`examples/test_perf_timing.yaml`。
9. SQL 校验落地：`drun/db/sql_validate.py`、`drun/models/sql_validate.py`。
10. 测试套件化运行与筛选：标签表达式与测试套件产物（`testsuites/*`）。
11. 提交流程与本地校验：打包与脚本（`pyproject.toml`）。

## CI 中的批量转换示例（建议纳入流水线）

```bash
# 将存量资产（cURL/Postman）转换为用例，导入期脱敏与变量占位
drun convert assets/requests.curl \
  --into testcases/imported.yaml \
  --redact Authorization,Cookie \
  --placeholders

# 如有 Postman 环境文件
drun convert assets/postman.json \
  --split-output \
  --suite-out testsuites/testsuite_postman.yaml \
  --redact Authorization \
  --placeholders

# 运行回归测试套件并产出报告
drun run testsuites/testsuite_regression.yaml \
  --report reports/run.json \
  --html reports/report.html \
  --env-file .env
```

## 阶段 6｜源码拆解与扩展
1. CLI 与命令体系：`drun/cli.py`（run/convert/export/check/fix、过滤/报告/通知参数）。
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

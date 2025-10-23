# Drun 学习课程目录 2.0

> 新版聚焦 CLI 工作流、格式转换/导出全链路与可持续落地能力，覆盖 0.1.x 最新特性。

## 学习成果（可验收任务）
1. **端到端起盘**：安装依赖后执行 `drun run testcases --env-file .env --html reports/report.html --report reports/run.json --allure-results allure-results --log-file logs/run.log --mask-secrets`，生成完整产物并说明脱敏效果。
2. **格式转换迁移**：使用 `drun convert` 将 cURL/HAR/Postman 资产导入，熟练掌握 `--split-output`、`--into`、`--case-name`、`--base-url` 的组合策略；为导入到同一 case/suite 的场景产出可复用脚本。（提示：`drun convert` 要求“文件在前，选项在后”，且不支持无选项转换。）
3. **导出与复现**：运用 `drun export curl` 生成脱敏、多行/单行可选的 cURL；通过 `--with-comments`、`--redact`、`--steps`、`--shell ps` 提供占位符与跨 Shell 复现；输出复现手册。
4. **标签治理**：使用 `-k` 与 `drun tags` 管理测试套件层级，实现冒烟/回归/权限的稳定筛选，并提交治理报告。
5. **参数化/复用**：基于压缩参数化覆盖多环境与边界场景，验证实例数并记录执行结果。
6. **环境管理**：通过 `DRUN_ENV` + `env/<name>.yaml` + `.env` + `--vars` 构建多层环境合并，梳理优先级与冲突解决策略。
7. **模板与内置函数**：熟练 `$var`/`${expr}`、`ENV()` 与 `now`/`uuid`/`random_int`/`hmac_sha256`；解析常见渲染陷阱，并能调试模板异常。
8. **鉴权与会话**：跑通登录→会话→自动 Authorization 注入链路，验证 `auth` 字段与 Token 复用场景。
9. **Hooks 与签名**：掌握 Case/Step/Suite hooks 的调用栈与 `hook_ctx` 内容，编写签名、上下文注入案例。
10. **SQL 校验**：配置 MySQL 连接并运行 `examples/test_sql_validate.yaml`、`examples/test_sql_store_reuse.yaml` 完成数据一致性校验。
11. **性能基线**：围绕 `$elapsed_ms` 设置阈值、输出基线报告，结合 `drun/utils/timeit.py` 分析优化收益。
12. **报告与最小复现**：从 HTML/JSON/Allure 报告中定位失败，复制 cURL/JSON 复现问题并记录流程。
13. **通知闭环**：配置飞书/钉钉/邮件任一渠道，利用 `--notify`、`--notify-only`、`--notify-attach-html` 产出失败聚合通知。
14. **安全与合规**：启用脱敏、管理 `.env`/环境变量，确保日志与报告不泄露敏感信息，并给出审计建议。
15. **CLI 守门**：结合 `drun check`、`drun fix`、`drun tags`、`drun export` 建立提交前检查流水；编写自动化脚本。
16. **架构与源码贡献**：理解 CLI→Loader→Runner→Engine→Reporter→Notifier 调用链，完成一次 <50 行修复或扩展并通过验证。
17. **CI 门禁**：在 CI 配置 `testsuites/testsuite_regression.yaml`，设定通过率/耗时门槛，联动物理通知并提供配置片段与产物链接。

---

## 模块 A｜核心理念与基础工具
- Python 语法与工程生态：venv/pip/pyproject、`pydantic`、`typer`、`httpx`。
- 自动化测试方法论：金字塔、等价类、幂等与重试、错误码治理。
- HTTP/REST 与鉴权：方法/状态码/缓存、HMAC/签名、cURL 调试技巧。
- YAML/JSON/JMESPath：语法、过滤、提取；常见错误模式。
- SQL 与数据准备：事务、隔离级别、断言场景、数据构造。
- CLI/Git/调试工具链：shell、Git 分支/PR、Postman/Insomnia、日志定位。

## 模块 B｜CLI 工作流总览
- 项目结构与入口：README、`drun/cli.py`；run/convert/export/tags/check/fix 命令体系。
- YAML DSL 速览：Case/Step/Request/Validate/Extract。
- 执行基础：`drun run` 参数、`--env-file`、`--vars`、`--html`、`--report`、`--log-file`、`--mask-secrets`。
- 环境加载：`.env`、`env/<name>.yaml`、`DRUN_ENV`、`load_environment` 优先级。
- 日志与报告：默认目录、命名策略、`--httpx-logs`、日志脱敏。

## 模块 C｜格式转换全链路
- cURL 导入：`drun convert sample.curl --into testcases/test_imported.yaml`；对多命令 `--split-output` 命名策略。
- HAR 导入：基于 `entries` 自动拆分，`--case-name`、`--base-url` 的补齐；冲突处理。
- Postman 导入：`drun convert collection.json --split-output --case-name "Postman Demo"`，处理文件夹/变量。
- 导入调试：识别自动推断 base_url、缺失 header/body 场景。
- 导出工作流：`drun export curl testcases --steps 1,3 --redact Authorization --with-comments --multiline`，跨 Shell (`--shell ps`) 与占位符注释 (`# Vars/Exprs`)，结合导出资产编写复现指南。
- 格式转换治理：模板/环境变量保留策略、转换产物归档与版本化建议。
- 实战指南：见 `docs/CLI.md#format-conversion`（覆盖导入期脱敏 `--redact/--placeholders`、Postman `--postman-env/--suite-out`、HAR 去噪筛选、OpenAPI 转换与示例命令）。

## 模块 D｜变量、模板与参数化
- `VarContext` 层级：环境 < config.variables < config.parameters < step < CLI；变量注入策略。
- TemplateEngine 解析流程：`$var`/`${expr}`、`ENV()`、内置函数；防御性渲染。
- 参数化实践：压缩模式；组合策略与测试套件治理。
- 内置函数库：`now`、`uuid`、`random_int`、`base64_encode`、`hmac_sha256`；自定义函数在 Hooks 中扩展。

## 模块 E｜运行器核心能力
- HTTP 引擎：`drun/engine/http.py`，超时、重试、重定向、证书校验、`auth` 字段。
- 数据提取与断言：`drun/runner/{extractors,assertions}.py`，JMESPath、比较器集合、错误提示优化。
- Hooks 机制：`drun_hooks.py`、`drun/loader/hooks.py`；`hook_ctx` 字段详解。
- SQL 校验：`drun/db/sql_validate.py`、`drun/models/sql_validate.py`；金额/库存校验与变量复用。
- 性能阈值：`examples/test_perf_timing.yaml`、`drun/utils/timeit.py`。

## 模块 F｜业务实战演练
- 契约驱动：从 `spec/openapi/ecommerce_api.json` 生成功能用例。
- 健康检查与登录：`testcases/test_health.yaml`、`testcases/test_auth.yaml`、`examples/test_register_and_login.yaml`。
- 业务流程：目录/商品/购物车/订单/权限/端到端下单 (`testcases/test_*`)。
- 鉴权策略：`examples/test_static_bearer.yaml`、`examples/test_hmac_sign.yaml`。
- 编码与边界：`examples/test_form_urlencoded.yaml`、`examples/test_multipart_upload.yaml`、`examples/test_headers_merge.yaml`。
- 重试/跳过：`examples/test_skip_and_retry.yaml`。
- 参数化扩展：`examples/test_params_zipped.yaml`。
- SQL 场景：`examples/test_sql_{validate,store_reuse,dsn_override}.yaml`。
- 测试套件治理：`testsuites/testsuite_{smoke,regression,permissions}.yaml`。

## 模块 G｜工程落地
- 报告体系：`drun/reporter/{html_reporter,json_reporter,allure_reporter}.py`，产物结构与附件策略。
- 通知与失败聚合：`drun/notifier/{feishu,dingtalk,emailer,format}.py`；环境变量/脱敏配置。
- 结构化日志：`drun/utils/logging.py`、`drun/utils/mask.py`，`--mask-secrets` 与 `reveal_secrets` 开关。
- 规范化工具：`drun check`、`drun fix`（`--only-spacing/--only-hooks`）、`drun tags`、`drun export` 协同使用。
- 资产治理：转换产物版本管理、导出脚本归档、报告/日志存储。
- 性能基线：`drun/utils/timeit.py`、CI 中的性能监控策略。
- CI/CD 实践：在流水线运行 `testsuites/testsuite_regression.yaml`，门禁配置与通知，缓存策略与产物共享。
  - CI 批量转换示例：
    ```bash
    # 1) 将已收集的资产转换为可运行用例（导入期脱敏与占位）
    drun convert assets/requests.curl \
      --into testcases/imported.yaml \
      --redact Authorization,Cookie \
      --placeholders

    # 如有 Postman 环境文件，可加 --postman-env assets/postman_env.json；否则可省略
    drun convert assets/postman.json \
      --split-output \
      --suite-out testsuites/testsuite_postman.yaml \
      --redact Authorization \
      --placeholders

    # 2) 运行回归测试套件并产出报告
    drun run testsuites/testsuite_regression.yaml \
      --html reports/report.html \
      --report reports/run.json \
      --env-file .env
    ```

## 模块 H｜源码深度拆解与扩展
- CLI 框架：`drun/cli.py`（run/convert/export/tags/check/fix、通知参数、产物输出、环境加载）。
- Loader：`drun/loader/{yaml_loader,collector,env,hooks}.py`，发现、参数展开、环境合并、hook 注入。
- 数据模型：`drun/models/{config,case,step,request,validators,sql_validate,report}.py`。
- TemplateEngine：`drun/templating/{engine,builtins,context}.py`。
- Runner 核心：`drun/runner/{runner,assertions,extractors}.py`；变量作用域、重试、断言链路。
- HTTP 引擎：`drun/engine/http.py`。
- SQL 校验：`drun/db/sql_validate.py`、`drun/models/sql_validate.py`。
- 报告/通知：`drun/reporter/*`、`drun/notifier/*`。
- 导入/导出实现：`drun/importers/{curl,har,postman}.py`、`drun/exporters/curl.py`。
- 工具库：`drun/utils/{logging,mask,curl,timeit,errors}.py`。
- Hooks 扩展点：`drun_hooks.py`、`drun/loader/hooks.py`。
- 规范与自动修复：定制 Dumper、步骤空行策略、`drun fix` 逻辑。
- 打包与发行：`pyproject.toml`、入口配置、版本元数据。
- 示例资产：`examples/*.yaml`、`testcases/*`、`testsuites/*`、`spec/openapi/ecommerce_api.json`。

---

如需对 2.0 版本继续调整或追加章节，请整理意见后再发起更新。

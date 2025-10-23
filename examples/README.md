示例（Examples）

本目录包含一组最小可运行的示例，演示 Drun 的常见用法与新规范（Suite/Case 级 hooks 需写在 config 内）。

准备工作
- 复制 `.env.example` 为 `.env`，设置 `BASE_URL`；如需登录示例，请设置 `USER_USERNAME/USER_PASSWORD`，或使用“注册+登录”示例。

示例列表
- 用例级 hooks（写在 config 内）：`test_case_hooks.yaml`
  - 演示在用例的 `config.setup_hooks/config.teardown_hooks` 中声明 hooks。
  - 运行：`drun run examples/test_case_hooks.yaml --env-file .env`

- 引用型 Testsuite（在 `testsuites/` 下，通过 `testcases:` 引用用例）
  - 冒烟套件：`testsuites/testsuite_smoke.yaml`
    - 运行：`drun run testsuites/testsuite_smoke.yaml --env-file .env`
  - 回归套件：`testsuites/testsuite_regression.yaml`
    - 运行：`drun run testsuites/testsuite_regression.yaml --env-file .env`
  - 权限套件：`testsuites/testsuite_permissions.yaml`
    - 运行：`drun run testsuites/testsuite_permissions.yaml --env-file .env`

- 提取 token 并自动注入 Authorization：`test_login_whoami.yaml`
  - 第一步登录提取 `token`，第二步访问 `GET /api/v1/users/me`；未手动写 `Authorization` 头，运行器会自动注入 `Bearer $token`。
  - 需要 `.env` 中存在有效账号。
  - 运行：`drun run examples/test_login_whoami.yaml --env-file .env`

- 自注册 + 登录 + whoami：`test_register_and_login.yaml`
  - 无需预置账号，示例自动注册随机用户并登录，再访问 `GET /api/v1/users/me`。
  - 运行：`drun run examples/test_register_and_login.yaml --env-file .env`

批量运行
- 运行整个示例目录：`drun run examples --env-file .env`

注意
- 若运行登录相关示例失败，请先检查 `.env` 的用户名/密码是否有效，或直接使用“自注册 + 登录”示例。
- 参数化（压缩参数）：`test_params_zipped.yaml`
  - 展示 `config.parameters` 的压缩写法，确保多变量按行成组注入（也支持在 testsuite 条目级通过 `parameters` 覆盖）。
  - 运行：`drun run examples/test_params_zipped.yaml --env-file .env`

- SQL 校验（需要数据库连接）：`test_sql_validate.yaml`
   - 示例展示 `sql_validate` 的写法；需在环境中提供 `MYSQL_*` 或 `MYSQL_DSN`。
   - 运行：`drun run examples/test_sql_validate.yaml --env-file .env`

 - HMAC 加签（需要 APP_SECRET）：`test_hmac_sign.yaml`
   - 使用 `setup_hook_hmac_sign` 对请求进行签名，演示自定义安全头注入。
   - 运行：`DRUN_HOOKS_FILE=drun_hooks.py APP_SECRET=xxxx drun run examples/test_hmac_sign.yaml --env-file .env`

- 断言与提取合集：`test_assertions_showcase.yaml`
  - 针对产品列表与详情，演示 contains/regex/gt 等断言与提取。

- 性能耗时断言：`test_perf_timing.yaml`
  - 使用 `$elapsed_ms` 断言接口耗时在 2 秒以内。

- 参数化示例
  - 压缩参数：`test_params_zipped.yaml`
  - Testsuite 条目级参数化示例：`testsuites/testsuite_regression.yaml`

- Headers 合并与覆盖：`test_headers_merge.yaml`
  - 演示 `config.headers` 与 `step.headers` 的覆盖关系（示例仅检查 200）。

- Hooks 上下文演示：`test_hook_contexts.yaml`
  - 演示签名与提取 `request_id` 的 hooks 作用。

- 鉴权与负例
  - 未登录负例：`test_negative_auth.yaml`（预期 401/403）
  - 静态 Bearer：`test_static_bearer.yaml`（通过 `STATIC_BEARER` 提供 token；未提供则跳过）

- 跳过与重试：`test_skip_and_retry.yaml`
  - 展示 `skip` 字段与 `retry/retry_backoff` 的用法。

- SQL 进阶（基于可选 DSN）
  - 结果存储与复用：`test_sql_store_reuse.yaml`（当 `MYSQL_DSN` 存在时执行）
  - 覆盖 DSN：`test_sql_dsn_override.yaml`（步骤级 `dsn` 覆盖）

- 其他内容类型（模板）
  - 表单：`test_form_urlencoded.yaml`（默认跳过，示例模板）
  - 文件上传：`test_multipart_upload.yaml`（默认跳过，示例模板）

# Drun 示例（Examples）

本目录包含 Drun 的各种示例，帮助你快速上手和学习最佳实践。

## 📁 目录结构

```
examples/
├── README.md              # 本文件
├── basic-examples/        # 基础功能示例（单个 YAML 文件）
│   ├── test_assertions_showcase.yaml
│   ├── test_case_hooks.yaml
│   ├── test_login_whoami.yaml
│   └── ...
└── example-project/       # 完整项目示例（包含测试用例、套件、钩子等）
    ├── README.md
    ├── drun_hooks.py
    ├── testcases/
    ├── testsuites/
    ├── logs/
    └── reports/
```

---

## 🚀 快速开始

### 1. 基础示例（basic-examples/）

这些是独立的 YAML 文件，演示 Drun 的各种功能特性。适合快速学习和测试单个功能。

### 2. 完整项目示例（example-project/）

这是一个完整的项目结构示例，展示了如何组织真实项目中的测试用例、测试套件、自定义钩子等。

**推荐从这里开始**，查看 [example-project/README.md](example-project/README.md) 了解详情。

---

## 📚 基础示例列表

### 准备工作
- 复制项目根目录的 `.env.example` 为 `.env`，设置 `BASE_URL`
- 如需登录示例，请设置 `USER_USERNAME/USER_PASSWORD`，或使用"注册+登录"示例

### 示例分类

#### 🔐 认证与授权
- **用例级 hooks**：`basic-examples/test_case_hooks.yaml`
  - 演示在用例的 `config.setup_hooks/config.teardown_hooks` 中声明 hooks
  - 运行：`drun run examples/basic-examples/test_case_hooks.yaml --env-file .env`

- **提取 token 并自动注入**：`basic-examples/test_login_whoami.yaml`
  - 第一步登录提取 `token`，第二步访问 `GET /api/v1/users/me`
  - 运行器会自动注入 `Bearer $token`
  - 运行：`drun run examples/basic-examples/test_login_whoami.yaml --env-file .env`

- **自注册 + 登录 + whoami**：`basic-examples/test_register_and_login.yaml`
  - 无需预置账号，自动注册随机用户并登录
  - 运行：`drun run examples/basic-examples/test_register_and_login.yaml --env-file .env`

- **未登录负例**：`basic-examples/test_negative_auth.yaml`（预期 401/403）
- **静态 Bearer**：`basic-examples/test_static_bearer.yaml`（通过 `STATIC_BEARER` 提供 token）

#### 📊 断言与提取
- **断言与提取合集**：`basic-examples/test_assertions_showcase.yaml`
  - 演示 contains/regex/gt 等断言与提取
  
- **性能耗时断言**：`basic-examples/test_perf_timing.yaml`
  - 使用 `$elapsed_ms` 断言接口耗时在 2 秒以内

#### 🔄 参数化
- **压缩参数**：`basic-examples/test_params_zipped.yaml`
  - 展示 `config.parameters` 的压缩写法
  - 运行：`drun run examples/basic-examples/test_params_zipped.yaml --env-file .env`
- **CSV 参数化**：`basic-examples/test_params_csv.yaml`
  - 展示 `config.parameters` 中的 CSV 引入
  - 运行：`drun run examples/basic-examples/test_params_csv.yaml --env-file .env`

#### 🗄️ SQL 校验
- **SQL 校验**：`basic-examples/test_sql_validate.yaml`
  - 需在环境中提供 `MYSQL_*` 或 `MYSQL_DSN`
  - 运行：`drun run examples/basic-examples/test_sql_validate.yaml --env-file .env`

- **结果存储与复用**：`basic-examples/test_sql_store_reuse.yaml`
- **覆盖 DSN**：`basic-examples/test_sql_dsn_override.yaml`

#### 🔒 安全与签名
- **HMAC 加签**：`basic-examples/test_hmac_sign.yaml`
  - 使用 `setup_hook_hmac_sign` 对请求进行签名
  - 运行：`DRUN_HOOKS_FILE=examples/example-project/drun_hooks.py APP_SECRET=xxxx drun run examples/basic-examples/test_hmac_sign.yaml --env-file .env`

#### 🔧 高级功能
- **Headers 合并与覆盖**：`basic-examples/test_headers_merge.yaml`
  - 演示 `config.headers` 与 `step.headers` 的覆盖关系

- **Hooks 上下文演示**：`basic-examples/test_hook_contexts.yaml`
  - 演示签名与提取 `request_id` 的 hooks 作用

- **跳过与重试**：`basic-examples/test_skip_and_retry.yaml`
  - 展示 `skip` 字段与 `retry/retry_backoff` 的用法

#### 📤 其他内容类型
- **表单**：`basic-examples/test_form_urlencoded.yaml`（默认跳过，示例模板）
- **文件上传**：`basic-examples/test_multipart_upload.yaml`（默认跳过，示例模板）

---

## 🏃 批量运行

```bash
# 运行所有基础示例
drun run examples/basic-examples --env-file .env

# 运行完整项目示例
cd examples/example-project
drun run testcases/ --env-file .env
```

---

## 💡 提示

- 若运行登录相关示例失败，请先检查 `.env` 的用户名/密码是否有效
- 推荐先查看 [example-project/](example-project/) 了解完整项目结构
- 更多文档请参考 [../docs/](../docs/)

# Drun 基础示例

本目录包含独立的 YAML 测试文件，每个文件演示 Drun 的一个或多个功能特性。

## 📚 示例列表

### 🔐 认证与授权
- `test_case_hooks.yaml` - 用例级 hooks 演示
- `test_login_whoami.yaml` - 登录并自动注入 token
- `test_register_and_login.yaml` - 自注册 + 登录流程
- `test_negative_auth.yaml` - 未登录负例测试
- `test_static_bearer.yaml` - 静态 Bearer token

### 📊 断言与提取
- `test_assertions_showcase.yaml` - 各种断言类型演示
- `test_perf_timing.yaml` - 性能耗时断言

### 🔄 参数化
- `test_params_zipped.yaml` - 压缩参数写法

### 🗄️ SQL 校验
- `test_sql_validate.yaml` - SQL 校验基础
- `test_sql_store_reuse.yaml` - SQL 结果存储与复用
- `test_sql_dsn_override.yaml` - 覆盖 DSN 配置

### 🔒 安全与签名
- `test_hmac_sign.yaml` - HMAC 签名演示

### 🔧 高级功能
- `test_headers_merge.yaml` - Headers 合并与覆盖
- `test_hook_contexts.yaml` - Hooks 上下文演示
- `test_skip_and_retry.yaml` - 跳过与重试

### 📤 其他内容类型
- `test_form_urlencoded.yaml` - 表单提交
- `test_multipart_upload.yaml` - 文件上传

## 🚀 快速开始

```bash
# 运行单个示例
drun run examples/basic-examples/test_login_whoami.yaml --env-file .env

# 运行所有示例
drun run examples/basic-examples --env-file .env

# 使用标签过滤
drun run examples/basic-examples --tags smoke --env-file .env
```

## 💡 提示

- 这些示例是独立的，可以单独运行
- 如需完整项目结构示例，请查看 [../example-project/](../example-project/)
- 更多文档请参考 [../../docs/](../../docs/)


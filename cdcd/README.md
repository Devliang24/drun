# Drun API 测试项目

本项目使用 [Drun](https://github.com/Devliang24/drun) 框架进行 HTTP API 自动化测试。

## 📁 项目结构

```
.
├── testcases/              # 测试用例目录
│   ├── test_demo.yaml      # 完整认证流程示例
│   ├── test_api_health.yaml # 健康检查示例
│   ├── test_performance.yaml # HTTP 性能分析示例
│   ├── test_db_assert.yaml # 数据库断言示例
│   └── test_import_users.yaml # CSV 参数化用例
├── testsuites/             # 测试套件目录
│   ├── testsuite_smoke.yaml # 冒烟测试套件
│   └── testsuite_csv.yaml  # CSV 示例套件
├── data/                   # 数据文件目录
│   └── users.csv           # CSV 参数数据
├── converts/               # 格式转换源文件
│   ├── sample.curl         # cURL 命令示例
│   └── README.md           # 转换命令说明
├── reports/                # HTML/JSON 报告输出
├── logs/                   # 日志文件输出
├── .env                    # 环境变量配置
├── drun_hooks.py           # 自定义 Hooks 函数
└── README.md               # 本文档
```

## 🚀 快速开始

### 1. 安装 Drun

```bash
pip install -e /path/to/drun
# 或者从 GitHub 安装（如果已发布）
# pip install drun
```

### 2. 配置环境变量

编辑 `.env` 文件，设置你的 API 基础地址：

```env
BASE_URL=http://localhost:8000
USER_USERNAME=test_user
USER_PASSWORD=test_pass123
```

### 3. 运行测试

```bash
# 运行单个测试用例
drun run testcases/test_api_health.yaml

# 运行数据库断言示例
drun run testcases/test_db_assert.yaml

# 运行批量 SQL 断言示例（多变量/列表/索引切片）
drun run testcases/test_db_assert_batch.yaml

# 运行无序对象数组断言示例（多 contains 与过滤器）
drun run testcases/test_db_assert_unordered.yaml


# 运行整个测试目录
drun run testcases

# 运行测试套件
drun run testsuites/testsuite_smoke.yaml

# 运行 CSV 数据驱动示例
drun run testcases/test_import_users.yaml

# 或运行 CSV 套件（包含相同用例）
drun run testsuites/testsuite_csv.yaml

# 使用标签过滤
drun run testcases -k "smoke and not slow"

# 生成 HTML 报告
drun run testcases --html reports/report.html

# 启用详细日志
drun run testcases --log-level debug

# 生成 JSON 报告并在用例中用 $elapsed_ms 做性能断言
drun run testcases --report reports/run.json
```

> 提示：未显式指定 `--env-file` 时会自动读取当前目录的 `.env`。如果需要加载其他文件，可运行如 `drun run testcases --env-file configs/staging.env`。
>
> 性能分析：自 2.1.0 起移除了 httpstat 分解视图；请在用例断言中使用 `$elapsed_ms`，或借助 `curl -w`/APM/k6 等工具进行更深入的性能测试与监控。

### 4. 查看报告

测试运行后，查看生成的报告：

```bash
# HTML 报告（浏览器打开）
open reports/report-*.html

# JSON 报告（供 CI/CD 集成）
cat reports/run.json
```

## 📊 数据驱动示例（CSV）

- CSV 数据文件：`data/users.csv`
- 对应用例：`testcases/test_import_users.yaml`
- 示例套件：`testsuites/testsuite_csv.yaml`
- 默认假设 `BASE_URL` 指向 [httpbin](https://httpbin.org)，以便 `/anything` 接口回显请求数据。

运行命令：

```bash
drun run testcases/test_import_users.yaml

# 或运行套件
drun run testsuites/testsuite_csv.yaml
```

> 疑似失败时，可检查 CSV 内容与环境变量是否匹配，例如确认 `BASE_URL` 是否对外提供 `/anything` 接口。

## 🗄️ 数据库断言示例

- 关联 Hook：`setup_hook_assert_sql`（前置 SQL 校验）、`expected_sql_value`（在 `validate` 预期值中执行查询）。
- 对应用例：`testcases/test_db_assert.yaml`
- 依赖环境：在 `.env` 中配置 `MYSQL_CONFIG`，并确保数据库可连通。

运行命令：

```bash
drun run testcases/test_db_assert.yaml
```

用例会先在步骤前执行 `setup_hook_assert_sql` 判定数据库中是否存在目标记录，并在断言阶段通过 `expected_sql_value` 获取最新字段值用于对比，从而实现“仅保留一种断言写法”的 SQL 校验。

## 📝 编写测试用例

### 基本结构

```yaml
config:
  name: 测试用例名称
  base_url: ${ENV(BASE_URL)}
  tags: [smoke, p0]

steps:
  - name: 步骤名称
    request:
      method: GET
      path: /api/endpoint
    validate:
      - eq: [status_code, 200]
      - eq: [$.data.status, success]
```

### 变量和提取

```yaml
steps:
  - name: 登录
    request:
      method: POST
      path: /api/auth/login
      body:
        username: ${ENV(USER_USERNAME)}
        password: ${ENV(USER_PASSWORD)}
    extract:
      token: $.data.access_token  # 提取 token
    validate:
      - eq: [status_code, 200]

  - name: 访问受保护资源
    request:
      method: GET
      path: /api/users/me
      headers:
        Authorization: Bearer $token  # 使用提取的 token
    validate:
      - eq: [status_code, 200]
```

### 使用 Hooks

```yaml
steps:
  - name: 调用需要签名的接口
    setup_hooks:
      - ${setup_hook_sign_request($request)}
    request:
      method: POST
      path: /api/secure/endpoint
    validate:
      - eq: [status_code, 200]
```

## 🔄 格式转换

将现有的 API 请求转换为 Drun 测试用例：

### cURL 转 YAML

```bash
drun convert converts/curl/sample.curl \
  --outfile testcases/from_curl.yaml \
  --redact Authorization \
  --placeholders
```

### Postman Collection 转 YAML

```bash
drun convert your_collection.json \
  --split-output \
  --suite-out testsuites/from_postman.yaml \
  --redact Authorization \
  --placeholders
```

### HAR 文件转 YAML

```bash
drun convert recording.har \
  --exclude-static \
  --only-2xx \
  --outfile testcases/from_har.yaml
```

更多转换选项请查看 `converts/README.md`。

## 🏷️ 标签管理

查看项目中使用的所有标签：

```bash
drun tags testcases
```

使用标签过滤测试：

```bash
# 运行 smoke 测试
drun run testcases -k "smoke"

# 排除 slow 测试
drun run testcases -k "not slow"

# 组合条件
drun run testcases -k "(smoke or regression) and not flaky"
```

## 🔍 验证和检查

验证 YAML 文件语法：

```bash
drun check testcases
```

自动修复格式问题：

```bash
drun fix testcases
```

## 📊 CI/CD 集成

### GitHub Actions 示例

```yaml
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install Drun
        run: pip install -e /path/to/drun

      - name: Run Tests
        env:
          BASE_URL: ${{ secrets.API_BASE_URL }}
          USER_USERNAME: ${{ secrets.TEST_USERNAME }}
          USER_PASSWORD: ${{ secrets.TEST_PASSWORD }}
        run: |
          drun run testcases \
            --html reports/report.html \
            --report reports/run.json

      - name: Upload Reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-reports
          path: reports/
```

### 性能监控示例

在 CI 中通过断言约束响应时间，避免性能回退：

```yaml
      - name: Run API tests with latency guard
        run: |
          drun run testcases --report reports/run-${{ github.sha }}.json
```

建议：
- 在用例中为关键接口添加耗时断言：`- le: [$elapsed_ms, 2000]`
- 持续性能测试可使用 `k6`/`wrk`，错误追踪用 APM（如 SkyWalking、Jaeger）。

## 📚 更多资源

- [Drun 官方文档](https://github.com/Devliang24/drun)
- [完整参考文档](https://github.com/Devliang24/drun/blob/main/docs/REFERENCE.md)
- [格式转换指南](https://github.com/Devliang24/drun/blob/main/docs/FORMAT_CONVERSION.md)
- [CI/CD 集成示例](https://github.com/Devliang24/drun/blob/main/docs/CI_CD.md)

## 🐛 问题排查

### 常见问题

1. **找不到 .env 文件**
   - 确保 `.env` 文件在项目根目录
   - 使用 `--env-file` 指定路径

2. **BASE_URL 缺失**
   - 检查 `.env` 文件中是否配置了 `BASE_URL`
   - 或通过 `--vars base_url=http://...` 传递

3. **变量未定义**
   - 检查变量名拼写
   - 确认变量在 `config.variables` 或 `extract` 中定义

### 启用调试日志

```bash
drun run testcases --log-level debug --httpx-logs --env-file .env
```

## 📄 许可证

本项目使用 MIT 许可证。

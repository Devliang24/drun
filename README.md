# Drun

<div align="center">

**零代码 HTTP API 测试框架 · 基于 YAML DSL · 5 分钟上手**

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.3.9-orange)]()

[快速开始](#-快速开始-5-分钟) • [核心特性](#-核心特性) • [核心概念](#-核心概念) • [示例](#-实战示例) • [格式转换](docs/FORMAT_CONVERSION.md) • [CLI](docs/CLI.md) • [Reference](docs/REFERENCE.md) • [命名规范](docs/NAMING_CONVENTION.md) • [CI/CD](docs/CI_CD.md)

</div>

---

## 📖 项目简介

Drun 是一个**极简、强大、生产就绪**的 HTTP API 测试框架。使用清晰的 YAML 语法编写测试用例，无需编写代码，5 分钟即可完成第一个测试。

```yaml
# 就是这么简单！
config:
  name: 健康检查
  base_url: ${ENV(BASE_URL)}

steps:
  - name: 检查 API 状态
    request:
      method: GET
      url: /health
    validate:
      - eq: [status_code, 200]
      - eq: [$.data.status, "healthy"]
```

---

 

### 💡 为什么选择 Drun？

| 特性 | Drun | 其他工具 |
|------|-----------|----------|
| **零代码** | ✅ 纯 YAML，无需编程 | ❌ 需要 Python/JavaScript 代码 |
| **学习曲线** | ✅ 5 分钟上手 | ⚠️ 需要学习测试框架 |
| **模板系统** | ✅ 简洁的 `${expr}` 语法 | ⚠️ 复杂的模板引擎 |
| **格式转换** | ✅ 统一 `convert` 命令智能识别格式 | ❌ 需要手动编写或第三方工具 |
| **数据库验证** | ✅ 内置 SQL 断言 | ❌ 需要额外开发 |
| **CI/CD 就绪** | ✅ 开箱即用 | ⚠️ 需要配置 |
| **报告系统** | ✅ HTML + JSON + 通知 | ⚠️ 需要集成第三方 |

### 🎯 适用场景

- ✅ **接口测试**：REST API、微服务接口验证
- ✅ **E2E 测试**：完整业务流程测试
- ✅ **冒烟测试**：快速验证服务可用性
- ✅ **回归测试**：CI/CD 流水线集成
- ✅ **性能监控**：响应时间断言

---

## ⚡ 核心特性

### 🔥 开箱即用

- **零配置启动**：`pip install -e . && drun run testcases`
- **YAML DSL**：声明式测试用例（Case），人类可读
- **智能变量管理**：6 层作用域，自动 token 注入
- **JMESPath 提取**：强大的 JSON 数据提取能力
- **智能格式转换**：统一的 `drun convert` 命令，根据文件后缀自动识别 cURL/Postman/HAR 格式，支持双向转换与 `--split-output` 单步导出

### 🚀 高级功能

- **Hooks 系统**：测试套件（Suite）/用例（Case）/步骤（Step）三级生命周期钩子，支持请求签名、数据准备
- **SQL 验证**：内置 MySQL 支持，查询结果断言与提取列结果为变量
- **参数化测试**：压缩模式（zipped），保证多参数按行成组传递
- **重试机制**：指数退避，容错不稳定接口

### 📊 企业级特性

- **专业报告**：
  - 交互式 HTML 报告（一键复制 JSON/cURL，ES5 兼容，支持旧浏览器和 file:// 协议）
  - 结构化 JSON 报告（CI/CD 集成）
  - Allure 集成（趋势分析、附件丰富）
- **通知集成**：飞书卡片/文本、钉钉文本/Markdown、邮件 HTML/附件，失败聚合通知
- **安全保护**：敏感数据自动脱敏（headers/body/环境变量），支持 `--mask-secrets` 选项
- **调试友好**：
  - Rich 彩色输出
  - cURL 命令生成（使用 `--data-raw`、JSON 自动格式化、自动 Content-Type）
  - 详细日志（支持 `--log-level debug`、`--httpx-logs`）
  - 智能错误诊断（YAML 缩进错误提示、精准行号定位）

---

## 🚀 快速开始 (5 分钟)

### 1. 安装

```bash
# 克隆项目
git clone https://github.com/Devliang24/drun.git
cd drun

# 安装（开发模式）
pip install -e .

# 验证安装
drun --help
```

### 2. 配置环境

创建 `.env` 文件：

```env
BASE_URL=https://api.example.com
USER_USERNAME=test_user
USER_PASSWORD=test_pass
# 可选：某些测试可能需要以下变量
# SHIPPING_ADDRESS=1 Test Road, Test City
# API_KEY=demo-api-key
# APP_SECRET=demo-app-secret
```

### 3. 编写第一个测试

创建 `testcases/test_hello.yaml`：

```yaml
config:
  name: 我的第一个测试
  base_url: ${ENV(BASE_URL)}
  tags: [smoke]

steps:
  - name: 健康检查
    request:
      method: GET
      url: /health
    validate:
      - eq: [status_code, 200]
      - eq: [$.success, true]
```

### 4. 运行测试

```bash
# 运行测试
drun run testcases/test_hello.yaml --env-file .env

# 生成 HTML 报告
drun run testcases --html reports/report.html --env-file .env

# 使用标签过滤
drun run testcases -k "smoke" --env-file .env
```

> 💡 **环境别名**：传入 `--env-file dev` 会自动解析为 `.env.dev`（同理 `staging` -> `.env.staging`）。如果需要指定其他路径，仍可直接提供完整文件名。

### 5. 查看结果

```
Filter expression: None
[RUN] Discovered files: 1 | Matched cases: 1 | Failfast=False
[CASE] Start: 我的第一个测试 | params={}
[CASE] Result: 我的第一个测试 | status=passed | duration=145.3ms
Total: 1 Passed: 1 Failed: 0 Skipped: 0 Duration: 145.3ms
HTML report written to reports/report.html
```

🎉 **恭喜！**你已经完成了第一个 API 测试。打开 `reports/report.html` 查看详细报告。

### 6. 快速转换现有请求（可选）

如果你已有 cURL 命令、Postman Collection 或浏览器 HAR 记录，可以快速转换为 YAML：

注意：`drun convert` 要求“文件在前，选项在后”，且不支持无选项转换（需至少提供一个选项，如 `--outfile`/`--split-output`/`--redact`/`--placeholders`）。

- 正确：`drun convert requests.curl --outfile testcases/from_curl.yaml`
- 错误：`drun convert --outfile testcases/from_curl.yaml requests.curl`

```bash
# cURL → 用例（脱敏 + 变量占位）
drun convert requests.curl --outfile testcases/from_curl.yaml --redact Authorization,Cookie --placeholders

# Postman → 用例（如有环境文件，可加 --postman-env postman_env.json；否则可省略）
drun convert api_collection.json \
  --split-output \
  --suite-out testsuites/testsuite_postman.yaml \
  --redact Authorization \
  --placeholders

# HAR → 用例（过滤静态/仅保留 2xx/正则排除）
drun convert recording.har --exclude-static --only-2xx --exclude-pattern '(\.png$|/cdn/)' --outfile testcases/from_har.yaml

# OpenAPI → 用例（按 tag 过滤，多文件输出）
drun convert-openapi spec/openapi/ecommerce_api.json --tags users,orders --split-output --outfile testcases/from_openapi.yaml --redact Authorization --placeholders
```

**提示**：更多“转换实战”示例见下方「drun convert - 智能格式转换」一节。

---

## 📚 核心概念

### 测试用例（Case）结构

一个测试用例（Case）包含配置和测试步骤（Step）：

```yaml
config:                              # 配置块
  name: 测试用例名称                  # 必需
  base_url: https://api.example.com  # 基础 URL
  variables:                         # 用例级变量
    api_key: my-key
  tags: [smoke, p0]                  # 标签（用于过滤）

steps:                               # 测试步骤（Step）列表
  - name: 步骤 1                      # 步骤名称
    request:                         # HTTP 请求定义
      method: GET                    # HTTP 方法
      url: /api/users                # 路径（相对于 base_url）
    validate:                        # 断言列表
      - eq: [status_code, 200]       # 状态码断言
```

### Dollar 模板语法

Drun 使用简洁的 **Dollar 表达式** `${...}` 进行变量插值和函数调用：

```yaml
# 1. 简单变量引用
url: /users/$user_id                 # 等同于 /users/123

# 2. 函数调用（花括号）
headers:
  X-Timestamp: ${ts()}               # 调用自定义函数（需在 drun_hooks.py 中定义）
  X-Signature: ${md5($api_key)}      # 函数嵌套、参数可以是变量

# 3. 环境变量读取
base_url: ${ENV(BASE_URL)}           # 读取环境变量（必需）
api_key: ${ENV(API_KEY, default)}    # 带默认值（可选参数）

# 4. 算术运算
body:
  user_id: ${int($user_id) + 1}      # 支持基本运算（类型转换 + 计算）
  total: ${float($price) * $quantity}
```

> **提示**：`$var` 是 `${var}` 的简写形式，两者完全等价。复杂表达式必须使用 `${...}` 格式。

### 变量作用域优先级

变量查找顺序（**从高到低**）：

```
1. CLI 覆盖      --vars key=value (最高优先级)
2. 步骤变量      steps[].variables (当前步骤内有效)
3. 配置变量      config.variables (用例级全局)
4. 参数变量      config.parameters (参数化测试时注入)
5. 提取变量      steps[].extract (从当前步骤响应提取，存入会话供后续步骤使用)
```

> **注意**：`${ENV(KEY)}` 用于读取操作系统环境变量，不属于变量作用域的一部分，而是模板引擎的内置函数。

示例：

```yaml
config:
  variables:
    user_id: 100        # 优先级 3：配置变量（用例级全局）
  parameters:
    - user_id: [1, 2]       # 优先级 4：参数变量会被配置变量覆盖

steps:
  - name: 登录
    request:
      url: /api/login
    extract:
      user_id: $.data.id  # 优先级 5：从响应提取，存入会话
                          # 提取后对本步骤及后续所有步骤可见

  - name: 创建订单
    request:
      url: /api/orders/$user_id  # 使用提取的 user_id（来自登录响应）

  - name: 查看订单详情
    variables:
      user_id: 999      # 优先级 2：步骤变量（仅当前步骤内最高）
    request:
      url: /api/users/$user_id  # 使用 999（步骤变量覆盖提取变量）
```

---

## 🔧 常用功能

### 断言和验证

支持丰富的断言器：

| 断言器 | 说明 | 示例 |
|--------|------|------|
| `eq` | 等于 | `- eq: [status_code, 200]` |
| `ne` | 不等于 | `- ne: [$.error, null]` |
| `lt` / `le` | 小于 / 小于等于 | `- lt: [$elapsed_ms, 1000]` |
| `gt` / `ge` | 大于 / 大于等于 | `- gt: [$.count, 0]` |
| `contains` | 包含子串/元素 | `- contains: [$.message, "success"]` |
| `not_contains` | 不包含 | `- not_contains: [$.errors, "fatal"]` |
| `regex` | 正则匹配 | `- regex: [$.email, ".*@example\\.com"]` |
| `len_eq` | 长度等于 | `- len_eq: [$.items, 10]` |
| `in` | 元素在集合中 | `- in: ["admin", $.roles]` |

**检查目标**：

```yaml
validate:
  - eq: [status_code, 200]            # 状态码
  - eq: [headers.Content-Type, "application/json"]  # 响应头
  - eq: [$.data.user.id, 123]         # 响应体（JMESPath）
  - lt: [$elapsed_ms, 500]            # 响应时间（毫秒）
```

### 数据提取 (JMESPath)

从响应中提取数据供后续步骤使用：

```yaml
steps:
  - name: 登录
    request:
      method: POST
      url: /api/auth/login
      body:
        username: admin
        password: pass123
    extract:
      token: $.data.access_token      # 提取 token
      user_id: $.data.user.id          # 提取用户 ID
      role: $.data.user.role           # 提取角色
    validate:
      - eq: [status_code, 200]

  - name: 获取用户信息
    request:
      method: GET
      url: /api/users/$user_id         # 使用提取的 user_id
      headers:
        Authorization: Bearer $token    # 使用提取的 token
    validate:
      - eq: [$.data.role, $role]       # 使用提取的 role
```

**常用 JMESPath 模式**：

```yaml
extract:
  # 基础路径
  user_id: $.data.user.id              # 嵌套对象
  first_name: $[0].name                # 数组第一个元素

  # 数组操作
  all_ids: $.data.items[*].id          # 所有 ID
  first_id: $.data.items[0].id         # 第一个 ID

  # 响应元数据
  content_type: $headers.Content-Type   # 响应头
  status: $status_code                  # 状态码
```

### Token 自动注入

提取名为 `token` 的变量后，后续请求自动添加 `Authorization: Bearer {token}` 头：

```yaml
steps:
  - name: 登录
    request:
      method: POST
      url: /api/auth/login
      body:
        username: ${ENV(USER_USERNAME)}
        password: ${ENV(USER_PASSWORD)}
    extract:
      token: $.data.access_token        # 提取 token

  - name: 访问受保护资源
    request:
      method: GET
      url: /api/users/me
      # 无需手动设置 Authorization 头，自动注入！
    validate:
      - eq: [status_code, 200]
```

> **注意**：如果步骤显式设置了 `Authorization` 头，则不会自动注入。

### 标签过滤

使用逻辑表达式过滤要运行的测试：

```bash
# 运行 smoke 测试
drun run testcases -k "smoke"

# 同时包含两个标签
drun run testcases -k "smoke and regression"

# 任一标签匹配
drun run testcases -k "smoke or p0"

# 排除慢速测试
drun run testcases -k "not slow"

# 复杂表达式
drun run testcases -k "(smoke or regression) and not slow and not flaky"
```

**标签定义**：

```yaml
config:
  name: 用户登录测试
  tags: [smoke, auth, p0]    # 定义多个标签
```

想快速查看项目中已有的标签，可使用 CLI：

```bash
drun tags              # 扫描默认的 testcases 目录
drun tags testsuites   # 指定其它目录
```

**输出格式**：

```
[OK] testcases/test_login.yaml -> 1 cases
[OK] testcases/test_health.yaml -> 1 cases

Tag Summary:
- smoke: 2 cases
    • 健康检查 -> testcases/test_health.yaml
    • 用户登录测试 -> testcases/test_login.yaml
- auth: 1 cases
    • 用户登录测试 -> testcases/test_login.yaml
- p0: 1 cases
    • 用户登录测试 -> testcases/test_login.yaml
```

输出包含：
- **文件扫描日志**：显示每个文件的解析状态和用例数量
- **标签汇总**：按字母序列出所有标签，每个标签显示用例数量和详细的用例名称与文件路径

---

## 🔄 格式转换

详尽的转换/导出攻略请查看 [docs/FORMAT_CONVERSION.md](docs/FORMAT_CONVERSION.md)。该文档按资产类型整理了高频命令、脱敏策略、导出组合以及常见问题排查，风格与 CI/CD 文档保持一致。命令的完整参数说明仍可在 [docs/CLI.md](docs/CLI.md) 中查阅。

---

## 🎨 高级功能

### Hooks 系统

Hooks 允许在测试生命周期的不同阶段执行自定义 Python 函数。

> **提示**：项目根目录已提供 `drun_hooks.py` 示例文件，包含常用的模板辅助函数（如 `ts()`、`md5()`、`uid()`）和生命周期 Hooks（如 `setup_hook_sign_request`），可直接使用。
>
> **迁移提醒（0.2.x → 0.3.x）**：
> - 如果你的项目仍使用旧文件名 `arun_hooks.py`，请改名为 `drun_hooks.py`。
> - 若之前通过 `ARUN_HOOKS_FILE=/path/to/arun_hooks.py` 指定自定义路径，请改成 `DRUN_HOOKS_FILE=/path/to/drun_hooks.py`（路径可保持不变）。
> - 更新完毕后重新运行 `drun run ...`，确认 `${hook(...)}`
>   调用按预期触发。

**函数分类**：
- **模板辅助函数**：在 `${}` 表达式中调用，用于数据生成、格式化等（如 `${ts()}`、`${md5($key)}`）
- **生命周期 Hooks**：在 `setup_hooks/teardown_hooks` 中使用，用于请求前处理、响应后验证（如 `${setup_hook_sign_request($request)}`）

#### Hook 类型

```yaml
# Suite 级别（在 Suite 配置中）
config:
  setup_hooks:              # Suite 开始前执行
    - ${suite_setup()}
  teardown_hooks:           # Suite 结束后执行
    - ${suite_teardown()}

# Case 级别（在 Case 配置中）
config:
  setup_hooks:              # Case 开始前执行
    - ${case_setup()}
  teardown_hooks:           # Case 结束后执行
    - ${case_cleanup()}

# Step 级别（在测试步骤（Step）中）
steps:
  - name: 发送请求
    setup_hooks:            # 步骤开始前执行
      - ${setup_hook_sign_request($request)}
    teardown_hooks:         # 步骤结束后执行
      - ${teardown_hook_validate($response)}
```

#### 自定义 Hooks

在项目根目录创建 `drun_hooks.py`：

```python
import time
import hmac
import hashlib

def ts() -> int:
    """返回当前 Unix 时间戳"""
    return int(time.time())

def setup_hook_sign_request(request: dict, variables: dict = None, env: dict = None) -> dict:
    """请求签名 Hook：添加时间戳和 HMAC 签名"""
    secret = env.get('APP_SECRET', '').encode()
    method = request.get('method', 'GET')
    url = request.get('url', '')
    timestamp = str(ts())

    # 计算 HMAC 签名
    message = f"{method}|{url}|{timestamp}".encode()
    signature = hmac.new(secret, message, hashlib.sha256).hexdigest()

    # 添加签名头
    headers = request.setdefault('headers', {})
    headers['X-Timestamp'] = timestamp
    headers['X-Signature'] = signature

    # 返回新变量（可选）
    return {'last_signature': signature}

def teardown_hook_validate(response: dict, variables: dict = None, env: dict = None):
    """响应验证 Hook：确保状态码为 200"""
    if response.get('status_code') != 200:
        raise AssertionError(f"Expected 200, got {response.get('status_code')}")
```

**Hook 上下文变量**：

- `$request` - 当前请求对象
- `$response` - 当前响应对象
- `$step_name` - 当前步骤名称
- `$session_variables` - 所有会话变量
- `$session_env` - 环境变量

#### 使用 Hooks

```yaml
config:
  name: 签名 API 测试
  base_url: ${ENV(BASE_URL)}
  setup_hooks:
    - ${setup_hook_sign_request($request)}

steps:
  - name: 获取用户信息
    request:
      method: GET
      url: /api/secure/users
    teardown_hooks:
      - ${teardown_hook_validate($response)}
    validate:
      - eq: [status_code, 200]
```

### 参数化测试

Drun 支持**压缩（zipped）参数化**，让你使用不同参数组合多次运行同一测试。参数定义在 `config.parameters` 中，支持单变量列表和多变量绑定两种用法。

#### 用法 1：单变量列表

适合单个参数的多个取值场景，如测试不同数量、不同环境等。

```yaml
config:
  name: 订单数量测试
  base_url: ${ENV(BASE_URL)}
  parameters:
    - quantity: [1, 2, 5, 10]
    # 生成 4 个测试实例，分别测试 quantity=1, 2, 5, 10

steps:
  - name: 创建订单
    request:
      method: POST
      url: /api/orders
      body:
        product_id: "PROD-001"
        quantity: $quantity
    validate:
      - eq: [status_code, 201]
      - eq: [$.data.quantity, $quantity]
```

**实际示例：** `testcases/test_e2e_purchase.yaml:11-12`

#### 用法 2：多变量绑定（推荐）

使用**连字符 `-`** 连接变量名，将多个相关参数绑定为一组。适合测试用户凭证、坐标对、配置组合等场景。

```yaml
config:
  name: 登录测试
  base_url: ${ENV(BASE_URL)}
  parameters:
    - username-password-expected_status:
        - ["alice", "pass123", 200]      # 正常登录
        - ["bob", "wrong_pwd", 401]      # 密码错误
        - ["unknown", "any_pwd", 401]    # 用户不存在
    # 生成 3 个测试实例，每组参数成对使用

steps:
  - name: 尝试登录
    request:
      method: POST
      url: /api/login
      body:
        username: $username
        password: $password
    validate:
      - eq: [status_code, $expected_status]
```

**实际示例：** `testcases/test_login_zipped.yaml:5-8`

#### 用法 3：多组笛卡尔积（高级）

定义多个压缩组时，Drun 会自动生成笛卡尔积组合，适合跨环境、跨区域的组合测试。

```yaml
config:
  name: 多环境健康检查
  base_url: ${ENV(BASE_URL)}
  parameters:
    - env: [dev, staging, prod]         # 3 个环境
    - region: [us, eu, asia]            # 3 个区域
    # 生成 3 × 3 = 9 个测试实例

steps:
  - name: 检查服务健康
    variables:
      full_url: https://${env}-${region}.example.com
    request:
      method: GET
      url: ${full_url}/health
    validate:
      - eq: [status_code, 200]
      - contains: [$.data.region, $region]
```

**组合说明：** 两个压缩组会生成 9 个实例：
- (dev, us), (dev, eu), (dev, asia)
- (staging, us), (staging, eu), (staging, asia)
- (prod, us), (prod, eu), (prod, asia)

> **最佳实践：**
> - 单变量用列表：`- quantity: [1, 2, 3]`
> - 多变量用绑定：`- username-password: [[alice, pass123], [bob, secret456]]`
> - 需要笛卡尔积时定义多个压缩组：`- env: [dev, prod]` + `- region: [us, eu]`
> - 变量名用连字符分隔，不要使用下划线或空格

**更多示例：** 参见 `examples/test_params_zipped.yaml` 和 `testcases/test_register_zipped.yaml`

#### 用法 4：CSV 数据驱动

当测试数据较多或已经维护在表格中时，可以直接引入 CSV 文件。`path` 支持相对路径（相对于用例文件），Drun 会把每一行转换为参数字典，再与其它参数组做笛卡尔积。

```yaml
config:
  name: 登录校验（CSV）
  base_url: ${ENV(BASE_URL)}
  parameters:
    - csv:
        path: data/login_users.csv   # 相对于当前 YAML 的路径
        strip: true                  # 可选：自动 trim 每个单元格

steps:
  - name: 尝试登录
    request:
      method: GET
      url: /login?username=$username&password=$password&env=$env
    validate:
      - eq: [status_code, 200]
```

可选字段：

- `columns`: CSV 没有表头时指定列名（示例：`[username, password, env]`）。
- `header`: 是否读取首行为表头，默认 `true`。
- `delimiter`: 分隔符，默认逗号。
- `encoding`: 文件编码，默认 `utf-8`。

**实际示例：** `examples/basic-examples/test_params_csv.yaml`

### SQL 验证

对数据库状态进行断言，确保 API 操作正确写入数据库。

#### 环境配置

```env
# 方式 1：独立配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=test_user
MYSQL_PASSWORD=test_pass
MYSQL_DB=test_database

# 方式 2：DSN 连接串
MYSQL_DSN=mysql://user:pass@localhost:3306/test_db
```

#### 使用示例

```yaml
steps:
  - name: 创建订单
    request:
      method: POST
      url: /api/orders
      body:
        product_id: "PROD-001"
        quantity: 2
    extract:
      order_id: $.data.order_id
    validate:
      - eq: [status_code, 201]

    sql_validate:
      # 查询 1：验证订单状态
      - query: "SELECT status, total FROM orders WHERE id='$order_id'"
        expect:
          - eq: [status, "pending"]     # 断言 status 字段
          - gt: [total, 0]              # 断言 total 字段
        extract:
          db_status: $status            # 提取列结果为变量
          db_total: $total

      # 查询 2：验证订单项数量
      - query: "SELECT COUNT(*) AS cnt FROM order_items WHERE order_id='$order_id'"
        expect:
          - ge: [cnt, 1]                # 至少 1 条记录

      # 查询 3：使用不同数据库
      - query: "SELECT log FROM audit.logs WHERE order_id='$order_id'"
        dsn: mysql://user:pass@audit-host:3306/audit_db
        expect:
          - contains: [log, "order_created"]
```

**SQL 验证选项**：

- `query` - SQL 查询（必需，支持变量插值）
- `expect` - 断言列表（可选）
- `extract` - 使用 `$` 表达式提取列结果为变量（可选，例如 `$status`）
- `allow_empty` - 允许空结果（可选，默认 false）
- `dsn` - 覆盖数据库连接（可选）

### 重试机制

为不稳定的接口配置自动重试：

```yaml
steps:
  - name: 调用不稳定接口
    request:
      method: GET
      url: /api/flaky-endpoint
    retry: 3                  # 最多重试 3 次
    retry_backoff: 0.5        # 初始退避 0.5 秒
                              # 重试间隔：0.5s → 1.0s → 2.0s（指数增长，上限 2.0s）
    validate:
      - eq: [status_code, 200]
```

---

## 📊 报告和通知

### HTML 报告

生成交互式 HTML 报告：

```bash
drun run testcases --html reports/report.html
```

截图预览（统一浅色风格）

```bash
# 生成并预览（示例使用引用型测试套件（Testsuite））
python -m drun.cli run testsuites/testsuite_smoke.yaml \
  --env-file .env \
  --html reports/report.html

# 打开：reports/report.html
```

**特性**：
- 📈 **摘要仪表板**：总数、通过、失败、跳过、耗时（随筛选动态更新）
- 🔍 **详细断言**：每个断言的期望值、实际值、结果（支持"仅失败断言"筛选）
- 📦 **完整调试信息**：请求/响应/提取变量/cURL 命令（支持一键复制，带视觉反馈）
  - ✅ 复制成功：绿色高亮提示"已复制"
  - ⚠️ 复制失败（HTTPS 限制）：橙色提示"已选中，按 Ctrl/Cmd+C"自动选中文本
  - 🎯 精准复制：基于原始数据，确保 JSON 格式准确无误
  - 🔧 cURL 命令：使用 `--data-raw` 确保载荷不被修改，JSON 自动格式化
- 🎛️ **交互增强**：
  - 状态筛选：通过/失败/跳过
  - 仅失败断言、仅失败断言步骤、展开/折叠全部、仅失败用例
- 🧩 **JSON 语法高亮**：请求/响应/提取变量采用轻量高亮（零依赖、ES5 兼容）
- 🎨 **GitHub 主题**：默认浅色 GitHub 风格，简洁专业
- 🌐 **兼容性**：ES5 兼容，支持旧浏览器和 `file://` 协议访问

### JSON 报告

生成结构化 JSON 报告：

```bash
drun run testcases --report reports/run.json
```

**格式**：

```json
{
  "summary": {
    "total": 10,
    "passed": 8,
    "failed": 2,
    "skipped": 0,
    "duration_ms": 2456.7
  },
  "cases": [
    {
      "name": "用户登录",
      "status": "passed",
      "duration_ms": 145.3,
      "parameters": {},
      "steps": [...]
    }
  ]
}
```

### Allure 报告

生成 Allure 原始结果（可用 Allure CLI/插件渲染成可视化报告）：

```bash
# 生成 Allure 结果
drun run testcases --allure-results allure-results

# 使用 Allure CLI 生成与打开报告（本地需安装 allure 命令）
allure generate allure-results -o allure-report --clean
allure open allure-report
```

#### Allure CLI 安装

**macOS / Linux:**
```bash
# 使用 Homebrew (macOS/Linux)
brew install allure

# 或使用 Scoop (Windows)
scoop install allure

# 或手动下载
# 1. 从 https://github.com/allure-framework/allure2/releases 下载最新版本
# 2. 解压并添加 bin 目录到 PATH
```

**验证安装：**
```bash
allure --version
```

#### 特性说明

- **附件丰富**：为每个步骤生成请求/响应/cURL/断言/提取变量等附件（遵循 `--mask-secrets` 脱敏策略）
- **测试套件分组**：默认按用例来源文件名归类（若可用），否则归为 "Drun"
- **趋势分析**：多次运行后可查看历史趋势（需保留 `allure-report/history` 目录）
- **CI/CD 集成**：可配合 Jenkins/GitLab CI 的 Allure 插件自动生成并展示报告

### 通知集成

> 提示：未显式传入 `--notify`/`--notify-only` 时，Drun 会根据环境变量自动启用对应渠道：
> 配置了 `FEISHU_WEBHOOK`、`DINGTALK_WEBHOOK` 或 `SMTP_HOST`/`MAIL_TO` 将分别触发飞书、钉钉、邮件通知；
> 策略默认读取 `DRUN_NOTIFY_ONLY`（fallback 为 `failed`）。

#### 飞书通知

```bash
# 环境变量配置
export FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
export FEISHU_SECRET=your-secret      # 可选，签名验证
export FEISHU_STYLE=card              # card 或 text（默认）
export SYSTEM_NAME=我的测试系统       # 可选，自定义卡片标题（支持 SYSTEM_NAME 或 PROJECT_NAME）
export DRUN_NOTIFY_ONLY=failed        # failed 或 always

# 运行并通知（已配置 FEISHU_WEBHOOK 时可直接运行）
drun run testcases --env-file .env
# 如需明确指定渠道，可额外加 --notify feishu
drun run testcases --notify feishu --env-file .env
```

**飞书卡片示例**（`FEISHU_STYLE=card`）：
- 🏷️ **自定义标题**：显示系统名称（来自 `SYSTEM_NAME`，默认 "Drun 测试结果"）
- 📊 **用例统计**：总数、通过、失败、跳过、耗时
- 🔢 **步骤统计**：总步骤数、通过步骤数、失败步骤数
- 🚨 **失败步骤详情**：步骤名称、错误消息、耗时（前 5 个）
- 📁 **执行文件**：显示测试文件列表（单文件或多文件汇总）
- 🔗 **报告链接**：HTML 报告和日志文件（需配置 `REPORT_URL`）
- 👤 **@提醒**：支持 @ 指定人员（需配置 `FEISHU_MENTION`）

#### 邮件通知

```bash
# 环境变量配置
export SMTP_HOST=smtp.example.com
export SMTP_PORT=465
export SMTP_USER=noreply@example.com
export SMTP_PASS=app-password
export MAIL_FROM=noreply@example.com
export MAIL_TO=qa@example.com,dev@example.com

# 运行并通知（附带 HTML 报告；已配置 SMTP/MAIL_TO 时可直接运行）
drun run testcases --notify-attach-html --env-file .env
# 如需明确指定渠道，可额外加 --notify email
drun run testcases --notify email --notify-attach-html --env-file .env
```

**邮件内容**：
- 📧 **纯文本/HTML 正文**：测试摘要 + 失败用例
- 📎 **附件**：完整 HTML 报告（可选）

#### 钉钉通知

```bash
# 环境变量配置
export DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
# 可选：安全设置为“加签”时需配置 SECRET（自动追加 timestamp/sign）
export DINGTALK_SECRET=your-secret
# 可选：@ 指定手机号（逗号分隔）；或全员 @
export DINGTALK_AT_MOBILES=13800138000,13900139000
export DINGTALK_AT_ALL=false
# 可选：消息样式 text/markdown（默认 text）
export DINGTALK_STYLE=text

# 运行并通知（失败才发；已配置 DINGTALK_WEBHOOK 时可直接运行）
drun run testcases --notify-only failed --env-file .env
# 如需明确指定渠道，可额外加 --notify dingtalk
drun run testcases --notify dingtalk --notify-only failed --env-file .env

# 也可多渠道同时发
drun run testcases --notify feishu,dingtalk --notify-only always --env-file .env
```

说明：
- 文本内容为测试摘要与失败 TOPN（默认 5）；包含报告和日志路径（若存在）。
- 配置了 `DINGTALK_SECRET` 时，通知将按钉钉机器人加签规范使用 HMAC-SHA256 进行签名（毫秒级时间戳）。

---

## 🛠 命令行工具

为保持 README 精炼，CLI 详情请见：docs/CLI.md

## 💻 实战示例

为保持 README 精炼，完整实战示例请见：docs/EXAMPLES.md

---

## 🔗 CI/CD 集成

为保持 README 精炼，CI 示例已迁移至 docs：

- GitHub Actions、GitLab CI、Jenkins 示例与最佳实践：docs/CI_CD.md

---

## 🐛 故障排查

### 常见问题

#### 1. BASE_URL 缺失警告

```
[ENV] Default .env not found and BASE_URL is missing. Relative URLs may fail.
```

**原因**：未提供 `.env` 文件且环境中没有 `BASE_URL` 变量。

**解决方案**：
```bash
# 方式 1：创建 .env 文件（推荐）
cat > .env <<EOF
BASE_URL=http://localhost:8000
USER_USERNAME=test_user
USER_PASSWORD=test_pass
EOF

# 方式 2：通过 CLI 传递
drun run testcases --vars base_url=http://localhost:8000

# 方式 3：导出环境变量
export BASE_URL=http://localhost:8000
```

#### 2. 找不到测试文件

```
No YAML test files found.
```

**原因**：文件不符合命名规范。

**解决方案**：
- 文件放在 `testcases/` 或 `testsuites/` 目录，或
- 文件命名为 `test_*.yaml` 或 `suite_*.yaml`

#### 3. 模块导入错误

```
ModuleNotFoundError: No module named 'drun'
```

**解决方案**：

```bash
pip install -e .
```

#### 4. 变量未定义

```
KeyError: 'user_id'
```

**原因**：变量在当前作用域不存在。

**解决方案**：
- 检查变量名拼写
- 确认变量在 `config.variables`、`steps[].variables` 或 `extract` 中定义
- 检查提取路径是否正确

#### 5. SQL 验证失败

```
MySQL assertion requires MYSQL_USER or dsn.user.
```

**解决方案**：

```env
# 添加到 .env
MYSQL_HOST=localhost
MYSQL_USER=test_user
MYSQL_PASSWORD=test_pass
MYSQL_DB=test_db
```

或安装数据库驱动：

```bash
pip install pymysql
```

#### 6. Hooks 未加载

**原因**：`drun_hooks.py` 文件位置不正确，或文件名拼写错误。

**解决方案**：

> **注意**：0.3.0 起仅加载 `drun_hooks.py`（可通过 `DRUN_HOOKS_FILE` 指定其他路径），旧的 `arun_hooks.py`/`ARUN_HOOKS_FILE` 不再生效。

1. 旧项目请将 `arun_hooks.py` 重命名为 `drun_hooks.py`
2. 如果使用环境变量，改用 `DRUN_HOOKS_FILE=/path/to/drun_hooks.py`
3. 确认文件位于项目根目录或由 `DRUN_HOOKS_FILE` 指向的路径
4. 重新运行命令，确保 `${hook(...)}`
   已恢复

例如：

```bash
mv arun_hooks.py drun_hooks.py
export DRUN_HOOKS_FILE=/absolute/path/to/drun_hooks.py
drun run testcases
```

### 调试技巧

#### 1. 启用详细日志

```bash
drun run testcases --log-level debug --log-file debug.log
```

#### 2. 显示 httpx 请求日志

```bash
drun run testcases --httpx-logs
```

#### 3. 查看 cURL 命令

调试日志和 HTML 报告都包含每个请求的 cURL 等效命令（使用 `--data-raw` 确保载荷不被修改，JSON 自动格式化提升可读性）：

```bash
# 调试日志示例
[DEBUG] cURL: curl -X POST 'https://api.example.com/login' \
  -H 'Content-Type: application/json' \
  --data-raw '{
  "username": "test",
  "password": "***"
}'

# HTML 报告中可一键复制 cURL 命令
# JSON 自动格式化（indent=2）+ 自动添加 Content-Type
```

#### 4. 验证 YAML 语法

```bash
drun check testcases
```

---

## 📚 完整参考

为保持 README 精炼，完整参考请见：docs/REFERENCE.md

### 快速贡献

我们欢迎任何形式的贡献！

1. **Fork** 本仓库
2. 创建功能分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m "feat: add amazing feature"`
4. 推送到分支：`git push origin feature/amazing-feature`
5. 创建 **Pull Request**

### 贡献指南

- 遵循现有代码风格（black、ruff）
- 为新功能添加测试用例
- 更新相关文档
- 编写清晰的提交消息
- 保持更改集中和原子化

### 开发环境

```bash
# 克隆仓库
git clone https://github.com/Devliang24/drun.git
cd drun

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装开发依赖
pip install -e .

# 运行测试
drun run testcases --env-file .env

# 验证代码风格
# black drun/
# ruff check drun/
```

### 社区资源

- **示例集合**：[examples/](examples/)
- **问题追踪**：[GitHub Issues](https://github.com/Devliang24/drun/issues)
- **变更日志**：查看提交历史

---

## 📄 许可证

本项目采用 **MIT 许可证** - 详见 LICENSE

---

## 🙏 致谢

Drun 基于优秀的开源项目构建：

- [httpx](https://www.python-httpx.org/) - 现代 HTTP 客户端
- [pydantic](https://docs.pydantic.dev/) - 数据验证
- [jmespath](https://jmespath.org/) - JSON 查询
- [rich](https://rich.readthedocs.io/) - 终端美化
- [typer](https://typer.tiangolo.com/) - CLI 框架

感谢所有贡献者！

---

<div align="center">

**由 Drun 团队用 ❤️ 构建**

[⬆ 回到顶部](#drun)

</div>

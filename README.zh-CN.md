# Drun - 轻量级 HTTP API 测试框架

[![版本](https://img.shields.io/badge/version-2.4.10-blue.svg)](https://github.com/Devliang24/drun)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://python.org)
[![许可证](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

[English](README.md) | 简体中文

Drun 是一个基于 **YAML 的零代码 HTTP API 测试框架**，专为现代 CI/CD 流水线设计，提供企业级测试能力。通过简单的声明式语法，让团队快速创建、管理和执行 API 自动化测试。

## ✨ 核心特性

### 🚀 核心能力
- **零代码测试** - 使用声明式 YAML DSL 编写测试，无需编程
- **多格式导入** - 支持从 cURL、Postman、HAR、OpenAPI 格式转换
- **数据驱动测试** - CSV 参数化和压缩参数支持
- **数据库断言** - MySQL SQL 验证，确保数据一致性
- **模板引擎** - 变量替换与内置函数支持
- **多种报告格式** - HTML、JSON 和 Allure 报告生成
- **企业级通知** - 飞书、钉钉、邮件集成
- **标签过滤** - 支持复杂的布尔表达式筛选测试
- **SSE 流式响应** - 服务器推送事件支持
- **CI/CD 就绪** - 无缝集成 GitHub Actions、GitLab CI 和 Jenkins

### 📦 支持格式

| 导入 | 导出 | 使用场景 |
|------|------|----------|
| ✅ cURL | ✅ cURL | 命令行转换 |
| ✅ Postman Collection | ❌ | 迁移现有测试 |
| ✅ HAR (HTTP Archive) | ❌ | 浏览器流量转换 |
| ✅ OpenAPI/Swagger | ❌ | API 规范导入 |

### 📊 报告格式

| 格式 | 用途 | 集成场景 |
|------|------|----------|
| HTML | 可视化仪表盘 | 本地查看、干系人展示 |
| JSON | 机器可读数据 | 自定义处理、数据分析 |
| Allure | 详细测试报告 | CI/CD 系统、团队看板 |

## 🏗️ 架构设计

```
┌─────────────────────────────────────┐
│          CLI 层 (cli.py)            │  ← 命令行接口
├─────────────────────────────────────┤
│         导入/导出层                  │  ← 格式转换
│   (cURL, Postman, HAR, OpenAPI)     │
├─────────────────────────────────────┤
│          加载器层                    │  ← 文件加载与解析
│  (YAML, 环境变量, Hooks)            │
├─────────────────────────────────────┤
│         模型层                       │  ← 数据模型
│   (Case, Step, Config, Report)      │
├─────────────────────────────────────┤
│        运行器层                      │  ← 测试执行
│  (HTTP 客户端, 断言引擎)            │
├─────────────────────────────────────┤
│       报告器层                       │  ← 报告生成
│   (HTML, JSON, Allure)              │
├─────────────────────────────────────┤
│       通知器层                       │  ← 通知集成
│  (飞书, 钉钉, 邮件)                 │
└─────────────────────────────────────┘
```

## 📋 目录

- [安装](#-安装)
- [快速开始](#-快速开始)
- [编写测试](#-编写测试)
- [格式转换](#-格式转换)
- [配置管理](#-配置管理)
- [报告与通知](#-报告与通知)
- [高级功能](#-高级功能)
- [示例项目](#-示例项目)
- [贡献指南](#-贡献指南)
- [许可证](#-许可证)

## 📦 安装

### 环境要求

- Python 3.10 或更高版本
- pip 或 poetry 包管理器

### 通过 pip 安装

```bash
pip install drun
```

### 从源码安装

```bash
git clone https://github.com/Devliang24/drun.git
cd drun
pip install -e .
```

### 验证安装

```bash
drun --version
# 输出: drun, version 2.4.10
```

## 🚀 快速开始

### 1. 初始化新项目

```bash
drun init my-api-tests
cd my-api-tests
tree
```

生成的项目结构：
```
my-api-tests/
├── testcases/           # 测试用例目录
│   ├── test_api_health.yaml
│   ├── test_demo.yaml
│   └── ...
├── testsuites/          # 测试套件目录
│   ├── testsuite_smoke.yaml
│   └── testsuite_regression.yaml
├── data/                # 测试数据目录
│   └── users.csv
├── converts/            # 格式转换示例
├── reports/             # 测试报告输出目录
├── logs/                # 日志输出目录
├── drun_hooks.py        # 自定义 Hook 函数
├── .env.example         # 环境配置模板
└── README.md            # 项目说明文档
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件：
```env
# API 基础地址
BASE_URL=http://localhost:8000

# 用户凭证
USER_USERNAME=testuser
USER_PASSWORD=testpass

# 数据库配置
MYSQL_MAIN__DEFAULT__DSN=mysql://user:pass@localhost:3306/db
MYSQL_MAIN__DEFAULT__CHARSET=utf8mb4
```

### 3. 编写第一个测试

创建 `testcases/test_hello.yaml`：

```yaml
name: Hello World API 测试
config:
  base_url: https://httpbin.org
  tags: [demo, smoke]

steps:
  - name: 获取 IP 地址
    request:
      method: GET
      url: /ip
    validate:
      - eq: [$.origin]  # 验证 origin 字段存在

  - name: POST 请求测试
    request:
      method: POST
      url: /post
      body:
        message: "Hello Drun"
    validate:
      - eq: [$.json.message, "Hello Drun"]
```

### 4. 运行测试

```bash
# 运行单个测试用例
drun run testcases/test_hello.yaml

# 运行目录下所有测试
drun run testcases/

# 运行测试套件
drun run testsuites/testsuite_smoke.yaml

# 生成 HTML 报告
drun run testcases/ --html reports/report.html
```

### 5. 查看测试报告

报告生成在 `reports/` 目录下：
- `report.html` - 可视化测试仪表盘
- `run.json` - 机器可读的测试结果

## 📝 编写测试

### 测试用例结构

```yaml
name: 用户登录测试
config:
  base_url: ${ENV(BASE_URL)}
  tags: [smoke, auth, critical]
  variables:
    username: testuser
    password: Test@123456

steps:
  - name: 用户登录
    request:
      method: POST
      url: /api/v1/auth/login
      headers:
        Content-Type: application/json
      body:
        username: ${username}
        password: ${password}
    extract:
      - token: $.data.token
      - user_id: $.data.user.id
    validate:
      - eq: [$.code, 200]
      - contains: [$.message, "成功"]
      - eq: [$.data.user.username, ${username}]

  - name: 获取用户信息
    request:
      method: GET
      url: /api/v1/users/me
      headers:
        Authorization: Bearer ${token}
    validate:
      - eq: [$.data.id, ${user_id}]
```

### 断言操作符

| 操作符 | 说明 | 示例 |
|--------|------|------|
| `eq` | 等于 | `- eq: [$.id, 123]` |
| `ne` | 不等于 | `- ne: [$.status, "deleted"]` |
| `lt` | 小于 | `- lt: [$.count, 10]` |
| `le` | 小于等于 | `- le: [$.score, 100]` |
| `gt` | 大于 | `- gt: [$.age, 18]` |
| `ge` | 大于等于 | `- ge: [$.version, 2.0]` |
| `contains` | 包含子串 | `- contains: [$.message, "成功"]` |
| `regex` | 正则表达式 | `- regex: [$.email, ".*@.*\\..*"]` |
| `in` | 在数组中 | `- in: [$.status, ["active", "pending"]]` |
| `len_eq` | 长度等于 | `- len_eq: [$.items, 5]` |
| `contains_all` | 包含所有元素 | `- contains_all: [$.tags, ["api", "test"]]` |
| `match_regex_all` | 所有元素匹配正则 | `- match_regex_all: [$.urls, "https://.*"]` |

### 数据提取

使用 JMESPath 表达式提取响应数据：

```yaml
steps:
  - name: 创建订单
    request:
      method: POST
      url: /api/v1/orders
      body:
        items: [{product_id: 1, quantity: 2}]
    extract:
      - order_id: $.data.order_id
      - order_number: $.data.order_number
      - total_amount: $.data.total
      - first_item_name: $.data.items[0].name
```

### 参数化测试

#### 压缩参数化

```yaml
name: 多用户登录测试
config:
  base_url: ${ENV(BASE_URL)}
  parameters:
    username: [user1, user2, user3]
    role: [admin, user]
    # 生成 6 个测试实例 (3 * 2)

steps:
  - name: 登录 ${username} (${role})
    request:
      method: POST
      url: /api/v1/auth/login
      body:
        username: ${username}
        password: password123
    validate:
      - eq: [$.data.role, ${role}]
```

#### CSV 参数化

创建 `data/users.csv`：
```csv
user_id,username,email,expected_status
1,john,john@example.com,active
2,jane,jane@example.com,active
3,bob,bob@example.com,inactive
```

在测试中使用：
```yaml
name: 批量验证用户数据
config:
  parameters:
    - csv:
        path: data/users.csv

steps:
  - name: 验证用户 ${username}
    request:
      method: GET
      url: /api/v1/users/${user_id}
    validate:
      - eq: [$.data.username, ${username}]
      - eq: [$.data.email, ${email}]
      - eq: [$.data.status, ${expected_status}]
```

### 环境变量使用

在测试中引用环境变量：

```yaml
config:
  base_url: ${ENV(BASE_URL)}
  variables:
    # 使用默认值
    timeout: ${ENV(REQUEST_TIMEOUT, 30)}
    # 嵌套使用
    api_key: ${ENV(API_KEY)}

steps:
  - name: API 请求
    request:
      method: GET
      url: /api/v1/data
      headers:
        X-API-Key: ${api_key}
      timeout: ${timeout}
```

## 🔄 格式转换

### 从 cURL 导入

```bash
# 基础转换
drun convert converts/curl/sample.curl --outfile testcases/from_curl.yaml

# 启用占位符替换
drun convert request.curl --placeholders --outfile testcases/test.yaml

# 分割输出（每个请求一个文件）
drun convert multi_requests.curl --split-output --into testcases/
```

### 从 Postman 导入

```bash
# 转换 Postman Collection
drun convert collection.json --split-output --suite-out testsuites/imported.yaml

# 使用环境变量
drun convert collection.json \
  --postman-env environment.json \
  --placeholders \
  --split-output

# 脱敏处理
drun convert collection.json --redact "Authorization,Cookie" --placeholders
```

### 从 HAR 导入

```bash
# 基础转换
drun convert recording.har --outfile testcases/from_har.yaml

# 过滤静态资源
drun convert recording.har --exclude-static --only-2xx --split-output

# 指定域名过滤
drun convert recording.har \
  --filter-domain "api.example.com" \
  --split-output \
  --into testcases/api/
```

### 从 OpenAPI 导入

```bash
# 基础转换
drun convert-openapi api_spec.yaml --outfile testcases/from_openapi.yaml

# 按标签过滤
drun convert-openapi api_spec.json \
  --tags "users,orders" \
  --split-output \
  --base-url "https://api.example.com"

# 生成测试套件
drun convert-openapi api_spec.yaml \
  --split-output \
  --suite-out testsuites/api_tests.yaml \
  --placeholders
```

### 导出为 cURL

```bash
# 导出单个步骤
drun export curl testcases/test_login.yaml --steps 1

# 导出所有步骤（多行格式）
drun export curl testcases/test_flow.yaml

# 生成 Shell 脚本
drun export curl testcases/test_login.yaml --steps 1 --shell > test.sh

# 添加注释
drun export curl testcases/test_login.yaml --with-comments
```

## ⚙️ 配置管理

### 测试套件配置

创建 `testsuites/testsuite_regression.yaml`：

```yaml
name: 回归测试套件
config:
  base_url: ${ENV(BASE_URL)}
  tags: [regression]
  variables:
    test_user: regression_user
    test_pass: Regression@123

setup_hooks:
  - setup_test_data

teardown_hooks:
  - cleanup_test_data

cases:
  - testcases/test_auth_flow.yaml
  - testcases/test_products.yaml
  - testcases/test_shopping_cart.yaml
  - testcases/test_orders.yaml
  - testcases/test_admin_permissions.yaml
```

### 多环境管理

创建环境配置文件：

`.env.dev`:
```env
BASE_URL=https://dev.example.com
MYSQL_MAIN__DEFAULT__DSN=mysql://user:pass@dev-db:3306/testdb
```

`.env.staging`:
```env
BASE_URL=https://staging.example.com
MYSQL_MAIN__DEFAULT__DSN=mysql://user:pass@staging-db:3306/testdb
```

`.env.prod`:
```env
BASE_URL=https://api.example.com
MYSQL_MAIN__DEFAULT__DSN=mysql://user:pass@prod-db:3306/testdb
```

使用环境：
```bash
# 使用 dev 环境
drun run testsuites/smoke.yaml --env-file .env.dev

# 使用 staging 环境
drun run testsuites/regression.yaml --env-file .env.staging
```

### 自定义 Hooks

在 `drun_hooks.py` 中定义自定义函数：

```python
import time
import hmac
import hashlib
from typing import Dict, Any

def ts():
    """生成当前时间戳"""
    return str(int(time.time()))

def uid():
    """生成 UUID"""
    import uuid
    return str(uuid.uuid4())

def short_uid(length: int = 8):
    """生成短 UUID"""
    import uuid
    return str(uuid.uuid4()).replace('-', '')[:length]

def setup_hook_hmac_sign(hook_ctx: Dict[str, Any]):
    """HMAC 签名 Hook"""
    secret = hook_ctx.get("app_secret", "")
    timestamp = ts()
    message = f"{timestamp}:{secret}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    hook_ctx["timestamp"] = timestamp
    hook_ctx["signature"] = signature

def setup_hook_assert_sql(hook_ctx: Dict[str, Any]):
    """SQL 断言 Hook"""
    from drun.db.database_proxy import DatabaseProxy
    dsn = hook_ctx.get("MYSQL_MAIN__DEFAULT__DSN", "")
    if dsn:
        db = DatabaseProxy(dsn=dsn)
        hook_ctx["db"] = db

def expected_sql_value(record_id, column="value"):
    """从数据库获取期望值"""
    # 实现查询逻辑
    pass
```

在测试中使用：
```yaml
setup_hooks:
  - setup_hook_hmac_sign

steps:
  - name: 签名请求
    request:
      method: POST
      url: /api/v1/secure
      headers:
        X-Timestamp: ${timestamp}
        X-Signature: ${signature}
      body:
        data: "sensitive data"
```

### 标签过滤

```bash
# 运行 smoke 测试
drun run testcases/ -k "smoke"

# 运行 smoke 或 critical 测试
drun run testcases/ -k "smoke or critical"

# 运行 regression 但排除 slow 测试
drun run testcases/ -k "regression and not slow"

# 复杂表达式
drun run testcases/ -k "(smoke or critical) and not (slow or flaky)"
```

## 📊 报告与通知

### HTML 报告

```bash
# 生成 HTML 报告
drun run testsuites/regression.yaml --html reports/regression_report.html

# 指定日志级别
drun run testcases/ --html reports/report.html --log-level info

# 敏感信息脱敏
drun run testcases/ --html reports/report.html --mask-secrets
```

HTML 报告特性：
- ✅ 可视化测试结果，颜色编码状态
- ✅ 详细的步骤信息展示
- ✅ 响应体预览（支持 JSON 格式化）
- ✅ 执行时间统计
- ✅ 失败原因高亮显示

### JSON 报告

```bash
# 生成 JSON 报告（用于 CI/CD）
drun run testsuites/regression.yaml --report reports/run.json
```

JSON 报告结构：
```json
{
  "summary": {
    "total": 20,
    "passed": 18,
    "failed": 2,
    "duration": 12.34,
    "start_time": "2025-10-31T10:00:00",
    "end_time": "2025-10-31T10:00:12"
  },
  "cases": [
    {
      "name": "用户登录测试",
      "status": "passed",
      "duration": 1.23,
      "steps": [...]
    }
  ]
}
```

### Allure 报告

```bash
# 生成 Allure 结果
drun run testsuites/regression.yaml --allure-results allure-results/

# 启动 Allure 服务查看报告
allure serve allure-results/
```

### 通知集成

#### 飞书通知

在 `.env` 中配置：
```env
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx-xxx
FEISHU_SECRET=your-secret-key
FEISHU_MENTION=13800138000,ou_xxxx
FEISHU_STYLE=card
REPORT_URL=https://ci.example.com/reports/latest.html
```

运行测试并发送通知：
```bash
# 失败时通知（默认）
drun run testsuites/regression.yaml \
  --notify feishu \
  --html reports/report.html

# 总是通知
drun run testsuites/regression.yaml \
  --notify feishu \
  --notify-only always

# 附加 HTML 报告
drun run testsuites/regression.yaml \
  --notify feishu \
  --notify-attach-html \
  --html reports/report.html
```

#### 钉钉通知

在 `.env` 中配置：
```env
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
DINGTALK_SECRET=your-secret-key
```

运行测试并发送通知：
```bash
drun run testsuites/regression.yaml \
  --notify dingtalk \
  --notify-only failed
```

#### 邮件通知

在 `.env` 中配置：
```env
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USER=noreply@example.com
SMTP_PASS=your-app-password
MAIL_FROM=noreply@example.com
MAIL_TO=qa-team@example.com,dev-team@example.com
NOTIFY_ATTACH_HTML=true
NOTIFY_HTML_BODY=true
```

运行测试并发送邮件：
```bash
drun run testsuites/regression.yaml \
  --notify email \
  --html reports/report.html
```

## 🔧 高级功能

### SQL 数据库断言

配置数据库连接（在 `.env` 中）：
```env
MYSQL_MAIN__DEFAULT__DSN=mysql://root:password@localhost:3306/testdb
MYSQL_MAIN__DEFAULT__CHARSET=utf8mb4
```

在 `drun_hooks.py` 中实现 SQL 断言函数：
```python
from drun.db.database_proxy import DatabaseProxy

def setup_hook_assert_sql(hook_ctx):
    """初始化数据库连接"""
    dsn = hook_ctx.get("MYSQL_MAIN__DEFAULT__DSN", "")
    if dsn:
        db = DatabaseProxy(dsn=dsn)
        hook_ctx["_db_proxy"] = db

def expected_sql_value(record_id, column="value", table="orders"):
    """从数据库查询期望值"""
    from drun.db.database_proxy import get_db
    db = get_db()
    if not db:
        return None
    
    query = f"SELECT {column} FROM {table} WHERE id = %s"
    result = db.execute_query(query, (record_id,))
    return result[0][column] if result else None
```

在测试中使用：
```yaml
name: 订单数据一致性验证
setup_hooks:
  - setup_hook_assert_sql

steps:
  - name: 创建订单
    request:
      method: POST
      url: /api/v1/orders
      body:
        items: [{product_id: 1, quantity: 2, price: 99.99}]
        shipping_fee: 10.00
    extract:
      - order_id: $.data.order_id
    validate:
      - eq: [$.data.total, 209.98]

  - name: 验证订单金额写入数据库
    validate:
      - eq: [${expected_sql_value($order_id, column="total")}, 209.98]

  - name: 验证订单状态
    validate:
      - eq: [${expected_sql_value($order_id, column="status")}, "pending"]
```

### 模板函数

#### 内置函数

```yaml
config:
  variables:
    # 时间相关
    timestamp: ${now()}
    date_str: ${now("%Y-%m-%d")}
    
    # UUID 生成
    uuid: ${uuid()}
    request_id: ${short_uid(16)}
    
    # 随机数
    random_num: ${random_int(1, 100)}
    
    # 编码
    encoded: ${base64_encode("hello world")}
    
    # HMAC 签名
    signature: ${hmac_sha256("message", "secret")}

steps:
  - name: 使用模板函数
    request:
      method: POST
      url: /api/v1/events
      headers:
        X-Request-ID: ${request_id}
        X-Timestamp: ${timestamp}
      body:
        event_id: ${uuid}
        value: ${random_num}
```

#### 自定义函数

在 `drun_hooks.py` 中定义：
```python
def calculate_checksum(data: str) -> str:
    """计算校验和"""
    import hashlib
    return hashlib.md5(data.encode()).hexdigest()

def generate_order_number(prefix: str = "ORD") -> str:
    """生成订单号"""
    import time
    import random
    timestamp = int(time.time())
    random_part = random.randint(1000, 9999)
    return f"{prefix}{timestamp}{random_part}"
```

在测试中使用：
```yaml
steps:
  - name: 创建订单
    request:
      method: POST
      url: /api/v1/orders
      body:
        order_number: ${generate_order_number("ORD")}
        checksum: ${calculate_checksum("data")}
```

### 性能监控

监控接口响应时间并设置阈值：

```yaml
name: 性能测试
config:
  base_url: ${ENV(BASE_URL)}
  tags: [performance]

steps:
  - name: 列表接口性能测试
    request:
      method: GET
      url: /api/v1/products
      query:
        page: 1
        size: 50
    validate:
      - eq: [$.code, 200]
      - le: [$elapsed_ms, 1000]  # 响应时间 <= 1秒

  - name: 搜索接口性能测试
    request:
      method: POST
      url: /api/v1/products/search
      body:
        keyword: "test"
    validate:
      - le: [$elapsed_ms, 2000]  # 响应时间 <= 2秒
```

### 数据提取与复用

复杂的数据提取与跨步骤复用：

```yaml
steps:
  - name: 创建订单
    request:
      method: POST
      url: /api/v1/orders
      body:
        items: [
          {product_id: 1, quantity: 2},
          {product_id: 2, quantity: 1}
        ]
    extract:
      # 提取基础字段
      - order_id: $.data.order_id
      - order_number: $.data.order_number
      
      # 提取嵌套字段
      - total_amount: $.data.payment.total
      - discount: $.data.payment.discount
      
      # 提取数组元素
      - first_item_id: $.data.items[0].id
      - first_item_name: $.data.items[0].name
      
      # 提取数组长度
      - items_count: length($.data.items)

  - name: 查询订单详情
    request:
      method: GET
      url: /api/v1/orders/${order_id}
    validate:
      - eq: [$.data.order_number, ${order_number}]
      - eq: [$.data.total, ${total_amount}]
      - len_eq: [$.data.items, ${items_count}]
```

### 条件跳过与重试

```yaml
steps:
  - name: 可选的预检查
    request:
      method: GET
      url: /api/v1/health
    skip_if: ${ENV(SKIP_HEALTH_CHECK, false)}

  - name: 可能不稳定的接口
    request:
      method: GET
      url: /api/v1/unstable
      retry: 3
      timeout: 10
    validate:
      - eq: [$.status, "ok"]
```

## 📚 示例项目

完整示例项目位于 `ecommerce-api-test/` 目录，包含：

### 测试用例（17个）
- **健康检查** - `test_health_check.yaml`
- **用户认证流程** - `test_auth_flow.yaml`
- **商品管理** - `test_products.yaml`
- **购物车操作** - `test_shopping_cart.yaml`
- **订单管理** - `test_orders.yaml`
- **E2E 完整流程** - `test_e2e_purchase.yaml`
- **管理员权限** - `test_admin_permissions.yaml`
- **SQL 数据验证** - `test_*_with_sql.yaml`
- **断言示例** - `test_assertions.yaml`
- **CSV 参数化** - `test_import_users.yaml`

### 测试套件（3个）
- **冒烟测试** - `testsuite_smoke.yaml` (~30秒)
- **回归测试** - `testsuite_regression.yaml` (~5-10分钟)
- **CSV 测试** - `testsuite_csv.yaml`

### 格式转换示例
- cURL 命令示例
- Postman Collection 示例
- HAR 浏览器录制示例
- OpenAPI 规范示例

运行示例项目：
```bash
cd ecommerce-api-test

# 配置环境
cp .env.example .env
vim .env  # 编辑配置

# 运行冒烟测试
drun run testsuites/testsuite_smoke.yaml

# 运行完整回归测试
drun run testsuites/testsuite_regression.yaml --html reports/report.html

# 运行 E2E 流程
drun run testcases/test_e2e_purchase.yaml
```

## 🧪 开发与测试

### 开发环境搭建

```bash
# 克隆仓库
git clone https://github.com/Devliang24/drun.git
cd drun

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 开发模式安装
pip install -e .

# 安装开发依赖
pip install pytest pytest-cov black flake8
```

### 运行单元测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行覆盖率测试
pytest tests/ --cov=drun --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

### 代码规范检查

```bash
# 运行 drun check 检查测试用例
drun check testcases/

# 自动修复问题
drun fix testcases/ --only-spacing
```

## 📈 CI/CD 集成

### GitHub Actions

创建 `.github/workflows/api-tests.yml`：

```yaml
name: API Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 0 * * *'  # 每日定时执行

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -e .

      - name: Run smoke tests
        env:
          BASE_URL: ${{ secrets.BASE_URL }}
          MYSQL_MAIN__DEFAULT__DSN: ${{ secrets.MYSQL_DSN }}
        run: |
          drun run testsuites/testsuite_smoke.yaml \
            --html reports/smoke_report.html \
            --report reports/smoke_run.json

      - name: Run regression tests
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
        env:
          BASE_URL: ${{ secrets.BASE_URL }}
          MYSQL_MAIN__DEFAULT__DSN: ${{ secrets.MYSQL_DSN }}
        run: |
          drun run testsuites/testsuite_regression.yaml \
            --html reports/regression_report.html \
            --report reports/regression_run.json \
            --notify feishu \
            --notify-only failed

      - name: Upload test reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-reports-${{ matrix.python-version }}
          path: reports/

      - name: Publish test results
        uses: EnricoMi/publish-unit-test-result-action@v2
        if: always()
        with:
          files: reports/*.json
```

### GitLab CI

创建 `.gitlab-ci.yml`：

```yaml
stages:
  - test
  - report

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip
    - venv/

before_script:
  - python -m venv venv
  - source venv/bin/activate
  - pip install -e .

smoke-tests:
  stage: test
  script:
    - drun run testsuites/testsuite_smoke.yaml 
        --html reports/smoke_report.html 
        --report reports/smoke_run.json
  artifacts:
    when: always
    paths:
      - reports/
    reports:
      junit: reports/*.xml

regression-tests:
  stage: test
  only:
    - main
    - schedules
  script:
    - drun run testsuites/testsuite_regression.yaml 
        --html reports/regression_report.html 
        --report reports/regression_run.json
        --notify dingtalk
        --notify-only failed
  artifacts:
    when: always
    paths:
      - reports/

pages:
  stage: report
  dependencies:
    - regression-tests
  script:
    - mkdir -p public
    - cp -r reports/* public/
  artifacts:
    paths:
      - public
  only:
    - main
```

### Jenkins Pipeline

创建 `Jenkinsfile`：

```groovy
pipeline {
    agent any

    environment {
        BASE_URL = credentials('api-base-url')
        MYSQL_DSN = credentials('mysql-dsn')
    }

    stages {
        stage('Setup') {
            steps {
                sh 'python -m venv venv'
                sh '. venv/bin/activate && pip install -e .'
            }
        }

        stage('Smoke Tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    drun run testsuites/testsuite_smoke.yaml \
                        --html reports/smoke_report.html \
                        --report reports/smoke_run.json
                '''
            }
        }

        stage('Regression Tests') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    . venv/bin/activate
                    drun run testsuites/testsuite_regression.yaml \
                        --html reports/regression_report.html \
                        --report reports/regression_run.json \
                        --notify email \
                        --notify-only failed
                '''
            }
        }
    }

    post {
        always {
            publishHTML([
                allowMissing: false,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'reports',
                reportFiles: '*.html',
                reportName: 'API Test Report'
            ])
            
            archiveArtifacts artifacts: 'reports/**/*', fingerprint: true
        }
        
        failure {
            emailext (
                subject: "API Tests Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                body: "Check console output at ${env.BUILD_URL}",
                to: 'qa-team@example.com'
            )
        }
    }
}
```

## 🤝 贡献指南

我们欢迎各种形式的贡献！

### 如何贡献

1. **Fork 本仓库**
2. **创建特性分支** (`git checkout -b feature/amazing-feature`)
3. **提交更改** (`git commit -m 'feat: add amazing feature'`)
4. **推送到分支** (`git push origin feature/amazing-feature`)
5. **发起 Pull Request**

### 提交规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
feat: 新功能
fix: 修复 Bug
docs: 文档更新
style: 代码格式调整
refactor: 代码重构
test: 测试相关
chore: 构建/工具链更新
```

示例：
```
feat: add GraphQL support
fix: resolve encoding issue in response body
docs: update installation guide
```

### 开发规范

- 遵循 PEP 8 代码风格
- 使用类型注解
- 为新功能编写单元测试
- 更新相关文档
- 提交前运行 `drun check` 和 `pytest`

### 项目结构

```
drun/
├── drun/                    # 核心代码
│   ├── cli.py               # CLI 命令入口（1967行）
│   ├── __init__.py          # 版本信息
│   ├── engine/              # HTTP 引擎
│   │   └── http.py          # httpx 客户端封装
│   ├── loader/              # 加载器
│   │   ├── yaml_loader.py   # YAML 解析
│   │   ├── collector.py     # 用例发现
│   │   ├── env.py           # 环境加载
│   │   └── hooks.py         # Hook 发现
│   ├── models/              # 数据模型
│   │   ├── case.py          # 用例/套件模型
│   │   ├── step.py          # 步骤模型
│   │   ├── request.py       # 请求模型
│   │   ├── config.py        # 配置模型
│   │   ├── report.py        # 报告模型
│   │   └── validators.py    # 校验器
│   ├── runner/              # 运行器
│   │   ├── runner.py        # 核心执行逻辑（818行）
│   │   ├── assertions.py    # 断言引擎
│   │   └── extractors.py    # 提取引擎
│   ├── templating/          # 模板引擎
│   │   ├── engine.py        # Dollar 表达式
│   │   ├── builtins.py      # 内置函数
│   │   └── context.py       # 变量上下文
│   ├── reporter/            # 报告生成
│   │   ├── json_reporter.py # JSON 报告
│   │   ├── html_reporter.py # HTML 报告
│   │   └── allure_reporter.py # Allure 集成
│   ├── notifier/            # 通知模块
│   │   ├── base.py          # 通知基类
│   │   ├── feishu.py        # 飞书通知
│   │   ├── dingtalk.py      # 钉钉通知
│   │   ├── emailer.py       # 邮件通知
│   │   └── format.py        # 消息格式化
│   ├── db/                  # 数据库模块
│   │   ├── database_proxy.py # 数据库代理
│   │   └── generate_mysql_config.py
│   ├── importers/           # 格式导入
│   │   ├── base.py          # 导入基类
│   │   ├── curl.py          # cURL 导入
│   │   ├── postman.py       # Postman 导入
│   │   ├── har.py           # HAR 导入
│   │   └── openapi.py       # OpenAPI 导入
│   ├── exporters/           # 格式导出
│   │   └── curl.py          # cURL 导出
│   ├── scaffolds/           # 脚手架
│   │   └── templates.py     # 项目模板
│   └── utils/               # 工具函数
│       ├── logging.py       # 日志
│       ├── mask.py          # 脱敏
│       ├── curl.py          # cURL 工具
│       ├── errors.py        # 错误定义
│       ├── timeit.py        # 计时
│       └── config.py        # 配置工具
├── ecommerce-api-test/      # 示例项目
├── docs/                    # 文档
├── tests/                   # 单元测试
├── pyproject.toml           # 项目配置
├── LICENSE                  # MIT 许可证
└── README.md                # 英文文档
```

## ❓ 常见问题

### 安装与配置

**Q: 如何升级到最新版本？**
```bash
pip install --upgrade drun
```

**Q: 虚拟环境安装失败？**
```bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install drun
```

### 测试执行

**Q: 如何调试失败的测试用例？**

1. 查看详细日志：
```bash
drun run testcases/test_failed.yaml --log-level debug
```

2. 导出 cURL 复现问题：
```bash
drun export curl testcases/test_failed.yaml --steps 3
```

3. 查看 HTML 报告中的请求/响应详情

**Q: 如何处理动态参数（如时间戳、签名）？**

使用内置函数或自定义 Hook：
```yaml
config:
  variables:
    timestamp: ${now()}
    signature: ${hmac_sha256("${timestamp}:${secret}", "${app_key}")}

# 或使用 Hook
setup_hooks:
  - setup_hook_generate_signature
```

**Q: 测试用例执行太慢怎么办？**

1. 使用标签筛选只运行需要的测试
2. 调整超时设置
3. 检查是否有不必要的 sleep 或重试
4. 考虑并行执行（未来版本支持）

### 数据库相关

**Q: 支持哪些数据库？**

当前原生支持 MySQL。可通过扩展 `drun/db/database_proxy.py` 支持其他数据库（PostgreSQL、MongoDB 等）。

**Q: 数据库连接失败怎么办？**

检查配置：
```env
# 确保 DSN 格式正确
MYSQL_MAIN__DEFAULT__DSN=mysql://user:password@host:port/database

# 检查字符集配置
MYSQL_MAIN__DEFAULT__CHARSET=utf8mb4
```

验证连接：
```bash
# 使用 mysql 客户端测试
mysql -h host -P port -u user -p database
```

### 报告与通知

**Q: HTML 报告中看不到响应体？**

确保响应是 JSON 格式，或检查是否被 `--mask-secrets` 脱敏。

**Q: 飞书/钉钉通知发送失败？**

1. 检查 Webhook URL 是否正确
2. 验证 Secret 配置（如果启用签名）
3. 查看日志中的错误信息
4. 测试 Webhook 可用性（使用 curl 发送测试消息）

**Q: 如何在报告中脱敏敏感信息？**

```bash
drun run testcases/ --html reports/report.html --mask-secrets
```

在代码中配置需要脱敏的字段：
```python
# drun/utils/mask.py
SENSITIVE_KEYS = ['password', 'token', 'secret', 'authorization']
```

### CI/CD 集成

**Q: 如何在 CI 中处理环境变量？**

```yaml
# GitHub Actions 示例
- name: Run tests
  env:
    BASE_URL: ${{ secrets.BASE_URL }}
    MYSQL_MAIN__DEFAULT__DSN: ${{ secrets.MYSQL_DSN }}
  run: drun run testsuites/regression.yaml
```

**Q: CI 中测试失败但本地正常？**

1. 检查环境变量是否正确配置
2. 确认网络访问权限
3. 查看 CI 日志中的详细错误信息
4. 考虑环境差异（数据库、API 版本等）

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

```
MIT License

Copyright (c) 2025 Drun Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 🆘 支持与联系

- 📖 **文档**: [在线文档](https://github.com/Devliang24/drun/tree/main/docs)
- 💬 **讨论**: [GitHub Discussions](https://github.com/Devliang24/drun/discussions)
- 🐛 **问题反馈**: [GitHub Issues](https://github.com/Devliang24/drun/issues)
- 📧 **邮件**: support@example.com

## 🎯 路线图

### 计划中的功能

- [ ] **GraphQL 支持** - GraphQL API 测试能力
- [ ] **gRPC 测试** - gRPC 服务测试支持
- [ ] **WebSocket 测试** - WebSocket 协议测试
- [ ] **并行执行** - 多线程/多进程并行运行测试
- [ ] **可视化编辑器** - Web UI 可视化测试设计器
- [ ] **云端执行** - 云端分布式测试执行平台
- [ ] **性能测试模块** - 负载测试和压力测试
- [ ] **Mock 服务** - 内置 Mock Server 功能
- [ ] **数据库支持扩展** - PostgreSQL、MongoDB、Redis 等
- [ ] **插件系统** - 支持第三方插件扩展

### 近期更新（v2.5.0 规划）

- [ ] 并行执行支持
- [ ] GraphQL 查询测试
- [ ] 更多断言操作符
- [ ] 性能测试基础框架
- [ ] 增强的错误诊断

## 📌 版本历史

详见 [CHANGELOG.md](CHANGELOG.md)。

### 最新版本: 2.4.10 (2025-10-31)

- ✅ 数据库配置简化为使用环境变量
- ✅ 标签过滤功能改进
- ✅ SSE 流式响应支持增强
- ✅ Bug 修复和性能优化

### 版本亮点

- **v2.4.x** - 数据库断言、环境管理优化、通知增强
- **v2.3.x** - CSV 参数化、格式转换改进
- **v2.2.x** - 断言操作符扩展、脚手架优化
- **v2.1.x** - Hook 增强、批量 SQL 断言
- **v2.0.x** - HTTP Stat 功能、SQL 校验重构

## 🏆 致谢

感谢所有贡献者的付出！

特别感谢以下开源项目：
- [httpx](https://github.com/encode/httpx) - 现代化的 HTTP 客户端
- [pydantic](https://github.com/pydantic/pydantic) - 数据验证框架
- [typer](https://github.com/tiangolo/typer) - CLI 构建框架
- [jmespath](https://github.com/jmespath/jmespath.py) - JSON 查询语言
- [rich](https://github.com/Textualize/rich) - 终端美化

## 📊 项目统计

- **版本**: 2.4.10
- **代码行数**: 8,000+ 行核心代码
- **Python 版本**: 3.10+
- **依赖包**: 6 个核心依赖
- **测试用例**: 完整的电商 API 测试套件（17个用例）
- **文档**: 完善的中英文档与示例
- **开源协议**: MIT License

---

**⭐ 如果这个项目对您有帮助，请给我们一个 Star！**

**Built with ❤️ by Drun Team**

*零代码测试，让 API 测试更简单*

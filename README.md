# Drun — Modern HTTP API Testing Framework

[![Version](https://img.shields.io/badge/version-7.0.0-blue.svg)](https://github.com/Devliang24/drun)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Drun** — Easy-to-use API testing with DevOps automation support. Write tests in simple YAML, run anywhere with CI/CD integration.

## 🎯 Why Drun?

- **Zero Code Required**: Write tests in simple YAML, no programming knowledge needed
- **Postman-Like Experience**: Variable extraction, environment management, and test chaining
- **Developer Friendly**: Dollar-style templating, built-in functions, and custom hooks
- **CI/CD Ready**: HTML/JSON/Allure reports, notifications, and exit codes
- **Format Agnostic**: Import from cURL, Postman, HAR, OpenAPI; export to cURL
- **Modern Stack**: Built on httpx, Pydantic v2, and typer for reliability

## ✨ Key Features

### Core Testing Capabilities
- ✅ **YAML DSL**: Intuitive test case syntax with `config`, `steps`, `extract`, `validate`, `export`
- ✅ **Dollar Templating**: `$var` and `${func(...)}` for dynamic values
- ✅ **Rich Assertions**: 12 validators (eq, ne, lt, contains, regex, len_eq, etc.)
- ✅ **Data-Driven**: CSV parameters for batch testing
- ✅ **CSV Export**: Export API response arrays to CSV files (v4.2)
- ✅ **Streaming Support**: SSE (Server-Sent Events) with per-event assertions
- ✅ **File Uploads**: Multipart/form-data support
- ✅ **Smart File Discovery**: Run tests without `.yaml` extension (NEW in v5.0)

### Variable Management (NEW in v4.0)
- ✅ **Auto-Persist**: Extracted variables automatically saved to `.env`
- ✅ **Smart Naming**: `token` → `TOKEN`, `apiKey` → `API_KEY` conversion
- ✅ **Memory Passing**: Variables shared between test cases in suites
- ✅ **Environment Files**: Support for `.env`, YAML env files, and OS variables

### Advanced Features
- ✅ **Custom Hooks**: Python functions for setup/teardown and request signing
- ✅ **Test Suites**: Ordered execution with variable chaining
- ✅ **Authentication**: Basic/Bearer auth with auto-injection
- ✅ **Tag Filtering**: Boolean expressions like `smoke and not slow`
- ✅ **Database Assertions**: MySQL integration for data validation

### Reports & Integrations
- ✅ **HTML Reports**: Single-file, shareable test reports
- ✅ **JSON/Allure**: Structured results for CI/CD pipelines
- ✅ **Notifications**: Feishu, DingTalk, Email alerts on failure
- ✅ **Format Conversion**: Import/export with cURL, Postman, HAR, OpenAPI
- ✅ **Code Snippets**: Auto-generate executable Shell and Python scripts (v4.2)
- ✅ **Unified Logging**: Consistent log format with timestamps (NEW in v5.0)
- ✅ **Web Report Server**: Real-time HTML report viewing with SQLite database (NEW in v6.0)

## 🚀 Quick Start

### Installation

```bash
# Install uv (if not installed)
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Create virtual environment
uv venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install drun
uv pip install drun

# Update drun to latest version
uv pip install --upgrade drun
```

**Requirements**: Python 3.10+

> 💡 推荐使用 [uv](https://docs.astral.sh/uv/) 管理虚拟环境。也支持传统方式：`pip install drun`

### Initialize a Project

```bash
drun init my-api-test
cd my-api-test
```

This creates:
```
my-api-test/
├── testcases/                      # 测试用例目录
│   ├── test_demo.yaml              # HTTP 功能演示
│   ├── test_api_health.yaml        # 健康检查示例
│   ├── test_performance.yaml       # 性能分析示例
│   ├── test_import_users.yaml      # CSV 参数化用例
│   ├── test_db_assert.yaml         # 数据库断言示例
│   ├── test_assertions.yaml        # 断言操作符示例
│   └── test_stream.yaml            # 流式响应示例
├── testsuites/                     # 测试套件目录
│   ├── testsuite_smoke.yaml        # 冒烟测试套件
│   └── testsuite_csv.yaml          # CSV 示例套件
├── data/                           # 测试数据目录
│   └── users.csv                   # CSV 参数数据
├── converts/                       # 格式转换源文件
│   ├── curl/
│   │   └── sample.curl             # cURL 命令示例
│   ├── postman/
│   │   ├── sample_collection.json  # Postman Collection
│   │   └── sample_environment.json # Postman 环境变量
│   ├── har/
│   │   └── sample_recording.har    # HAR 录制文件
│   └── openapi/
│       └── sample_openapi.json     # OpenAPI 规范
├── reports/                        # HTML/JSON 报告输出
├── logs/                           # 日志文件输出
├── snippets/                       # 自动生成代码片段
├── .env                            # 环境变量配置
├── drun_hooks.py                   # 自定义 Hooks 函数
├── .gitignore                      # Git 忽略规则
└── README.md                       # 项目说明文档
```

### Create Your First Test

**.env**
```bash
BASE_URL=https://api.example.com
API_KEY=your-api-key-here
```

**testcases/test_user_api.yaml**
```yaml
config:
  name: User API Test
  base_url: ${ENV(BASE_URL)}
  tags: [smoke, users]

steps:
  - name: Create User
    request:
      method: POST
      path: /users
      headers:
        Authorization: Bearer ${ENV(API_KEY)}
      body:
        username: testuser_${uuid()}
        email: test@example.com
    extract:
      userId: $.data.id
      username: $.data.username
    validate:
      - eq: [status_code, 201]
      - regex: [$.data.id, '^\d+$']
      - eq: [$.data.email, test@example.com]

  - name: Get User
    request:
      method: GET
      path: /users/${ENV(USER_ID)}
      headers:
        Authorization: Bearer ${ENV(API_KEY)}
    validate:
      - eq: [status_code, 200]
      - eq: [$.data.id, ${ENV(USER_ID)}]
      - eq: [$.data.username, ${ENV(USERNAME)}]
```

### Run Tests

```bash
# Run single test (with or without .yaml extension)
drun r testcases/test_user_api.yaml
drun r test_user_api

# Run with HTML report
drun r test_user_api --html reports/report.html

# Run with tag filtering
drun r testcases -k "smoke and not slow"

# Run test suite
drun r testsuite_e2e
```

## 📚 Core Concepts

### Test Case Structure

```yaml
config:
  name: Test name
  base_url: https://api.example.com
  tags: [smoke, api]
  variables:
    dynamic_value: ${uuid()}
  timeout: 30.0
  headers:
    User-Agent: Drun-Test

steps:
  - name: Step name
    request:
      method: POST
      path: /endpoint
      params: { key: value }
      headers: { Authorization: Bearer token }
      body: { data: value }
      auth:
        type: bearer
        token: ${ENV(API_TOKEN)}
      timeout: 10.0
    extract:
      variableName: $.response.path
    export:
      csv:
        data: $.response.items
        file: data/output.csv
    validate:
      - eq: [status_code, 200]
      - contains: [$.data.message, success]
    setup_hooks:
      - ${custom_function($request)}
    teardown_hooks:
      - ${cleanup_function()}
```

### Variable Extraction & Auto-Persist (v4.0)

**Extraction automatically persists to environment:**

```yaml
# test_login.yaml
steps:
  - name: Login
    request:
      method: POST
      path: /login
      body:
        username: admin
        password: pass123
    extract:
      token: $.data.token          # Auto-saved as TOKEN=value
      userId: $.data.user.id       # Auto-saved as USER_ID=value
```

**Variables immediately available in subsequent tests:**

```yaml
# test_orders.yaml
steps:
  - name: Create Order
    request:
      method: POST
      path: /orders
      headers:
        Authorization: Bearer ${ENV(TOKEN)}  # Uses extracted token
      body:
        user_id: ${ENV(USER_ID)}            # Uses extracted userId
```

### Test Suites & Execution Order

```yaml
# testsuites/testsuite_e2e.yaml
config:
  name: E2E Test Flow
  base_url: ${ENV(BASE_URL)}
  tags: [e2e, critical]

testcases:
  - testcases/test_login.yaml          # 1. Extract token
  - testcases/test_create_order.yaml   # 2. Use token, extract orderId
  - testcases/test_payment.yaml        # 3. Use token & orderId
  - testcases/test_verify.yaml         # 4. Final verification
```

**Execution characteristics:**
- Strict sequential order (top to bottom)
- Variables shared via memory (no file I/O between tests)
- `.env` file read once at startup
- Variables extracted during run are persisted to `.env`

### Template System

**Dollar-style syntax:**
```yaml
variables:
  user_id: 12345
  timestamp: ${now()}

request:
  path: /users/$user_id?t=$timestamp  # Simple variable
  body:
    uuid: ${uuid()}                    # Function call
    auth_key: ${ENV(API_KEY, default)} # Env variable with default
```

**Built-in functions:**
- `now()` - ISO 8601 timestamp
- `uuid()` - UUID v4
- `random_int(min, max)` - Random integer
- `base64_encode(str)` - Base64 encoding
- `hmac_sha256(key, message)` - HMAC SHA256
- `fake_name()` - Random person name
- `fake_email()` - Random email address
- `fake_address()` - Random street address
- `fake_city()` - Random city name
- `fake_text(max_chars)` - Random text paragraph
- `fake_url()` - Random URL
- `fake_phone_number()` - Random phone number
- `fake_company()` - Random company name
- `fake_date()` - Random date string
- `fake_ipv4()` - Random IPv4 address
- `fake_user_agent()` - Random user agent string

### Assertions

```yaml
validate:
  # Equality
  - eq: [status_code, 200]
  - ne: [$.error, null]
  
  # Comparison
  - lt: [$.count, 100]
  - le: [$.price, 99.99]
  - gt: [$.total, 0]
  - ge: [$.age, 18]
  
  # String/Array operations
  - contains: [$.message, success]
  - not_contains: [$.errors, critical]
  - regex: [$.email, '^[a-z0-9]+@[a-z]+\.[a-z]{2,}$']
  - in: [$.status, [pending, approved, completed]]
  - not_in: [$.role, [banned, suspended]]
  
  # Collections
  - len_eq: [$.items, 5]
  - contains_all: [$.tags, [api, v1, public]]
  - match_regex_all: [$.emails, '^[a-z]+@example\.com$']
  
  # Performance
  - le: [$elapsed_ms, 2000]  # Response time ≤ 2s
```

### Data-Driven Testing (CSV)

**data/users.csv**
```csv
username,email,role
alice,alice@example.com,admin
bob,bob@example.com,user
carol,carol@example.com,guest
```

**Test case:**
```yaml
config:
  name: Batch User Registration
  parameters:
    - csv:
        path: data/users.csv
        strip: true

steps:
  - name: Register $username
    request:
      method: POST
      path: /register
      body:
        username: $username
        email: $email
        role: $role
    validate:
      - eq: [status_code, 201]
      - eq: [$.data.username, $username]
```

Drun will execute the test 3 times (once per CSV row).

### CSV Export (NEW in v4.2)

Export API response arrays to CSV files, similar to Postman's data export:

```yaml
steps:
  - name: Export User Data
    request:
      method: GET
      path: /api/users
    extract:
      userCount: $.data.total
    export:
      csv:
        data: $.data.users           # JMESPath expression
        file: data/users.csv         # Output file path
    validate:
      - eq: [status_code, 200]
      - gt: [$userCount, 0]
```

**Advanced options:**

```yaml
export:
  csv:
    data: $.data.orders
    file: reports/orders_${now()}.csv    # Dynamic filename
    columns: [orderId, customerName, totalAmount]  # Select columns
    mode: append                         # append or overwrite
    encoding: utf-8                      # File encoding
    delimiter: ","                       # CSV delimiter
```

**Common use cases:**

```yaml
# Filter and export
export:
  csv:
    data: $.users[?status=='active']    # JMESPath filter
    file: data/active_users.csv

# Paginated export with append
config:
  parameters:
    - page: [1, 2, 3, 4, 5]
steps:
  - name: Export page $page
    request:
      method: GET
      path: /api/products?page=$page
    export:
      csv:
        data: $.data.items
        file: data/all_products.csv
        mode: append                     # Append to file
```

**Comparison with extract:**

| Feature | extract | export |
|---------|---------|--------|
| Target | Memory variables | Disk files |
| Data type | Any type | Arrays only |
| Purpose | Temporary usage | Persistent storage |
| Example | `userId: $.data.id` | `csv: {data: $.data.users, file: users.csv}` |

CSV export functionality is fully documented above with complete examples.

### Code Snippets (NEW in v4.2)

Automatically generate executable Shell and Python scripts from test steps, similar to Postman's code snippet feature:

```bash
# Run test - code snippets are generated automatically (extension optional in v5.0)
$ drun r test_login

2025-11-24 14:23:18.551 | INFO | [CASE] Total: 1 Passed: 1 Failed: 0 Skipped: 0
2025-11-24 14:23:18.553 | INFO | [CASE] HTML report written to reports/report.html
2025-11-24 14:23:18.559 | INFO | [SNIPPET] Code snippets saved to snippets/20251124-143025/
2025-11-24 14:23:18.560 | INFO | [SNIPPET]   - step1_login_curl.sh
2025-11-24 14:23:18.560 | INFO | [SNIPPET]   - step1_login_python.py
2025-11-24 14:23:18.561 | INFO | [SNIPPET]   - step2_get_user_info_curl.sh
2025-11-24 14:23:18.561 | INFO | [SNIPPET]   - step2_get_user_info_python.py
2025-11-24 14:23:18.562 | INFO | [SNIPPET]   - step3_update_profile_curl.sh
2025-11-24 14:23:18.562 | INFO | [SNIPPET]   - step3_update_profile_python.py
```

**Generated Shell script (step1_login_curl.sh):**
```bash
#!/bin/bash
set -e  # Exit on error

echo "=== Step 1: Login ==="

curl -X POST 'https://api.example.com/api/v1/login' \
  -H 'Content-Type: application/json' \
  --data-raw '{"username":"admin","password":"pass123"}'

echo ""
echo "✅ Request completed"
```

**Generated Python script (step1_login_python.py):**
```python
import requests
import json

url = "https://api.example.com/api/v1/login"

payload = json.dumps({
  "username": "admin",
  "password": "pass123"
})
headers = {
  "Content-Type": "application/json"
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
```

**Execute generated scripts:**
```bash
# Run shell script
$ bash snippets/20251124-143025/step1_login_curl.sh

# Run Python script
$ python3 snippets/20251124-143025/step1_login_python.py
```

**CLI Options:**
```bash
# Extension optional (NEW in v5.0)
$ drun r test_api

# Disable snippet generation
$ drun r test_api --no-snippet

# Generate only Python scripts
$ drun r test_api --snippet-lang python

# Generate only curl scripts
$ drun r test_api --snippet-lang curl

# Custom output directory
$ drun r test_api --snippet-output exports/
```

**Features:**
- ✅ Each step generates independent executable files
- ✅ Timestamp-based directory management (no overwrite)
- ✅ Auto-detect variable dependencies with hints
- ✅ Scripts include shebang and execute permissions
- ✅ Support for all HTTP methods, headers, body, auth, timeout

### Custom Hooks

**drun_hooks.py**
```python
import hmac
import hashlib
import time

def setup_hook_sign_request(hook_ctx):
    """Add HMAC signature to request"""
    timestamp = str(int(time.time()))
    secret = hook_ctx['env'].get('API_SECRET', '')
    
    message = f"{timestamp}:{hook_ctx['body']}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return {
        'timestamp': timestamp,
        'signature': signature
    }

def teardown_hook_cleanup(hook_ctx):
    """Cleanup test data"""
    # Implement cleanup logic
    pass
```

**Usage in YAML:**
```yaml
steps:
  - name: Signed Request
    setup_hooks:
      - ${setup_hook_sign_request($request)}
    request:
      method: POST
      path: /api/secure
      headers:
        X-Timestamp: $timestamp
        X-Signature: $signature
      body: { data: sensitive }
    teardown_hooks:
      - ${teardown_hook_cleanup()}
```

## 🔧 CLI Reference

### Web Report Server (NEW in v6.0)

```bash
# Start report server
drun s

# Custom port and options
drun s --port 8080 --no-open

# Development mode with auto-reload
drun s --reload

# Server will be accessible at http://0.0.0.0:8080
# Features:
# - Auto-scans reports/ directory
# - Real-time report indexing with SQLite
# - Paginated list view (15 reports per page)
# - Detailed report view with back navigation
# - Statistics dashboard
# - RESTful API at /api/reports
```

### Run Tests

```bash
# Basic execution
drun r PATH

# Smart file discovery (NEW in v5.0) - extension optional
drun r test_api_health              # Finds test_api_health.yaml or .yml
drun r testcases/test_user          # Supports paths without extension
drun r test_api_health.yaml         # Traditional format still works

# With options
drun r testcases/ \
  -k "smoke and not slow" \
  --vars api_key=secret \
  --env-file .env.staging \
  --html reports/report.html \
  --report reports/results.json \
  --allure-results allure-results \
  --mask-secrets \
  --failfast
```

**Options:**
- `-k TAG_EXPR`: Filter by tags (e.g., `smoke and not slow`)
- `--vars k=v`: Override variables from CLI
- `--env-file PATH`: Specify environment file (supports aliases: `dev`, `staging`, `prod`)
- `--html FILE`: Generate HTML report
- `--report FILE`: Generate JSON report
- `--allure-results DIR`: Generate Allure results
- `--mask-secrets`: Mask sensitive data in logs/reports
- `--reveal-secrets`: Show sensitive data (default for local runs)
- `--response-headers`: Log response headers
- `--failfast`: Stop on first failure
- `--log-level LEVEL`: Set log level (DEBUG, INFO, WARNING, ERROR)
- `--log-file FILE`: Write logs to file
- `--notify CHANNELS`: Enable notifications (feishu, dingtalk, email)
- `--notify-only POLICY`: Notification policy (always, failed, passed)
- `--no-snippet`: Disable code snippet generation
- `--snippet-output DIR`: Custom output directory for snippets (default: snippets/{timestamp}/)
- `--snippet-lang LANG`: Generate snippets in specific language: all|curl|python (default: all)

### Format Conversion

```bash
# cURL to YAML
drun convert sample.curl --outfile testcases/from_curl.yaml

# With redaction and placeholders
drun convert sample.curl \
  --outfile testcases/from_curl.yaml \
  --redact Authorization,Cookie \
  --placeholders

# Postman Collection to YAML (with split output)
drun convert collection.json \
  --split-output \
  --suite-out testsuites/from_postman.yaml \
  --postman-env environment.json \
  --placeholders

# HAR to YAML
drun convert recording.har \
  --outfile testcases/from_har.yaml \
  --exclude-static \
  --only-2xx

# OpenAPI to YAML
drun convert-openapi openapi.json \
  --outfile testcases/from_openapi.yaml \
  --tags users,orders \
  --split-output \
  --placeholders
```

### Export to cURL

```bash
# Basic export
drun export curl testcases/test_api.yaml

# Advanced options
drun export curl testcases/test_api.yaml \
  --case-name "User API Test" \
  --steps 1,3-5 \
  --multiline \
  --shell sh \
  --redact Authorization \
  --with-comments \
  --outfile export.curl
```

### Other Commands

```bash
# List all tags
drun tags testcases/

# Check syntax and style
drun check testcases/

# Auto-fix YAML formatting
drun fix testcases/
drun fix testcases/ --only-spacing
drun fix testcases/ --only-hooks

# Initialize new project
drun init my-project
drun init my-project --force

# Version info
drun --version
```

## 🎨 Reports & Notifications

### HTML Reports

```bash
drun r testcases --html reports/report.html --mask-secrets
```

**Features:**
- Single-file HTML (no external dependencies)
- Request/response details
- Assertion results with highlighting
- Execution timeline
- Secret masking
- Responsive design

### JSON Reports

```bash
drun r testcases --report reports/results.json
```

**Structure:**
```json
{
  "summary": {
    "total": 10,
    "passed": 9,
    "failed": 1,
    "skipped": 0,
    "duration_ms": 5432.1
  },
  "cases": [
    {
      "name": "Test Name",
      "status": "passed",
      "duration_ms": 1234.5,
      "steps": [...]
    }
  ]
}
```

### Allure Integration

```bash
# Generate Allure results
drun r testcases --allure-results allure-results

# View Allure report
allure serve allure-results
```

### Notifications

**Environment variables:**
```bash
# Feishu
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
FEISHU_STYLE=card
FEISHU_MENTION=@user1,@user2

# DingTalk
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
DINGTALK_STYLE=markdown
DINGTALK_AT_MOBILES=13800138000
DINGTALK_AT_ALL=false

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
MAIL_FROM=your-email@gmail.com
MAIL_TO=recipient@example.com
SMTP_SSL=true
NOTIFY_ATTACH_HTML=true
```

**Usage:**
```bash
drun r testcases \
  --notify feishu,email \
  --notify-only failed \
  --notify-attach-html
```

## 🏗️ Architecture

### Module Structure

```
drun/                           # ~8,500 lines across 52 modules
├── cli.py                      # CLI interface (typer)
├── engine/
│   └── http.py                 # HTTP client (httpx wrapper)
├── loader/
│   ├── collector.py            # Test discovery
│   ├── yaml_loader.py          # YAML parsing
│   ├── env.py                  # Environment loading
│   └── hooks.py                # Hook discovery
├── models/
│   ├── case.py                 # Test case models
│   ├── config.py               # Configuration models
│   ├── step.py                 # Step models
│   ├── request.py              # Request models
│   ├── validators.py           # Validator models
│   └── report.py               # Report models
├── runner/
│   ├── runner.py               # Test execution engine
│   ├── assertions.py           # Assertion logic
│   └── extractors.py           # Extraction logic
├── templating/
│   ├── engine.py               # Template engine
│   ├── builtins.py             # Built-in functions
│   └── context.py              # Variable context
├── reporter/
│   ├── html_reporter.py        # HTML report generation
│   ├── json_reporter.py        # JSON report generation
│   └── allure_reporter.py      # Allure integration
├── notifier/
│   ├── feishu.py               # Feishu notifications
│   ├── dingtalk.py             # DingTalk notifications
│   └── emailer.py              # Email notifications
├── importers/
│   ├── curl.py                 # cURL import
│   ├── postman.py              # Postman import
│   ├── har.py                  # HAR import
│   └── openapi.py              # OpenAPI import
├── exporters/
│   └── curl.py                 # cURL export
├── utils/
│   ├── env_writer.py           # Environment file writer (NEW v4.0)
│   ├── logging.py              # Structured logging
│   ├── mask.py                 # Secret masking
│   └── errors.py               # Error handling
└── scaffolds/
    └── templates.py            # Project templates
```

### Design Philosophy

1. **Simplicity First**: YAML DSL over code, convention over configuration
2. **Type Safety**: Pydantic v2 models for validation and IDE support
3. **Composability**: Small, focused modules with clear responsibilities
4. **Extensibility**: Hooks for custom logic without modifying core
5. **CI/CD Native**: Exit codes, structured reports, and notifications
6. **Developer Experience**: Clear error messages and helpful diagnostics

### Dependencies

```toml
[dependencies]
httpx = ">=0.27"        # Modern HTTP client
pydantic = ">=2.6"      # Data validation
jmespath = ">=1.0"      # JSON path queries
PyYAML = ">=6.0"        # YAML parsing
rich = ">=13.7"         # Terminal formatting
typer = ">=0.12"        # CLI framework
Faker = ">=24.0"        # Mock data generation (optional)
```

## 📖 Best Practices

### Project Structure

```
my-api-test/
├── testcases/                  # Atomic test cases (reusable)
│   ├── auth/
│   │   ├── test_login.yaml
│   │   └── test_logout.yaml
│   ├── users/
│   │   ├── test_create_user.yaml
│   │   ├── test_get_user.yaml
│   │   └── test_update_user.yaml
│   └── orders/
│       ├── test_create_order.yaml
│       └── test_list_orders.yaml
├── testsuites/                 # Test orchestration
│   ├── testsuite_smoke.yaml    # Quick smoke tests
│   ├── testsuite_regression.yaml # Full regression
│   └── testsuite_e2e.yaml      # End-to-end flows
├── data/                       # Test data
│   ├── users.csv
│   └── products.json
├── env/                        # Environment configs
│   ├── dev.yaml
│   ├── staging.yaml
│   └── prod.yaml
├── .env                        # Local environment
├── .env.example                # Template (commit this)
├── drun_hooks.py               # Custom functions
├── .gitignore                  # Exclude .env, logs, reports
└── README.md
```

### Environment Management

```bash
# .env (local, not committed)
BASE_URL=https://api.dev.example.com
API_KEY=dev-key-here
DB_HOST=localhost

# .env.example (committed)
BASE_URL=https://api.example.com
API_KEY=your-api-key-here
DB_HOST=db.example.com
```

**Multi-environment:**
```bash
# Development
DRUN_ENV=dev drun r testsuites/testsuite_smoke.yaml

# Staging
DRUN_ENV=staging drun r testsuites/testsuite_regression.yaml

# Production (smoke tests only)
DRUN_ENV=prod drun r testsuites/testsuite_smoke.yaml
```

### Naming Conventions

**Test cases:**
- `test_*.yaml` - Individual test cases
- Descriptive names: `test_create_user.yaml`, not `case1.yaml`

**Test suites:**
- `testsuite_*.yaml` - Test suite files
- By scenario: `testsuite_smoke.yaml`, `testsuite_e2e.yaml`

**Variables:**
- Environment: `UPPER_CASE` (BASE_URL, API_KEY)
- YAML: `lowerCase` or `snake_case` (token, apiKey, user_id)
- Auto-conversion: `token` → `TOKEN`, `apiKey` → `API_KEY`

### Tag Organization

```yaml
tags: [smoke, api, critical]      # Smoke test, critical path
tags: [regression, users]         # Regression test, user module
tags: [e2e, purchase]             # End-to-end, purchase flow
tags: [slow, performance]         # Slow test, performance testing
tags: [db, data-verify]           # Database validation
```

**Filtering:**
```bash
drun r testcases -k "smoke"                    # Smoke tests only
drun r testcases -k "regression and not slow"  # Fast regression
drun r testcases -k "critical or e2e"          # Critical + E2E
```

### CI/CD Integration

**GitHub Actions Example:**
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
        run: pip install drun
      
      - name: Run Smoke Tests
        run: |
          drun r testsuites/testsuite_smoke.yaml \
            --html reports/smoke.html \
            --report reports/smoke.json \
            --mask-secrets \
            --failfast
        env:
          BASE_URL: ${{ secrets.BASE_URL }}
          API_KEY: ${{ secrets.API_KEY }}
      
      - name: Run Regression Tests
        if: github.event_name == 'pull_request'
        run: |
          drun r testsuites/testsuite_regression.yaml \
            --html reports/regression.html \
            --report reports/regression.json \
            --mask-secrets
        env:
          BASE_URL: ${{ secrets.BASE_URL }}
          API_KEY: ${{ secrets.API_KEY }}
      
      - name: Upload Reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-reports
          path: reports/
      
      - name: Notify on Failure
        if: failure()
        run: |
          drun r testsuites/testsuite_smoke.yaml \
            --notify feishu \
            --notify-only failed
        env:
          FEISHU_WEBHOOK: ${{ secrets.FEISHU_WEBHOOK }}
```

## 🚧 Advanced Topics

### File Upload Testing

```yaml
steps:
  - name: Upload Avatar
    request:
      method: POST
      path: /users/avatar
      headers:
        Authorization: Bearer ${ENV(TOKEN)}
      files:
        avatar: ["data/avatar.jpg", "image/jpeg"]
      timeout: 30.0
    validate:
      - eq: [status_code, 200]
      - regex: [$.data.avatar_url, '^https?://']
```

### Streaming (SSE) Testing

```yaml
steps:
  - name: Chat Stream
    request:
      method: POST
      path: /v1/chat/completions
      headers:
        Authorization: Bearer ${ENV(API_KEY)}
      body:
        model: gpt-3.5-turbo
        messages: [{role: user, content: Hello}]
        stream: true
      stream: true
      stream_timeout: 30
    extract:
      first_content: $.stream_events[0].data.choices[0].delta.content
      event_count: $.stream_summary.event_count
    validate:
      - eq: [status_code, 200]
      - gt: [$event_count, 0]
```

### Database Assertions

**drun_hooks.py:**
```python
import pymysql

def setup_hook_assert_sql(hook_ctx, user_id):
    """Query database and store result"""
    conn = pymysql.connect(
        host=hook_ctx['env']['DB_HOST'],
        user=hook_ctx['env']['DB_USER'],
        password=hook_ctx['env']['DB_PASSWORD'],
        database=hook_ctx['env']['DB_NAME']
    )
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM users WHERE id = %s", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    return {'db_status': result[0] if result else None}

def expected_sql_value(user_id):
    """Get expected value from previous query"""
    return hook_ctx.get('db_status')
```

**Usage:**
```yaml
steps:
  - name: Verify User Status
    setup_hooks:
      - ${setup_hook_assert_sql($user_id)}
    request:
      method: GET
      path: /users/$user_id
    validate:
      - eq: [status_code, 200]
      - eq: [$.data.status, ${expected_sql_value($user_id)}]
```

### Performance Testing

```yaml
config:
  name: Performance Baseline
  tags: [performance]

steps:
  - name: API Latency Check
    request:
      method: GET
      path: /api/products?limit=100
    validate:
      - eq: [status_code, 200]
      - le: [$elapsed_ms, 2000]  # Must respond within 2s
      - ge: [$.data.length, 100]
```

## 📦 Development

### Running from Source

```bash
# Clone repository
git clone https://github.com/Devliang24/drun.git
cd drun

# Install in editable mode
pip install -e .

# Run
drun --version
python -m drun.cli --version
```

### Project Statistics

- **Language**: Python 3.10+
- **Lines of Code**: ~8,500
- **Modules**: 52 Python files
- **Test Coverage**: Comprehensive (unit + integration)
- **Code Style**: PEP 8, type hints, Pydantic models

### Module Breakdown

| Module | Files | Purpose |
|--------|-------|---------|
| CLI | 1 | Command-line interface |
| Engine | 1 | HTTP client wrapper |
| Loader | 4 | Test discovery and parsing |
| Models | 6 | Data models (Pydantic) |
| Runner | 3 | Test execution |
| Templating | 3 | Template engine |
| Reporter | 3 | Report generation |
| Notifier | 4 | Notifications |
| Importers | 5 | Format conversion (import) |
| Exporters | 1 | Format conversion (export) |
| Utils | 7 | Utilities |
| Scaffolds | 1 | Project templates |

## 🎉 What's New in v4.0

### Postman-Like Variable Management

**Auto-Persist Extracted Variables:**
- Variables automatically saved to `.env` after extraction
- Smart naming: `token` → `TOKEN`, `apiKey` → `API_KEY`
- No manual configuration needed

**Memory-Based Variable Passing:**
- Extracted variables immediately available in subsequent tests
- Test suites share variables via memory (no file I/O)
- Single `.env` file read at startup for optimal performance

**Example:**
```yaml
# Step 1: Login (extracts token)
extract:
  token: $.data.token  # Auto-saved as TOKEN=value in .env

# Step 2: Create Resource (uses token)
headers:
  Authorization: Bearer ${ENV(TOKEN)}  # Available immediately
```

### Execution Order Control

**Test Suites Define Strict Order:**
```yaml
testcases:
  - test_login.yaml       # 1. First
  - test_create.yaml      # 2. Second (uses login token)
  - test_verify.yaml      # 3. Third (uses created resource)
```

### Breaking Changes

- None! v4.0 is fully backward compatible with v3.x

### Migration from v3.x

No changes required! v4.0 adds new features without breaking existing tests.

## 📝 Version History

### v7.0.0 (2025-11-27) - Built-in Mock Data Generation
- **NEW**: Faker integration for mock data generation
  - 11 new built-in functions: `fake_name()`, `fake_email()`, `fake_address()`, etc.
  - Consistent calling style with existing functions like `uuid()`
  - No quotes required in YAML: `body: { name: ${fake_name()} }`
- **ADDED**: `Faker>=24.0` as optional dependency

### v6.0.1 (2024-11-25) - Web Report Server Refinements
- **FIXED**: Width adjustments for better layout consistency
  - List page: 1460px container (1420px content area)
  - Detail page: 1400px container (1360px content area)
  - Enhanced CSS specificity for reliable width override
  - Table layout fixed to ensure full container width usage

### v6.0.0 (2024-11-25) - Web Report Server
- **NEW**: Web-based report server with live indexing
  - Real-time HTML report viewing at `http://0.0.0.0:8080`
  - Automatic report scanning and indexing
  - SQLite-based report database for fast querying
  - RESTful API for report management
  - Responsive UI with Alpine.js
  - Command: `drun s --port 8080 --no-open`
- **NEW**: Report list page with comprehensive features
  - Statistics cards (total reports, passed/failed counts, average duration)
  - Sortable table with report metadata (status, name, time, environment, stats)
  - Pagination support (15 items per page)
  - Chinese localization
  - Clean minimalist design
- **NEW**: Report detail page enhancements
  - Dynamic back button injection
  - Unified styling with list page (consistent header spacing)
  - Text-only button styles (no borders/backgrounds)
  - All toolbar buttons converted to link-style
- **IMPROVED**: Public network access support with 0.0.0.0 binding
- **IMPROVED**: Report scanning with HTML badge parsing fallback

### v5.0.1 (2024-11-24) - Documentation Cleanup
- **IMPROVED**: Simplified documentation structure
  - Removed 10 obsolete documentation files (4 release notes, 5 feature guides, 1 course outline)
  - Consolidated all feature documentation into README.md
  - Total reduction: 1,988 lines of redundant documentation
- **IMPROVED**: Easier project navigation with focused core documentation (README.md + CHANGELOG.md)

### v5.0.0 (2024-11-24) - Enhanced User Experience
- **NEW**: Smart file discovery - Run tests without `.yaml`/`.yml` extension
  - `drun r test_api_health` automatically finds `test_api_health.yaml` or `.yml`
  - Supports paths: `drun r testcases/test_user`
  - Auto-searches in `testcases/` and `testsuites/` directories
  - Backward compatible: full filenames still work
- **IMPROVED**: Unified logging format for code snippet generation
  - Code snippet logs now include timestamps and log levels
  - Consistent format with other log outputs: `YYYY-MM-DD HH:MM:SS.mmm | LEVEL | [TAG] message`
- **IMPROVED**: Enhanced CLI usability with simplified command patterns

### v4.2.0 (2024-11-24) - Code Snippet & CSV Export
- **NEW**: Code Snippet - Auto-generate executable Shell and Python scripts from test steps
  - Each step generates independent `.sh` and `.py` files with execute permissions
  - Timestamp-based directory management (no overwrite history)
  - Auto-detect variable dependencies with hints
  - CLI options: `--no-snippet`, `--snippet-output`, `--snippet-lang`
- **NEW**: CSV Export - Export API response arrays to CSV files
  - `export.csv` configuration with `data` and `file` fields
  - Support column selection, append mode, custom encoding
  - Full JMESPath syntax support (filter, slice, projection)
- **NEW**: Scaffolds auto-create `snippets/` directory

### v4.0.0 (2024-11-20) - Postman-Like Variable Management
- **NEW**: Auto-persist extracted variables to `.env`
- **NEW**: Memory-based variable passing in test suites
- **NEW**: Smart variable name conversion (camelCase → UPPER_CASE)
- **IMPROVED**: Single `.env` read per execution for performance
- **IMPROVED**: Test suite execution with variable chaining

### v3.6.9 (2024-11-19)
- **FIXED**: Removed blank lines between variables in `.env` files
- **IMPROVED**: Compact `.env` file format

### v3.6.7 (2024-11-18)
- **NEW**: Automatic environment variable persistence
- **NEW**: `--persist-env` CLI option
- **NEW**: `env_writer` utility module

### v3.5.1 (2024-11-16)
- **FIXED**: Variable reference resolution in `config.variables`
- **IMPROVED**: Sequential variable resolution for dependencies

### v2.3.0 (2024-10-29)
- **CHANGED**: CSV file paths now relative to project root
- **IMPROVED**: Consistent path resolution across scaffolds

See [CHANGELOG.md](CHANGELOG.md) for complete history.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure `drun check` passes
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Repository**: https://github.com/Devliang24/drun
- **Issues**: https://github.com/Devliang24/drun/issues
- **PyPI**: https://pypi.org/project/drun/
- **Documentation**: See `docs/` directory

## 💡 Tips

- Use `drun check` before commits
- Enable `--mask-secrets` in CI/CD
- Organize tests by module/feature
- Use test suites for complex workflows
- Tag tests for easy filtering
- Review HTML reports for debugging
- Use hooks for custom logic
- Keep `.env` out of version control

---

**Built with ❤️ by the Drun Team**

*Simplifying API testing, one YAML at a time.*

# Drun — Modern HTTP API Testing Framework

[![Version](https://img.shields.io/badge/version-7.0.14-blue.svg)](https://github.com/Devliang24/drun)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Drun** — Easy-to-use API testing with DevOps automation support. Write tests in simple YAML, run anywhere with CI/CD integration.

## Why Drun?

- **Zero Code Required**: Write tests in simple YAML, no programming knowledge needed
- **Postman-Like Experience**: Variable extraction, environment management, and test chaining
- **Developer Friendly**: Dollar-style templating, built-in functions, and custom hooks
- **CI/CD Ready**: HTML/JSON/Allure reports, notifications, and exit codes
- **Format Agnostic**: Import from cURL, Postman, HAR, OpenAPI; export to cURL
- **Modern Stack**: Built on httpx, Pydantic v2, and typer for reliability

## Key Features

### Core Testing Capabilities
- **YAML DSL**: Intuitive test case syntax with `config`, `steps`, `extract`, `validate`, `export`
- **Dollar Templating**: `$var` and `${func(...)}` for dynamic values
- **Rich Assertions**: 12 validators (eq, ne, lt, contains, regex, len_eq, etc.)
- **Data-Driven**: CSV parameters for batch testing
- **CSV Export**: Export API response arrays to CSV files
- **Streaming Support**: SSE (Server-Sent Events) with per-event assertions
- **File Uploads**: Multipart/form-data support
- **Smart File Discovery**: Run tests without `.yaml` extension
- **Test Case Invoke**: Nested test case calls with variable passing (NEW in v6.2)
- **Quality Scoring**: Test case quality assessment system (NEW in v6.3)

### Variable Management
- **Auto-Persist**: Extracted variables automatically saved to `.env`
- **Smart Naming**: `token` → `TOKEN`, `apiKey` → `API_KEY` conversion
- **Memory Passing**: Variables shared between test cases in suites
- **Environment Files**: Support for `.env`, YAML env files, and OS variables

### Advanced Features
- **Custom Hooks**: Python functions for setup/teardown and request signing
- **Test Suites**: Ordered execution with variable chaining and caseflow
- **Authentication**: Basic/Bearer auth with auto-injection
- **Tag Filtering**: Boolean expressions like `smoke and not slow`
- **Database Assertions**: MySQL integration for data validation

### Reports & Integrations
- **HTML Reports**: Single-file, shareable test reports
- **JSON/Allure**: Structured results for CI/CD pipelines
- **Notifications**: Feishu, DingTalk, Email alerts on failure
- **Format Conversion**: Import/export with cURL, Postman, HAR, OpenAPI
- **Code Snippets**: Auto-generate executable Shell and Python scripts
- **Unified Logging**: Consistent log format with timestamps
- **Web Report Server**: Real-time HTML report viewing with SQLite database

## Quick Start

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

> Recommended to use [uv](https://docs.astral.sh/uv/) for virtual environment management. Traditional method also works: `pip install drun`

### Initialize a Project

```bash
drun init my-api-test
cd my-api-test
```

This creates:
```
my-api-test/
├── testcases/                      # Test cases directory
│   ├── test_demo.yaml              # HTTP feature demo
│   ├── test_api_health.yaml        # Health check example
│   ├── test_performance.yaml       # Performance analysis example
│   ├── test_import_users.yaml      # CSV parameterization example
│   ├── test_db_assert.yaml         # Database assertion example
│   ├── test_assertions.yaml        # Assertion operators example
│   └── test_stream.yaml            # Streaming response example
├── testsuites/                     # Test suites directory
│   ├── testsuite_smoke.yaml        # Smoke test suite
│   └── testsuite_csv.yaml          # CSV example suite
├── data/                           # Test data directory
│   └── users.csv                   # CSV parameter data
├── converts/                       # Format conversion source files
│   ├── curl/
│   │   └── sample.curl             # cURL command example
│   ├── postman/
│   │   ├── sample_collection.json  # Postman Collection
│   │   └── sample_environment.json # Postman environment
│   ├── har/
│   │   └── sample_recording.har    # HAR recording file
│   └── openapi/
│       └── sample_openapi.json     # OpenAPI spec
├── reports/                        # HTML/JSON report output
├── logs/                           # Log file output
├── snippets/                       # Auto-generated code snippets
├── .env                            # Environment variables
├── drun_hooks.py                   # Custom Hooks functions
├── .gitignore                      # Git ignore rules
└── README.md                       # Project documentation
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

## Core Concepts

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
    setup_hooks:
      - ${custom_function($request)}
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
    teardown_hooks:
      - ${cleanup_function()}
```

### Variable Extraction & Auto-Persist

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

### Test Suites & Caseflow (NEW in v6.2)

**Modern caseflow syntax with invoke:**

```yaml
# testsuites/testsuite_e2e.yaml
config:
  name: E2E Test Flow
  tags: [e2e, critical]

caseflow:
  - name: Login and Get Token
    invoke: test_login              # Extracts: token, userId (auto-exported)

  - name: Create Order
    variables:
      user_id: $userId              # Use variable from previous step
    invoke: test_create_order       # Extracts: orderId

  - name: Process Payment
    variables:
      order_id: $orderId
      token: $token
    invoke: test_payment

  - name: Verify Order Status
    variables:
      order_id: $orderId
    invoke: test_verify
```

> **Note**: In caseflow, `variables` comes before `invoke`. Extracted variables are automatically exported to subsequent steps - no explicit `export` needed.

**Legacy testcases syntax (still supported):**

```yaml
config:
  name: E2E Test Flow
  base_url: ${ENV(BASE_URL)}

testcases:
  - testcases/test_login.yaml
  - testcases/test_create_order.yaml
  - testcases/test_payment.yaml
  - testcases/test_verify.yaml
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

### CSV Export

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

### Code Snippets

Automatically generate executable Shell and Python scripts from test steps:

```bash
# Run test - code snippets are generated automatically
$ drun r test_login

2025-11-24 14:23:18.551 | INFO | [CASE] Total: 1 Passed: 1 Failed: 0 Skipped: 0
2025-11-24 14:23:18.553 | INFO | [CASE] HTML report written to reports/report.html
2025-11-24 14:23:18.559 | INFO | [SNIPPET] Code snippets saved to snippets/20251124-143025/
2025-11-24 14:23:18.560 | INFO | [SNIPPET]   - step1_login_curl.sh
2025-11-24 14:23:18.560 | INFO | [SNIPPET]   - step1_login_python.py
```

**CLI Options:**
```bash
# Disable snippet generation
$ drun r test_api --no-snippet

# Generate only Python scripts
$ drun r test_api --snippet-lang python

# Generate only curl scripts
$ drun r test_api --snippet-lang curl

# Custom output directory
$ drun r test_api --snippet-output exports/
```

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

## CLI Reference

### Web Report Server

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
# - Paginated list view (18 reports per page)
# - Detailed report view with back navigation
# - Statistics dashboard
# - RESTful API at /api/reports
```

### Test Case Scoring (NEW in v6.3)

Evaluate test case quality to improve test standards:

```bash
# Score a directory
drun score testcases/

# Score a single file
drun score testcases/test_api.yaml
```

**Scoring Dimensions:**

| Level | Dimension | Weight | Description |
|-------|-----------|--------|-------------|
| Step | Assertions | 50% | Number of validate rules |
| Step | Extraction | 30% | Variable extraction usage |
| Step | Retry | 20% | Retry mechanism usage |
| Case | Parameters | 50% | Data-driven parameterization |
| Case | Hooks | 30% | Setup/teardown hooks usage |
| Case | Reuse | 20% | Test case invoke usage |

**Score Grades:**
- **A** (90+): Excellent - Green badge
- **B** (70-89): Good - Blue badge
- **C** (50-69): Fair - Yellow badge
- **D** (<50): Needs improvement - Red badge

**HTML Report Integration:**
- Average score displayed in report header
- Per-case and per-step scores shown
- Improvement suggestions provided

### Run Tests

```bash
# Basic execution
drun r PATH

# Smart file discovery - extension optional
drun r test_api_health              # Finds test_api_health.yaml or .yml
drun r testcases/test_user          # Supports paths without extension
drun r test_api_health.yaml         # Traditional format still works

# With options (--env is required)
drun r testcases/ \
  --env staging \
  -k "smoke and not slow" \
  --vars api_key=secret \
  --html reports/report.html \
  --report reports/results.json \
  --allure-results allure-results \
  --mask-secrets \
  --failfast
```

**Options:**
- `--env NAME`: **Required** - Environment name, loads `.env.<name>` (e.g., `--env dev` loads `.env.dev`)
- `-k TAG_EXPR`: Filter by tags (e.g., `smoke and not slow`)
- `--vars k=v`: Override variables from CLI
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
- `--snippet-output DIR`: Custom output directory for snippets
- `--snippet-lang LANG`: Generate snippets in specific language: all|curl|python

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

## Reports & Notifications

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
- Quality scores (NEW in v6.3)

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

## Architecture

### Module Structure

```
drun/                           # ~8,500 lines across 52 modules
├── cli.py                      # CLI interface (typer)
├── scorer.py                   # Test case quality scoring (NEW)
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
│   ├── env_writer.py           # Environment file writer
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
Faker = ">=24.0"        # Mock data generation
fastapi = ">=0.104"     # Web report server
uvicorn = ">=0.24"      # ASGI server
```

## Best Practices

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

## Advanced Topics

### Test Case Invoke (NEW in v6.2)

Call other test cases from within a test case, enabling modular test design:

**Basic invoke:**
```yaml
steps:
  - name: Execute Login Flow
    variables:
      username: admin               # Pass variables to invoked case
    invoke: test_login              # Extracted variables auto-exported

  - name: Use Extracted Token
    request:
      method: GET
      path: /api/users/$userId      # Use variables from previous step
      headers:
        Authorization: Bearer $token
```

**Path resolution:**
- `test_login` → Searches in `testcases/`, `testsuites/`
- `test_login.yaml` → With extension
- `testcases/auth/test_login` → With directory
- `testcases/auth/test_login.yaml` → Full path

**Nested invoke (A → B → C):**
```yaml
# test_full_flow.yaml
steps:
  - name: Complete Authentication
    invoke: test_auth_flow          # test_auth_flow invokes test_login
                                    # Extracted variables auto-exported
```

**Use cases:**
- Reusable authentication flows
- Common setup/teardown procedures
- Modular test composition
- Reduce code duplication

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

## Development

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

## Version History

### v7.0.0 (2025-11-27) - Built-in Mock Data Generation
- **NEW**: Faker integration for mock data generation
  - 11 new built-in functions: `fake_name()`, `fake_email()`, `fake_address()`, etc.
  - Consistent calling style with existing functions like `uuid()`
  - No quotes required in YAML: `body: { name: ${fake_name()} }`
- **ADDED**: `Faker>=24.0` as dependency

### v6.3.0 (2025-11-26) - Test Case Quality Scoring
- **NEW**: Test case scoring system for quality assessment
  - Step-level scoring: assertions (50%), extraction (30%), retry (20%)
  - Case-level scoring: parameterization (50%), hooks (30%), reuse (20%)
  - Score grades: A (90+ green), B (70-89 blue), C (50-69 yellow), D (<50 red)
  - CLI command: `drun score testcases/`
  - HTML report integration with average scores and improvement suggestions

### v6.3.2/v6.3.3 (2025-11-26) - Report List Enhancements
- **IMPROVED**: Report list page with notification and result columns
- **IMPROVED**: Score display style (gray text like `A (95)`)
- **CHANGED**: Default page size from 15 to 18 reports

### v6.2.0 (2025-11-26) - Test Case Invoke
- **NEW**: `invoke` step type for nested test case calls
  - Syntax: `invoke: test_login` or `invoke: testcases/auth/test_login.yaml`
  - Smart path resolution (shorthand, extension, directory)
  - Variable passing via `variables` (placed before `invoke`)
  - Extracted variables automatically exported to subsequent steps
  - Support for nested invokes (A → B → C)

### v6.0.0 (2024-11-25) - Web Report Server
- **NEW**: Web-based report server with live indexing
  - Real-time HTML report viewing at `http://0.0.0.0:8080`
  - Automatic report scanning and indexing
  - SQLite-based report database
  - RESTful API for report management
  - Command: `drun s --port 8080 --no-open`
- **NEW**: Report list and detail pages with pagination

### v5.0.0 (2024-11-24) - Enhanced User Experience
- **NEW**: Smart file discovery - Run tests without `.yaml`/`.yml` extension
- **IMPROVED**: Unified logging format for code snippets

### v4.2.0 (2024-11-24) - Code Snippet & CSV Export
- **NEW**: Code Snippet - Auto-generate Shell and Python scripts
- **NEW**: CSV Export - Export API response arrays to CSV files

### v4.0.0 (2024-11-20) - Postman-Like Variable Management
- **NEW**: Auto-persist extracted variables to `.env`
- **NEW**: Memory-based variable passing in test suites
- **NEW**: Smart variable name conversion (camelCase → UPPER_CASE)

See [CHANGELOG.md](CHANGELOG.md) for complete history.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure `drun check` passes
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Links

- **Repository**: https://github.com/Devliang24/drun
- **Issues**: https://github.com/Devliang24/drun/issues
- **PyPI**: https://pypi.org/project/drun/

## Tips

- Use `drun check` before commits
- Enable `--mask-secrets` in CI/CD
- Organize tests by module/feature
- Use test suites for complex workflows
- Tag tests for easy filtering
- Review HTML reports for debugging
- Use hooks for custom logic
- Keep `.env` out of version control
- Use `drun score` to evaluate test quality

---

**Built with care by the Drun Team**

*Simplifying API testing, one YAML at a time.*


"""
Drun project scaffold templates
Used by `drun init` command to generate project structure
"""

# Demo test case template (GET + POST with extract)
DEMO_TESTCASE = """config:
  name: HTTP Demo
  base_url: ${ENV(BASE_URL)}
  tags: [demo, smoke]

steps:
  - name: GET Request
    request:
      method: GET
      path: /get?page=1&limit=10
    validate:
      - eq: [status_code, 200]
      - eq: [$.args.page, "1"]

  - name: POST Request with Extract
    request:
      method: POST
      path: /post
      headers:
        Content-Type: application/json
      body:
        username: ${ENV(USER_USERNAME)}
        data: test_${short_uid(6)}
    extract:
      posted_data: $.json.data
    validate:
      - eq: [status_code, 200]
      - contains: [$.json.username, ${ENV(USER_USERNAME)}]
"""

# Health check test case
HEALTH_TESTCASE = """config:
  name: API Health Check
  base_url: ${ENV(BASE_URL)}
  tags: [smoke, health]

steps:
  - name: Check Service Status
    request:
      method: GET
      path: /get
    validate:
      - eq: [status_code, 200]
      - contains: [headers.Content-Type, application/json]
"""

# Smoke test suite (caseflow format)
DEMO_TESTSUITE = """config:
  name: Smoke Test Suite
  tags: [smoke]

caseflow:
  - name: Health Check
    invoke: test_api_health

  - name: Demo Flow
    invoke: test_demo
"""

# CSV sample data
CSV_USERS_SAMPLE = """username,email,role
alice,alice@example.com,admin
bob,bob@example.com,user
"""

# CSV data-driven test case
CSV_DATA_TESTCASE = """config:
  name: CSV Data-Driven Test
  base_url: ${ENV(BASE_URL)}
  tags: [csv]
  parameters:
    - csv:
        path: data/users.csv

steps:
  - name: Register User $username
    request:
      method: POST
      path: /anything/register
      body:
        username: $username
        email: $email
        role: $role
    validate:
      - eq: [status_code, 200]
      - eq: [$.json.username, $username]
"""

# cURL sample
SAMPLE_CURL = """# Sample: POST request with JSON body
curl -X POST 'https://api.example.com/api/v1/login' \\
  -H 'Content-Type: application/json' \\
  --data-raw '{"username": "test", "password": "pass123"}'

# Convert: drun convert sample.curl --outfile testcases/from_curl.yaml --placeholders
"""

# Environment config template
ENV_TEMPLATE = """# API Configuration
BASE_URL=https://httpbin.org
USER_USERNAME=test_user
USER_PASSWORD=test_password

# System Name (for notifications and reports)
SYSTEM_NAME=My Test System

# Database (optional)
# MYSQL_MAIN__DEFAULT__DSN=mysql://user:pass@localhost:3306/app

# Feishu Notification (optional)
# FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx

# DingTalk Notification (optional)
# DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx

# Email Notification (optional)
# SMTP_HOST=smtp.example.com
# SMTP_PORT=465
# SMTP_USER=noreply@example.com
# SMTP_PASS=your-password
# MAIL_FROM=noreply@example.com
# MAIL_TO=qa@example.com
"""

# Hooks template
HOOKS_TEMPLATE = '''"""
Drun Hooks - Custom functions for test cases

Usage:
- Template functions: ${ts()}, ${uid()}, ${md5($password)}
- Setup hooks: setup_hooks: [${setup_hook_sign_request($request)}]
"""
import hashlib
import hmac
import time
import uuid
from typing import Any

from drun.db.database_proxy import get_db


# ==================== Template Functions ====================

def ts() -> int:
    """Return current Unix timestamp (seconds)"""
    return int(time.time())


def uid() -> str:
    """Generate UUID with hyphens"""
    return str(uuid.uuid4())


def short_uid(length: int = 8) -> str:
    """Generate short UUID (no hyphens, truncated)"""
    return str(uuid.uuid4()).replace("-", "")[:length]


def md5(text: str) -> str:
    """Calculate MD5 hash"""
    return hashlib.md5(str(text).encode("utf-8")).hexdigest()


def sha256(text: str) -> str:
    """Calculate SHA256 hash"""
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


# ==================== Setup Hooks ====================

def setup_hook_sign_request(request: dict, variables: dict = None, env: dict = None) -> dict:
    """Add HMAC-SHA256 signature to request headers"""
    env = env or {}
    secret = env.get("APP_SECRET", "default-secret").encode()
    method = request.get("method", "GET")
    url = request.get("url", "")
    timestamp = str(int(time.time()))

    message = f"{method}|{url}|{timestamp}".encode()
    signature = hmac.new(secret, message, hashlib.sha256).hexdigest()

    headers = request.setdefault("headers", {})
    headers["X-Timestamp"] = timestamp
    headers["X-Signature"] = signature

    return {"last_signature": signature, "last_timestamp": timestamp}


# ==================== Database Functions ====================

def _get_db_proxy(db_name: str = "main", role: str | None = None):
    """Get database proxy by name/role"""
    return get_db().get(db_name, role)


def setup_hook_assert_sql(
    identifier: Any,
    *,
    query: str | None = None,
    db_name: str = "main",
    role: str | None = None,
) -> dict:
    """Assert SQL query returns non-empty result before step execution"""
    proxy = _get_db_proxy(db_name=db_name, role=role)
    sql = query or f"SELECT * FROM users WHERE id = {identifier}"
    if not proxy.query(sql):
        raise AssertionError(f"SQL returned empty: {sql}")
    return {"sql_assert_ok": True}


def expected_sql_value(
    identifier: Any,
    *,
    query: str | None = None,
    column: str = "status",
    db_name: str = "main",
    role: str | None = None,
) -> Any:
    """Get column value from SQL query for validation"""
    proxy = _get_db_proxy(db_name=db_name, role=role)
    sql = query or f"SELECT {column} FROM users WHERE id = {identifier}"
    row = proxy.query(sql)
    if not row:
        raise AssertionError(f"SQL returned empty: {sql}")
    return row.get(column)
'''

# .gitignore template
GITIGNORE_TEMPLATE = """# Reports and logs
reports/
logs/
allure-results/
*.log

# Code snippets (auto-generated)
snippets/

# Environment (sensitive)
.env
.env.*
!.env.example

# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/

# IDE
.vscode/
.idea/
.DS_Store
"""

# Project README template
README_TEMPLATE = """# Drun API Test Project

API automation testing with [Drun](https://github.com/Devliang24/drun).

## Project Structure

```
.
├── testcases/           # Test cases
│   ├── test_demo.yaml
│   ├── test_api_health.yaml
│   └── test_import_users.yaml
├── testsuites/          # Test suites (caseflow)
│   └── testsuite_smoke.yaml
├── data/                # Test data
│   └── users.csv
├── .env                 # Environment variables
└── drun_hooks.py        # Custom hooks
```

## Quick Start

```bash
# Install drun
pip install drun

# Run tests
drun r testcases --env dev --html reports/report.html

# Run test suite
drun r testsuite_smoke --env dev

# Run with tag filter
drun r testcases -k "smoke" --env dev
```

## Test Case Example

```yaml
config:
  name: My Test
  base_url: ${ENV(BASE_URL)}
  tags: [smoke]

steps:
  - name: Login
    request:
      method: POST
      path: /login
      body:
        username: ${ENV(USER_USERNAME)}
    extract:
      token: $.data.token
    validate:
      - eq: [status_code, 200]
```

## Test Suite Example (caseflow)

```yaml
config:
  name: E2E Flow
  tags: [e2e]

caseflow:
  - name: Login
    invoke: test_login

  - name: Create Order
    variables:
      token: $token
    invoke: test_create_order
```

## More

- [Drun Documentation](https://github.com/Devliang24/drun)
"""

# .gitkeep content
GITKEEP_CONTENT = "# Keep this directory in version control\n"

# GitHub Actions workflow template
GITHUB_WORKFLOW_TEMPLATE = """name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install
        run: pip install drun

      - name: Run Tests
        env:
          BASE_URL: ${{ secrets.BASE_URL }}
        run: |
          drun r testcases \\
            --html reports/report.html \\
            --mask-secrets

      - name: Upload Reports
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: reports
          path: reports/
"""

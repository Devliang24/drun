# Drun - Zero-Code HTTP API Testing Framework

[![Version](https://img.shields.io/badge/version-3.5.0-blue.svg)](https://github.com/Devliang24/drun)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

Drun is a **zero-code HTTP API testing framework** designed for modern CI/CD pipelines. Write powerful API tests using simple YAML configuration - no programming required.

## 🚀 Core Features

- **Zero-Code Testing** - Write tests in declarative YAML, no coding needed
- **Multi-Format Conversion** - Import from cURL, Postman, HAR, OpenAPI
- **Rich Assertions** - 15+ operators (eq, ne, contains, regex, etc.)
- **Variable Extraction** - Chain data between API calls
- **Data-Driven Testing** - CSV parameterization support
- **Stream Testing** - SSE and streaming API support
- **Enterprise Reports** - HTML, JSON, Allure formats
- **CI/CD Ready** - GitHub Actions, GitLab CI integration

## 📦 Installation

```bash
pip install drun
```

Or install from source:

```bash
git clone https://github.com/Devliang24/drun.git
cd drun
pip install -e .
```

## ⚡ Quick Start

Create your first test in 3 simple steps:

### 1. Create a test file

`test_api.yaml`:
```yaml
name: API Health Check
config:
  base_url: https://httpbin.org
  tags: [smoke]

steps:
  - name: Check API status
    request:
      method: GET
      path: /ip
    validate:
      - contains: [$.origin, "."]

  - name: Test JSON response
    request:
      method: GET
      path: /json
    validate:
      - eq: [$.slideshow.author, "Yours Truly"]
```

### 2. Run the test

```bash
drun run test_api.yaml
```

### 3. Generate HTML report

```bash
drun run test_api.yaml --html report.html
```

## 📝 Basic Usage

### Variable Extraction

```yaml
name: User API Test
config:
  base_url: https://httpbin.org

steps:
  - name: Create user
    request:
      method: POST
      url: /post
      body:
        name: "John Doe"
        email: "john@example.com"
    extract:
      - user_id: $.json.id
      - token: $.json.token

  - name: Get user details
    request:
      method: GET
      path: /anything/${user_id}
      headers:
        Authorization: Bearer ${token}
    validate:
      - eq: [$.json.name, "John Doe"]
```

### Assertions

```yaml
steps:
  - name: Validate response
    request:
      method: GET
      path: /api/users
    validate:
      - eq: [$.status, "success"]           # Equal
      - ne: [$.error, null]                 # Not equal
      - contains: [$.message, "users"]      # Contains substring
      - gt: [$.count, 0]                    # Greater than
      - len_eq: [$.users, 5]                # Array length equals
```

## 🔄 Format Conversion (Highlight Feature)

Convert your existing API assets to Drun tests:

### From cURL
```bash
# Convert single cURL command
drun convert request.curl --outfile test.yaml

# Convert with placeholders for variables
drun convert api_calls.curl --placeholders --split-output
```

### From Postman
```bash
# Convert Postman Collection
drun convert collection.json --split-output --suite-out testsuite.yaml

# With environment variables
drun convert collection.json --postman-env environment.json
```

### From OpenAPI
```bash
# Convert OpenAPI spec
drun convert-openapi api.json --split-output --base-url https://api.example.com
```

## 📊 Reports & Notifications

### Generate Reports
```bash
# HTML report
drun run tests/ --html reports/report.html

# JSON report (for CI/CD)
drun run tests/ --report reports/run.json

# Allure report
drun run tests/ --allure-results allure-results/
```

### Notifications
Configure notifications in `.env`:
```env
# Feishu
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx

# DingTalk
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx

# Email
SMTP_HOST=smtp.example.com
SMTP_USER=noreply@example.com
MAIL_TO=team@example.com
```

Run with notifications:
```bash
drun run tests/ --notify feishu --html report.html
```

## 🏷️ Tag Management

Organize and run specific tests using tags:

```yaml
name: User Management Test
config:
  tags: [users, regression]
```

```bash
# Run smoke tests only
drun run tests/ -k "smoke"

# Run regression but not slow tests
drun run tests/ -k "regression and not slow"

# Complex expressions
drun run tests/ -k "(smoke or critical) and not flaky"
```

## 🔧 Advanced Features

### CSV Parameterization
```yaml
name: Test Multiple Users
config:
  parameters:
    - csv:
        path: data/users.csv

steps:
  - name: Login as ${username}
    request:
      method: POST
      path: /login
      body:
        username: ${username}
        password: ${password}
```

### Hooks
Create `drun_hooks.py`:
```python
import time

def generate_timestamp():
    return str(int(time.time()))

def setup_auth(hook_ctx):
    token = authenticate()
    hook_ctx["auth_token"] = token
```

Use in tests:
```yaml
config:
  setup_hooks:
    - setup_auth
  variables:
    timestamp: ${generate_timestamp()}
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📖 **Documentation**: [GitHub Wiki](https://github.com/Devliang24/drun/wiki)
- 🐛 **Issues**: [GitHub Issues](https://github.com/Devliang24/drun/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/Devliang24/drun/discussions)

---

**⭐ If this project helps you, give us a star!**

*Zero-code testing, making API testing simpler*
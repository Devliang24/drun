# Drun: Modern HTTP API Testing Framework

[English](README.en.md) | [中文](README.md)

[![Version](https://img.shields.io/badge/version-7.2.15-blue.svg)](https://github.com/Devliang24/drun)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

`Drun` is a YAML-driven HTTP API testing framework. It lets you describe requests, variable extraction, assertions, suite orchestration, and report output in concise YAML, making API validation, debugging, and CI/CD execution easier to maintain.

## Highlights

- YAML DSL: write tests with `config`, `steps`, `extract`, `validate`, and `caseflow`.
- Template system: supports `$var`, `${ENV(KEY)}`, `${uuid()}`, and other dynamic expressions.
- Rich assertions: built-in checks such as `eq`, `contains`, `regex`, `len_eq`, and `gt`.
- Test orchestration: supports suites, `invoke`, step `repeat`, and tag filtering.
- Sleep steps: supports explicit wait DSL such as `sleep: 2000`, using milliseconds.
- Outputs: HTML, JSON, Allure reports, logs, and generated code snippets.
- Debug-friendly: `drun q` for quick requests, plus converters from cURL, Postman, HAR, and OpenAPI.

## Installation

Python 3.10+ is recommended.

```bash
pip install drun
```

If you prefer `uv`:

```bash
uv venv
source .venv/bin/activate
uv pip install drun
```

## Quick Start

### 1. Initialize a Project

```bash
drun init myproject
cd myproject
```

Default scaffold:

```text
myproject/
├── testcases/
├── testsuites/
├── data/
├── converts/
├── logs/
├── reports/
├── snippets/
├── .env
└── Dhook.py
```

### 2. Configure Environment Variables

`.env`

```bash
BASE_URL=https://api.example.com
API_KEY=demo-token
```

### 3. Write Your First Test

`testcases/test_user_api.yaml`

```yaml
config:
  name: User API Test
  base_url: ${ENV(BASE_URL)}
  tags: [smoke, user]

steps:
  - name: Create User
    request:
      method: POST
      path: /users
      headers:
        Authorization: Bearer ${ENV(API_KEY)}
      body:
        username: test_${uuid()}
        email: test@example.com
    extract:
      userId: $.data.id
    validate:
      - eq: [status_code, 201]
      - regex: [$.data.id, '^\d+$']

  - name: Get User
    request:
      method: GET
      path: /users/${ENV(USER_ID)}
      headers:
        Authorization: Bearer ${ENV(API_KEY)}
    validate:
      - eq: [status_code, 200]
```

### 4. Run Tests

```bash
drun run testcases/test_user_api.yaml -env dev
drun run test_user_api -env dev
drun run testcases -env dev -k "smoke and not slow"
drun run test_user_api -env dev -html reports/report.html
```

Notes:

- `.yaml` can be omitted in run targets.
- Temporary single-file runs write only one log file to the current directory.
- Scaffolded project runs keep outputs in `logs/`, `reports/`, and `snippets/`.

## Common Patterns

### Single Test File

```yaml
config:
  name: Login API
  base_url: ${ENV(BASE_URL)}

steps:
  - name: Login
    request:
      method: POST
      path: /login
      body:
        username: admin
        password: pass123
    extract:
      token: $.data.token
    validate:
      - eq: [status_code, 200]
```

### Suite File

```yaml
config:
  name: Smoke Suite

caseflow:
  - name: Login
    invoke: test_login
  - name: Profile
    invoke: test_profile
```

### Data-Driven Execution

```yaml
config:
  name: Batch Registration
  parameters:
    - csv:
        path: data/users.csv

steps:
  - name: Register $username
    request:
      method: POST
      path: /register
      body:
        username: $username
        email: $email
    validate:
      - eq: [status_code, 201]
```

### Repeated Steps

```yaml
steps:
  - name: Retry Health Check
    repeat: 3
    request:
      method: GET
      path: /health
    validate:
      - eq: [status_code, 200]
```

### Sleep Steps

```yaml
steps:
  - name: Wait for stabilization
    sleep: 2000

  - name: Wait from variable
    sleep: ${wait_ms}
```

## Common Commands

### Run and Debug

```bash
drun run PATH -env dev
drun q https://api.example.com/ping
drun q https://api.example.com/users -X POST -d '{"name":"alice"}'
drun tags testcases
drun check testcases
drun fix testcases
```

### Format Conversion

```bash
drun convert sample.curl -outfile out.yaml
drun convert-openapi spec/openapi/ecommerce_api.json -outdir converted
drun export curl testcases/test_user_api.yaml -outfile request.sh
```

### Report Server

```bash
drun server
drun server -port 8080
```

After startup, you can browse the report list and detail pages in the browser.

## Reports and Outputs

- HTML: good for local viewing and sharing.
- JSON: good for CI pipelines and machine consumption.
- Allure: good for integration with test platforms.
- Snippets: generates Shell or Python request scripts for replaying requests.

Examples:

```bash
drun run testcases -env dev -html reports/report.html
drun run testcases -env dev -allure-results allure-results
allure serve allure-results
```

## Develop from Source

```bash
git clone https://github.com/Devliang24/drun.git
cd drun
pip install -e ".[dev]"
python -m pytest -q
python -m build
python -m drun.cli --version
```

Repository overview:

- `drun/`: core implementation.
- `tests/`: regression tests.
- `spec/`: sample OpenAPI specs.
- `CHANGELOG.md`: version history.
- `AGENTS.md`: contributor rules and local development notes.

## Use Cases

- HTTP API regression testing
- Smoke testing and release verification
- Data-driven execution
- API debugging and request replay
- CI/CD quality gates for interfaces

## Contributing

Before opening a PR, run at least:

```bash
python -m pytest -q
python -m build
drun --help
```

If you are contributing within this repository, read `AGENTS.md` first.

## License

MIT

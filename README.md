# Drun: Modern HTTP API Testing Framework

[English](README.md) | [中文](README.zh.md)

[![Version](https://img.shields.io/badge/version-7.2.19-blue.svg)](https://github.com/Devliang24/drun)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[Documentation](https://devliang24.github.io/drun/) · [GitHub](https://github.com/Devliang24/drun)

`Drun` is a YAML-driven HTTP API testing framework. It lets you describe requests, variable extraction, checks, suite orchestration, and report output in concise YAML, making API validation, debugging, and CI/CD execution easier to maintain.

## Highlights

- YAML DSL: write tests with `config`, `steps`, `extract`, `check`, and `caseflow`.
- Template system: supports `$var`, `${ENV(KEY)}`, `${uuid()}`, and other dynamic expressions.
- Rich checks: built-in checks such as `eq`, `contains`, `regex`, `len_eq`, and `gt`.
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

## Commands

Drun CLI subcommands are all single letters. Use `drun <letter>`:

| Letter | What it does                                |
|--------|----------------------------------------------|
| `i`    | Initialize a project scaffold                |
| `r`    | Run test cases or suites                    |
| `c`    | Check YAML syntax/DSL diagnostics            |
| `f`    | Auto-fix YAML formatting                     |
| `t`    | List all tags used in your test cases        |
| `q`    | Quick HTTP request debug (no YAML needed)    |
| `o`    | Convert `.curl` / `.har` / `.json` to YAML   |
| `w`    | Convert OpenAPI spec to YAML test skeleton   |
| `e`    | Export tests to `curl` commands              |
| `s`    | Start a web server to view test reports      |

> Migrating from v8.0 or earlier? `drun <long-name>` still produces a
> clear hint: `Error: Command 'init' has been renamed to single-letter form. Use 'drun i' instead.`

## Quick Start

### 1. Initialize a Project

```bash
drun i myproject
cd myproject
```

Default scaffold:

```text
myproject/
├── tcases/
├── tsuites/
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

`tcases/tc_user_api.yaml`

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
    check:
      - eq: [status_code, 201]
      - regex: [$.data.id, '^\d+$']

  - name: Get User
    request:
      method: GET
      path: /users/${ENV(USER_ID)}
      headers:
        Authorization: Bearer ${ENV(API_KEY)}
    check:
      - eq: [status_code, 200]
```

### 4. Run Tests

```bash
drun r tcases/tc_user_api.yaml -env dev
drun r test_user_api -env dev
drun r tcases -env dev -k "smoke and not slow"
drun r test_user_api -env dev -html reports/report.html
```

Notes:

- `.yaml` can be omitted in run targets.
- Temporary single-file runs write only one log file to the current directory.
- Scaffolded project runs keep outputs in `logs/`, `reports/`, and `snippets/`.
- `drun r` prints a preflight Run Plan before execution and a final Artifacts block that lists HTML, JSON, Allure, log, and snippet outputs.

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
    check:
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
    check:
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
    check:
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
drun r PATH -env dev
drun q https://api.example.com/ping
drun q https://api.example.com/users -X POST -d '{"name":"alice"}'
drun t tcases
drun c tcases
drun f tcases
```

`drun c` aggregates YAML/DSL authoring diagnostics with stable error codes such as `DRUN-YAML-003`, file locations, fix hints, and minimal examples. `drun r` still stops quickly on blocking YAML errors.

### Format Conversion

```bash
drun o sample.curl -outfile out.yaml
drun w spec/openapi/ecommerce_api.json -output-mode split -outfile converted/ecommerce.yaml
drun e curl tcases/tc_user_api.yaml -outfile request.curl
```

### Report Server

```bash
drun s
drun s -port 8080
```

After startup, you can browse the report list and detail pages in the browser.

## Reports and Outputs

- HTML: good for local viewing and sharing.
- JSON: good for CI pipelines and machine consumption.
- Allure: good for integration with test platforms.
- Snippets: generates Shell or Python request scripts for replaying requests.

Examples:

```bash
drun r tcases -env dev -html reports/report.html
drun r tcases -env dev -allure-results allure-results
allure serve allure-results
```

## Develop from Source

```bash
git clone https://github.com/Devliang24/drun.git
cd drun
pip install -e ".[dev]"
python -m pytest -q
python -m drun.cli --version
```

Repository overview:

- `drun/`: core implementation.
- `tests/`: regression tests.
- `spec/`: sample OpenAPI specs.
- `CHANGELOG.md`: version history.
- `drun-usage/`: local deep-usage skill for AI coding assistants, covering `drun` YAML, CLI usage, conversion, and troubleshooting.
- `AGENTS.md`: contributor rules and local development notes.

## AI Assistant Collaboration

This repository includes a local skill at `drun-usage/`. Its purpose is to help AI coding assistants answer `drun` questions using the repository's actual CLI and DSL behavior, and to return runnable YAML, CLI commands, and troubleshooting guidance instead of generic API testing advice.

Typical use cases:

- Generate `drun` YAML cases
- Explain `invoke`, `invoke_case_name`, `invoke_case_names`, `repeat`, and `sleep`
- Design `drun r`, `drun q`, `drun o`, `drun w`, and `drun e curl` commands
- Explain HTML / JSON / Allure / snippet / `server`
- Troubleshoot `drun` errors

### Claude Code

If you use `Claude Code`, the safest approach is to mention the skill explicitly or ask it to read the skill files before working.

Example prompts:

```text
Use drun-usage to generate a drun testsuite for login and profile lookup.
```

```text
Read drun-usage/SKILL.md first, then convert this curl command into drun YAML and provide the run command.
```

### Codex

If you use `Codex`, explicitly naming `drun-usage` works well. Natural trigger phrases such as "drun YAML", "drun invoke", or "drun troubleshooting" are also useful. When collaborating in this repository, read `AGENTS.md` first.

Example prompts:

```text
Use drun-usage to explain the difference between invoke_case_name and invoke_case_names, and give me a runnable example.
```

```text
Help me debug this drun error, and consult drun-usage/references/troubleshooting.md if needed.
```

### OpenCode

If you use `OpenCode` and your workflow does not automatically discover local skills, explicitly ask it to read `drun-usage/SKILL.md` first, then load the matching file under `references/` as needed.

Example prompts:

```text
Read drun-usage/SKILL.md first, then generate a drun YAML case for file upload and provide the matching run command.
```

```text
Read drun-usage/references/debug-convert-export.md and give me a drun w command for this spec.
```

### Usage Tips

- If you want runnable YAML and commands, mention `drun-usage` explicitly
- If you only need one DSL concept, ask directly, for example: "Explain drun repeat"
- If you change CLI, DSL, reporting, or troubleshooting behavior, update `drun-usage/` accordingly

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
drun --help
```

If you are contributing within this repository, read `AGENTS.md` first.

## License

MIT

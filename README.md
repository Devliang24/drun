# Drun — Zero‑code HTTP API Test Runner

Minimal, fast CLI to write and run HTTP API tests in YAML. Drun focuses on practical DX: a small YAML DSL, dollar‑style templating, solid logs and HTML reports, import/export from common tools, and lightweight notifications.

## Features

- YAML test cases with a compact DSL: config, steps, extract, validate, hooks
- Dollar‑style templating: `$var`, `${func(...)}`, environment access via `ENV(NAME[, default])`
- Powerful validators: `eq/ne/lt/le/gt/ge/contains/not_contains/regex/in/not_in/len_eq/contains_all/match_regex_all`
- Data‑driven tests via CSV under `config.parameters`
- Hooks before/after each step and per case/suite (Python functions in `drun_hooks.py`)
- HTTP engine built on httpx; supports JSON, headers, query, auth (basic/bearer), files, timeouts
- Streaming (SSE) support with per‑event extraction and assertions
- Tag filtering, fast collector, helpful `check` and `fix` commands for YAML
- Reports: JSON and clean single‑file HTML; optional Allure results
- Import: curl/HAR/Postman/OpenAPI → YAML; Export: YAML → curl
- Optional notifications: Feishu, DingTalk, Email (config via env vars)

## Installation

```bash
pip install drun
```

Requirements: Python 3.10+.

## Quick start

Initialize a project scaffold (folders, examples, hooks, CI stubs):

```bash
drun init my-api-test
cd my-api-test
```

Create a `.env` with your base URL and any variables used by tests:

```dotenv
BASE_URL=https://httpbin.org
USER_USERNAME=test_user
USER_PASSWORD=test_pass
```

Run a sample case and generate an HTML report:

```bash
drun run testcases/test_api_health.yaml --html reports/report.html --mask-secrets
```

You can also use simplified filenames (automatically searches in `testcases/` and `testsuites/` directories):

```bash
# These are equivalent
drun run test_api_health.yaml
drun run testcases/test_api_health.yaml
```

### Example case (YAML)

```yaml
config:
  name: Demo: HTTP basics
  base_url: ${ENV(BASE_URL)}
  tags: [demo, smoke]
  variables:
    test_data: test_value_${uuid()}
    user_agent: Drun-Test-Client

steps:
  - name: GET with query params
    request:
      method: GET
      path: /get?page=1&limit=10
      headers:
        User-Agent: $user_agent
    validate:
      - eq: [status_code, 200]
      - eq: [$.args.page, "1"]
      - eq: [$.args.limit, "10"]
      - contains: [headers.Content-Type, application/json]

  - name: POST JSON and extract
    request:
      method: POST
      path: /post
      headers:
        Content-Type: application/json
      body:
        username: ${ENV(USER_USERNAME)}
        data: $test_data
        timestamp: ${now()}
    extract:
      posted_data: $.json.data
      posted_username: $.json.username
    validate:
      - eq: [status_code, 200]
      - eq: [$.json.username, test_user]
      - eq: [$.json.data, $test_data]

  - name: Basic auth
    request:
      method: GET
      path: /basic-auth/${ENV(USER_USERNAME)}/${ENV(USER_PASSWORD)}
      auth:
        type: basic
        username: ${ENV(USER_USERNAME)}
        password: ${ENV(USER_PASSWORD)}
    validate:
      - eq: [status_code, 200]
      - eq: [$.authenticated, true]
```

### Data‑driven (CSV) example

```yaml
config:
  name: Users from CSV
  base_url: ${ENV(BASE_URL)}
  parameters:
    - csv:
        path: data/users.csv
        strip: true

steps:
  - name: Register $username
    request:
      method: POST
      path: /anything/register
      headers: { Content-Type: application/json }
      body:
        username: $username
        email: $email
        password: $password
        role: $role
    validate:
      - eq: [status_code, 200]
      - eq: [$.json.username, $username]
```

### Streaming (SSE) example

```yaml
config:
  base_url: https://api.example.com

steps:
  - name: Chat stream
    request:
      method: POST
      path: /v1/chat/completions
      headers: { Authorization: Bearer ${ENV(API_KEY, "demo-key")} }
      body:
        model: gpt-3.5-turbo
        messages: [{ role: user, content: "Hello" }]
        stream: true
      stream: true
      stream_timeout: 30
    extract:
      first_content: $.stream_events[0].data.choices[0].delta.content
      event_count: $.stream_summary.event_count
    validate:
      - eq: [status_code, 200]
      - gt: [$event_count, 0]
      - lt: [$elapsed_ms, 30000]
```

## Templating and hooks

- Use `$var` or `${expr}` anywhere in strings, dicts, or lists; expressions are evaluated safely (no Jinja).
- Built‑ins: `now()`, `uuid()`, `random_int(a,b)`, `base64_encode(x)`, `hmac_sha256(key,msg)`, and `ENV(NAME[,default])`.
- Define your own helpers/hooks in `drun_hooks.py` (auto‑discovered next to your YAML):

```python
def setup_hook_sign_request(request: dict, variables: dict = None, env: dict = None) -> dict:
    # add HMAC signature and timestamp headers
    ...
    return {"last_signature": "..."}
```

Use in YAML:

```yaml
steps:
  - name: Signed call
    setup_hooks:
      - ${setup_hook_sign_request($request)}
    request:
      method: POST
      path: /api/secure
```

## CLI overview

- Run tests: `drun run PATH [-k TAG_EXPR] [--vars k=v ...] [--env-file <path|alias>] [--html out.html] [--report out.json] [--allure-results dir] [--mask-secrets] [--response-headers]`  
  Tips: `-k` supports boolean expressions like `smoke and not slow`. `--env-file` accepts shortcuts like `dev` resolving to `.env/dev`, `.env.dev`, `.env.dev.yaml`, etc. You can also set `DRUN_ENV=dev` to load `env/dev.yaml`.  
  PATH can be a directory, full file path, or simplified filename with extension (e.g., `test_api.yaml`) - the tool will automatically search in `testcases/` and `testsuites/` directories.
- List tags: `drun tags PATH`
- Syntax/style check (no run): `drun check PATH`
- Auto‑fix YAML (spacing, move hooks into config, replace request.url→path): `drun fix PATH [--only-spacing|--only-hooks]`
- Import to YAML (auto by suffix): `drun convert INFILE(.curl|.har|.json) [--outfile | --into FILE] [--split-output] [--base-url URL] [--case-name NAME] [--postman-env ENV.json] [--redact hdr1,hdr2] [--placeholders] [--suite-out SUITE.yaml]`
- Import OpenAPI: `drun convert-openapi SPEC.(json|yaml) [--outfile FILE] [--base-url URL] [--case-name NAME] [--tags a,b] [--split-output] [--redact ...] [--placeholders]`
- Export curl: `drun export curl PATH [--case-name NAME] [--steps 1,3-5] [--multiline/--one-line] [--shell sh|ps] [--redact hdrs] [--with-comments] [--outfile out.curl]`
- Scaffold project: `drun init [NAME] [--force]`
- Version: `drun --version`

## Environment and variables

- `.env` (key=value) is loaded by default; override with `--env-file`. You may pass a short alias (e.g. `dev`) and Drun will resolve common locations: `.env/dev`, `.env.dev`, `.env.dev.yaml`, `env/dev.yaml`, etc.
- Named YAML environments can be selected via `DRUN_ENV=<name>` and placed under `env/<name>.yaml` (supports structure: `{ base_url, headers, variables: {...} }`).
- OS env passthrough: any `ENV_*`, plus `BASE_URL`, `SYSTEM_NAME`, `PROJECT_NAME` are merged.

## Reports and notifications

- Outputs an HTML report by default (to `reports/<system>-<timestamp>.html`) and optional JSON via `--report`.
- Allure: `--allure-results <dir>` produces results for `allure generate`.
- Notifications (best effort): enable with `--notify feishu,email,dingtalk` (or set `DRUN_NOTIFY`).
  Env keys (examples):
  - Feishu: `FEISHU_WEBHOOK`, `FEISHU_SECRET`, `FEISHU_MENTION`
  - DingTalk: `DINGTALK_WEBHOOK`, `DINGTALK_SECRET`, `DINGTALK_AT_MOBILES`, `DINGTALK_AT_ALL`
  - Email: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `MAIL_FROM`, `MAIL_TO`, `SMTP_SSL`, `NOTIFY_ATTACH_HTML`

## Authoring rules and tips

- Use `request.path` (not `url`) for endpoints; provide `config.base_url` or `BASE_URL` for relative paths.
- JSON payload field is `body` (not `json`).
- Checks and extracts must use dollar‑style selectors on the response: `status_code`, `headers.*`, `$`/`$.path[0].field`, `$elapsed_ms`. The old `body.*` form is not supported.
- JSON extraction uses a JSONPath‑like syntax mapped to JMESPath under the hood; order‑agnostic helpers like `sort/sort_by` are disabled in expressions to keep assertions explicit.
- Secret handling: logs show raw values by default; prefer `--mask-secrets` in CI.

## Converters (import/export)

- Convert `curl` files or stdin, HAR sessions, Postman collections (with optional environment), or OpenAPI specs into Drun YAML.
- Redaction and placeholders: `--redact Authorization,Cookie` masks sensitive headers; `--placeholders` lifts secrets into `config.variables` and references them as `$var`.

## Development

- Codebase is pure Python with Typer CLI and Pydantic models.
- Run from source: `python -m drun.cli --version` or install in editable mode.

## License

MIT. See `LICENSE`.

# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Common commands

### Set up a local dev environment (editable install)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

# sanity check
drun --version
```

### Run from source (without relying on the installed console script)
```bash
python -m drun.cli --version
python -m drun.cli --help
```

### Build / package verification
This repo uses `setuptools` via `pyproject.toml`.
```bash
python -m pip install -U build twine
python -m build
twine check dist/*
```

Release automation:
- `.github/workflows/publish-pypi.yml` publishes to PyPI on pushed tags matching `v*.*.*`.

### Cleanup
```bash
make clean
make clean-build
make clean-reports

# includes git clean of ignored files
make deepclean GIT=1
```

### CLI “test” workflow (Drun projects)
Drun’s CLI is primarily exercised against YAML test projects (directories like `testcases/` and `testsuites/`).

Key commands while developing the runner/loader/template system:
```bash
# validate YAML syntax + style rules (does not execute HTTP)
drun check testcases/

# auto-fix common YAML issues (spacing, hooks placement)
drun fix testcases/

# run a single case file (extension optional)
drun r testcases/test_login.yaml --env dev
# or shorthand lookup under testcases/testsuites
drun r test_login --env dev

# run a suite
drun r testsuites/testsuite_smoke --env dev

# tag filter (boolean expr)
drun r testcases --env dev -k "smoke and not slow"
```

Environment files:
- `drun r ... --env dev` requires a file named `.env.dev` in the current working directory (the CLI errors if it’s missing).

Practical smoke test (this repo doesn’t include a `testcases/` tree by default):
```bash
tmpdir=$(mktemp -d)
drun init "$tmpdir"
cp "$tmpdir/.env" "$tmpdir/.env.dev"
cd "$tmpdir"
drun r testcases --env dev
```

### Report server (manual QA on HTML output)
```bash
# serves reports/ via FastAPI + SQLite index
# (DRUN_REPORTS_DIR is set internally by the CLI command)
drun s --port 8080 --host 127.0.0.1
```

## High-level architecture

### End-to-end execution flow (CLI)
- Entry point: `drun/cli.py` defines the Typer app and commands.
- `drun r …` runs through `_run_impl(...)`:
  1) resolves and loads `.env.<name>` via `drun/loader/env.py`
  2) discovers YAML files via `drun/loader/collector.py` (`discover`, `match_tags`)
  3) parses YAML into Pydantic models via `drun/loader/yaml_loader.py` (`load_yaml_file`, `expand_parameters`)
  4) executes cases via `drun/runner/runner.py` (uses `drun/engine/http.py` for HTTP)
  5) renders reports via `drun/reporter/*` and optionally sends notifications via `drun/notifier/*`
  6) optionally generates snippets via `drun/exporters/snippet.py`

### YAML loading and schema enforcement
- YAML is parsed/normalized in `drun/loader/yaml_loader.py` and then validated using Pydantic models in `drun/models/*`.
- Notable enforcement points that affect many features:
  - steps must be either `request` or `invoke` (`drun/models/step.py`)
  - extracts/checks against response bodies use `$...` expressions (JMESPath via `jmespath.search` in `drun/runner/extractors.py`)
  - legacy `request.json` is intentionally rejected during YAML normalization (the canonical field is `request.body`).

### Templating and variable resolution
- Dollar templating is implemented in `drun/templating/engine.py`.
  - Supports `$var` (expanded to `${var}`) and `${...}` expressions.
  - Expressions are evaluated via a restricted AST evaluator (not Jinja2).
- Built-ins live in `drun/templating/builtins.py` (includes Faker-powered `fake_*` helpers).
- Custom project hooks are discovered/imported from `drun_hooks.py` (or `hooks.py`) by `drun/loader/hooks.py` and provided to the runner/template engine.

### Runner responsibilities
`drun/runner/runner.py` is the orchestration layer for execution:
- renders config/step data via `TemplateEngine`
- executes HTTP requests via `HTTPClient` (`drun/engine/http.py`), including SSE streaming mode
- extracts variables (JMESPath), evaluates assertions (`drun/runner/assertions.py`), and persists extracted vars to env files via `drun/utils/env_writer.py`
- supports nested case execution via `invoke` path resolution (`drun/loader/collector.py:resolve_invoke_path`)

### Reporting and serving reports
- HTML report generation: `drun/reporter/html_reporter.py` (single-file HTML output)
- Report server: `drun/server/app.py` (FastAPI) + `drun/server/database.py` (SQLite) + `drun/server/scanner.py` (indexing) with frontend in `drun/server/templates/index.html`.

### Database support (used by hooks)
- MySQL connectivity is provided in `drun/db/database_proxy.py` and is intentionally optional at install-time:
  - it dynamically loads one of `pymysql`, `mysql-connector-python`, or `mysqlclient` when used
  - configuration is parsed from `MYSQL_*` environment variables in the selected runtime env files

## Where to implement changes (common tasks)
- Add/adjust CLI behavior and flags: `drun/cli.py`
- Change YAML schema/validation: `drun/models/*` and `drun/loader/yaml_loader.py`
- Add a new assertion operator: `drun/runner/assertions.py` (and keep docs in sync under `docs/`)
- Add a new template builtin: `drun/templating/builtins.py`
- Modify HTML report layout/details: `drun/reporter/html_reporter.py`
- Modify report server UI/API: `drun/server/app.py` and `drun/server/templates/index.html`

## Docs in this repo
- `README.md` is the primary product overview and CLI reference.
- `docs/` contains the deeper user-facing docs, including:
  - `docs/05_命令行工具.md` (CLI reference)
  - `docs/16_二次开发.md` (using Drun as a library / extension points)

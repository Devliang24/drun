# Releases

## Release 10.0.0

3 Jun 2026

### ⚠️ Breaking

- **Unified retry**: `repeat` and `retry_backoff` removed. All retry/repeat semantics merged into a single `retry` field (`int | RetryConfig`).
  - `retry: 3` → max 4 attempts, retries on HTTP exceptions and check failures
  - `retry: {max: 10, every: "2s"}` → polls every 2s, up to 10 times
  - `repeat` is gone; `retry_backoff` is gone
  - Step result metadata: `repeat_index/no/total` → `attempt` / `attempt_total`
  - Template variables: `$repeat_index`, `$repeat_no` → `$attempt`, `$attempt_total`
- Invoke step: `invoke_result_prefix` and repeat metadata removed from `execute_invoke_step`

### 🚀 Added

- `RetryConfig` model with `max` and `every` fields
- `parse_duration()` utility for duration strings (e.g. `"2s"`, `"500ms"`)
- Retry now covers both HTTP exceptions and check failures
- Invoke steps support retry

### 🔧 Changed

- Setup hooks run once before retry loop; teardown hooks run once after
- Skip decision evaluated once before first attempt
- Sleep steps no longer support repeat (retry not applicable)
- Dry-run displays retry config
- Legacy `loop`/`foreach` error messages updated

### 🧱 Internal

- `retry_execute()` removed; retry loop inlined into `StepLifecycle`
- `_resolve_repeat_count`, `_build_repeat_variables`, `_format_repeat_step_name` removed
- `StepResult` fields: `attempt`, `attempt_total` replace `repeat_index`, `repeat_no`, `repeat_total`

## Release 9.1.1

3 Jun 2026

### 🐛 Fixed

- Dry-run: recursive template rendering in request body (dict/list values).

## Release 9.1.0

3 Jun 2026

### 🚀 Added

- `drun r -dry-run`: preview test execution plan without HTTP requests, hooks, or artifacts. Shows matched cases, parameter expansion, and step-level details with static variable rendering.
- `-dry-run-limit` flag to cap displayed parameter instances (default 20).
- Dry-run does not require `.env`; unresolved variables shown as-is.

## Release 9.0.1

3 Jun 2026

### ⚠️ Breaking

- Default hook file discovery now uses `dhook.py` instead of `Dhook.py`. Rename existing hook files to `dhook.py`; explicitly setting `DRUN_HOOKS_FILE=Dhook.py` remains available for manual migration.

### 🐛 Fixed

- Made the release tag/version checker compatible with Python 3.10 used by the publish workflow.

---

## Release 8.2.0

3 Jun 2026

### 🚀 Added

- Run Plan for `drun r`: execution now prints a concise preflight overview before the first Case runs, including target, environment, Base URL source, files, Cases, Case instances, filters, and planned output paths.
- Final Artifacts Block: completed runs now end with a centralized list of HTML, JSON, Allure, log, and snippet outputs.
- Failed Case rerun hints: failed Cases now include a `drun r ...` rerun command when the Case name can be represented safely.

### 🔧 Changed

- Restored focused subcommand help such as `drun r --help`, `drun q --help`, `drun e --help`, and `drun e curl --help`.
- Standardized user-facing examples and diagnostics to prefer single-letter commands.
- Improved no-match tag output with concise scanned counts and actionable fix suggestions.
- Improved `drun q -save-yaml` output with next-step commands for checking and running the saved YAML Case.
- Reordered final run output to `Summary -> Failed Cases -> Artifacts`.

### 🔒 Security

- Reduced environment logging exposure by avoiding INFO-level environment key/value dumps; DEBUG output respects the configured secrets mode.

### 🧱 Internal

- Notifier email body builder extracted to a dedicated module; shared best-effort helpers consolidated.
- Runner internals split `run_case` into clearer `prepare_context`, `execute_setup_hooks`, and `execute_teardown_hooks` phases.
- CLI structure moved convert/export helpers to `commands/convert.py`, YAML dump utilities to `commands/yaml_dump.py`, and quick command logic to `commands/quick.py`.
- Removed stale run-command forwarding helper and dead imports.

---

## Release 8.1.4

1 Jun 2026

### 🚀 Added

- CLI polish pass: improved help output formatting and copy across all subcommands.
- Old long-name commands (e.g. `drun init`) now print a clear migration hint: `Error: Command 'init' has been renamed to single-letter form. Use 'drun i' instead.`

### 🐛 Fixed

- Option-only commands (commands with no positional arguments) now correctly show help text when invoked with `--help` and no subcommand.

### 🔧 Changed

- GSD workflow configuration moved from per-project to pi global config.
- Dropped pi prompt-template aliases from GSD command set.
- Removed unused E2E fixture project from `test/`.

---

## Release 8.1.0

1 Jun 2026

### 🚀 Added

- **Breaking**: all CLI subcommands renamed to single-letter abbreviations for speed:

  | Old (long)     | New (short) |
  |----------------|-------------|
  | `drun q` was already short, retained as-is; all other commands follow the same pattern. |

  Old long-name invocations still work and will show a migration hint pointing to the new short form.

### 🐛 Fixed

- Empty-arg commands now correctly render help text in expanded `--help` output.
- CI publish workflow help-text assertions updated for single-letter command names.

### 🔧 Changed

- Documentation and test suite fully updated to reflect single-letter command names.

---

## Release 8.0.0

1 Jun 2026

### 🔧 Changed

- **Breaking**: internal naming convention renamed project-wide:
  - `testcases` → `tcases`
  - `testsuites` → `tsuites`
  - `test_` → `tc_`
  - `suite_` → `ts_`
- Stale planning documents removed from the repository.
- Drun usage skill documentation expanded for agent consumption.

---

## Release 7.2.22

1 Jun 2026

### 🐛 Fixed

- Typer/Click compatibility: help output now renders correctly across Click version boundaries.

---

## Release 7.2.21

1 Jun 2026

### 🐛 Fixed

- Export command group now appears in expanded `--help` output.

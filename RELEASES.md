# Releases

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

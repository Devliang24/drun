# Repository Guidelines

## Project Structure & Module Organization
- `drun/` runtime: `cli.py` (Typer entrypoint), `engine/http.py` (HTTPX client), `runner/` (assertions/extract/run), `loader/` (YAML/env parsing), `templating/` (dollar rendering), and `models/` (Pydantic v2 schemas).
- Supporting stacks: `exporters/`, `importers/`, `reporter/`, `notifier/`, `scaffolds/`.
- Reference assets: `data/` CSV fixtures, `spec/openapi/` sample spec. Generated outputs belong in `logs/`, `reports/`, `dist/` and should stay untracked.
- `Makefile` only cleans caches/reports; no build shortcuts.

## Build, Test, and Development Commands
- Bootstrap: `python -m venv .venv && source .venv/bin/activate && pip install -e .`.
- CLI checks: `drun --help`; run flows with your YAML: `drun run <testcases|testsuites> --html reports/run.html`.
- Package verification: `python -m build` (install `build` once).
- Cleanup: `make clean`, `make clean-reports`, `make deepclean GIT=1` for ignored files.

## Coding Style & Naming Conventions
- Python 3.10+, 4-space indents, pervasive type hints; keep `from __future__ import annotations` where present.
- snake_case for functions/variables, PascalCase for classes; mirror patterns in `drun/models/` for new Pydantic types.
- Prefer `drun.utils.logging` over prints; keep messages concise and user-facing.
- Be frugal with dependencies—stick to httpx, Pydantic, typer, rich unless justified.

## Testing Guidelines
- No repo test suite yet; add `pytest` cases under `tests/` (`test_<module>.py`).
- Stub HTTP with httpx `MockTransport` or recorded fixtures; avoid live endpoints.
- Cover templating edge cases, YAML loading, runner assertions, and CSV import/export paths (store sample CSVs under `data/`).
- When tests are absent, list manual checks in PRs (`drun run ...`, `python -m build`, etc.).

## Commit & Pull Request Guidelines
- Use Conventional Commits seen in history (`feat: ...`, `fix: ...`, `docs: ...`, `chore: ...`); subjects imperative and ~72 chars.
- PRs should state scope, behavior change, test evidence, and linked issues; add screenshots/log snippets only when they clarify output format.
- Keep diffs focused; document user-visible changes in README/CHANGELOG when applicable.

## Security & Configuration Tips
- Do not commit secrets or `.env`; use `ENV()` lookups and masking helpers (`mask_body`, `mask_headers`) when logging.
- Default new settings safely and validate CLI/YAML inputs with clear error messages.

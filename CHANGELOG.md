# Changelog

All notable changes to this project will be documented in this file.

## [0.3.4] - 2025-10-23

### Improved
- **`drun init` output**: Enhanced project initialization output with tree-style layout
  - Use standard tree command characters (├──, │, └──) for better visual hierarchy
  - Right-aligned descriptions in a unified column for cleaner appearance
  - Added directory/file count summary (6 directories, 12 files)
  - Simplified quick start guide (removed redundant --env-file .env)

## [0.3.3] - 2025-10-23

### Changed
- `drun init` quickstart instructions now rely on the default `.env` lookup instead of repeating `--env-file .env`
- Bundled example project co-locates its sample `.env` within `examples/example-project/` and documentation reflects the new layout

## [0.3.0] - 2025-01-23

### Added
- **New command**: `drun init` for project scaffolding - quickly generate complete Drun project structure with test cases, configs, and documentation
- **Scaffolds module**: Built-in templates for testcases, testsuites, hooks, and format conversion examples
- Support for step name rendering in test execution output

### Changed
- **Breaking**: `drun convert` now requires the input file to come before options
  - Correct: `drun convert file.curl --outfile out.yaml`
  - Incorrect: `drun convert --outfile out.yaml file.curl`
- **Breaking**: OpenAPI conversion moved to top-level command: `drun convert-openapi ...` (was `drun convert openapi ...`)
- **Breaking**: Hooks module renamed to `drun_hooks.py` (`DRUN_HOOKS_FILE`); legacy `arun_hooks.py`/`ARUN_HOOKS_FILE` names are no longer loaded
- Moved parameter definitions to `config.parameters` for cleaner syntax

### Improved
- Removed unnecessary quotes in YAML parameterization across all test files and examples
- Standardized assertion and parameter array syntax for better readability
- Enhanced documentation with comprehensive parameterization examples

### Fixed
- Ensure `config.variables` is always a dictionary during conversion (avoid `None` ValidationError)
- Fixed login test case expected results

## Unreleased

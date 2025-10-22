# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2025-01-23

### Added
- **New command**: `arun init` for project scaffolding - quickly generate complete ARun project structure with test cases, configs, and documentation
- **Scaffolds module**: Built-in templates for testcases, testsuites, hooks, and format conversion examples
- Support for step name rendering in test execution output

### Changed
- **Breaking**: `arun convert` now requires the input file to come before options
  - Correct: `arun convert file.curl --outfile out.yaml`
  - Incorrect: `arun convert --outfile out.yaml file.curl`
- **Breaking**: OpenAPI conversion moved to top-level command: `arun convert-openapi ...` (was `arun convert openapi ...`)
- Moved parameter definitions to `config.parameters` for cleaner syntax

### Improved
- Removed unnecessary quotes in YAML parameterization across all test files and examples
- Standardized assertion and parameter array syntax for better readability
- Enhanced documentation with comprehensive parameterization examples

### Fixed
- Ensure `config.variables` is always a dictionary during conversion (avoid `None` ValidationError)
- Fixed login test case expected results

## Unreleased


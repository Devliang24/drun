# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

_No unreleased changes._

## [2.1.1] - 2025-10-26

### Added
- 脚手架示例与 Hook 增强：
  - 批量 SQL 断言辅助：`setup_hook_assert_sql_in(...)`、`expected_sql_values(...)`、`expected_sql_map(...)`；排序与映射工具：`sort_list(...)`、`to_map(...)`。
  - 新增可运行示例用例：`cdcd/testcases/test_db_assert_batch.yaml`（多变量/列表/索引切片）、`cdcd/testcases/test_db_assert_unordered.yaml`（无序与映射对齐）。
  - 在无数据库环境下提供内存演示数据回退，保证示例开箱即用。

### Docs
- 更新 `cdcd/README.md`，补充批量与无序对齐示例运行指引。

## [2.1.0] - 2025-10-25

### Removed
- 移除接口性能统计（httpstat）功能及相关输出：删除 `--http-stat` CLI 开关、`HttpStat` 模型、`TimingCollector`、控制台 httpstat 格式化、`StepResult.httpstat` 字段、示例与文档（docs/HTTP_STAT.md）。

### Changed
- Runner 和 HTTPClient 仅保留基础耗时 `elapsed_ms`；建议在用例中以断言约束时延（例如 `- le: [$elapsed_ms, 2000]`）。
- 脚手架与 README/模板去除 httpstat 用法，CI 示例改为基于 `elapsed_ms` 的守护。

### BREAKING
- 移除 `--http-stat` 和 `StepResult.httpstat` 属破坏性变更；如需分阶段迁移，请固定在 2.0.x 或改造脚本使用 `elapsed_ms`。

## [2.0.4] - 2025-10-25

### Fixed
- 版本号一致性：将 `pyproject.toml` 与 `drun.__version__` 对齐为 `2.0.4`，确保 `drun --version` 与帮助信息显示正确。

## [2.0.3] - 2025-10-25

### Added
- 控制台输出新增 HTTP Stat 汇总日志：启用 `--http-stat` 时自动打印 DNS/TCP/TLS/Server 等耗时详情。

### Fixed
- Runner 在启用 httpstat 模式下会读取 `console_reporter` 的格式化函数，避免重复实现。

## [2.0.2] - 2025-10-25

### Added
- HTTP Stat 仪表功能：启用 `--http-stat` 后采集 DNS/TCP/TLS/服务器处理等耗时，JSON 报告输出 `httpstat` 字段。
- TimingCollector 和 HttpStat 模型，用于构建耗时分析数据；CLI 脚手架新增 `test_performance.yaml` 示例与相关文档。
- 新增 `docs/HTTP_STAT.md`、`docs/SCAFFOLD_HTTP_STAT.md` 以及控制台 Reporter，帮助理解耗时分析结果。

### Changed
- `drun init` 生成项目时包含性能测试示例和说明；`HTTPClient` 支持 `enable_http_stat` 并在步骤结果写入耗时数据。
- 报告模型扩展 `httpstat` 字段，配套测试覆盖基础/端到端场景。

## [2.0.1] - 2025-10-25 *(yanked)*

> 内部构建版本，功能已由 2.0.2 覆盖，未正式发布。

## [2.0.0] - 2025-10-25

### Removed
- YAML DSL 中的 `sql_validate` 字段被移除；SQL 校验需通过 Hook（如 `setup_hook_assert_sql`、`expected_sql_value`）实现。

### Changed
- README 与 `docs/COURSE_OUTLINE_3.0.md` 说明改为 Hook 方案，并新增 HTTP 耗时统计功能介绍。
- `drun/cli.py` 与 loader 不再尝试修复或清理 `sql_validate` 字段，出现时直接报错。
- `drun/db/database_proxy.py` 注释更新，强调仅供 Hook 复用。
- `Runner` 结构移除 SQL 校验流程，并能在 `StepResult` 中附带 `httpstat` 数据。

### Fixed
- 模型校验现在在加载阶段就提示不再支持 `sql_validate`，避免运行期再出错。

## [0.3.9] - 2025-10-24

### Changed
- **SQL 校验 DSL**：`store` 字段更名为 `extract`，改为使用 `$列名` 表达式提取结果，并统一错误提示

### Added
- **脚手架 CSV 示例**：`drun init` 默认生成 `data/users.csv` 与 `testcases/test_import_users.yaml`，并附带 `testsuites/testsuite_csv.yaml` 套件

### Improved
- **脚手架产物**：初始化目录树和 README 快速开始描述新增 CSV 示例命令，输出对齐更友好

## [0.3.8] - 2025-10-24

### Added
- CSV parameterization: new `- csv: { path: ... }` blocks under `config.parameters` load rows from CSV files (relative to the case), enabling data-driven tests without rewriting zipped arrays

## [0.3.7] - 2025-10-24

### Improved
- **CLI notifications**: Auto-enable notification channels (Feishu/DingTalk/Email) when their environment variables are present
  - Automatically detects and enables channels based on `FEISHU_WEBHOOK`, `DINGTALK_WEBHOOK`, `EMAIL_*` environment variables
  - Eliminates the need for explicit `--notify` or `--notify-only` flags when environment is configured
  - Enhanced user experience with seamless notification integration

### Fixed
- **CLI notifications**: Properly honor `DRUN_NOTIFY_ONLY` environment variable when not set via command line
  - Fixed issue where environment variable was ignored if CLI flag was not explicitly provided
  - Ensures consistent behavior between environment variables and CLI flags

## [0.3.6] - 2025-10-23

### Improved
- **`test_api_health.yaml` template**: Enhanced health check example with response validation
  - Changed from `/status/200` to `/get` endpoint for better demonstration
  - Added response body validation (Content-Type header, url field)
  - Better showcase of API testing capabilities with actual response data
- **CLI notifications**: `drun run` now honours `DRUN_NOTIFY_ONLY` and auto-enables Feishu/DingTalk/Email channels when their environment variables are present, eliminating the need for explicit `--notify`/`--notify-only`

## [0.3.5] - 2025-10-23

### Fixed
- **`drun init` output**: Perfect alignment for all descriptions
  - All descriptions now start at column 46 for consistent visual appearance
  - Fixed alignment for cURL, Postman, HAR, OpenAPI, and Git descriptions

## [0.3.4] - 2025-10-23

### Improved
- **`drun init` output**: Enhanced project initialization output with tree-style layout
  - Use standard tree command characters (├──, │, └──) for better visual hierarchy
  - All descriptions perfectly aligned to column 46 for consistent appearance
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

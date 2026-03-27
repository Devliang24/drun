# Changelog

All notable changes to this project will be documented in this file.

> Historical note: entries mentioning the scoring system are retained for release history only. The current CLI does not expose a `drun score` command.

## [7.1.3] - 2026-03-27

### Added
- 非脚手架的单文件 YAML 运行默认进入轻量模式，只生成当前目录下一个日志文件。
- 新增单文件轻量运行与脚手架项目默认产物策略的回归测试。

### Changed
- 脚手架项目内的默认 `logs/`、`reports/`、`snippets/` 输出会相对识别出的项目根目录计算。
- CLI 帮助与运行文档补充单文件轻量运行和脚手架项目模式的差异说明。
- 版本号提升至 7.1.3。

## [7.1.2] - 2026-03-27

### Added
- `request.files` 上传规范化，支持路径字符串与 `[path, content_type]` 写法，并在请求结束后自动关闭框架打开的文件句柄。
- 二进制响应元数据与 `response.save_body_to`，支持音频/文件响应保存到磁盘。
- `--env-file` 与当前目录 `.env` 自动加载，降低单文件用例运行门槛。
- 新增针对文件上传、二进制响应和环境解析的回归测试。

### Changed
- `drun check` / YAML 加载阶段会更早校验明显错误的 `request.files` 结构。
- 文档补齐 multipart 上传、二进制响应保存和环境加载优先级说明。
- 版本号提升至 7.1.2，统一包元数据与运行时版本号。

## [7.1.1] - 2026-03-25

### Changed
- 版本号提升至 7.1.1，触发 PyPI 发布。

## [7.1.0] - 2026-03-25

### Added
- **扩展与报告服务稳定性增强**: 稳定 extensions 和 report server 功能。
- **快速调试命令**: 新增 httpie 风格的快速调试命令 `drun quick`。
- **命令层回归测试**: 新增 command-layer 回归测试并同步架构文档。

### Changed
- **模板规则重构**: 合并模板规则，移除评分系统残留代码。
- **CLI 模块拆分**: 将 run/fix/check/tags 拆分为独立命令模块。
- **Runner 重构**: 分离 hooks 调用与断言评估逻辑。
- **P0 文档对齐**: 对齐 p0 docs CLI 与 CI 配置。

### Fixed
- **导出占位符与包版本稳定性**: 修复 export placeholders 和 package version 问题。

### Docs
- 完善最佳实践文档。
- 重构文档结构，新增 19 篇用户文档。
- 添加框架架构文档。
- 新增 drun quick 命令使用文档。

## [7.0.17] - 2025-12-04

### Changed
- 版本号提升至 7.0.17，发布 PyPI。

## [7.0.16] - 2025-12-04

### Changed
- **脚手架精简**: 精简 scaffolds 内容，将 `run` 命令替换为 `r` 简写命令。

### Docs
- 修复 README 项目结构描述，补充 `--env` 参数到 CLI 示例。

## [7.0.15] - 2025-12-03

### Docs
- 更新 README，新增 caseflow 示例和质量评分说明。

## [7.0.14] - 2025-12-03

### Added
- **HTML 报告步骤/用例编号**: 新增步骤与用例编号显示，合并参数化用例在 HTML 报告中的展示。

## [7.0.13] - 2025-12-03

### Fixed
- **报告详情页宽度**: 报告详情页宽度与列表页保持一致（1310px）。

## [7.0.12] - 2025-12-03

### Changed
- **报告表格 UI 优化**: 保留文件名大小写，优化报告表格 UI 展示。

## [7.0.11] - 2025-12-02

### Added
- **Invoke 步骤结果扁平化**: 在报告展示中扁平化 invoke 步骤的结果，提升可读性。

## [7.0.10] - 2025-12-02

### Changed
- **环境参数重构**: 将 `--env-file` 替换为 `--env`，要求指定环境名称。

## [7.0.9] - 2025-12-02

### Added
- **长度校验器**: 新增长度校验器，模板引擎中保护系统变量。

### Fixed
- Caseflow 变量传递、累积和函数求值问题修复。
- 修复 HTML 报告中 CSV 参数的显示。

## [7.0.8] - 2025-12-01

### Fixed
- **隐藏 CSV 参数**: 在 HTML 报告中隐藏 CSV 参数化参数。

## [7.0.7] - 2025-12-01

### Added
- **CSV 自动类型转换**: CSV 数据自动类型转换，支持 extract 函数调用。

## [7.0.6] - 2025-12-01

### Added
- **`--env` 参数**: 新增 `--env` 参数支持。
- **HTML 报告数据内嵌**: 在 HTML 报告中嵌入 `__REPORT_DATA__`，实现离线查看。

## [7.0.5] - 2025-11-30

### Fixed
- **报告路径扫描**: 使用配置路径重新扫描报告，修复报告文件定位问题。

## [7.0.3] - 2025-11-30

### Fixed
- **HTML 报告页脚**: 移除 HTML 报告详情页的页脚。

## [7.0.2] - 2025-11-27

### Docs
- 扩展 README 中的项目结构说明，展示所有脚手架文件。

## [7.0.1] - 2025-11-27

### Docs
- 更新 README，补充 v7.0.0 Faker 集成说明。

## [7.0.0] - 2025-11-27

### Added
- **内置 Mock 数据生成**: 集成 `Faker` 库，支持在 YAML 模板中直接生成随机测试数据。
- **扁平化 Fake 函数**: 新增 `fake_name()`, `fake_email()`, `fake_address()`, `fake_date()`, `fake_ipv4()` 等一系列内置函数。
- **简洁语法支持**: 支持无引号调用，例如 `body: { name: ${fake_name()} }`。

## [6.3.3] - 2025-11-26

### Changed
- **报告列表默认页大小**：将报告列表页的默认分页大小从 15 调整为 18，提升大屏幕下的浏览体验。

## [6.3.2] - 2025-11-26

### Changed
- **报告列表页优化**：
  - 新增"通知"列，显示通知发送渠道（如 feishu, dingtalk）
  - 新增"结果"列，显示通知发送状态（成功/失败）
  - 表头"状态"改为"结果"，列宽调整优化显示
- **报告详情页优化**：
  - 移除用例头部的通知信息显示，保持界面简洁
  - 优化评分显示：从徽章样式改为灰色文本样式（如 `A (95)`），紧跟用例名称
  - 报告整体布局和样式微调

## [6.3.0] - 2025-11-26

### Added
- **用例评分系统**：评估测试用例质量，帮助提升用例规范性
  - 步骤级评分：断言数量(50%)、变量提取(30%)、重试机制(20%)
  - 用例级评分：参数化(50%)、Hooks(30%)、用例复用(20%)
  - 评分等级：A(90+绿色)、B(70-89蓝色)、C(50-69黄色)、D(<50红色)
  - CLI命令：`drun score testcases/` 评分目录或文件
  - HTML报告集成：显示平均评分、用例评分、步骤评分、改进建议

## [6.2.0] - 2025-11-26

### Added
- **用例嵌套调用 `invoke`**：新增 `invoke` 步骤类型，支持在测试用例中调用其他用例
  - 语法：`invoke: test_login` 或 `invoke: testcases/auth/test_login.yaml`
  - 智能路径解析：支持简写（不带扩展名）、带扩展名、带目录等多种格式
  - 变量传递：通过 `variables` 向被调用用例传入参数
  - 变量导出：通过 `export` 导出被调用用例提取的变量
  - 支持嵌套调用（A invoke B, B invoke C）
  
示例：
```yaml
steps:
  - name: 执行登录流程
    invoke: test_login
    variables:
      username: admin
    export:
      - token
      - userId
      
  - name: 使用 token
    request:
      method: GET
      path: /api/users/$userId
      headers:
        Authorization: Bearer $token
```

## [6.1.10] - 2025-11-26

### Fixed
- 移除报告列表页的页脚。

## [6.1.9] - 2025-11-26

### Changed
- 移除 CASE/STEP 汇总日志中的 Duration 显示。

## [6.1.8] - 2025-11-26

### Fixed
- 移除 STEP 完成日志中的 duration 信息。

## [6.1.7] - 2025-11-26

### Added
- STEP 汇总日志新增 duration 显示。

## [6.1.6] - 2025-11-26

### Added
- STEP 完成日志新增 duration 显示。

## [6.1.5] - 2025-11-26

### Removed
- 移除 `SERVER_USAGE.md` 和临时测试文件。

## [6.1.4] - 2025-11-26

### Fixed
- 修复环境变量日志重复输出问题。

## [6.1.3] - 2025-11-26

### Added
- 测试执行前打印已加载的环境变量。

## [6.1.2] - 2025-11-26

### Changed
- 移除 PASS/FAIL 输出中的 ANSI 颜色代码。

## [6.1.1] - 2025-11-26

### Changed
- 版本号提升至 6.1.1。

## [6.1.0] - 2025-11-26

### Added
- 日志输出新增步骤编号（Start/Completed 格式）。

### Fixed
- 非 TTY 环境下禁用 ANSI 颜色。

## [6.0.13] - 2025-11-26

### Changed
- 简化断言日志输出，使用彩色 PASS/FAIL 标签。

## [6.0.12] - 2025-11-26

### Added
- Hook 返回值和 SQL 查询自动记录日志，支持格式化 JSON 输出。

## [6.0.11] - 2025-11-25

### Added
- HTML 报告用例列表新增通知渠道和状态列。

## [6.0.10] - 2025-11-25

### Fixed
- 页脚固定到页面底部。

## [6.0.9] - 2025-11-25

### Added
- 记录变量替换前后的值。

## [6.0.8] - 2025-11-25

### Changed
- 将 `serve` 命令替换为 `s` 简写命令。

## [6.0.7] - 2025-11-25

### Added
- 新增 `s` 简写命令用于启动报告服务器。

## [6.0.6] - 2025-11-25

### Docs
- 更新 serve 命令文档，使用 `s` 简写。

## [6.0.5] - 2025-11-25

### Docs
- 新增 `--reload` 选项说明到 serve 命令文档。

## [6.0.4] - 2025-11-25

### Docs
- 更新 README，使用 `uv` 安装方式和 `r` 简写命令。

## [6.0.3] - 2025-11-25

### Changed
- Python 代码片段格式更新，与 Postman 风格对齐。

## [6.0.2] - 2025-11-25

### Fixed
- 修复 500 错误并调整布局宽度。

## [6.0.1] - 2025-11-25

### Fixed
- 调整详情页和列表页容器宽度，确保表格使用完整宽度。
- 增强 wrap 宽度覆盖的 CSS 优先级。

## [6.0.0] - 2025-11-25

### Added
- **Web 报告服务器**: 基于 FastAPI + SQLite 的报告查看服务，支持实时查看和分页。

## [5.2.0] - 2025-11-24

### Added
- 新增 `drun r` 作为 `drun run` 的简写命令。

## [5.1.0] - 2025-11-24

### Added
- **报告 Web Server**: 增加基于 FastAPI + SQLite 的报告管理服务。

## [5.0.1] - 2025-11-24

### Docs
- 清理过时文档。
- 更新 README.md 至 v5.0.0。

## [5.0.0] - 2025-11-24

### Added
- 统一代码片段日志格式，支持省略 `.yaml` 扩展名执行。

### Docs
- 更新 README.md 添加 Code Snippet 功能说明。

## [4.2.0] - 2025-11-24

### Added
- **Code Snippet**: 自动生成可执行脚本。
- **数组导出 CSV**: 实现数组数据导出为 CSV 文件。

### Docs
- 更新 README.md 添加 CSV 导出功能说明。

## [4.1.2] - 2025-11-23

### Changed
- 优化钉钉 Markdown 消息格式。

## [4.1.1] - 2025-11-23

### Added
- 钉钉通知支持测试报告链接。

### Fixed
- 修复钉钉通知签名参数传递问题。

## [4.1.0] - 2025-11-23

### Added
- 增强环境变量类型自动转换，支持数字、布尔值和 null。
- 支持环境变量中的 JSON 数组和对象自动解析。

### Docs
- 添加环境变量智能类型转换使用指南。
- 新增英文 README。

## [4.0.0] - 2025-11-20

### Added
- 提取变量同时更新内存环境，实现测试套件中的变量传递。

## [3.6.9] - 2025-11-19

### Fixed
- 移除 env 文件变量间的多余空行。

## [3.6.8] - 2025-11-19

### Changed
- 版本号提升至 3.6.8。

## [3.6.7] - 2025-11-19

### Added
- 支持提取变量自动持久化到环境文件。

## [3.6.6] - 2025-11-18

### Fixed
- 修复流式响应面板双滚动条问题。

## [3.6.5] - 2025-11-17

### Changed
- HTML 报告中请求和响应 body 面板固定高度。

## [3.6.4] - 2025-11-17

### Added
- 流式响应分块显示完整 JSON 结构。

## [3.6.3] - 2025-11-17

### Fixed
- 修复 `http.py` 中流式响应上下文管理器错误。

## [3.6.2] - 2025-11-17

### Added
- 增强流式响应显示，支持渐进式内容追踪。

## [3.6.1] - 2025-11-17

### Fixed
- 移除扩展名自动补全，要求输入完整文件名。

## [3.6.0] - 2025-11-17

### Added
- 支持在 `testcases`/`testsuites` 目录下简化文件名搜索。
- 新增 sandbox 项目目录。

## [3.5.2] - 2025-11-17

### Docs
- 新增英文 README，包含概述、用法和示例。

## [3.5.1] - 2025-11-16

### Fixed
- **配置变量顺序解析**：修复 `config.variables` 中变量无法相互引用的问题。之前所有变量使用空上下文同时解析，导致类似 `username: testuser_${user_id}_${timestamp}` 的表达式无法找到依赖变量。现改为顺序解析，后面的变量可以引用前面已解析的值，支持变量间依赖关系。

## [3.5.0] - 2025-11-03

### Changed
- 清理未使用代码，改善项目可维护性。

## [3.4.0] - 2025-11-02

### Fixed
- 对齐变量缩进与冒号位置。

## [3.3.0] - 2025-11-02

### Fixed
- 移除变量显示中的花括号。
- 对齐变量缩进与冒号间距。

## [3.2.0] - 2025-11-02

### Fixed
- 改进变量显示格式，使用冒号和正确缩进。

## [3.1.2] - 2025-11-02

### Changed
- 变量显示改为垂直列表格式。

## [3.1.1] - 2025-11-02

### Fixed
- 改进 REQUEST body 变量显示，移除不必要的转义引号。

## [3.1.0] - 2025-11-02

### Added
- 新增多行对齐变量显示。

## [3.0.1] - 2025-11-02

### Fixed
- 改进变量显示，去除转义引号。

## [3.0.0] - 2025-11-02

### Fixed
- 转义 YAML 数组中的模板表达式，防止解析错误。

## [2.6.2] - 2025-11-02

### Fixed
- 统一 filter 表达式日志输出格式。

## [2.6.1] - 2025-11-02

### Added
- 测试执行输出中显示 `base_url`。

## [2.6.0] - 2025-11-02

### Added
- 新增变量打印功能，修复格式转换中的 stream 参数。

## [2.5.0] - 2025-11-02

### Fixed
- 改进 JSONPath 表达式处理，支持包含特殊字符的字段名。

## [2.4.12] - 2025-11-01

### Docs
- 将中文 README 设为主 README。

## [2.4.11] - 2025-11-01

### Docs
- 新增中文 README。

## [2.4.10] - 2025-10-31

### Changed
- 简化数据库配置，使用环境变量。

### Removed
- 移除过时文档。

## [2.4.9] - 2025-10-31

### Fixed
- 修复 tag 过滤逻辑。

## [2.4.8] - 2025-10-31

### Fixed
- 规范化通知环境变量值。
- 去除飞书内联注释中的多余空格。

## [2.4.7] - 2025-10-31

### Added
- 新增 GitLab CI 脚手架模板。

## [2.4.6] - 2025-10-31

### Fixed
- 移除飞书通知模板中的尾随空格。

## [2.4.5] - 2025-10-31

### Fixed
- 环境变量加载后重新计算系统特定的默认日志路径，修复日志文件配置。

## [2.4.4] - 2025-10-31

### Added
- 新增 GitHub Actions 工作流脚手架模板。

## [2.4.3] - 2025-10-31

### Fixed
- HTML 报告中转义系统名称。

## [2.4.2] - 2025-10-31

### Changed
- 版本号提升至 2.4.2。

## [2.4.1] - 2025-10-31

### Fixed
- 包含 utils config 模块。
- 清理默认报告/日志文件名。
- 修复 API 端点以符合 OpenAPI 规范。

### Docs
- 更新 README 中的 API 端点。

## [2.4.0] - 2025-10-30

### Added
- 电商 API 测试套件，支持 SQL Hook 函数断言。

### Docs
- 新增 SQL 断言改进文档和 MySQL 配置说明。

## [2.3.4] - 2025-10-29

### Fixed
- 保留 hook 返回值的原始类型。

## [2.3.3] - 2025-10-29

### Changed
- 对齐版本号与标记，发布 v2.3.3。

## [2.3.2] - 2025-10-29

### Changed
- 仅更新打包元数据，未包含代码改动。

## [2.3.1] - 2025-10-29

### Removed
- 移除临时开发资产：`testcases/` 示例、`tests/` 单测、`dede/` 临时项目、`dist/` 构建产物以及 `STREAMING_FEATURE.md` 说明。

## [2.3.0] - 2025-10-29

### Changed
- CSV 参数文件路径现在始终相对于项目根目录或执行目录解析，删除对 `../data/...` 等用例目录相对写法的兼容，避免路径越界并统一脚手架用法。

## [2.2.2] - 2025-10-29

### Changed
- **脚手架输出优化**：
  - 移除版本号下方的空行，使输出更紧凑
  - 简化快速开始命令，移除内联注释说明
  - 删除"格式转换"示例部分（详细说明仍在 converts/README.md 中）
  - 在文件树和快速开始中显示 `test_assertions.yaml`（断言操作符完整示例）

## [2.2.1] - 2025-10-29

### Added
- **断言操作符完整示例**：脚手架新增 `test_assertions.yaml`，包含所有断言操作符的使用示例（eq、ne、lt、le、gt、ge、contains、regex、in、len_eq、contains_all、match_regex_all）

## [2.1.2] - 2025-10-28

### Fixed
- Streaming SSE: forward Basic/Bearer credentials by passing `auth=auth_tuple` to `httpx.stream`, and align options by forwarding `files=files`.
- HTML reporter: import `typing.Dict` to avoid `NameError` when rendering streaming response panel.

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

## [1.0.4] - 2025-10-25

### Added
- 根据 OpenAPI Schema 生成示例请求体。

### Fixed
- 处理 curl 续行和引号 token。

## [1.0.3] - 2025-10-25

### Fixed
- 确保转换器正确处理 path 字段，path 置于 headers 之前。

## [1.0.2] - 2025-10-24

### Added
- CLI 帮助信息本地化（中文）。

### Fixed
- 改进 YAML fix 修复逻辑。

## [1.0.1] - 2025-10-24

### Changed
- 请求地址从 url 切换为 path 方式。

### Fixed
- 修复报告状态过滤兼容性。
- 修复请求路径上报问题。

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

## [0.3.2] - 2025-10-23

### Added
- 新增 `--version`/`-v` CLI 选项显示版本号。

### Fixed
- CI 中为 GitHub Release 创建添加 contents write 权限。

## [0.3.1] - 2025-10-23

### Changed
- 项目从 `arun` 重命名为 `drun`。
- 将 datasense copilot 套件移至 examples 目录。

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

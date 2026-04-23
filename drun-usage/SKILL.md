---
name: drun-usage
description: 面向 drun 深度使用与实战生成的本地 skill。当用户提到 drun 用例、drun 深度使用、drun YAML、drun run 命令、drun invoke、drun convert、drun export curl、drun 报告、drun 排障，或要求编写/解释/调试 drun YAML 与命令时触发。默认中文，优先给可运行 YAML、CLI 命令和修正建议。
---

# Drun 深度使用

面向真实场景直接产出 `drun` YAML、运行命令、转换命令和排障建议。不要重复 README 的快速开始，优先给用户现在就能执行的方案。

## 触发范围

- 编写或改写 `drun` 用例、`caseflow`、上传场景、登录链路
- 解释高级 DSL：`invoke`、`invoke_case_name`、`invoke_case_names`、`repeat`、`sleep`、hooks、参数化
- 设计 `drun run` / `drun q` 命令、环境加载方案、`-persist-env`
- 使用 `convert` / `convert-openapi` / `export curl`
- 解释 JSON / HTML / Allure / snippet / `server`
- 基于 `drun` 错误日志做排障和修正

## 非触发范围

- 泛化 HTTP 或 API 测试理论
- 与 `drun` 无关的框架对比
- 纯 OpenAPI 设计讨论

## 默认行为

1. 先判断问题类型，只读取必要 reference，不要一次性加载全部文档。
2. 以仓库代码与测试为准；README 和实现冲突时，跟实现。
3. 默认中文输出，先给可运行 YAML 或 CLI 命令，再补关键字段解释。
4. 优先使用当前仓库已支持的能力：`invoke_case_name`、`invoke_case_names`、`sleep`、`repeat`、`request.files`、`-persist-env`、`-snippet`、`convert`、`export curl`、`server`。
5. 不虚构未实现 DSL、兼容字段或旧命令。

## 引用导航

- DSL、模板、上传：`references/dsl-core.md`
- `run` 目标、环境优先级、`-vars`、`-persist-env`：`references/execution-and-env.md`
- `caseflow`、`invoke`、`repeat`、`sleep`、hooks、参数化：`references/composition-and-reuse.md`
- `q`、`convert`、`convert-openapi`、`export curl`：`references/debug-convert-export.md`
- JSON/HTML/Allure/snippet/server：`references/reports-and-outputs.md`
- 常见错误与修正：`references/troubleshooting.md`

## 输出规则

- 默认结构：可执行 YAML / CLI 命令 -> 关键字段解释 -> 常见坑。
- 示例优先围绕三类高频场景：
  - 单接口调试
  - 登录后链路调用
  - 文件上传与报告输出
- 明确哪些规则是实现约束，尤其是：
  - `step` 只能三选一：`request`、`invoke`、`sleep`
  - `sleep` 不能与 `validate`、`extract`、`export`、`response`、`retry` 共存
  - `request.files` 不能与 `request.body` 并用；multipart 表单字段放 `request.data`
  - YAML 请求字段用 `request.path` 和 `request.body`，不要写 `request.url` 或 `request.json`
  - `config.parameters` 才是参数化入口，顶层 `parameters` 无效
  - 旧 `cases:` 套件已不支持；旧 `loop` / `foreach` 已废弃，请用 `repeat`
- 如果用户只问单个点，只回答该点，不输出整本手册。

## Ask Only If Blocked

仅在以下信息缺失且会直接影响可执行结果时提问：

- 接口最小信息缺失：HTTP 方法、路径、请求体、预期结果
- 目标环境或 `base_url` 无法推断
- 鉴权变量名或请求头名无法推断
- 用户明确在意目录落点，但当前没有约定

其余情况直接做合理假设，并在答案里写清楚假设。

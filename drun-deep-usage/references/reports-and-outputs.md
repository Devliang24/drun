# Reports And Outputs

适用于 JSON / HTML / Allure / snippet / `server` 的说明，以及输出目录行为。

## 输出类型总览

- 日志：`drun run` 总会产生日志文件
- JSON 报告：显式传 `-report`
- HTML 报告：项目模式默认生成；临时单文件模式默认不生成，除非传 `-html`
- Allure：显式传 `-allure-results`
- 代码片段：项目模式默认生成；临时单文件模式默认不生成，除非传 `-snippet-output`
- 报告 Web 查看：`drun server`

## 临时单文件 vs 脚手架项目

当前实现会区分两种运行模式。

临时单文件模式：

- 目标是单个 YAML 文件
- 且该文件不在脚手架项目根下
- 默认只在当前目录产生日志文件
- 默认不自动生成 HTML 和 snippets

脚手架项目模式：

- 运行路径位于一个包含 `testcases/` 或 `testsuites/`，且同时带 `.env` 或 `Dhook.py` 的项目根下
- 默认输出：
  - `logs/<system>-<timestamp>.log`
  - `reports/<system>-<timestamp>.html`
  - `snippets/<timestamp>/`

## 命令示例

```bash
drun run testsuites/testsuite_login_flow.yaml -env dev -report reports/login.json
drun run testsuites/testsuite_login_flow.yaml -env dev -allure-results allure-results
drun run testsuites/testsuite_login_flow.yaml -env dev -snippet curl
drun run testsuites/testsuite_login_flow.yaml -env dev -snippet python -snippet-output snippets/manual
drun run /tmp/test_upload.yaml -env dev -html reports/upload.html -snippet-output snippets/upload
```

## JSON / HTML / Allure

- `-report reports/result.json` 会把完整 `RunReport` 序列化到 JSON
- HTML 报告在项目模式默认开启；如果你想指定路径，用 `-html reports/custom.html`
- `-allure-results allure-results` 会写 Allure 2 results 文件和附件

生成 Allure 后，通常还会再跑：

```bash
allure generate allure-results -o allure-report --clean
```

## snippets

`-snippet` 支持：

- `off`
- `all`
- `curl`
- `python`

说明：

- snippets 只为 request step 生成
- `invoke` 和 `sleep` step 不会产出代码片段
- 项目模式默认会在 `snippets/<timestamp>/` 下产出
- 临时单文件模式下，只有显式传 `-snippet-output` 才会生成

## 报告服务

```bash
drun server
drun server -port 8080
drun server -host 127.0.0.1 -reports-dir reports -headless
```

说明：

- `server` 会读取 `reports` 目录；目录不存在时会自动创建
- 默认监听 `0.0.0.0:8080`
- 本地 `127.0.0.1` / `localhost` 且非 `-headless`、非 `-reload` 时，会尝试自动打开浏览器
- 启动后可查看：
  - Web UI：`http://host:port`
  - API docs：`http://host:port/docs`

## 文件上传与报告输出的组合示例

```bash
drun run testcases/test_upload_avatar.yaml \
  -env dev \
  -report reports/upload.json \
  -allure-results allure-results \
  -snippet curl
```

这个组合适合“先验证上传接口，再把请求片段交给研发复现”的场景。

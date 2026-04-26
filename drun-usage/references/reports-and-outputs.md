# Reports And Outputs

适用于 JSON / HTML / Allure / snippet / `server`、响应保存和 `export.csv` 的说明，以及输出目录行为。

## 输出类型总览

- 日志：`drun run` 总会产生日志文件
- JSON 报告：显式传 `-report`
- HTML 报告：项目模式默认生成；临时单文件模式默认不生成，除非传 `-html`
- Allure：显式传 `-allure-results`
- 代码片段：项目模式默认生成；临时单文件模式默认不生成，除非传 `-snippet-output`
- 响应体保存：YAML step 里写 `response.save_body_to`
- 响应数组导出 CSV：YAML step 里写 `export.csv`
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
- HTML 报告会展示请求头、请求体、响应体、断言、提取变量和 curl；复制按钮是图标按钮，复制状态通过 tooltip / icon 反馈

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

## 保存响应体

`response.save_body_to` 适合音频、图片、压缩包、模型生成文件等二进制响应。

```yaml
steps:
  - name: 下载文件
    request:
      method: GET
      path: /api/files/${file_id}
    response:
      save_body_to: artifacts/${file_id}.bin
    validate:
      - eq: [status_code, 200]
      - gt: [$body_size, 0]
```

说明：

- 路径可使用模板变量
- 相对路径按当前运行目录解析，建议从项目根目录运行，并写到 `artifacts/`、`reports/` 或业务约定目录
- 报告中会保留 `content_type`、`body_size`、`body_bytes_b64`、`saved_body_to`

## 导出响应数组到 CSV

`export.csv` 适合把接口返回的数组落盘，供后续人工核对或作为下一轮数据源。

```yaml
steps:
  - name: 查询订单列表并导出
    request:
      method: GET
      path: /api/orders
    export:
      csv:
        data: $.data.items
        file: data/orders.csv
        columns: [id, status, amount]
        mode: overwrite
        encoding: utf-8
        delimiter: ","
    validate:
      - eq: [status_code, 200]
```

边界：

- `export.csv.data` 必须返回数组，且数组元素必须是对象
- `columns` 不传时使用第一行对象的全部字段
- `mode` 支持 `overwrite` / `append`
- `columns` 指定不存在的字段会报错
- 相对输出路径优先按向上查找到的 `Dhook.py` 所在目录解析；找不到时按当前运行目录解析

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

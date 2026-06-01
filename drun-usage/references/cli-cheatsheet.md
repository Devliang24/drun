# CLI Cheatsheet

适用于 Agent 快速选择 `drun` 命令。更详细的行为说明见 execution、debug/convert/export 和 reports references。

## 基础

```bash
drun --help
drun check tcases
drun run tcases -env dev
```

## 运行 Case 或 suite

```bash
drun run tcases/tc_login.yaml -env dev -secrets mask
drun run tsuites/ts_login_flow.yaml -env dev -secrets mask
drun run tcases -env dev -k "smoke and not slow" -secrets mask
drun run tcases:登录,查询资料 -env dev -secrets mask
```

排障时常用：

```bash
drun run tcases/tc_login.yaml -env dev -failfast -secrets mask
drun run tcases/tc_login.yaml -env dev -log-level DEBUG -httpx-logs -secrets mask
drun run tcases/tc_login.yaml -env dev -response-headers -secrets mask
```

## 环境与变量

```bash
drun run tcases/tc_login.yaml -env dev -secrets mask
drun run tcases/tc_login.yaml -env-file .env.local -secrets mask
drun run tcases/tc_login.yaml -vars tenant=blue -secrets mask
drun run tcases/tc_login.yaml -env dev -persist-env .env.runtime -secrets mask
```

## 单接口调试

```bash
drun q https://api.example.com/ping -check 'status_code=200' -secrets mask
```

POST JSON 示例：

```bash
drun q https://api.example.com/api/login \
  -X POST \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"secret"}' \
  -check 'status_code=200' \
  -extract 'token=$.data.token' \
  -save-yaml tcases/tc_login_from_q.yaml \
  -secrets mask
```

## 转换与导出

```bash
drun convert sample.curl -outfile tcases/from_curl.yaml -placeholders on -redact Authorization,Cookie
drun convert traffic.har -output-mode split -outfile tcases/imported.yaml
drun convert-openapi spec/openapi.json -output-mode split -outfile tcases/api.yaml -placeholders on
drun export curl tcases/tc_login.yaml -steps 1 -redact Authorization,Cookie
drun export curl tcases/tc_upload.yaml -layout multiline -shell sh -redact Authorization,Cookie
```

## 报告与查看

```bash
drun run tcases/tc_login.yaml -env dev -report reports/login.json -secrets mask
drun run tcases/tc_login.yaml -env dev -html reports/login.html -secrets mask
drun run tcases/tc_login.yaml -env dev -allure-results allure-results -secrets mask
drun run tcases/tc_login.yaml -env dev -snippet curl -secrets mask
drun server -reports-dir reports
drun server -host 127.0.0.1 -port 8080 -reports-dir reports
```

## 选择建议

- 先验证 YAML 作者错误：`drun check`
- 执行已有 Case 或 suite：`drun run`
- 单接口临时调试：`drun q`
- 从已有 cURL / HAR / Postman 迁移：`drun convert`
- 从 OpenAPI 生成骨架：`drun convert-openapi`
- 从 Case 反推可复现请求：`drun export curl`
- 查看 HTML 报告：`drun server`

# Debug Convert Export

适用于单接口调试、把已有请求材料转成 `drun` YAML，以及从现有 case 导出 curl。

## `drun q`：先打通请求，再决定要不要落 YAML

`q` 直接发 HTTP 请求，不依赖 YAML。适合单接口调试、校验 headers/body、快速试断言和提取。

```bash
drun q https://api.example.com/api/login \
  -X POST \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"secret"}' \
  -validate 'status_code=200' \
  -extract 'token=$.data.token' \
  -save-yaml testcases/test_login_from_q.yaml \
  -secrets mask
```

常用选项：

- `-H 'Key: Value'`
- `-p k=v`
- `-d @body.json`
- `-validate 'status_code=200'`
- `-validate '$.data.count>0'`
- `-validate 'len_ge:$.items=1'`
- `-extract 'token=$.data.token'`
- `-o body.json`
- `-save-yaml testcases/test_xxx.yaml`
- `-v`

边界：

- `q` 适合快速试请求，不适合多步链路编排
- `-save-yaml` 生成的是单 case 骨架，复杂复用还要再手工整理

## `drun convert`：从 cURL / HAR / Postman 迁移

### cURL

```bash
drun convert sample.curl -outfile testcases/from_curl.yaml -placeholders on -redact Authorization,Cookie
```

### HAR

```bash
drun convert traffic.har -output-mode split -outfile testcases/imported.yaml
```

### Postman

```bash
drun convert collection.json -postman-env env.json -output-mode split -outfile testcases/postman.yaml -suite-out testsuites/postman_flow.yaml
```

实现边界：

- 选项必须写在 `INFILE` 后面
- 不支持裸转；至少要给 `-outfile`、`-into`、`-output-mode split`、`-placeholders on` 这类选项之一
- `-output-mode single` 生成一个多 step case
- `-output-mode split` 按导入 step 拆成多个 YAML
- `-into` 适合把导入结果并到已有 case 文件
- `-suite-out` 当前只在 Postman 转换链路里可用，用来额外生成 `caseflow`

## `drun convert-openapi`：从规范快速起骨架

```bash
drun convert-openapi spec/openapi/ecommerce_api.json \
  -output-mode split \
  -outfile testcases/ecommerce.yaml \
  -tags orders,payment \
  -placeholders on
```

说明：

- 输入支持 `.json` / `.yaml`
- `-tags` 会按 OpenAPI operation tags 过滤
- `-base-url` 不传时，优先取 spec `servers[0].url`，再退化到 `http://localhost:8000`
- 生成结果更适合“起手骨架”，断言、提取、鉴权通常还需要手补

## `drun export curl`：从现有 case 反推可复现请求

```bash
drun export curl testcases/test_login.yaml \
  -steps 1 \
  -layout multiline \
  -comments on \
  -outfile converts/login_step1.curl
```

可选写法：

```bash
drun export curl testcases/test_upload.yaml -layout oneline
drun export curl testcases -case-name 登录 -steps 1,3-4
```

边界：

- `-steps` 从 1 开始，可写区间
- `-outfile` 必须以 `.curl` 结尾
- 更适合导出普通 request step；`invoke` / `sleep` 不是理想导出源
- 若 YAML 里还有无法解析的模板变量，导出的 curl 里可能保留占位符

## 什么时候选哪一个

- 只想立刻打接口：先 `q`
- 手里有 cURL / HAR / Postman：先 `convert`
- 手里是 OpenAPI 规范：用 `convert-openapi`
- 已经有 `drun` case，只想拿到可复现命令：用 `export curl`

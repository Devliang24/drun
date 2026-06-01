# YAML Fields

适用于 Agent 快速确认 drun YAML 字段位置、字段名称和常见约束。更完整示例见 recipes 和 DSL core references。

## 顶层字段

| 字段 | 说明 |
| --- | --- |
| `config` | 单个 Case 或 suite 的配置。 |
| `steps` | 单个 Case 的 Step 列表。每个 Step 只能有一个 Executable Target。 |
| `caseflow` | suite 编排列表，用于组织 Invoke Step / Sleep Step。 |

## config

| 字段 | 说明 |
| --- | --- |
| `config.name` | Case 或 suite 名称。 |
| `config.base_url` | 相对 `request.path` 的基础地址。常用 `${ENV(BASE_URL)}`。 |
| `config.variables` | Case 初始变量。 |
| `config.parameters` | 参数化入口；不要写顶层 `parameters`。 |
| `config.headers` | 默认请求头。 |
| `config.timeout` | 默认超时时间。 |
| `config.verify` | TLS 校验开关。 |
| `config.tags` | 标签列表，可配合 `drun run -k` 过滤。 |
| `config.setup_hooks` | Case 级 setup hooks。 |
| `config.teardown_hooks` | Case 级 teardown hooks。 |

## steps[]

每个 Step 必须且只能拥有一个 Executable Target：

| 字段 | 说明 |
| --- | --- |
| `request` | Request Step，发送 HTTP 请求。 |
| `invoke` | Invoke Step，调用另一个 YAML Case。 |
| `sleep` | Sleep Step，等待毫秒数。 |

Step 通用字段：

| 字段 | 说明 |
| --- | --- |
| `name` | Step 名称。 |
| `repeat` | 重复执行 Step，值最终必须解析为非负整数。 |
| `skip` | 跳过条件。 |
| `setup_hooks` | Step 级 setup hooks。 |
| `teardown_hooks` | Step 级 teardown hooks。 |

## request

| 字段 | 说明 |
| --- | --- |
| `request.method` | HTTP 方法，例如 `GET`、`POST`。 |
| `request.path` | 请求路径；不要写 `request.url`。 |
| `request.headers` | 当前 Request Step 的请求头。 |
| `request.body` | JSON 或普通请求体；不要写 `request.json`。 |
| `request.data` | multipart 表单的普通字段。 |
| `request.files` | multipart 文件字段，不能与 `request.body` 并用。 |
| `request.auth` | basic / bearer 鉴权配置。 |
| `request.timeout` | 当前请求超时。 |
| `request.verify` | 当前请求 TLS 校验。 |
| `request.allow_redirects` | 是否允许重定向。 |
| `request.stream` | 是否按流式响应处理。 |
| `request.stream_timeout` | 流式响应超时。 |

## extract 与 check

`extract` 和 `check` 是 Request Step 的响应后处理字段，必须与 `request` 同级，不在 `request` 里面。

```yaml
steps:
  - name: 登录
    request:
      method: POST
      path: /api/login
      body:
        username: ${ENV(USERNAME)}
        password: ${ENV(PASSWORD)}
    extract:
      token: $.data.token
    check:
      - eq: [status_code, 200]
```

| 字段 | 说明 |
| --- | --- |
| `extract` | 从响应中提取变量，供后续 Step 使用。响应 body 路径使用 `$` 语法，例如 `$.data.token`。 |
| `check` | 响应检查列表。可检查 `status_code`、headers 或 `$` 响应 body 路径。 |

## response

| 字段 | 说明 |
| --- | --- |
| `response.save_body_to` | 保存响应体到文件，适合下载图片、音频、压缩包等二进制响应。 |

## export

| 字段 | 说明 |
| --- | --- |
| `export.csv` | 把响应数组导出为 CSV。 |
| `export.csv.data` | 指向响应数组的 `$` 路径。 |
| `export.csv.file` | 输出 CSV 文件路径。 |
| `export.csv.columns` | 输出列名。 |
| `export.csv.mode` | `overwrite` 或 `append`。 |

## caseflow

`caseflow` 用于 suite 编排，常见字段：

| 字段 | 说明 |
| --- | --- |
| `name` | 编排 Step 名称。 |
| `invoke` | 调用目标 Case。 |
| `invoke_case_name` | 在被调用目标中选择一个 Case 名。 |
| `invoke_case_names` | 在被调用目标中选择多个 Case 名。 |
| `sleep` | 等待毫秒数。 |
| `repeat` | 重复执行当前编排 Step。 |
| `export` | 显式导出 invoke 产生的变量。 |

## parameters

参数化入口是 `config.parameters`。

数组参数化：

```yaml
config:
  parameters:
    - username-password:
        - [alice, pass1]
        - [bob, pass2]
```

CSV 参数化：

```yaml
config:
  parameters:
    - csv:
        path: data/login_cases.csv
        columns: [username, password, expected_status]
```

CSV 当前不支持 `rows`、`where`、`filter` 等按行过滤 DSL。

## 快速约束

- YAML 请求字段用 `request.path` 和 `request.body`。
- `extract` / `check` 与 `request` 同级。
- `request.files` 不能与 `request.body` 并用；multipart 普通字段放 `request.data`。
- Sleep Step 不能携带 `check`、`extract`、`export`、`response`、`retry`。
- 旧 `validate` 改为 `check`。
- 旧 `cases` 改为 `caseflow`。
- 旧 `loop` / `foreach` 改为 `repeat`。

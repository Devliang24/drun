# Troubleshooting

适用于根据报错快速定位 `drun` YAML、环境、上传、编排和转换问题。

## YAML 诊断错误码

`drun c` 会聚合输出 YAML/DSL 作者错误；`drun r` 遇到第一个阻断性 YAML 错误仍会快速停止。诊断使用稳定错误码 `DRUN-YAML-xxx`，并尽量输出文件行号、YAML path、修复建议和最小示例。

| 错误码 | 含义 | 常见处理方向 |
| --- | --- | --- |
| `DRUN-YAML-001` | YAML 语法解析失败 | 先修正缩进、冒号、列表和引号等 YAML 基础语法。 |
| `DRUN-YAML-002` | YAML schema 不符合 DSL | 检查根节点、`config`、`steps`、`check` 等字段形状。 |
| `DRUN-YAML-003` | `request` 字段不支持 | 常见是把 `request.path` 写成了 `request.url`。 |
| `DRUN-YAML-004` | 不支持 `request.json` | JSON 或原始请求体改写到 `request.body`。 |
| `DRUN-YAML-005` | 字段错误缩进到 `request` 下 | 将 `check`、`extract`、hooks 等移出 `request`，与其同级。 |
| `DRUN-YAML-006` | 参数位置错误 | 使用 `config.parameters`，不要使用顶层 `parameters`。 |
| `DRUN-YAML-007` | 响应 body 路径语法错误 | `check` / `extract` 中用 `$.data.id`，不要用 `body.id`。 |
| `DRUN-YAML-008` | `request.files` 声明错误 | 修正 files 结构；multipart 普通字段放 `request.data`。 |
| `DRUN-YAML-009` | 旧版 DSL 写法 | 将 `cases`、`loop`、`foreach` 迁移到当前 `caseflow` / `repeat` 写法。 |
| `DRUN-YAML-010` | `caseflow` 写法错误 | `caseflow` 必须是列表，每项至少包含有效 `invoke`。 |
| `DRUN-YAML-011` | step 执行目标错误 | 每个 step 只保留 `request`、`invoke`、`sleep` 中的一种。 |
| `DRUN-YAML-012` | 旧字段 `validate` | 改成 `check`，不再作为兼容 alias 接受。 |
| `DRUN-YAML-013` | hooks 声明错误 | hooks 放在支持的位置，并写成 `${func(...)}` 表达式列表。 |
| `DRUN-YAML-014` | step 间距不符合检查规则 | 在多个 step item 之间增加空行。 |
| `DRUN-YAML-015` | `repeat` / `sleep` 值错误 | `repeat` 用非负整数；`sleep` 用非负数值，或可解析表达式。 |
| `DRUN-YAML-999` | YAML 加载兜底错误 | 查看 hint 中的原始异常；后续可细分为更具体错误码。 |

### `request.url` 写错字段

优化前：

```text
FAIL: tcases/tc_demo.yaml -> Failed to load tcases/tc_demo.yaml: 1 validation error for Case
steps.0.request.url
  Extra inputs are not permitted
```

优化后：

```text
DRUN-YAML-003 Invalid request field: request.url
File: tcases/tc_demo.yaml:8
Path: steps[0].request.url

Use `request.path` instead of `request.url`.

Example:
  request:
    method: GET
    path: /api/users
```

修正：YAML 请求字段用 `request.path`，不要写 `request.url`。

### 顶层 `parameters` 位置错误

优化前：

```text
FAIL: tcases/tc_users.yaml -> Invalid top-level 'parameters'. Move case parameters under 'config.parameters'.
```

优化后：

```text
DRUN-YAML-006 Invalid parameter location
File: tcases/tc_users.yaml:2
Path: parameters

Move `parameters` under `config.parameters`.

Example:
  config:
    name: User cases
    parameters:
      - user_id: [1, 2, 3]
```

修正：参数化入口是 `config.parameters`，不要使用顶层 `parameters`。

### 旧字段 `validate` 已更名

错误示例：

```yaml
steps:
  - name: ping
    request:
      method: GET
      path: /ping
    validate:
      - eq: [status_code, 200]
```

诊断输出：

```text
DRUN-YAML-012 validate has been renamed to check
File: tcases/tc_ping.yaml:8
Path: steps[0].validate

Use `check` instead of `validate`.

Example:
  check:
    - eq: [$.data.id, 1]
```

修正：

```yaml
steps:
  - name: ping
    request:
      method: GET
      path: /ping
    check:
      - eq: [status_code, 200]
```

### `drun c` 多文件聚合

优化前：

```text
FAIL: tcases/tc_a.yaml -> Invalid request field 'json' ...
```

优化后：

```text
FAIL tcases/tc_a.yaml
  DRUN-YAML-004 request.json is not supported
  DRUN-YAML-007 Invalid check syntax: body.id

FAIL tcases/tc_b.yaml
  DRUN-YAML-011 Step cannot combine `request`, `invoke`, and `sleep`

Checked 8 file(s): 6 OK, 2 failed, 3 error(s).
```

修正：先用 `drun c tcases` 批量清理 YAML 作者错误，再执行 `drun r`。

## 环境未命中

症状：

```text
[ERROR] Environment not found. Use -env, -env-file, or provide .env in current directory.
```

修正：

- 传 `-env dev`
- 或传 `-env-file .env.local`
- 或在当前目录放 `.env`
- 如果你本来就只想走 OS 环境或命名 YAML 环境，也可以显式写 `-env dev`

## `base_url` 缺失

症状：

```text
[ERROR] base_url is required for cases using relative URLs.
```

修正：

- 在 `config.base_url` 里写死
- 或在环境里补 `BASE_URL`
- 或运行时传 `-vars base_url=https://api.example.com`

## 未解析变量 / 严格渲染失败

症状：

```text
Unresolved template variables: token
```

修正：

- 检查变量是来自 `config.variables`、上一步 `extract`、`-vars` 还是 `${ENV(...)}` 
- 请求、`repeat`、`sleep`、`skip` 都会严格渲染；缺变量时会在请求发送前失败
- 如果变量其实应该来自环境文件，优先确认 `-env` / `-env-file` 是否指对

## `invoke_case_name` / `invoke_case_names` 无匹配

症状：

```text
No matched case names for invoke '...': requested=[Case Z] available=[Case A, Case B]
```

或：

```text
No matched case names for run target '...': requested=[Case Z] available=[Case A, Case B]
```

修正：

- case 名必须精确匹配
- 优先先看实际 `config.name`
- 普通单 case YAML 通常没有多 case 可供选择；这时不要强上 `invoke_case_name`

## 上传文件路径错误

症状：

```text
request.files.file path not found: ./data/demo.wav
```

修正：

- 相对路径按当前运行目录解析，不是按 YAML 文件目录解析
- 建议从项目根目录运行，并让上传路径也相对项目根目录
- 如果是 multipart 表单，普通字段放 `request.data`，文件放 `request.files`

## `request.files` 和 `body` 混用

症状：

```text
request.body cannot be used with request.files. Use request.data for multipart form fields.
```

修正：

- `body` 改成 `data`
- `files` 只保留文件字段

正确写法：

```yaml
request:
  method: POST
  path: /upload
  data:
    biz: profile
  files:
    avatar: ./data/avatar.png
```

## `sleep` / `request` / `invoke` 混用

症状：

```text
Step cannot combine 'request', 'invoke', and 'sleep'. Use exactly one.
```

或：

```text
Step with 'sleep' cannot use 'check'.
```

修正：

- 一个 step 只能有一种执行目标
- `sleep` 只负责等待；检查、提取、导出要放到前后 request step

## `repeat` 或 `sleep` 表达式类型不对

症状：

```text
repeat error: Step '轮询状态' repeat must resolve to an integer
sleep error: Step '等待异步' sleep must resolve to a number
```

修正：

- `repeat` 最终必须是整数且 `>= 0`
- `sleep` 最终必须是数值，单位毫秒
- 如果写成 `${retry_count}`、`${wait_ms}`，确认变量不是空字符串、布尔值或对象

## CSV 参数化不能按行过滤

症状：

```text
用户要求只运行 CSV 第 3 行，或在 YAML 中写 rows/where 之类字段
```

修正：

- 当前 CSV 参数化会展开全部数据行
- 不要生成 `rows`、`where`、`filter` 这类未实现字段
- 临时只跑少量数据时，建议复制目标行到单独 CSV，或用普通数组参数化写最小样例

## `export.csv` 数据格式错误

症状：

```text
export.csv.data 必须返回数组
export.csv.data 数组元素必须是对象
export.csv.columns 指定的列不存在
```

修正：

- `data` 应指向响应里的数组，例如 `$.data.items`
- 如果接口返回对象，先改提取路径指向对象内的列表字段
- `columns` 只写数组元素对象里真实存在的字段

## 保存二进制响应失败

症状：

```text
response.save_body_to requires a response body
response.save_body_to requires raw response bytes
```

修正：

- `response.save_body_to` 主要用于音频、图片、文件下载等二进制响应
- JSON 响应一般直接用报告或 `-report` 保存，不需要 `save_body_to`
- 如果路径里用了变量，确认变量已在前置步骤或环境中存在

## YAML 字段写成旧格式

症状：

```text
Invalid request field 'url'
Invalid request field 'json'
Invalid top-level 'parameters'
Legacy inline suite ('cases:') is not supported
```

修正：

- `request.url` -> `request.path`
- `request.json` -> `request.body`
- 顶层 `parameters` -> `config.parameters`
- 旧 `cases:` -> `caseflow`

## `drun o` 命令写法错误

症状：

```text
[CONVERT] Options must follow INFILE.
[CONVERT] No options provided. Bare conversion is not supported.
```

修正：

- 先写输入文件，再写选项
- 至少给一个有效输出相关选项

正确示例：

```bash
drun o sample.curl -outfile tcases/from_curl.yaml
drun o traffic.har -output-mode split -outfile tcases/imported.yaml
```

## 快速预览：dry-run

### 看参数展开结果

写参数化用例时，可以先 dry-run 看展开结果，不必真正跑 HTTP：

```bash
drun r tcases -dry-run
drun r tcases -env dev -dry-run -dry-run-limit 50
```

### dry-run 不要求环境文件

如果没有 `.env`，dry-run 仍然可以输出预览，此时 `${ENV(...)}` 和需要运行时 extract 的变量会保留原样。真正执行时仍然要求环境文件。

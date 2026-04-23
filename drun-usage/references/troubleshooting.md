# Troubleshooting

适用于根据报错快速定位 `drun` YAML、环境、上传、编排和转换问题。

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
Step with 'sleep' cannot use 'validate'.
```

修正：

- 一个 step 只能有一种执行目标
- `sleep` 只负责等待；断言、提取、导出要放到前后 request step

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

## `convert` 命令写法错误

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
drun convert sample.curl -outfile testcases/from_curl.yaml
drun convert traffic.har -output-mode split -outfile testcases/imported.yaml
```

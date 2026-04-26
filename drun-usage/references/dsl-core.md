# DSL Core

适用于编写或解释 `config`、`steps`、`request`、`extract`、`validate`、模板表达式、严格渲染、`request.files`、流式请求和响应保存。

## 能力说明

- 单个用例文件的核心结构是 `config` + `steps`
- `config` 常用字段：`name`、`base_url`、`variables`、`headers`、`timeout`、`verify`、`tags`
- 每个 step 只能拥有一个执行目标：`request`、`invoke` 或 `sleep`
- 请求体字段在 YAML 中写 `body`，不要写 `json`
- request 常用控制字段：`auth`、`timeout`、`verify`、`allow_redirects`、`stream`、`stream_timeout`
- 提取与断言对响应体统一使用 `$...` 表达式；元数据用 `status_code` 或 `headers.<name>`

## 最小可运行 YAML

```yaml
config:
  name: 获取用户详情
  base_url: ${ENV(BASE_URL)}
  variables:
    user_id: 1001
  tags: [smoke, user]

steps:
  - name: 获取用户 ${user_id}
    request:
      method: GET
      path: /api/users/${user_id}
      headers:
        Authorization: Bearer ${ENV(API_TOKEN)}
    extract:
      nickname: $.data.nickname
    validate:
      - eq: [status_code, 200]
      - exists: [$.data.id, true]
      - contains: [$.data.nickname, liang]
```

```bash
drun check testcases/test_user_detail.yaml
drun run testcases/test_user_detail.yaml -env dev
```

## 模板表达式与严格渲染

- 变量可直接写 `$var` 或 `${expr}`
- 环境变量优先用 `${ENV(KEY)}`
- 常用内建函数包括 `${uuid()}`、`${now()}`、`${random_int(1000,9999)}`
- 请求渲染、`repeat`、`sleep`、`skip` 在执行时会走严格渲染；缺变量或表达式运行报错会在发请求前失败，不会静默吞掉

```yaml
config:
  name: 创建用户
  base_url: ${ENV(BASE_URL)}

steps:
  - name: 创建用户 ${uuid()}
    request:
      method: POST
      path: /api/users
      body:
        username: demo_${random_int(1000,9999)}
        email: ${ENV(TEST_EMAIL)}
    extract:
      user_id: $.data.id
    validate:
      - eq: [status_code, 201]
```

如果 `${TEST_EMAIL}`、`${ENV(TEST_EMAIL)}` 或 `${missing_var}` 无法解析，运行会直接报未解析变量错误。

## 请求控制字段

除了直接写 `headers.Authorization`，也可以用 `request.auth` 表达 basic / bearer 鉴权。

```yaml
steps:
  - name: bearer 鉴权请求
    request:
      method: GET
      path: /api/profile
      auth:
        type: bearer
        token: ${ENV(API_TOKEN)}
      timeout: 10
      verify: true
      allow_redirects: false
    validate:
      - eq: [status_code, 200]

  - name: basic 鉴权请求
    request:
      method: GET
      path: /api/admin
      auth:
        type: basic
        username: ${ENV(BASIC_USER)}
        password: ${ENV(BASIC_PASS)}
```

流式响应适合 SSE / 大模型接口调试；响应里会记录 `stream_events`、`stream_summary` 和原始 chunk。

```yaml
steps:
  - name: 调用流式接口
    request:
      method: POST
      path: /v1/chat/completions
      headers:
        Authorization: Bearer ${ENV(API_TOKEN)}
      body:
        model: demo-model
        stream: true
        messages:
          - role: user
            content: hello
      stream: true
      stream_timeout: 60
    extract:
      first_chunk_ms: $stream_summary.first_chunk_ms
      events: $stream_events
    validate:
      - eq: [status_code, 200]
```

流式相关可提取字段：

- `$stream_events`
- `$stream_summary`
- `$stream_summary.first_chunk_ms`
- `$stream_raw_chunks`

## 文件上传

`request.files` 适合 multipart 上传；表单字段放在 `request.data`，不要放在 `request.body`。

```yaml
config:
  name: 上传头像
  base_url: ${ENV(BASE_URL)}

steps:
  - name: 上传头像
    request:
      method: POST
      path: /api/files/avatar
      headers:
        Authorization: Bearer ${ENV(API_TOKEN)}
      data:
        biz: profile
        user_id: ${ENV(USER_ID)}
      files:
        avatar: ["./data/avatar.png", "image/png"]
    extract:
      file_url: $.data.url
    validate:
      - eq: [status_code, 200]
      - exists: [$.data.url, true]
```

```bash
drun run testcases/test_upload_avatar.yaml -env dev
```

`request.files` 常见可用形态：

- `avatar: ./data/avatar.png`
- `avatar: ["./data/avatar.png", "image/png"]`
- `files: [[avatar, "./data/avatar.png"]]` 这种列表形态用于动态生成时保留字段名
- `files: [[attachment, ["./data/readme.txt", "text/plain"]]]`

`("filename", <bytes>, "content/type")` 是 Python/httpx 内部形态，不建议作为手写 YAML 示例。

## 二进制响应与保存

当响应不是 JSON / 文本时，报告里会保留二进制元数据，可用 `response.save_body_to` 保存原始响应体。

```yaml
config:
  name: 下载音频
  base_url: ${ENV(BASE_URL)}

steps:
  - name: 下载 TTS 音频
    request:
      method: GET
      path: /api/tts?id=${audio_id}
    response:
      save_body_to: artifacts/tts_${audio_id}.mp3
    validate:
      - eq: [status_code, 200]
      - eq: [$content_type, audio/mpeg]
      - gt: [$body_size, 0]
```

二进制响应常用元数据：

- `$content_type`
- `$body_size`
- `$body_bytes_b64`
- `$raw_bytes`

## 常见坑

- `request.url` 不支持，写 `request.path`
- `request.json` 不支持，写 `request.body`
- `extract` 和 `validate` 中不要写 `body.id`，统一写 `$.id` 或 `$.data.id`
- `request.files` 不能和 `request.body` 同时出现
- 上传路径相对当前运行目录解析，不是相对 YAML 文件解析；习惯上从项目根目录执行
- `response.save_body_to` 需要响应里存在原始 body bytes；普通 JSON 响应通常没必要使用

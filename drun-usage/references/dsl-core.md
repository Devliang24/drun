# DSL Core

适用于编写或解释 `config`、`steps`、`request`、`extract`、`validate`、模板表达式、严格渲染和 `request.files`。

## 能力说明

- 单个用例文件的核心结构是 `config` + `steps`
- `config` 常用字段：`name`、`base_url`、`variables`、`headers`、`timeout`、`verify`、`tags`
- 每个 step 只能拥有一个执行目标：`request`、`invoke` 或 `sleep`
- 请求体字段在 YAML 中写 `body`，不要写 `json`
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
- `avatar: ("avatar.png", <bytes>, "image/png")`

## 常见坑

- `request.url` 不支持，写 `request.path`
- `request.json` 不支持，写 `request.body`
- `extract` 和 `validate` 中不要写 `body.id`，统一写 `$.id` 或 `$.data.id`
- `request.files` 不能和 `request.body` 同时出现
- 上传路径相对当前运行目录解析，不是相对 YAML 文件解析；习惯上从项目根目录执行

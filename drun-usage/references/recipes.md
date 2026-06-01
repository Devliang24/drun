# Recipes

适用于 Agent 直接复制、裁剪和组合的 drun YAML / CLI 模板。

## 使用原则

- 敏感值使用 `${ENV(...)}`，不要写真实 token、Cookie 或密码。
- YAML 请求字段用 `request.path` 和 `request.body`。
- `extract` / `check` 与 `request` 同级，不要缩进到 `request` 下。
- 生成 YAML 后，默认给出 `drun check` 和 `drun run` 命令。
- 涉及敏感信息的运行示例默认使用 `-secrets mask`。

## 单接口 GET

适用：查询详情、健康检查、只读接口。

`tcases/tc_user_detail.yaml`

```yaml
config:
  name: 查询用户详情
  base_url: ${ENV(BASE_URL)}
  variables:
    user_id: 1001

steps:
  - name: 查询用户 ${user_id}
    request:
      method: GET
      path: /api/users/${user_id}
      headers:
        Authorization: Bearer ${ENV(API_TOKEN)}
    check:
      - eq: [status_code, 200]
      - exists: [$.data.id, true]
```

运行：

```bash
drun check tcases/tc_user_detail.yaml
drun run tcases/tc_user_detail.yaml -env dev -secrets mask
```

## POST JSON 创建资源

适用：创建用户、创建订单、提交表单类 JSON 接口。

`tcases/tc_create_user.yaml`

```yaml
config:
  name: 创建用户
  base_url: ${ENV(BASE_URL)}

steps:
  - name: 创建用户
    request:
      method: POST
      path: /api/users
      headers:
        Authorization: Bearer ${ENV(API_TOKEN)}
      body:
        username: demo_${random_int(1000,9999)}
        email: ${ENV(TEST_EMAIL)}
    extract:
      user_id: $.data.id
    check:
      - eq: [status_code, 201]
      - exists: [$.data.id, true]
```

运行：

```bash
drun check tcases/tc_create_user.yaml
drun run tcases/tc_create_user.yaml -env dev -secrets mask
```

## 登录提取 token

适用：登录接口调试，或作为后续 Case 的前置认证步骤。

`tcases/tc_login.yaml`

```yaml
config:
  name: 登录
  base_url: ${ENV(BASE_URL)}

steps:
  - name: 登录并提取 token
    request:
      method: POST
      path: /api/login
      body:
        username: ${ENV(USERNAME)}
        password: ${ENV(PASSWORD)}
    extract:
      token: $.data.token
      user_id: $.data.user_id
    check:
      - eq: [status_code, 200]
      - exists: [$.data.token, true]
```

运行：

```bash
drun check tcases/tc_login.yaml
drun run tcases/tc_login.yaml -env dev -secrets mask
```

## 登录后查询当前用户

适用：一个 Case 内串联多个 Request Step，并复用前一步 `extract` 的变量。

`tcases/tc_login_and_me.yaml`

```yaml
config:
  name: 登录后查询当前用户
  base_url: ${ENV(BASE_URL)}

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

  - name: 查询当前用户
    request:
      method: GET
      path: /api/me
      headers:
        Authorization: Bearer ${token}
    check:
      - eq: [status_code, 200]
      - exists: [$.data.id, true]
```

运行：

```bash
drun check tcases/tc_login_and_me.yaml
drun run tcases/tc_login_and_me.yaml -env dev -secrets mask
```

## 文件上传 multipart

适用：上传头像、附件、音频、图片等 multipart 接口。普通表单字段放 `request.data`，文件字段放 `request.files`。

`tcases/tc_upload_avatar.yaml`

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
    check:
      - eq: [status_code, 200]
      - exists: [$.data.url, true]
```

运行：

```bash
drun check tcases/tc_upload_avatar.yaml
drun run tcases/tc_upload_avatar.yaml -env dev -secrets mask
```

## 下载二进制并保存

适用：下载图片、音频、压缩包或模型生成文件。

`tcases/tc_download_file.yaml`

```yaml
config:
  name: 下载文件
  base_url: ${ENV(BASE_URL)}
  variables:
    file_id: demo-file

steps:
  - name: 下载文件 ${file_id}
    request:
      method: GET
      path: /api/files/${file_id}
      headers:
        Authorization: Bearer ${ENV(API_TOKEN)}
    response:
      save_body_to: artifacts/${file_id}.bin
    check:
      - eq: [status_code, 200]
      - gt: [$body_size, 0]
```

运行：

```bash
drun check tcases/tc_download_file.yaml
drun run tcases/tc_download_file.yaml -env dev -secrets mask
```

## 轮询接口

适用：异步任务状态查询。`repeat` 负责重复 Request Step，`sleep` 需要单独 Step。

`tcases/tc_poll_order.yaml`

```yaml
config:
  name: 轮询订单状态
  base_url: ${ENV(BASE_URL)}
  variables:
    order_id: demo-order
    retry_count: 3
    wait_ms: 1000

steps:
  - name: 查询订单状态
    repeat: ${retry_count}
    request:
      method: GET
      path: /api/orders/${order_id}
      headers:
        Authorization: Bearer ${ENV(API_TOKEN)}
    check:
      - eq: [status_code, 200]

  - name: 等待异步处理
    sleep: ${wait_ms}
```

运行：

```bash
drun check tcases/tc_poll_order.yaml
drun run tcases/tc_poll_order.yaml -env dev -secrets mask
```

## CSV 参数化

适用：使用 CSV 数据批量执行同一个 Case。

`tcases/tc_login_csv.yaml`

```yaml
config:
  name: CSV 批量登录
  base_url: ${ENV(BASE_URL)}
  parameters:
    - csv:
        path: data/login_cases.csv
        columns: [username, password, expected_status]
        header: true
        strip: true

steps:
  - name: 登录 $username
    request:
      method: POST
      path: /api/login
      body:
        username: $username
        password: $password
    check:
      - eq: [status_code, $expected_status]
```

运行：

```bash
drun check tcases/tc_login_csv.yaml
drun run tcases/tc_login_csv.yaml -env dev -secrets mask
```

注意：CSV 参数化当前不支持 `rows`、`where` 或 `filter` 之类的按行过滤 DSL。

## caseflow + invoke

适用：把登录、查询资料等拆成多个 Case，再用 suite 编排。

`tsuites/ts_login_flow.yaml`

```yaml
config:
  name: 登录后链路
  tags: [smoke, auth]

caseflow:
  - name: 登录
    invoke: test_login

  - name: 查询资料
    invoke: test_profile
```

运行：

```bash
drun check tsuites/ts_login_flow.yaml
drun run tsuites/ts_login_flow.yaml -env dev -secrets mask
```

## drun q 快速调试并保存 YAML

适用：先打通单接口，再保存成 Case 骨架。

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

保存后建议继续执行：

```bash
drun check tcases/tc_login_from_q.yaml
drun run tcases/tc_login_from_q.yaml -env dev -secrets mask
```

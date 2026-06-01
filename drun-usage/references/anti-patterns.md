# Anti-Patterns

适用于 Agent 生成或修复 drun YAML 前快速排除高风险错误写法。下面的错误写法不要作为推荐 YAML 输出。

## 不要写 request.url

错误：

```yaml
request:
  method: GET
  url: /api/users
```

正确：

```yaml
request:
  method: GET
  path: /api/users
```

原因：drun YAML 使用 `request.path`；`request.url` 会触发 `DRUN-YAML-003`。

## 不要写 request.json

错误：

```yaml
request:
  method: POST
  path: /api/users
  json:
    username: alice
```

正确：

```yaml
request:
  method: POST
  path: /api/users
  body:
    username: alice
```

原因：JSON 请求体写在 `request.body`；`request.json` 会触发 `DRUN-YAML-004`。

## 不要把 extract 或 check 缩进到 request 下

错误：

```yaml
steps:
  - name: 查询当前用户
    request:
      method: GET
      path: /api/me
      check:
        - eq: [status_code, 200]
      extract:
        user_id: $.data.id
```

正确：

```yaml
steps:
  - name: 查询当前用户
    request:
      method: GET
      path: /api/me
    extract:
      user_id: $.data.id
    check:
      - eq: [status_code, 200]
```

原因：`extract` 和 `check` 是 Request Step 的响应后处理字段，与 `request` 同级；缩进到 `request` 下会触发 `DRUN-YAML-005`。

## 不要写旧字段 validate

错误：

```yaml
validate:
  - eq: [status_code, 200]
```

正确：

```yaml
check:
  - eq: [status_code, 200]
```

原因：`validate` 已更名为 `check`，不再作为兼容 alias 接受，会触发 `DRUN-YAML-012`。

## 不要写旧套件 cases

错误：

```yaml
cases:
  - tc_login.yaml
  - tc_profile.yaml
```

正确：

```yaml
caseflow:
  - invoke: test_login
  - invoke: test_profile
```

原因：旧 `cases` 内联套件已不支持；多 Case 编排使用 `caseflow`。

## 不要写 loop 或 foreach

错误：

```yaml
steps:
  - name: 查询订单
    loop: 3
    request:
      method: GET
      path: /api/orders/${order_id}
```

正确：

```yaml
steps:
  - name: 查询订单
    repeat: 3
    request:
      method: GET
      path: /api/orders/${order_id}
```

原因：旧 `loop` / `foreach` 已废弃；重复执行 Step 使用 `repeat`。

## 不要混用 request.files 和 request.body

错误：

```yaml
request:
  method: POST
  path: /api/upload
  body:
    biz: profile
  files:
    avatar: ./data/avatar.png
```

正确：

```yaml
request:
  method: POST
  path: /api/upload
  data:
    biz: profile
  files:
    avatar: ./data/avatar.png
```

原因：multipart 普通表单字段放 `request.data`，文件字段放 `request.files`；`request.files` 不能与 `request.body` 并用。

## 不要写顶层 `parameters`

错误：

```yaml
parameters:
  - user_id: [1, 2]

steps:
  - name: 查询用户
    request:
      method: GET
      path: /api/users/$user_id
```

正确：

```yaml
config:
  parameters:
    - user_id: [1, 2]

steps:
  - name: 查询用户
    request:
      method: GET
      path: /api/users/$user_id
```

原因：参数化入口是 `config.parameters`；顶层 `parameters` 会触发 `DRUN-YAML-006`。

## 不要为 CSV 参数化虚构行过滤 DSL

错误：

```yaml
config:
  parameters:
    - csv:
        path: data/users.csv
        where: status == active
        rows: [3]
```

正确：

```yaml
config:
  parameters:
    - csv:
        path: data/users.csv
```

原因：CSV 参数化当前会展开全部数据行，不支持 `rows`、`where`、`filter` 之类按行过滤字段。需要少量数据时，建议拆小 CSV 或用普通数组参数化。

## 不要让 sleep Step 携带 request-only 字段

错误：

```yaml
steps:
  - name: 等待异步处理
    sleep: 1000
    check:
      - eq: [status_code, 200]
```

正确：

```yaml
steps:
  - name: 等待异步处理
    sleep: 1000
```

原因：Sleep Step 只能等待，不能携带 `check`、`extract`、`export`、`response`、`retry` 等 Request Step 字段。

## 不要写真实敏感值

错误：

```yaml
headers:
  Authorization: Bearer real-production-token
```

正确：

```yaml
headers:
  Authorization: Bearer ${ENV(API_TOKEN)}
```

原因：示例和排障内容不要暴露真实 token、Cookie、密码或密钥。运行命令优先使用 `-secrets mask`，导出 curl 时优先使用 `-redact Authorization,Cookie`。

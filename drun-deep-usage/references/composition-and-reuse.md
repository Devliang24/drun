# Composition And Reuse

适用于 `caseflow`、`invoke`、`invoke_case_name`、`invoke_case_names`、`repeat`、`sleep`、hooks、参数化。

## 登录后链路的典型拆法

把登录、查询资料、下单等场景拆成单独 case 文件，再用 `caseflow` 组织。

`testcases/test_login.yaml`

```yaml
config:
  name: 登录
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
      user_id: $.data.user_id
    validate:
      - eq: [status_code, 200]
```

`testcases/test_profile.yaml`

```yaml
config:
  name: 查询资料
  base_url: ${ENV(BASE_URL)}

steps:
  - name: 获取资料
    request:
      method: GET
      path: /api/users/${user_id}
      headers:
        Authorization: Bearer ${token}
    validate:
      - eq: [status_code, 200]
```

`testsuites/testsuite_login_flow.yaml`

```yaml
config:
  name: 登录后链路
  tags: [smoke, auth]

caseflow:
  - name: 登录并导出变量
    invoke: test_login

  - name: 等待会话落库
    sleep: 500

  - name: 连续查询资料
    invoke: test_profile
    repeat: 2
```

```bash
drun run testsuites/testsuite_login_flow.yaml -env dev -persist-env .env.runtime
```

## `invoke` 与变量传递

- `invoke` 会加载目标 YAML 并执行其中 case
- 被调用 case 的 `extract` 默认会自动回传到当前上下文
- 如果只想导出部分变量，可以在 invoke step 上显式写 `export`

```yaml
caseflow:
  - name: 登录后只导出 token
    invoke: test_login
    export:
      session_token: token
```

## `invoke_case_name` / `invoke_case_names`

当前实现已经支持这两个选择器，并会校验空字符串、重复项和互斥关系。

```yaml
caseflow:
  - name: 只跑一个命中的子用例
    invoke: imported_auth_flow
    invoke_case_name: 获取渠道 token

  - name: 跑多个命中的子用例
    invoke: imported_auth_flow
    invoke_case_names:
      - 获取渠道 token
      - 刷新渠道 token
```

重要边界：

- 只有当被 `invoke` 的目标文件能解析出多个 case 对象时，选择器才真正生效
- 普通手写单 case YAML 通常仍是一文件一用例，这时它和普通 `invoke` 没本质区别
- `invoke_case_names` 的执行顺序以源文件中的 case 顺序为准，不以你书写列表的顺序为准
- 未命中时会报 `requested=[...] available=[...]`

## `repeat` 与 `sleep`

`repeat` 支持整数或表达式字符串；重复执行时会自动注入：

- `repeat_index`
- `repeat_no`
- `repeat_total`

```yaml
steps:
  - name: 轮询订单状态
    repeat: ${retry_count}
    request:
      method: GET
      path: /api/orders/${order_id}
    validate:
      - eq: [status_code, 200]

  - name: 等待异步处理
    sleep: ${wait_ms}
```

实现约束：

- `repeat` 解析后必须是整数，且 `>= 0`
- `sleep` 单位是毫秒，解析后必须是有限数字
- `sleep` step 不能再带 `validate`、`extract`、`export`、`response`、`retry`

## hooks

case 级 hooks 要写在 `config.setup_hooks` / `config.teardown_hooks`，step 级 hooks 写在 step 本身。

```yaml
config:
  name: 带 hooks 的登录
  base_url: ${ENV(BASE_URL)}
  setup_hooks:
    - ${load_test_account()}
  teardown_hooks:
    - ${cleanup_test_account()}

steps:
  - name: 签名后登录
    setup_hooks:
      - ${sign_login_request()}
    request:
      method: POST
      path: /api/login
      body:
        username: ${ENV(USERNAME)}
        password: ${ENV(PASSWORD)}
    teardown_hooks:
      - ${remember_trace_id()}
```

hooks 项必须是 `${func(...)}` 这种表达式字符串。

## 参数化

参数化入口是 `config.parameters`，不是顶层 `parameters`。

```yaml
config:
  name: 批量登录
  base_url: ${ENV(BASE_URL)}
  parameters:
    - username-password:
        - [alice, pass1]
        - [bob, pass2]

steps:
  - name: 登录 $username
    request:
      method: POST
      path: /api/login
      body:
        username: $username
        password: $password
    validate:
      - eq: [status_code, 200]
```

CSV 也支持：

```yaml
config:
  name: CSV 批量上传
  base_url: ${ENV(BASE_URL)}
  parameters:
    - csv:
        path: data/upload_cases.csv
```

## 常见坑

- 不要再写旧的 `cases:` 内联套件；现在用 `caseflow`
- 不要写 `loop` / `foreach`，现在统一用 `repeat`
- 需要导出 invoke 结果时，优先用 `extract` + `export`

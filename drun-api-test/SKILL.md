---
name: drun-api-test
version: 1.2.0
description: 使用 Drun 框架编写 HTTP API 测试用例。当用户提供接口信息并说"写测试用例"、"创建测试"、"编写接口测试"、"生成测试"、"补充测试用例"、"增加测试场景"时触发。
allowed-tools: Bash(drun *), Write, Read, Glob, Grep
---

# Drun API 测试用例编写

使用 Drun 框架通过自然语言快速编写 HTTP API 测试用例。

## 核心概念

### 测试用例结构 (YAML)

```yaml
config:
  name: 测试名称
  base_url: ${ENV(BASE_URL)}  # 支持环境变量
  tags: [smoke, user]        # 标签用于筛选

steps:
  - name: 步骤名称
    request:
      method: GET|POST|PUT|DELETE|PATCH
      path: /api/path
      headers:                # 可选
        Content-Type: application/json
        Authorization: ${ENV(TOKEN)}
      params:                 # URL 查询参数（可选）
        page: 1
        limit: 10
      body:                   # 请求体（可选）
        username: test
        email: test@example.com
    extract:                  # 变量提取（可选）
      user_id: $.data.id
      token: $.data.token
    validate:                 # 断言（可选）
      - eq: [status_code, 200]
      - contains: [$.message, success]
      - regex: [$.data.email, ^[\w.-]+@[\w.-]+\.\w+$]
```

### 支持的断言类型 (共19种)

| 断言 | 示例 | 说明 |
|------|------|------|
| `eq` | `eq: [status_code, 200]` | 相等 |
| `ne` | `ne: [status_code, 500]` | 不等 |
| `contains` | `contains: [$.message, OK]` | 包含 |
| `not_contains` | `not_contains: [$.message, error]` | 不包含 |
| `regex` | `regex: [$.email, ^\w+@]` | 正则匹配 |
| `lt` | `lt: [$.count, 100]` | 小于 |
| `le` | `le: [$.count, 10]` | 小于等于 |
| `gt` | `gt: [$.count, 0]` | 大于 |
| `ge` | `ge: [$.count, 1]` | 大于等于 |
| `len_eq` | `len_eq: [$.items, 10]` | 长度等于 |
| `len_gt` | `len_gt: [$.items, 0]` | 长度大于 |
| `len_ge` | `len_ge: [$.items, 1]` | 长度大于等于 |
| `len_lt` | `len_lt: [$.items, 100]` | 长度小于 |
| `len_le` | `len_le: [$.items, 10]` | 长度小于等于 |
| `in` | `in: [status_code, [200, 201]]` | 在列表中 |
| `not_in` | `not_in: [status_code, [400, 500]]` | 不在列表中 |
| `contains_all` | `contains_all: [$.tags, ["smoke", "user"]]` | 列表包含所有元素 |
| `match_regex_all` | `match_regex_all: [$.emails, ^[\w.-]+@]` | 所有元素都匹配正则 |
| `exists` | `exists: [$.data.id, true]` | 字段存在 |

### 环境变量

```yaml
# .env 文件
BASE_URL=https://api.example.com
TOKEN=your-token-here
USER_USERNAME=test
```

## 工作流程

### 场景 1: 根据接口描述生成测试

1. **收集接口信息**:
   - HTTP 方法 (GET/POST/PUT/DELETE)
   - 接口路径 (/api/users)
   - 请求参数/Body
   - 预期响应

2. **生成测试用例**:
   - 写入到 `testcases/` 目录
   - 文件名格式: `test_<模块>_<操作>.yaml`

3. **验证测试**:
   ```bash
   drun check testcases/test_user_login.yaml
   drun run testcases/test_user_login.yaml --env dev
   ```

### 场景 2: 从 cURL 命令转换

```bash
# 转换 cURL 为 Drun 测试用例
drun convert-curl request.curl --outfile testcases/login.yaml
```

### 场景 3: 数据驱动测试

```yaml
config:
  name: 批量用户注册
  base_url: ${ENV(BASE_URL)}
  parameters:
    - csv:
        path: data/users.csv

steps:
  - name: Register $username
    request:
      method: POST
      path: /users/register
      body:
        username: $username
        email: $email
        role: $role
    validate:
      - eq: [status_code, 200]
```

CSV 文件格式:
```csv
username,email,role
alice,alice@example.com,admin
bob,bob@example.com,user
```

### 场景 4: 测试套件（多用例串联）

```yaml
config:
  name: 用户完整流程
  tags: [e2e]

caseflow:
  - name: 注册用户
    invoke: test_user_register

  - name: 登录
    variables:
      user_id: $user_id  # 引用上一步提取的变量
    invoke: test_user_login

  - name: 获取用户信息
    variables:
      token: $token
    invoke: test_user_info
```

## 项目结构

```
drun_project/
├── testcases/           # 测试用例
│   ├── test_login.yaml
│   ├── test_user_*.yaml
│   └── test_*.yaml
├── testsuites/          # 测试套件
│   └── testsuite_*.yaml
├── data/                # 测试数据 (CSV/Excel)
│   └── users.csv
├── converts/            # 格式转换源文件
│   ├── sample.curl
│   └── import_*.har
├── reports/             # HTML/JSON 报告输出
├── logs/               # 日志文件输出
├── snippets/            # 代码片段
├── .env                # 环境变量（必需）
├── Dhook.py            # 自定义函数（可选）
└── .gitignore          # Git 忽略规则
```

### 多环境配置

Drun 支持多环境 `.env` 文件：

| 文件 | 用途 | 指定方式 |
|------|------|----------|
| `.env` | 默认环境 | `drun run --env dev` |
| `.env.dev` | 开发环境 | `drun run --env dev` |
| `.env.test` | 测试环境 | `drun run --env test` |
| `.env.prod` | 生产环境 | `drun run --env prod` |

```bash
# 运行指定环境
drun run testcases --env dev
drun run testcases --env test
drun run testcases --env prod --mask-secrets
```

### 标签筛选表达式

`-k` 参数支持布尔表达式：

```bash
# 只运行 smoke 标签
drun run testcases -k "smoke"

# smoke 且不是 slow
drun run testcases -k "smoke and not slow"

# smoke 或 regression
drun run testcases -k "smoke or regression"

# 组合表达式
drun run testcases -k "(smoke or regression) and not slow"
```

## 测试套件进阶 (caseflow)

### 变量传递

caseflow 中可以通过 `variables` 向被调用的用例传递变量：

```yaml
config:
  name: 完整用户流程
  tags: [e2e]

caseflow:
  - name: 注册用户
    invoke: test_user_register

  - name: 登录并传递参数
    variables:
      username: alice              # 传递固定值
      expected_role: admin         # 传递固定值
      base_url: $base_url         # 传递上一个用例提取的变量
    invoke: test_user_login
```

被调用用例 `test_user_login.yaml` 可以使用这些变量：

```yaml
config:
  name: 用户登录测试
  base_url: ${ENV(BASE_URL)}

steps:
  - name: 使用传入的用户名登录
    request:
      method: POST
      path: /api/login
      body:
        username: $username  # 使用 caseflow 传递的变量
        role: $expected_role
```

### Case/Suite 级别钩子

```yaml
config:
  name: 带套件钩子的测试
  suite_setup_hooks:      # 整个套件开始前执行
    - ${setup_hook_prepare_db()}
  suite_teardown_hooks:   # 整个套件结束后执行
    - ${teardown_hook_cleanup_db()}
  setup_hooks:           # 每个用例开始前执行
    - ${setup_hook_clear_cache()}
  teardown_hooks:         # 每个用例结束后执行
    - ${teardown_hook_log_result($response)}
```

### 数据库断言钩子

在 `Dhook.py` 中定义数据库断言函数：

```python
# Dhook.py
from drun.db.database_proxy import get_db

def setup_hook_assert_sql(
    identifier: Any,
    *,
    query: str | None = None,
    db_name: str = "main",
    role: str | None = None,
) -> dict:
    """断言 SQL 查询返回非空结果"""
    proxy = get_db().get(db_name, role)
    sql = query or f"SELECT * FROM users WHERE id = {identifier}"
    if not proxy.query(sql):
        raise AssertionError(f"SQL returned empty: {sql}")
    return {"sql_assert_ok": True}
```

使用：

```yaml
steps:
  - name: 创建订单
    setup_hooks:
      - ${setup_hook_assert_sql($order_id, db_name="orders")}
    request:
      method: POST
      path: /api/orders
      body:
        id: $order_id
```

## 敏感信息处理

### 脱敏输出

```bash
# 运行测试并自动脱敏敏感信息
drun run testcases --env prod --mask-secrets

# 显示敏感信息（仅在本地开发环境使用）
drun run testcases --env dev --reveal-secrets
```

### 转存 YAML 时脱敏

```bash
# 将 cURL 转换为 YAML 并脱敏
drun convert-curl request.curl --outfile test.yaml --mask-secrets
```

### 请求级别配置

```yaml
config:
  name: 带配置的测试
  base_url: ${ENV(BASE_URL)}
  timeout: 30          # 请求超时时间（秒）
  tags: [smoke]

steps:
  - name: 可能失败的请求
    retry: 3           # 重试次数
    retry_backoff: 1.0  # 重试间隔（秒），会指数退避
    request:
      method: GET
      path: /api/unstable
    validate:
      - eq: [status_code, 200]
```

### 响应类型处理

Drun 自动处理 JSON 响应，也可处理其他格式：

```yaml
steps:
  - name: JSON 响应
    request:
      method: GET
      path: /api/json
    extract:
      user_name: $.data.name
      user_email: $.data.email

  - name: XML 响应
    request:
      method: GET
      path: /api/xml
    extract:
      title: $.title

  - name: HTML 响应
    request:
      method: GET
      path: /api/html
    validate:
      - contains: [$.body, "欢迎"]
```

## 高级特性

### SSE/流式响应

Drun 支持 Server-Sent Events 流式响应测试：

```yaml
steps:
  - name: 订阅实时数据流
    request:
      method: GET
      path: /api/stream/events
      headers:
        Accept: text/event-stream
    extract:
      event_count: $.stream_summary.total_events
    validate:
      - gt: [$.stream_summary.total_events, 0]
      - exists: [$.stream_events.0.data]
```

### 文件上传

```yaml
steps:
  - name: 上传文件
    request:
      method: POST
      path: /api/upload
      headers:
        Content-Type: multipart/form-data
      files:
        file:
          path: ./data/test.pdf
          content_type: application/pdf
    validate:
      - eq: [status_code, 200]
      - contains: [$.message, success]
```

### 文件下载

```yaml
steps:
  - name: 下载文件
    request:
      method: GET
      path: /api/download/$file_id
      stream: true  # 流式下载
    extract:
      content_type: headers.Content-Type
      file_size: $.stream_summary.total_bytes
    validate:
      - contains: [$.content_type, application/pdf]
      - gt: [$.file_size, 0]
```

## 报告与通知

### 报告类型

```bash
# HTML 报告（可视化）
drun run testcases --env dev --html reports/report.html

# JSON 报告（便于程序解析）
drun run testcases --env dev --json reports/report.json

# Allure 报告（适合 CI 集成）
drun run testcases --env dev --allure reports/allure-results
```

### 通知渠道

测试完成后自动通知：

```bash
# 启用通知
drun run testcases --env prod --notify feishu,dingtalk,email
```

需要配置环境变量：

```bash
# 飞书通知
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx

# 钉钉通知
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx

# 邮件通知
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USER=noreply@example.com
SMTP_PASS=your-password
MAIL_FROM=noreply@example.com
MAIL_TO=qa@example.com,dev@example.com
```

## 常用命令

| 操作 | 命令 |
|------|------|
| 初始化项目 | `drun init my_project` |
| 初始化项目(带CI) | `drun init my_project --ci` |
| 运行所有测试 | `drun run testcases --env dev` |
| 运行单个用例 | `drun run testcases/login.yaml --env dev` |
| 按标签筛选 | `drun run testcases -k "smoke and not slow" --env dev` |
| 检查语法 | `drun check testcases/` |
| 生成 HTML 报告 | `drun run testcases --env dev --html reports/report.html` |
| 生成 JSON 报告 | `drun run testcases --env dev --json reports/report.json` |
| 生成 Allure 报告 | `drun run testcases --env dev --allure reports/allure-results` |
| 转换 cURL | `drun convert-curl curl.txt --outfile test.yaml` |
| 导入 Postman | `drun import-postman collection.json --outdir testcases/` |
| 转换 OpenAPI | `drun convert-openapi openapi.yaml --outdir testcases/` |
| 脱敏运行 | `drun run testcases --env prod --mask-secrets` |
| 启用通知 | `drun run testcases --env prod --notify feishu,dingtalk,email` |

## 模板函数 (Dhook.py)

Drun 提供内置函数，也可在 `Dhook.py` 中自定义:

```python
# 常用内置函数
${ts()}           # 当前时间戳
${uid()}          # UUID
${short_uid(8)}   # 短 UUID

# 自定义函数示例 (Dhook.py)
def md5(text: str) -> str:
    import hashlib
    return hashlib.md5(text.encode()).hexdigest()

# 使用: ${md5($password)}
```

## 快速开始

1. **初始化项目**:
   ```bash
   drun init api_tests
   cd api_tests
   ```

2. **配置环境变量** (.env):
   ```bash
   BASE_URL=https://api.example.com
   TOKEN=your-token
   ```

3. **编写测试用例**:
   ```yaml
   # testcases/test_login.yaml
   config:
     name: 登录接口
     base_url: ${ENV(BASE_URL)}

   steps:
     - name: POST login
       request:
         method: POST
         path: /api/login
         body:
           username: ${ENV(USER)}
           password: ${ENV(PASSWORD)}
       extract:
         token: $.data.token
       validate:
         - eq: [status_code, 200]
         - exists: [$.data.token]
   ```

4. **运行测试**:
   ```bash
   drun run testcases/test_login.yaml --env dev
   ```

## 钩子函数 (Hooks)

### 钩子类型

| 位置 | 钩子 | 说明 |
|------|------|------|
| Case 级别 | `setup_hooks` | 用例开始前执行 |
| Case 级别 | `teardown_hooks` | 用例结束后执行 |
| Suite 级别 | `suite_setup_hooks` | 整个套件开始前执行 |
| Suite 级别 | `suite_teardown_hooks` | 整个套件结束后执行 |
| Step 级别 | `setup_hooks` | 步骤开始前执行 |
| Step 级别 | `teardown_hooks` | 步骤结束后执行 |

### 使用示例

```yaml
config:
  name: 带钩子的测试
  setup_hooks:
    - ${setup_hook_sign_request($request)}  # 请求签名
  teardown_hooks:
    - ${cleanup_after_test($response)}

steps:
  - name: 创建用户
    setup_hooks:
      - ${validate_request_body($body)}
    request:
      method: POST
      path: /api/users
      body:
        username: test
    teardown_hooks:
      - ${log_response($response)}
```

### Dhook.py 中定义钩子函数

```python
# Dhook.py
def setup_hook_sign_request(request: dict, variables: dict = None, env: dict = None) -> dict:
    """请求签名钩子"""
    import hmac
    import hashlib
    import time

    secret = env.get("APP_SECRET", "default-secret").encode()
    method = request.get("method", "GET")
    url = request.get("url", "")
    timestamp = str(int(time.time()))

    message = f"{method}|{url}|{timestamp}".encode()
    signature = hmac.new(secret, message, hashlib.sha256).hexdigest()

    headers = request.setdefault("headers", {})
    headers["X-Timestamp"] = timestamp
    headers["X-Signature"] = signature
    return {"last_signature": signature}
```

## 认证处理

### Bearer Token

```yaml
steps:
  - name: 获取用户信息
    request:
      method: GET
      path: /api/user/info
      headers:
        Authorization: Bearer ${TOKEN}
```

### Cookie 会话

```yaml
steps:
  - name: 登录获取 Cookie
    request:
      method: POST
      path: /api/login
      body:
        username: ${USER}
        password: ${PASS}
    extract:
      session_cookie: headers.Set-Cookie

  - name: 使用 Cookie 访问
    request:
      method: GET
      path: /api/profile
      cookies:
        session: $session_cookie
```

### HMAC 签名

在 `Dhook.py` 中定义签名函数，参考上方钩子函数示例。

## 调试与排错

### 常见问题

1. **变量未解析**: 检查 `${ENV(VAR)}` 语法，确保 .env 文件中存在该变量
2. **JMESPath 提取失败**: 确认响应 JSON 结构，使用 `exists` 断言先验证字段存在
3. **Hook 未执行**: 检查函数名、语法，确认 `Dhook.py` 在项目根目录
4. **断言失败**: 使用 `--verbose` 或查看 HTML 报告定位具体失败步骤

### 调试技巧

```bash
# 检查测试用例语法
drun check testcases/test_login.yaml

# 运行并显示详细输出
drun run testcases/test_login.yaml --env dev -v

# 生成 HTML 报告查看详情
drun run testcases --env dev --html reports/report.html
```

## 用户使用场景

以下是用户可能说的话，对应可以生成的测试用例类型：

### 单接口测试

| 用户说 | 生成内容 |
|--------|----------|
| "帮我测试登录接口，用户名是 admin，密码是 123456" | POST /api/login，body 包含 username/password，断言 status_code=200 和 token 非空 |
| "写一个获取用户列表的测试用例" | GET /api/users，断言返回列表长度 > 0 |
| "测试新增用户接口，用户邮箱是 test@example.com" | POST /api/users，body 包含 email，断言创建成功 |
| "帮我测试删除用户接口，用户ID是 123" | DELETE /api/users/123，断言 status_code=204 |

### 数据驱动测试

| 用户说 | 生成内容 |
|--------|----------|
| "用这组测试数据跑一遍注册接口" | 读取 CSV，生成带 parameters 的测试用例，遍历每一行数据 |
| "批量测试多个用户的登录" | 从 CSV 读取用户名密码列表，循环执行登录接口 |
| "用 Excel 里的数据测试" | 读取 Excel 文件，转换为 CSV 格式用于数据驱动 |

### 业务流程测试

| 用户说 | 生成内容 |
|--------|----------|
| "测试完整的用户注册-登录-获取信息流程" | caseflow 串联 test_register → test_login → test_get_user_info |
| "写一个订单创建到支付的完整流程测试" | caseflow 串联 test_create_order → test_pay_order |
| "帮我测试用户从登录到下单的全链路" | caseflow 串联多个用例，变量按流程传递 |

### 条件断言测试

| 用户说 | 生成内容 |
|--------|----------|
| "登录后返回的 token 要校验非空" | extract: token: $.data.token + validate: - exists: [$.data.token, true] |
| "列表接口要校验返回至少有一条数据" | validate: - len_gt: [$.data.items, 0] |
| "校验返回的邮箱格式正确" | validate: - regex: [$.data.email, ^[\w.-]+@[\w.-]+\.\w+$] |
| "确保订单状态是已支付" | validate: - eq: [$.data.status, paid] |

### 认证相关测试

| 用户说 | 生成内容 |
|--------|----------|
| "测试需要 Token 的接口" | 在 headers 添加 Authorization: Bearer ${TOKEN} |
| "帮我测试带 Cookie 的会话接口" | 从登录接口 extract Set-Cookie，下一步使用 cookies 字段 |
| "测试带 HMAC 签名的接口" | 在 Dhook.py 定义签名函数，setup_hooks 调用 |

### 异常场景测试

| 用户说 | 生成内容 |
|--------|----------|
| "测试密码错误时返回 401" | POST /api/login 密码错误，validate: - eq: [status_code, 401] |
| "校验不存在的用户ID返回 404" | GET /api/users/99999，validate: - eq: [status_code, 404] |
| "测试必填参数缺失时返回 400" | POST /api/users body 为空，validate: - eq: [status_code, 400] |
| "测试重复注册返回 409" | 两次调用同一注册接口，第二次 validate: - eq: [status_code, 409] |

### cURL 转换

| 用户说 | 生成内容 |
|--------|----------|
| "把这个 cURL 命令转成测试用例" | drun convert-curl 转换并生成 YAML |
| "帮我导入这个 Postman 集合" | 使用 drun import-postman 转换 |
| "从 OpenAPI 规范生成测试" | drun convert-openapi 转换 |

### 环境相关

| 用户说 | 生成内容 |
|--------|----------|
| "在测试环境跑一遍" | drun run testcases --env test |
| "用生产环境配置跑" | drun run testcases --env prod --mask-secrets |
| "生成 HTML 报告" | drun run testcases --env dev --html reports/report.html |
| "生成 JSON 格式报告" | drun run testcases --env dev --json reports/report.json |
| "跑完发飞书通知" | drun run testcases --notify feishu |
| "测试完成后发邮件通知" | drun run testcases --notify email |

### 标签筛选

| 用户说 | 生成内容 |
|--------|----------|
| "只跑冒烟测试" | drun run testcases -k "smoke" |
| "跑 smoke 和 regression 标签" | drun run testcases -k "smoke or regression" |
| "排除 slow 标签" | drun run testcases -k "not slow" |
| "组合标签筛选" | drun run testcases -k "(smoke or regression) and not slow" |

### 导入与转换

| 用户说 | 生成内容 |
|--------|----------|
| "把这个 cURL 命令转成测试用例" | drun convert-curl 转换并生成 YAML |
| "帮我导入这个 Postman 集合" | drun import-postman collection.json |
| "从 OpenAPI 规范生成测试" | drun convert-openapi openapi.yaml |
| "导入 HAR 文件" | drun import-har request.har --outfile testcases/ |
| "把 Postman 环境变量转过来" | drun import-postman --env postman_env.json |

| 用户说 | 生成内容 |
|--------|----------|
| "帮我初始化一个测试项目" | drun init 新项目，创建完整目录结构 |
| "创建一个新的 drun 测试环境" | drun init，生成 testcases/data/converts 等目录 |
| "帮我搭建 drun 项目框架" | drun init，生成示例用例和配置文件 |
| "初始化一个 API 测试项目" | drun init my_api_tests，包含示例测试用例 |
| "新建项目，带 CI 配置" | drun init --ci，生成 GitHub Actions workflow |

### 补充/维护测试用例

| 用户说 | 生成内容 |
|--------|----------|
| "给登录接口加个 smoke 标签" | 在现有用例的 tags 添加 smoke |
| "补充登录失败的情况" | 新增步骤或新调用 validate: - eq: [status_code, 401] |
| "给这个接口加个超时时间" | 在 request 中添加 timeout 配置 |
| "补充 token 过期的断言" | 添加 validate: - exists: [$.data.token] |
| "增加一个获取用户详情的步骤" | 在 steps 中添加新的步骤 |
| "帮我完善用例的错误处理" | 添加断言校验错误码和错误信息格式 |

### 批量操作

| 用户说 | 生成内容 |
|--------|----------|
| "跑一下所有的登录用例" | drun run testcases -k "login" --env dev |
| "执行带有 smoke 标签的用例" | drun run testcases -k "smoke" --env dev |
| "只跑冒烟测试" | drun run testcases -k "smoke" --env test |
| "运行 testcases 目录下所有用例" | drun run testcases --env dev |
| "执行 testsuite_smoke 套件" | drun run testsuites/testsuite_smoke.yaml --env dev |

### 检查与验证

| 用户说 | 生成内容 |
|--------|----------|
| "检查一下用例语法对不对" | drun check testcases/test_login.yaml |
| "帮我看看这个用例有没有问题" | drun check 分析并指出语法错误 |
| "校验测试数据文件" | 检查 CSV 格式和必填字段 |
| "验证一下环境变量配置" | 检查 .env 文件是否包含必需变量 |

## 注意事项

1. **文件命名**: 使用 `test_<功能>_<场景>.yaml` 格式
2. **标签使用**: 合理标签便于筛选，如 `[smoke, regression, e2e]`
3. **变量提取**: 使用 JMESPath 语法，如 `$.data.id`
4. **环境分离**: 不同环境使用不同 .env 文件，如 `.env.dev`, `.env.prod`

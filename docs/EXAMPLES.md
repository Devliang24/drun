# 💻 实战示例

以下示例演示从登录流程、E2E 购物流程、参数化、请求签名 Hooks 到格式转换/导出等常见用法，以及测试套件（Testsuite，引用型）的组织方式。

> 提示：`drun run ... --env-file dev` 会自动读取 `.env.dev`；也可以继续省略该参数使用默认 `.env`。

### 示例 1：登录流程 + Token 自动注入

```yaml
config:
  name: 登录并访问受保护资源
  base_url: ${ENV(BASE_URL)}
  variables:
    username: ${ENV(USER_USERNAME)}
    password: ${ENV(USER_PASSWORD)}

steps:
  - name: 用户登录
    request:
      method: POST
      url: /api/v1/auth/login
      body:
        username: $username
        password: $password
    extract:
      token: $.data.access_token        # 提取 token
      user_id: $.data.user.id
    validate:
      - eq: [status_code, 200]
      - eq: [$.success, true]

  - name: 获取用户资料
    request:
      method: GET
      url: /api/v1/users/$user_id
      # Authorization 头自动注入：Bearer {token}
    validate:
      - eq: [status_code, 200]
      - eq: [$.data.id, $user_id]
```

### 示例 2：E2E 购物流程

> 说明：此示例使用了项目自带的 `uid()` 和 `short_uid()` 辅助函数（定义在根目录 `drun_hooks.py`），用于生成唯一的测试数据。

```yaml
config:
  name: E2E 购物流程
  base_url: ${ENV(BASE_URL)}
  tags: [e2e, critical]
  variables:
    # 动态生成测试数据，避免冲突
    username: user_${short_uid(8)}
    email: ${uid()}@example.com
    password: Test@${short_uid(6)}
    shipping_address: ${short_uid(12)} Test Street

steps:
  - name: 注册新用户
    request:
      method: POST
      url: /api/v1/auth/register
      body:
        username: $username
        email: $email
        password: $password
        full_name: Test User
        shipping_address: $shipping_address
    extract:
      username: $.data.username

  - name: 登录
    request:
      method: POST
      url: /api/v1/auth/login
      body:
        username: $username
        password: $password
    extract:
      token: $.data.access_token

  - name: 浏览商品
    request:
      method: GET
      url: /api/v1/products/
    extract:
      product_id: $.data.items[0].id

  - name: 加入购物车
    request:
      method: POST
      url: /api/v1/cart/items
      body:
        product_id: $product_id
        quantity: 2
    validate:
      - eq: [status_code, 201]
      - eq: [$.data.items[0].quantity, 2]

  - name: 下单
    request:
      method: POST
      url: /api/v1/orders/
      body:
        shipping_address: $shipping_address
    extract:
      order_id: $.data.order_id
    validate:
      - eq: [status_code, 201]
      - gt: [$.data.order_id, 0]
```

### 示例 3：参数化测试（压缩模式）

Drun 支持压缩（zipped）参数化，提供单变量列表和多变量绑定两种用法。以下从简单到复杂展示参数化的典型应用场景。

#### 3.1 单变量列表（技术演示）

最简单的参数化形式，适合单个参数的多个取值。

```yaml
config:
  name: 简单参数化示例
  base_url: ${ENV(BASE_URL)}
  parameters:
    - quantity: [1, 2, 5]
    # 生成 3 个测试实例

steps:
  - name: 测试不同数量
    request:
      method: GET
      url: /api/products?qty=$quantity
    validate:
      - eq: [status_code, 200]
```

**参考示例：** `examples/test_params_zipped.yaml`、`testcases/test_e2e_purchase.yaml:11-12`

#### 3.2 多变量绑定（实战：登录场景）

使用**连字符 `-`** 连接变量名，将多个参数绑定为一组，每组参数对应一个测试实例。

```yaml
config:
  name: 登录测试（正常+异常）
  base_url: ${ENV(BASE_URL)}
  tags: [auth, params]
  parameters:
    - username-password-expected_status-expected_message:
        - [alice, pass123, 200, 登录成功]        # 正常登录
        - [bob, wrong_pwd, 401, 登录失败]        # 密码错误
        - [unknown_user, any, 401, 登录失败]     # 用户不存在
    # 生成 3 个测试实例，每组 4 个参数成对使用

steps:
  - name: 尝试登录
    request:
      method: POST
      url: /api/v1/auth/login
      body:
        username: $username
        password: $password
    validate:
      - eq: [status_code, $expected_status]
      - eq: [$.message, $expected_message]
```

**优势：**
- 正常和异常场景集中管理
- 预期结果与输入参数绑定，避免遗漏
- 一次定义，自动生成多个测试实例

**参考示例：** `testcases/test_login_zipped.yaml`、`testcases/test_register_zipped.yaml`

#### 3.3 多组笛卡尔积（高级：多环境测试）

定义多个压缩组时，Drun 会自动生成笛卡尔积组合，适合跨环境、跨区域的全面测试。

```yaml
config:
  name: 多环境健康检查
  tags: [smoke, health]
  parameters:
    - env: [dev, staging, prod]       # 3 个环境
    - region: [us, eu, asia]          # 3 个区域
    # 生成 3 × 3 = 9 个测试实例

steps:
  - name: 检查服务健康
    variables:
      full_url: https://${env}-${region}.example.com
    request:
      method: GET
      url: ${full_url}/health
    validate:
      - eq: [status_code, 200]
      - eq: [$.status, healthy]
      - contains: [$.data.region, $region]
```

**生成的 9 个实例：**
- (dev, us), (dev, eu), (dev, asia)
- (staging, us), (staging, eu), (staging, asia)
- (prod, us), (prod, eu), (prod, asia)

#### 3.4 CSV 数据驱动（批量账号/配置）

当测试数据来源于表格或已有账号清单时，可以使用 CSV 文件作为参数源。Drun 会自动解析文件，每一行生成一个参数字典。

```yaml
config:
  name: 登录测试（CSV）
  base_url: ${ENV(BASE_URL)}
  parameters:
    - csv:
        path: data/login_users.csv   # 相对于当前 YAML 的路径
        strip: true

steps:
  - name: 尝试登录
    request:
      method: GET
      url: /login?username=$username&password=$password&env=$env
    validate:
      - eq: [status_code, 200]
```

CSV 默认首行为表头，可通过如下配置做定制：

- `columns`: 当文件没有表头时指定列名（示例：`[username, password, env]`）。
- `header`: 显式控制是否读取表头，默认 `true`。
- `delimiter`: 分隔符，默认 `,`。
- `encoding`: 文件编码，默认 `utf-8`。
- `strip`: 是否自动裁剪每个单元格的首尾空白，默认 `false`。

**示例文件：** `examples/basic-examples/data/login_users.csv`

**适用场景：**
- 跨环境 × 跨区域的全面覆盖
- 配置矩阵测试（数据库类型 × 操作系统版本）
- 兼容性测试（浏览器 × 操作系统）

#### 📝 参数化最佳实践

| 场景 | 推荐用法 | 示例 |
|------|---------|------|
| 单个参数多个值 | 单变量列表 | `- quantity: [1, 2, 5]` |
| 成对参数 | 多变量绑定 | `- username-password: [[alice, pass123], [bob, secret456]]` |
| 全面覆盖 | 多组笛卡尔积 | `- env: [dev, prod]` + `- region: [us, eu]` |
| 正常+异常 | 多变量绑定+预期结果 | `- input-expected_status: [[valid, 200], [invalid, 400]]` |

**注意事项：**
- 变量名用**连字符 `-`** 分隔（不要用下划线或空格）
- 多变量绑定时，每组值的数量必须与变量名数量一致
- 笛卡尔积会快速增加测试实例数量，注意控制规模

### 示例 4：请求签名 Hooks

drun_hooks.py：

```python
import time
import hmac
import hashlib

def setup_hook_hmac_sign(request: dict, variables: dict = None, env: dict = None) -> dict:
    """HMAC-SHA256 签名"""
    secret = env.get('APP_SECRET', '').encode()
    method = request.get('method', 'GET')
    url = request.get('url', '')
    timestamp = str(int(time.time()))

    message = f"{method}|{url}|{timestamp}".encode()
    signature = hmac.new(secret, message, hashlib.sha256).hexdigest()

    headers = request.setdefault('headers', {})
    headers['X-Timestamp'] = timestamp
    headers['X-HMAC'] = signature

    return {'last_signature': signature}
```

test_signed_api.yaml：

```yaml
config:
  name: 签名 API 测试
  base_url: ${ENV(BASE_URL)}
  setup_hooks:
    - ${setup_hook_hmac_sign($request)}

steps:
  - name: 访问签名接口
    request:
      method: GET
      url: /api/secure/data
      # X-Timestamp 和 X-HMAC 头自动添加
    validate:
      - eq: [status_code, 200]
```

### 示例 5：格式转换与导出工作流

演示从浏览器/Postman 到 Drun YAML 的完整转换流程。

注意：`drun convert` 要求“文件在前，选项在后”，且不支持无选项转换（至少提供 `--outfile`/`--split-output`/`--redact`/`--placeholders` 等其一）。

#### 场景 1：从浏览器 HAR 快速生成测试

```bash
# 1. 在浏览器中操作（F12 开发者工具）
#    - 打开 Network 面板
#    - 执行业务操作（登录、下单等）
#    - 右键 → Save all as HAR with content

# 2. 导入为测试用例（Case，每个请求一个文件）
drun convert recording.har --split-output \
  --case-name "浏览器录制" \
  --base-url https://api.example.com

# 输出：
# [CONVERT] Wrote YAML for '浏览器录制 - Step 1' to recording_step1.yaml
# [CONVERT] Wrote YAML for '浏览器录制 - Step 2' to recording_step2.yaml
# ...

# 3. 运行测试验证
drun run recording_step1.yaml --env-file .env

# 4. 导出为 cURL 命令调试
drun export curl recording_step1.yaml --with-comments
```

#### 场景 2：Postman Collection 迁移

```bash
# 1. 从 Postman 导出 Collection（JSON 格式）

# 2. 转换为 YAML（合并为一个测试套件）
drun convert api_collection.json \
  --outfile testcases/test_api_suite.yaml \
  --case-name "API 完整测试"

# 3. 编辑 YAML 添加断言和提取逻辑
# （此时可以利用 Drun 的变量提取、参数化等高级特性）

# 4. 运行测试
drun run testcases/test_api_suite.yaml --env-file .env --html reports/report.html
```

#### 场景 3：cURL 命令转测试用例（Case）

```bash
# 1. 复制浏览器 Network 面板中的 "Copy as cURL"
# 或从 API 文档复制 curl 示例

# 2. 保存到文件
cat > api_requests.curl <<'EOF'
curl 'https://api.example.com/auth/login' \
  -H 'Content-Type: application/json' \
  --data-raw '{"username":"admin","password":"secret"}'

curl 'https://api.example.com/users/me' \
  -H 'Authorization: Bearer TOKEN_HERE' \
  -H 'Accept: application/json'
EOF

# 3. 转换为 YAML
drun convert api_requests.curl \
  --outfile testcases/test_auth_flow.yaml \
  --case-name "认证流程测试"

# 4. 编辑 YAML 添加 token 提取
# steps[0].extract: { token: $.data.access_token }
# steps[1].request.headers: { Authorization: "Bearer $token" }

# 5. 运行测试
drun run testcases/test_auth_flow.yaml --env-file .env
```

#### 场景 4：测试用例分享与调试

```bash
# 团队成员 A：创建测试用例（Case）
cat > testcases/test_new_feature.yaml <<'EOF'
config:
  name: 新功能测试
  base_url: ${ENV(BASE_URL)}
steps:
  - name: 创建资源
    request:
      method: POST
      url: /api/resources
      body: {name: "test", type: "demo"}
    extract:
      resource_id: $.data.id
    validate:
      - eq: [status_code, 201]
EOF

# 导出为 cURL 命令分享给团队成员 B
drun export curl testcases/test_new_feature.yaml \
  --outfile share.curl \
  --with-comments

# 团队成员 B：收到 cURL 命令后
# 方式 1：直接在终端执行验证
bash share.curl

# 方式 2：导入为自己的测试用例（Case）
drun convert share.curl --outfile my_tests/imported.yaml
```

工作流优势：
- 🚀 快速上手：从现有工具（浏览器、Postman）无缝迁移
- 🔄 双向转换：YAML ↔ curl 灵活互转
- 🧪 渐进增强：先导入基础用例，再添加断言、提取、参数化
- 👥 团队协作：通过 cURL 命令快速分享请求示例

---

## 🧩 测试套件（Testsuite，引用用例）

除内联的 Suite（在一个文件的 `cases:` 中直接编写多个用例）外，还支持“引用型 Testsuite”：在 `testsuites/` 目录下的 Testsuite 文件通过 `testcases:` 引用 `testcases/` 下的单用例文件，并可在条目级覆盖名称、注入变量或提供参数化。

示例（`testsuites/testsuite_smoke.yaml`）：

```yaml
config:
  name: 冒烟测试套件
  base_url: ${ENV(BASE_URL)}
  tags: [smoke]

testcases:
  - name: 健康检查
    testcase: testcases/test_health.yaml
  - name: 目录基础
    testcase: testcases/test_catalog.yaml
```

示例（带条目级参数化）：

```yaml
config:
  name: 回归测试套件
  base_url: ${ENV(BASE_URL)}
  tags: [regression]

testcases:
  - name: 端到端下单（参数化）
    testcase: testcases/test_e2e_purchase.yaml
    parameters:
      quantity: [1, 2]
```

运行：

```bash
drun run testsuites --env-file .env
drun run testsuites -k "smoke" --env-file .env
```

说明：
- Testsuite 文件与内联 Suite 文件可共存。推荐优先使用 Testsuite（引用型），Suite（内联型）作为兼容形式继续支持。
- 条目级 `variables` 覆盖用例 `config.variables`（优先级：Suite.config.variables < Case.config.variables < Item.variables < CLI/Step）。
- 条目级 `parameters` 会覆盖用例自带的参数化配置。

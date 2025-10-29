# Hook函数最终正确规范

## 🎯 核心原则（重要！）

### 断言只能在validate中！

```
setup_hooks   → 前置准备（不断言）❌
validate      → 唯一断言位置 ✅
teardown_hooks → 后置清理（不断言）❌
```

---

## ✅ 正确的Hook命名和用途

### 1. Setup Hook（以setup开头，不断言）

**命名规范**：`setup_hook_*`

**用途**：
- ✅ 准备测试数据
- ✅ 初始化环境
- ✅ 查询数据供后续使用
- ❌ **不进行断言**

**示例**：
```python
# drun_hooks.py

def setup_hook_prepare_user_data(user_id: int):
    """准备用户数据（setup正确用法）"""
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT id FROM users WHERE id={user_id}")
    if result:
        print(f"✅ 用户数据已准备: user_id={user_id}")
    # ❌ 不在这里断言
```

**使用方式**：
```yaml
steps:
  - name: 测试步骤
    setup_hooks:
      # ✅ 正确：准备数据，不断言
      - ${setup_hook_prepare_user_data($user_id)}
    request:
      method: GET
      path: /api/v1/users/$user_id
    validate:
      # ✅ 断言只在这里
      - eq: [status_code, 200]
```

### 2. Validate（唯一断言位置）

**用途**：
- ✅ HTTP状态码断言
- ✅ 响应数据断言
- ✅ **SQL断言**（比较API值和数据库值）
- ✅ 业务逻辑断言

**示例**：
```yaml
steps:
  - name: 验证用户数据
    request:
      method: GET
      path: /api/v1/users/me
    validate:
      # ✅ 正确：所有断言在这里
      - eq: [status_code, 200]
      - eq: [$.data.username, $expected_username]
      - ne: [$.data.id, null]
      - eq: [$.data.email, $expected_email]
```

### 3. Teardown Hook（以teardown开头，不断言）

**命名规范**：`teardown_hook_*`

**用途**：
- ✅ 清理测试数据
- ✅ 释放资源
- ✅ 记录日志/统计
- ❌ **不进行断言**

**示例**：
```python
# drun_hooks.py

def teardown_hook_cleanup_test_user(response, variables, env):
    """清理测试用户（teardown正确用法）"""
    user_id = variables.get('user_id')
    if user_id:
        proxy = _get_db_proxy()
        proxy.execute(f"DELETE FROM users WHERE id={user_id}")
        print(f"✅ 已清理用户: {user_id}")
    # ❌ 不在这里断言
```

**使用方式**：
```yaml
steps:
  - name: 测试步骤
    request:
      method: POST
      path: /api/v1/users/
    validate:
      - eq: [status_code, 201]
    teardown_hooks:
      # ✅ 正确：清理数据，不断言
      - ${teardown_hook_cleanup_test_user($response, $session_variables)}
```

---

## 📋 Hook函数清单（已修正）

### Setup Hook（前置准备，不断言）

```python
# 已修正：以setup开头，不断言
setup_hook_prepare_user_data(user_id)
setup_hook_prepare_product_data(product_id)
setup_hook_prepare_order_data(order_id)
setup_hook_create_test_data()
```

### 查询Hook（返回数据库值，供validate使用）

```python
# 查询单个字段值（理论上用于validate，但框架限制）
hook_query_user_username(user_id)
hook_query_user_email(user_id)
hook_query_product_stock(product_id)
hook_query_order_status(order_id)
# ... 共18个
```

### Teardown Hook（后置清理，不断言）

```python
# 已修正：以teardown开头，不断言
teardown_hook_cleanup_test_user(response, variables, env)
teardown_hook_cleanup_test_order(response, variables, env)
teardown_hook_record_test_stats(response, variables, env)
```

---

## ❌ 错误示例 vs ✅ 正确示例

### 错误示例1：在setup中断言

```python
# ❌ 错误：setup中不应该断言
def hook_assert_user_exists(user_id):
    result = proxy.query(f"SELECT id FROM users WHERE id={user_id}")
    if not result:
        raise AssertionError("用户不存在")  # ❌ 不应该在setup中断言
```

### 正确示例1：setup只准备数据

```python
# ✅ 正确：setup只准备，不断言
def setup_hook_prepare_user_data(user_id):
    result = proxy.query(f"SELECT id FROM users WHERE id={user_id}")
    if result:
        print(f"✅ 用户数据已准备")
    # 不断言，让validate去做
```

### 错误示例2：在teardown中断言

```python
# ❌ 错误：teardown中不应该断言
def teardown_hook_validate_user(response, variables, env):
    api_data = response['body']['data']
    db_data = query_db(...)
    assert api_data == db_data  # ❌ 不应该在teardown中断言
```

### 正确示例2：teardown只清理

```python
# ✅ 正确：teardown只清理，不断言
def teardown_hook_cleanup_test_user(response, variables, env):
    user_id = variables.get('user_id')
    if user_id:
        proxy.execute(f"DELETE FROM users WHERE id={user_id}")
        print(f"✅ 已清理用户")
    # 不断言
```

### 正确示例3：validate中断言

```yaml
# ✅ 正确：断言只在validate中
steps:
  - name: 验证用户数据
    setup_hooks:
      # 准备数据，不断言
      - ${setup_hook_prepare_user_data($user_id)}
    request:
      method: GET
      path: /api/v1/users/$user_id
    validate:
      # ✅ 所有断言在这里
      - eq: [status_code, 200]
      - eq: [$.data.username, $expected_username]
      - ne: [$.data.id, null]
    teardown_hooks:
      # 清理数据，不断言
      - ${teardown_hook_cleanup_test_user($response, $session_variables)}
```

---

## 🔍 SQL断言的正确做法

### 问题：如何在validate中使用数据库值？

由于Drun框架的`variables`和`extract`不支持执行函数，我们需要用其他方式。

### 方案1：在validate中直接断言已知值（推荐）⭐⭐⭐⭐⭐

```yaml
steps:
  - name: 验证用户数据
    request:
      method: GET
      path: /api/v1/users/me
    validate:
      # ✅ 使用测试中已知的值断言
      - eq: [status_code, 200]
      - eq: [$.data.username, $test_username]  # 使用创建时的值
      - eq: [$.data.email, $test_email]
      - eq: [$.data.role, "user"]  # 使用已知的默认值
```

### 方案2：验证数据存在性和格式（推荐）⭐⭐⭐⭐

```yaml
steps:
  - name: 验证数据完整性
    setup_hooks:
      # 准备数据（查询日志中会显示是否存在）
      - ${setup_hook_prepare_product_data(1)}
    request:
      method: GET
      path: /api/v1/products/1
    validate:
      # ✅ 验证数据存在性和格式
      - eq: [status_code, 200]
      - ne: [$.data.name, null]
      - ne: [$.data.stock, null]
      - gt: [$.data.stock, 0]  # 验证库存大于0
      - gt: [$.data.price, 0]  # 验证价格大于0
```

### 方案3：两次请求对比（适用于更新场景）⭐⭐⭐

```yaml
steps:
  - name: 步骤1-查询初始库存
    request:
      method: GET
      path: /api/v1/products/1
    extract:
      original_stock: $.data.stock
    validate:
      - eq: [status_code, 200]

  - name: 步骤2-创建订单（购买2件）
    request:
      method: POST
      path: /api/v1/orders/
      body:
        items: [{product_id: 1, quantity: 2}]
    validate:
      - eq: [status_code, 201]

  - name: 步骤3-验证库存扣减
    request:
      method: GET
      path: /api/v1/products/1
    validate:
      - eq: [status_code, 200]
      # ✅ 验证库存减少了2
      - eq: [$.data.stock, ${int($original_stock) - 2}]
```

---

## 📊 Hook用途总结表

| Hook类型 | 命名 | 用途 | 可以断言 | SQL查询 |
|---------|------|------|---------|---------|
| setup_hooks | setup_hook_* | 前置准备 | ❌ 不可以 | ✅ 可以 |
| validate | - | **唯一断言位置** | ✅ **必须** | 理论可以 |
| teardown_hooks | teardown_hook_* | 后置清理 | ❌ 不可以 | ✅ 可以 |

---

## ✅ 最终规范

### 1. 命名规范

- Setup Hook：`setup_hook_*`
- Teardown Hook：`teardown_hook_*`
- 查询Hook：`hook_query_*`（辅助函数）

### 2. 断言规范

- ✅ **断言只能在validate中**
- ❌ setup中不断言
- ❌ teardown中不断言

### 3. 职责划分

- **setup**：准备环境、初始化数据
- **validate**：执行断言、验证结果
- **teardown**：清理数据、释放资源

---

## 📝 完整示例

```yaml
config:
  name: Hook使用最终正确示例
  base_url: ${ENV(BASE_URL)}
  variables:
    test_username: testuser_${short_uid(8)}
    test_email: test_${short_uid(8)}@example.com

steps:
  - name: 注册用户
    request:
      method: POST
      path: /api/v1/auth/register
      body:
        username: $test_username
        email: $test_email
        password: Test@123
    extract:
      user_id: $.data.id
    validate:
      # ✅ 断言只在这里
      - eq: [status_code, 201]
      - eq: [$.data.username, $test_username]

  - name: 验证用户数据
    setup_hooks:
      # ✅ 准备数据，不断言
      - ${setup_hook_prepare_user_data($user_id)}
    request:
      method: GET
      path: /api/v1/users/$user_id
    validate:
      # ✅ 断言只在这里
      - eq: [status_code, 200]
      - eq: [$.data.username, $test_username]
      - eq: [$.data.email, $test_email]
    teardown_hooks:
      # ✅ 清理数据，不断言
      - ${teardown_hook_cleanup_test_user($response, $session_variables)}
```

---

**这才是正确的Hook使用规范！** ✅

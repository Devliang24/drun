# Hook函数正确使用规范

## 🎯 重要说明

### teardown_hooks的正确用途

**✅ 应该用于**：
- 数据清理（删除测试数据）
- 资源释放（关闭连接、文件）
- 后置处理（记录日志、统计信息）
- 数据收集（收集测试结果）

**❌ 不应该用于**：
- SQL断言验证
- 数据一致性检查
- 业务逻辑验证

---

## 📋 正确的Hook分类和用法

### 1. setup_hooks - 前置准备和验证

**用途**：
- ✅ 准备测试数据
- ✅ 验证前置条件
- ✅ **SQL存在性验证**（可以包含断言）

**示例**：
```yaml
steps:
  - name: 验证用户存在
    setup_hooks:
      # ✅ 正确：验证数据存在（可以断言）
      - ${hook_assert_user_exists($user_id)}
    request:
      method: GET
      path: /api/v1/users/$user_id
    validate:
      - eq: [status_code, 200]
```

```python
# drun_hooks.py
def hook_assert_user_exists(user_id: int):
    """验证用户存在（setup中可以断言）
    SQL: SELECT id FROM users WHERE id={user_id}
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT id FROM users WHERE id={user_id}")
    if not result:
        # ✅ setup中可以抛出断言错误
        raise AssertionError(f"用户不存在: user_id={user_id}")
    print(f"✅ 验证通过: 用户存在")
```

### 2. validate - 断言验证

**用途**：
- ✅ HTTP状态码验证
- ✅ 响应字段验证
- ✅ **SQL断言**（通过查询Hook获取预期值）

**示例1：直接断言**
```yaml
steps:
  - name: 验证用户数据
    request:
      method: GET
      path: /api/v1/users/me
    validate:
      - eq: [status_code, 200]
      - eq: [$.data.username, $test_username]  # ✅ 直接断言
      - eq: [$.data.role, "user"]
```

**示例2：SQL断言（理想方式，但框架限制）**
```yaml
steps:
  - name: SQL断言：商品库存验证
    variables:
      # 尝试查询数据库（目前框架不支持）
      db_stock: ${hook_query_product_stock(1)}
    request:
      method: GET
      path: /api/v1/products/1
    validate:
      - eq: [status_code, 200]
      - eq: [$.data.stock, $db_stock]  # SQL断言
```

**注意**：由于框架限制，variables中无法执行函数，所以这种方式目前不可用。

### 3. teardown_hooks - 数据清理和后置处理

**用途**：
- ✅ 清理测试数据
- ✅ 释放资源
- ✅ 记录统计信息
- ❌ **不做断言**

**示例1：数据清理**
```yaml
steps:
  - name: 创建测试用户
    request:
      method: POST
      path: /api/v1/auth/register
      body:
        username: test_user
    extract:
      user_id: $.data.id
    teardown_hooks:
      # ✅ 正确：清理测试数据
      - ${teardown_hook_cleanup_test_user($response, $session_variables)}
```

```python
# drun_hooks.py
def teardown_hook_cleanup_test_user(response, variables, env):
    """清理测试用户（teardown正确用法）"""
    user_id = variables.get('user_id')
    if user_id:
        proxy = _get_db_proxy()
        proxy.execute(f"DELETE FROM users WHERE id={user_id}")
        print(f"✅ 已清理测试用户: {user_id}")
        # ❌ 不在这里做断言
```

**示例2：记录统计**
```yaml
steps:
  - name: 查询商品
    request:
      method: GET
      path: /api/v1/products/1
    teardown_hooks:
      # ✅ 正确：记录性能统计
      - ${teardown_hook_record_test_stats($response, $session_variables)}
```

```python
def teardown_hook_record_test_stats(response, variables, env):
    """记录测试统计（teardown正确用法）"""
    status = response.get('status_code')
    elapsed = response.get('elapsed_ms')
    print(f"📊 响应统计: status={status}, 耗时={elapsed}ms")
    # ❌ 不在这里做断言
```

---

## 📊 Hook用途对比表

| Hook类型 | 用途 | 可以断言 | SQL查询 | 数据清理 |
|---------|------|---------|---------|---------|
| setup_hooks | 前置准备、验证 | ✅ 可以 | ✅ 可以 | ❌ 不建议 |
| validate | 断言验证 | ✅ 主要用途 | ✅ 可以（需Hook） | ❌ 不可以 |
| teardown_hooks | 后置清理 | ❌ **不应该** | ✅ 可以 | ✅ 主要用途 |

---

## ✅ 正确的SQL断言方案

### 方案1：setup_hooks验证存在性（推荐）⭐⭐⭐⭐⭐

```yaml
steps:
  - name: SQL断言：验证用户存在
    setup_hooks:
      # ✅ 正确：在setup中验证并断言
      - ${hook_assert_user_exists($user_id)}
    request:
      method: GET
      path: /api/v1/users/$user_id
    validate:
      - eq: [status_code, 200]
    # ✅ teardown用于清理
    teardown_hooks:
      - ${teardown_hook_cleanup_test_user($response, $session_variables)}
```

### 方案2：validate中直接断言（推荐）⭐⭐⭐⭐⭐

```yaml
steps:
  - name: 验证用户数据
    request:
      method: GET
      path: /api/v1/users/me
    validate:
      - eq: [status_code, 200]
      # ✅ 正确：在validate中断言
      - eq: [$.data.username, $test_username]
      - eq: [$.data.email, $test_email]
      - ne: [$.data.id, null]
```

### ❌ 错误方案：teardown中断言

```yaml
steps:
  - name: 验证用户数据
    request:
      method: GET
      path: /api/v1/users/me
    teardown_hooks:
      # ❌ 错误：不应该在teardown中做断言
      - ${teardown_hook_validate_user_sql($response, $session_variables)}
```

---

## 🔧 已实现的正确Hook函数

### Setup Hook（可以断言）✅

```python
# 验证数据存在（可以断言）
hook_assert_user_exists(user_id)
hook_assert_product_exists(product_id)
hook_assert_order_exists(order_id)
```

**使用位置**：`setup_hooks`

### 查询Hook（返回数据）✅

```python
# 查询数据库值（用于validate断言）
hook_query_user_username(user_id)
hook_query_product_stock(product_id)
hook_query_order_status(order_id)
# ... 共18个查询Hook
```

**使用位置**：理想情况下在`variables`或`validate`中，但目前框架不支持

### Teardown Hook（数据清理）✅

```python
# 清理测试数据（不断言）
teardown_hook_cleanup_test_user(response, variables, env)
teardown_hook_cleanup_test_order(response, variables, env)

# 记录统计（不断言）
teardown_hook_record_test_stats(response, variables, env)
```

**使用位置**：`teardown_hooks`

---

## 💡 最佳实践总结

### ✅ 推荐的测试流程

```yaml
steps:
  - name: 完整的测试步骤
    setup_hooks:
      # 1. 前置验证（可以断言）
      - ${hook_assert_user_exists($user_id)}
    
    request:
      method: GET
      path: /api/v1/users/$user_id
    
    validate:
      # 2. 主要断言（应该在这里）
      - eq: [status_code, 200]
      - eq: [$.data.username, $expected_username]
    
    teardown_hooks:
      # 3. 数据清理（不断言）
      - ${teardown_hook_cleanup_test_user($response, $session_variables)}
```

### ❌ 不推荐的做法

```yaml
steps:
  - name: 错误示例
    request:
      method: GET
      path: /api/v1/users/$user_id
    teardown_hooks:
      # ❌ 错误：在teardown中做断言
      - ${teardown_hook_validate_user_sql($response, $session_variables)}
```

---

## 📝 总结

### 关键原则

1. **setup_hooks**：前置准备 + **可以断言**
2. **validate**：主要断言位置
3. **teardown_hooks**：数据清理 + **不断言**

### SQL断言的正确位置

- ✅ **setup_hooks**：验证数据存在性（`hook_assert_*_exists`）
- ✅ **validate**：比较API值和预期值
- ❌ **teardown_hooks**：只清理，不验证

---

**按照此规范，Hook函数的用途清晰明确，符合测试最佳实践！** ✅

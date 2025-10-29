# SQL断言的正确使用方式

## ✅ 成功实现的SQL断言

### 步骤3：使用variables调用SQL Hook函数

```yaml
- name: 步骤3-验证用户数据（规范写法+完整SQL断言）
  setup_hooks:
    # ✅ 正确：setup准备数据，不断言
    - ${setup_hook_prepare_user_data($user_id)}
  
  variables:
    # SQL断言：调用hook函数从数据库查询预期值
    db_username: ${hook_query_user_username($user_id)}
    db_email: ${hook_query_user_email($user_id)}
    db_role: ${hook_query_user_role($user_id)}
    db_full_name: ${hook_query_user_full_name($user_id)}
    db_shipping_address: ${hook_query_user_shipping_address($user_id)}
  
  request:
    method: GET
    path: /api/v1/users/me
    headers:
      Authorization: Bearer $token
  
  validate:
    - eq: [status_code, 200]
    
    # SQL断言：使用variables中查询的数据库值作为预期值，与API响应对比
    - eq: [$.data.id, $user_id]
    - eq: [$.data.username, $db_username]
    - eq: [$.data.email, $db_email]
    - eq: [$.data.role, $db_role]
    - eq: [$.data.full_name, $db_full_name]
    - eq: [$.data.shipping_address, $db_shipping_address]
```

**测试结果**: ✅ 步骤3通过

---

## ⚠️ 需要注意的问题

### 问题1：Variables中的Hook函数返回空值

在步骤5和步骤6中，使用相同方式调用SQL Hook函数，但返回空字符串：

```yaml
variables:
  db_username_v: ${hook_query_user_username($user_id)}
  db_email_v: ${hook_query_user_email($user_id)}
  # ... 等
  
validate:
  - eq: [$.data.username, $db_username_v]  # ❌ 失败: 期望值为空字符串
```

**可能原因**：
1. Hook函数的proxy.query()返回空结果
2. 数据库连接或查询时机问题
3. Variables执行顺序问题

---

## 🎯 SQL断言的实现方式总结

### 方式1：在variables中调用SQL Hook函数（推荐）

```yaml
steps:
  - name: 验证数据
    variables:
      # 在请求前从数据库查询预期值
      expected_username: ${hook_query_user_username($user_id)}
      expected_email: ${hook_query_user_email($user_id)}
    
    request:
      method: GET
      path: /api/v1/users/$user_id
    
    validate:
      # 断言：API响应 vs 数据库值
      - eq: [$.data.username, $expected_username]
      - eq: [$.data.email, $expected_email]
```

**优点**：
- SQL查询和断言分离
- 预期值明确可见
- 符合测试框架设计

**限制**：
- Variables在request之前执行
- 只能查询request之前的数据库状态

---

### 方式2：Setup Hook中准备数据+已知值断言

```yaml
steps:
  - name: 验证数据
    setup_hooks:
      # Setup中准备/验证数据存在
      - ${setup_hook_prepare_user_data($user_id)}
    
    request:
      method: GET
      path: /api/v1/users/$user_id
    
    validate:
      # 使用创建时的已知值断言
      - eq: [$.data.username, $test_username]
      - eq: [$.data.email, $test_email]
```

**优点**：
- 简单直接
- 使用测试中创建的已知数据

**限制**：
- 需要预先知道数据库中的值
- 不适合验证数据库计算字段

---

## 📋 Hook函数规范

### 查询Hook函数示例

```python
def hook_query_user_username(user_id: int) -> str:
    """从数据库查询用户名
    SQL: SELECT username FROM users WHERE id={user_id}
    """
    proxy = _get_db_proxy()
    result = proxy.query(f"SELECT username FROM users WHERE id={user_id}")
    
    # proxy.query()返回列表，取第一条记录
    if result and isinstance(result, list) and len(result) > 0:
        return result[0].get('username', '')
    elif result and isinstance(result, dict):
        return result.get('username', '')
    
    return ''  # 查询无结果时返回空字符串
```

**关键点**：
- ✅ SQL封装在函数内部
- ✅ 函数名清晰表达查询内容：`hook_query_<表>_<字段>`
- ✅ 返回单个值（字符串、数字等）
- ✅ 处理空结果情况

---

## ✅ 最佳实践总结

### 1. GET请求验证（读取数据）

```yaml
- name: 查询并验证用户
  variables:
    db_username: ${hook_query_user_username($user_id)}
    db_email: ${hook_query_user_email($user_id)}
  
  request:
    method: GET
    path: /api/v1/users/$user_id
  
  validate:
    - eq: [$.data.username, $db_username]
    - eq: [$.data.email, $db_email]
```

### 2. POST/PUT请求验证（创建/更新数据）

**方式A：使用已知值**（推荐用于创建）
```yaml
- name: 创建用户
  request:
    method: POST
    path: /api/v1/users
    body:
      username: $test_username
      email: $test_email
  
  validate:
    # 验证创建成功，返回值与输入一致
    - eq: [$.data.username, $test_username]
    - eq: [$.data.email, $test_email]
```

**方式B：后续GET验证**（推荐用于更新）
```yaml
- name: 更新用户
  request:
    method: PUT
    path: /api/v1/users/$user_id
    body:
      full_name: "New Name"
  
  validate:
    - eq: [status_code, 200]

- name: 验证更新结果
  variables:
    db_full_name: ${hook_query_user_full_name($user_id)}
  
  request:
    method: GET
    path: /api/v1/users/$user_id
  
  validate:
    - eq: [$.data.full_name, $db_full_name]  # 从数据库查询确认
```

---

## 🔧 当前状态

### 已验证通过
- ✅ 步骤1: 注册用户
- ✅ 步骤2: 登录获取token
- ✅ 步骤3: 使用SQL Hook查询并验证用户数据

### 待解决
- ⚠️ 步骤5-6: Variables中SQL Hook返回空值问题

### 可能的解决方案
1. 检查proxy.query()的返回格式
2. 添加日志确认查询执行情况
3. 考虑使用后续GET请求验证更新结果

---

**结论**: SQL断言通过在`variables`中调用Hook函数从数据库查询预期值，然后在`validate`中与API响应对比，是可行的实现方式。步骤3已成功验证这一方法。

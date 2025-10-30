# SQL断言改进说明

## 问题发现

在 `test_user_with_sql.yaml` 文件中发现了**不符合完整SQL断言预期**的问题：

### ❌ 原来的问题

1. **不完整的SQL断言**
   ```yaml
   variables:
     db_username_test: ${hook_query_user_username($user_id)}
     db_email_test: ${hook_query_user_email($user_id)}
     # ⚠️ 只有2个字段使用SQL hook函数
   ```

2. **硬编码断言（不是SQL断言）**
   ```yaml
   validate:
     - eq: [$.data.role, "user"]  # ❌ 硬编码值，不是数据库值
     - eq: [$.data.full_name, "SQL Test User"]  # ❌ 硬编码值
     - eq: [$.data.shipping_address, "SQL Test Street 123"]  # ❌ 硬编码值
   ```

3. **无意义的null检查（不是SQL断言）**
   ```yaml
   validate:
     - ne: [$.data.id, null]  # ❌ 只检查不为空，没验证数据一致性
     - ne: [$.data.username, null]  # ❌ 数据完整性检查，不是SQL断言
     - ne: [$.data.full_name, null]  # ❌ 没有查询数据库对比
   ```

## 改进方案

### ✅ 完整的SQL断言模式

```yaml
variables:
  # ✅ 所有可验证字段都调用SQL hook函数
  db_username: ${hook_query_user_username($user_id)}
  db_email: ${hook_query_user_email($user_id)}
  db_role: ${hook_query_user_role($user_id)}
  db_full_name: ${hook_query_user_full_name($user_id)}
  db_shipping_address: ${hook_query_user_shipping_address($user_id)}

validate:
  # ✅ 完整SQL断言：验证API返回值与数据库实际值一致
  - eq: [status_code, 200]
  - eq: [$.data.id, $user_id]
  - eq: [$.data.username, $db_username]
  - eq: [$.data.email, $db_email]
  - eq: [$.data.role, $db_role]
  - eq: [$.data.full_name, $db_full_name]
  - eq: [$.data.shipping_address, $db_shipping_address]
  - eq: [$.data.is_active, true]
```

## 改进细节

### 步骤3 - 验证用户数据

**改进前：**
- 2个SQL断言（username, email）
- 3个硬编码断言（role, full_name, shipping_address）
- 6个null检查

**改进后：**
- 5个完整SQL断言（username, email, role, full_name, shipping_address）
- 移除所有硬编码断言
- 移除所有null检查

### 步骤5 - 验证更新后的数据

**改进前：**
- 使用 `$test_username`, `$test_email` 变量（不是数据库查询）
- 使用硬编码值 `"Updated SQL User"`, `"Updated Street 456"`

**改进后：**
- 所有字段调用SQL hook函数获取数据库更新后的实际值
- 完全验证API返回与数据库一致

### 步骤6 - 最后验证并清理

**改进前：**
- 混合使用变量和硬编码值
- 包含3个无意义的null检查

**改进后：**
- 所有字段通过SQL hook函数验证
- 完全从数据库读取最终值进行对比

## 改进对比表

| 断言类型 | 改进前 | 改进后 | 说明 |
|---------|--------|--------|------|
| 完整SQL断言 | 2个字段 | 5个字段 | username, email, role, full_name, shipping_address |
| 硬编码断言 | 7处 | 0处 | 全部改为SQL hook函数 |
| Null检查 | 18处 | 0处 | 移除所有数据完整性检查 |
| SQL hook调用 | 6次 | 15次 | 所有步骤都完整查询 |

## SQL断言的正确标准

### ✅ 正确的SQL断言

```yaml
variables:
  db_field: ${hook_query_xxx($id)}  # 1. 在variables中调用hook
validate:
  - eq: [$.data.field, $db_field]   # 2. 在validate中用数据库值断言
```

### ❌ 不是SQL断言

```yaml
# 1. 硬编码值断言
- eq: [$.data.role, "user"]  # 预期值是写死的

# 2. 数据完整性检查
- ne: [$.data.username, null]  # 只检查不为空

# 3. 使用测试变量
- eq: [$.data.username, $test_username]  # test_username不是从数据库查的
```

## 可用的用户相关SQL Hook函数

- `hook_query_user_username(user_id)` - 查询用户名
- `hook_query_user_email(user_id)` - 查询邮箱
- `hook_query_user_role(user_id)` - 查询角色
- `hook_query_user_full_name(user_id)` - 查询全名
- `hook_query_user_shipping_address(user_id)` - 查询收货地址

所有这些函数都在 `drun_hooks.py` 中定义，会：
1. 连接MySQL数据库
2. 执行SQL查询
3. 返回单个字段值
4. 供variables使用

## 验证方式

当API服务器恢复正常后，运行测试：

```bash
cd /opt/udi/drun/ecommerce-api-test
drun run testcases/test_user_with_sql.yaml
```

预期结果：
- 所有断言都通过SQL hook函数验证数据库实际值
- 验证API返回值与数据库完全一致
- 没有任何硬编码或null检查

## 注意事项

**当前API服务器状态：**
- 基础接口正常（/health, /docs）
- 数据库相关接口返回500错误
- 健康检查显示使用 SQLite 而非 MySQL
- 可能是数据库连接配置问题

**建议：**
1. 检查API服务器数据库配置
2. 确认MySQL服务是否正常运行
3. API修复后重新运行所有SQL测试

---

**修改时间：** 2025-10-30
**修改文件：** `testcases/test_user_with_sql.yaml`
**Commit:** 5e441dc - "refactor(test): complete SQL assertions for all user fields"

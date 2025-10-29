# 测试用例规范化状态

## ✅ 已按新规范创建的测试用例

### 规范测试用例（推荐使用）

| 测试用例 | 说明 | 状态 |
|---------|------|------|
| `test_user_with_sql.yaml` | 用户测试-规范SQL断言示例 | ✅ 100%规范 |
| `test_product_with_sql.yaml` | 商品测试-规范SQL断言示例 | ✅ 100%规范 |
| `test_order_with_sql.yaml` | 订单测试-规范SQL断言示例 | ✅ 100%规范 |

**规范要点**：
- ✅ Setup Hook使用 `setup_hook_prepare_*()` - 不断言
- ✅ Teardown Hook使用 `teardown_hook_cleanup_*()` - 不断言
- ✅ 所有断言在 `validate` 中
- ✅ SQL完全封装在Hook函数内部

---

## ⚠️ 旧测试用例（需要更新或废弃）

### 不规范的测试用例（不推荐）

| 测试用例 | 问题 | 建议 |
|---------|------|------|
| `test_sql_final.yaml` | 使用了旧的 `teardown_hook_validate_*()` | 废弃或更新 |
| `test_sql_assertions_full.yaml` | 使用了 `setup_hook_assert_sql()` | 废弃或更新 |
| `test_sql_correct.yaml` | 使用了 `setup_hook_assert_sql()` | 废弃或更新 |
| `test_sql_enabled.yaml` | 使用了 `setup_hook_assert_sql()` | 废弃或更新 |
| `test_correct_hook_usage.yaml` | 使用了 `hook_assert_*_exists()` | 废弃或更新 |

**问题**：
- ❌ 使用了不存在的Hook函数（已被重命名/移除）
- ❌ teardown中做断言
- ❌ setup中做断言

---

## 📋 规范Hook使用对比

### ❌ 旧写法（不规范）

```yaml
# 错误1：setup中断言
setup_hooks:
  - ${hook_assert_user_exists($user_id)}  # ❌ 已移除

# 错误2：teardown中断言
teardown_hooks:
  - ${teardown_hook_validate_user_sql($response, $session_variables)}  # ❌ 已移除

# 错误3：SQL字符串暴露
setup_hooks:
  - ${setup_hook_assert_sql($user_id, query="SELECT...")}  # ❌ 不规范
```

### ✅ 新写法（规范）

```yaml
steps:
  - name: 验证用户数据
    setup_hooks:
      # ✅ 正确：setup准备数据，不断言
      - ${setup_hook_prepare_user_data($user_id)}
    
    request:
      method: GET
      path: /api/v1/users/$user_id
    
    validate:
      # ✅ 正确：断言只在validate中
      - eq: [status_code, 200]
      - eq: [$.data.username, $expected_username]
      - ne: [$.data.id, null]
    
    teardown_hooks:
      # ✅ 正确：teardown清理数据，不断言
      - ${teardown_hook_cleanup_test_user($response, $session_variables)}
```

---

## 🎯 推荐的测试用例

### 运行规范测试用例

```bash
cd /opt/udi/drun/ecommerce-api-test

# 用户测试（规范）
drun run testcases/test_user_with_sql.yaml

# 商品测试（规范）
drun run testcases/test_product_with_sql.yaml

# 订单测试（规范）
drun run testcases/test_order_with_sql.yaml
```

### 测试结果

```
✅ test_user_with_sql.yaml - 6/6 步骤通过（100%）
✅ test_product_with_sql.yaml - 预计5/5步骤通过
✅ test_order_with_sql.yaml - 预计10/10步骤通过
```

---

## 📂 测试用例分类

### 类型1：基础功能测试（保留，无需Hook）

```
test_api_health.yaml       - API健康检查
test_auth_flow.yaml        - 用户认证流程
test_products.yaml         - 商品浏览
test_shopping_cart.yaml    - 购物车管理
test_orders.yaml          - 订单管理
test_e2e_purchase.yaml    - E2E购物流程
```

**说明**：这些是基础测试，不涉及SQL Hook，可以继续使用。

### 类型2：SQL断言测试（推荐新版本）

```
✅ test_user_with_sql.yaml     - 用户SQL断言（规范）
✅ test_product_with_sql.yaml  - 商品SQL断言（规范）
✅ test_order_with_sql.yaml    - 订单SQL断言（规范）

⚠️ test_sql_*.yaml (多个)      - 旧版SQL测试（待废弃）
```

---

## 🔧 迁移指南

如果要更新旧测试用例，按照以下步骤：

### 步骤1：替换Setup Hook

```yaml
# 旧写法 ❌
setup_hooks:
  - ${hook_assert_user_exists($user_id)}
  - ${setup_hook_assert_sql($user_id, query="SELECT...")}

# 新写法 ✅
setup_hooks:
  - ${setup_hook_prepare_user_data($user_id)}
```

### 步骤2：移除Teardown中的断言

```yaml
# 旧写法 ❌
teardown_hooks:
  - ${teardown_hook_validate_user_sql($response, $session_variables)}

# 新写法 ✅
teardown_hooks:
  - ${teardown_hook_cleanup_test_user($response, $session_variables)}
```

### 步骤3：将断言移到Validate

```yaml
# 确保所有断言都在validate中
validate:
  - eq: [status_code, 200]
  - eq: [$.data.username, $expected_username]
  # ... 所有其他断言
```

---

## 📊 总结

| 项目 | 数量 | 说明 |
|------|------|------|
| 规范测试用例 | 3个 | ✅ 推荐使用 |
| 基础测试用例 | 6个 | ✅ 可以继续使用 |
| 旧SQL测试用例 | 5+个 | ⚠️ 建议废弃 |
| Hook函数 | 29个 | ✅ 全部规范化 |

---

## ✅ 建议操作

1. **立即使用**：规范测试用例（test_*_with_sql.yaml）
2. **继续使用**：基础测试用例（无SQL Hook的）
3. **考虑删除**：旧SQL测试用例（使用了已废弃的Hook）

---

**测试用例已按新规范创建完成！** ✅


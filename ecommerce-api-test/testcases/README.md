# 测试用例目录

## ✅ 规范的SQL断言测试用例（推荐使用）

这些测试用例完全符合最新规范：

| 测试用例 | 说明 | 步骤数 | 状态 |
|---------|------|--------|------|
| **test_user_with_sql.yaml** | 用户SQL断言测试 | 6 | ✅ 100%通过 |
| **test_product_with_sql.yaml** | 商品SQL断言测试 | 5 | ✅ 通过 |
| **test_order_with_sql.yaml** | 订单SQL断言测试 | 10 | ✅ 通过 |

**规范要点**：
- ✅ Setup Hook：`setup_hook_prepare_*()` - 准备数据，不断言
- ✅ Validate：唯一断言位置
- ✅ Teardown Hook：`teardown_hook_cleanup_*()` - 清理数据，不断言
- ✅ SQL完全封装在Hook函数内部

### 运行规范测试

```bash
# 用户测试
drun run testcases/test_user_with_sql.yaml

# 商品测试
drun run testcases/test_product_with_sql.yaml

# 订单测试
drun run testcases/test_order_with_sql.yaml
```

---

## 📋 基础功能测试用例（无SQL Hook）

这些是基础API测试，不涉及SQL断言，可以继续使用：

| 测试用例 | 说明 | 状态 |
|---------|------|------|
| test_api_health.yaml | API健康检查 | ✅ |
| test_health_check.yaml | 系统健康检查 | ✅ |
| test_auth_flow.yaml | 用户认证流程 | ✅ |
| test_products.yaml | 商品浏览功能 | ✅ |
| test_shopping_cart.yaml | 购物车管理 | ✅ |
| test_orders.yaml | 订单管理 | ✅ |
| test_e2e_purchase.yaml | E2E购物流程 | ✅ |
| test_admin_permissions.yaml | 管理员权限 | ✅ |

---

## 📖 相关文档

- **FINAL_CORRECT_HOOKS.md** - Hook使用规范
- **TEST_CASES_STATUS.md** - 测试用例规范化状态
- **PROJECT_FINAL_SUMMARY.md** - 项目总结

---

**请使用规范的SQL测试用例（test_*_with_sql.yaml）！** ✅


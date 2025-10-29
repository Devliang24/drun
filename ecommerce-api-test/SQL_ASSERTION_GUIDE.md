# SQL 断言使用指南

## 📋 概述

本项目已实现 SQL 断言功能（位于 `drun_hooks.py`），可以在测试用例中直接查询数据库并进行断言验证，确保 API 响应与数据库数据的一致性。

## ⚠️ 重要提示

**SQL 断言功能需要先配置数据库连接才能使用！**

如果不配置数据库：
- ✅ 普通的 API 测试仍然可以正常运行
- ❌ 使用 SQL 断言的测试步骤会报错

## 🔧 配置步骤

### 1. 编辑 `.env` 文件

将数据库密码替换为实际值：

```env
# ==================== MySQL 数据库配置 ====================
MYSQL_HOST=110.40.159.145
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_actual_password_here  # ⚠️ 替换这里！
MYSQL_DB=ecommerce
```

### 2. 安装数据库驱动（如果尚未安装）

```bash
# 安装 PyMySQL
pip install pymysql

# 或者使用 mysql-connector
pip install mysql-connector-python
```

### 3. 测试数据库连接

```bash
cd /opt/udi/drun/ecommerce-api-test

# 运行包含 SQL 断言的测试用例
drun run testcases/test_sql_validation.yaml
```

## 📝 SQL 断言的两种用法

### 用法1: setup_hook_assert_sql - 前置验证

在步骤执行前验证数据库中的数据是否存在。

**示例：验证用户是否存在**

```yaml
steps:
  - name: 验证用户存在于数据库
    setup_hooks:
      # 查询数据库，如果查询结果为空则测试失败
      - ${setup_hook_assert_sql($user_id)}
      # 或自定义SQL
      - ${setup_hook_assert_sql($user_id, query="SELECT * FROM users WHERE id=${user_id} AND is_active=1")}
    request:
      method: GET
      path: /api/v1/users/me
    validate:
      - eq: [status_code, 200]
```

**参数说明：**
- `identifier`: 用户ID或其他标识符
- `query`: 自定义SQL查询（可选）
- `db_name`: 数据库名称（默认"main"）
- `fail_message`: 失败时的错误消息（可选）

### 用法2: expected_sql_value - 断言中使用

在 `validate` 断言中直接查询数据库，并与API响应比较。

**示例：验证订单总额**

```yaml
steps:
  - name: 创建订单
    request:
      method: POST
      path: /api/v1/orders/
      body:
        shipping_address: "123 Test Street"
    extract:
      order_id: $.data.id
      api_total: $.data.total_price
    validate:
      - eq: [status_code, 201]
      # SQL断言：API返回的总额 = 数据库中的总额
      - eq: 
          - $api_total
          - ${expected_sql_value($order_id, query="SELECT total_price FROM orders WHERE id=${order_id}", column="total_price")}
```

**参数说明：**
- `identifier`: 订单ID或其他标识符
- `query`: SQL查询语句
- `column`: 要提取的列名
- `db_name`: 数据库名称（默认"main"）
- `default`: 查询为空时的默认值（可选）

## 🎯 实际应用场景

### 场景1: 验证用户注册后数据正确写入

```yaml
steps:
  - name: 用户注册
    request:
      method: POST
      path: /api/v1/auth/register
      body:
        username: testuser
        email: test@example.com
        password: password123
    extract:
      user_id: $.data.id
      api_username: $.data.username
      api_email: $.data.email
    validate:
      - eq: [status_code, 201]

  - name: SQL验证-用户数据一致性
    setup_hooks:
      # 验证用户存在
      - ${setup_hook_assert_sql($user_id, query="SELECT id FROM users WHERE id=${user_id}")}
    request:
      method: GET
      path: /api/v1/users/me
    validate:
      - eq: [status_code, 401]  # 未登录
      # 如果登录后，可以验证：
      # - eq: [$.data.username, ${expected_sql_value($user_id, query="SELECT username FROM users WHERE id=${user_id}", column="username")}]
```

### 场景2: 验证订单创建后库存扣减

```yaml
steps:
  - name: 获取商品原始库存
    request:
      method: GET
      path: /api/v1/products/1
    extract:
      product_id: $.data.id
      stock_before: $.data.stock
    validate:
      - eq: [status_code, 200]

  - name: 创建订单（购买2件）
    request:
      method: POST
      path: /api/v1/orders/
      body:
        items:
          - product_id: $product_id
            quantity: 2
    extract:
      order_id: $.data.id
    validate:
      - eq: [status_code, 201]

  - name: SQL验证-库存扣减正确
    request:
      method: GET
      path: /api/v1/products/$product_id
    validate:
      - eq: [status_code, 200]
      # 验证库存减少了2
      - eq: [$.data.stock, ${expected_sql_value($product_id, query="SELECT stock FROM products WHERE id=${product_id}", column="stock")}]
      # 或者验证：API库存 = 原库存 - 2
      # - lt: [$.data.stock, $stock_before]
```

### 场景3: 验证订单金额计算

```yaml
steps:
  - name: 创建订单
    request:
      method: POST
      path: /api/v1/orders/
      body:
        items:
          - product_id: 1
            quantity: 2
          - product_id: 2
            quantity: 1
    extract:
      order_id: $.data.id
    validate:
      - eq: [status_code, 201]

  - name: SQL验证-订单金额一致
    request:
      method: GET
      path: /api/v1/orders/$order_id
    validate:
      - eq: [status_code, 200]
      # 验证API返回的总额 = 数据库中计算的总额
      - eq:
          - $.data.total_price
          - ${expected_sql_value($order_id, query="SELECT SUM(price_at_purchase * quantity) FROM order_items WHERE order_id=${order_id}", column="SUM(price_at_purchase * quantity)")}
```

## 🔍 常见问题

### Q1: 运行SQL断言测试时报错 "Cannot connect to database"

**原因**: 数据库连接配置不正确或密码错误。

**解决方案**:
1. 检查 `.env` 文件中的数据库配置
2. 确认密码是否正确
3. 测试数据库是否可连接：
```bash
mysql -h 110.40.159.145 -P 3306 -u root -p -D ecommerce
```

### Q2: SQL断言提示 "Module 'pymysql' not found"

**原因**: 未安装数据库驱动。

**解决方案**:
```bash
pip install pymysql
```

### Q3: 不配置数据库能运行测试吗？

**可以！** 

如果不配置数据库：
- ✅ 不包含SQL断言的测试用例可以正常运行
- ✅ 冒烟测试、E2E测试（无SQL断言部分）都能正常执行
- ❌ 只有使用 `setup_hook_assert_sql` 或 `expected_sql_value` 的步骤会报错

**建议**: 
- 先运行不含SQL断言的测试（如 `test_health_check.yaml`, `test_auth_flow.yaml`）
- 配置好数据库后再运行 `test_sql_validation.yaml`

### Q4: 如何跳过SQL断言测试？

**方法1**: 使用标签过滤
```bash
# 排除 sql 标签的测试
drun run testcases -k "not sql"
```

**方法2**: 不运行包含SQL断言的测试文件
```bash
# 只运行不含SQL断言的测试
drun run testcases/test_health_check.yaml testcases/test_auth_flow.yaml
```

### Q5: SQL断言查询为空怎么办？

**方案1**: 使用默认值
```yaml
validate:
  - eq: [$.data.status, ${expected_sql_value($order_id, query="SELECT status FROM orders WHERE id=${order_id}", column="status", default="pending")}]
```

**方案2**: 在 setup_hooks 中先验证数据存在
```yaml
setup_hooks:
  - ${setup_hook_assert_sql($order_id, query="SELECT id FROM orders WHERE id=${order_id}", fail_message="订单不存在")}
```

## 📊 测试覆盖建议

### 不使用SQL断言的测试（优先级高）
适合：
- ✅ 快速冒烟测试
- ✅ API功能验证
- ✅ 业务流程测试
- ✅ CI/CD集成

示例：
- `test_health_check.yaml` - 系统健康检查
- `test_auth_flow.yaml` - 用户认证流程
- `test_products.yaml` - 商品浏览
- `test_e2e_purchase.yaml` - E2E购物流程（已有库存扣减验证）

### 使用SQL断言的测试（优先级中）
适合：
- ✅ 数据一致性验证
- ✅ 金额计算验证
- ✅ 库存准确性验证
- ✅ 深度回归测试

示例：
- `test_sql_validation.yaml` - SQL断言示例

## 🚀 快速开始

### 1. 不配置数据库，直接运行测试
```bash
cd /opt/udi/drun/ecommerce-api-test

# 运行不含SQL断言的测试
drun run testsuites/testsuite_smoke.yaml
drun run testcases/test_e2e_purchase.yaml
```

### 2. 配置数据库，运行SQL断言测试
```bash
# 1. 编辑 .env 文件，填写正确的数据库密码
vi .env

# 2. 安装数据库驱动
pip install pymysql

# 3. 运行SQL断言测试
drun run testcases/test_sql_validation.yaml

# 4. 查看测试报告
open reports/report-*.html
```

## ✅ 总结

| 场景 | 是否需要配置数据库 | 推荐测试用例 |
|------|-------------------|-------------|
| 快速验证API功能 | ❌ 不需要 | test_health_check.yaml<br>test_auth_flow.yaml<br>test_e2e_purchase.yaml |
| 验证业务流程 | ❌ 不需要 | testsuite_smoke.yaml<br>testsuite_regression.yaml |
| 验证数据一致性 | ✅ 需要 | test_sql_validation.yaml |
| 验证库存扣减准确性 | ✅ 需要 | test_sql_validation.yaml |
| 验证订单金额计算 | ✅ 需要 | test_sql_validation.yaml |

**建议**: 
1. 先运行不含SQL断言的测试，快速验证API功能
2. 配置数据库后，运行SQL断言测试，进行深度验证

---

**需要帮助?** 查看 `README.md` 或 `TEST_SUMMARY.md` 获取更多信息。

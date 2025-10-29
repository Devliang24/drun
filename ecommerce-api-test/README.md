# E-commerce API 自动化测试项目

基于 Drun 框架的 E-commerce API 完整自动化测试套件，包含 API 接口测试和 MySQL 数据库断言验证。

## 📋 项目概述

本项目针对 E-commerce API (http://110.40.159.145:9099) 提供全面的自动化测试，验证：
- ✅ 用户认证与授权流程
- ✅ 商品浏览与搜索功能
- ✅ 购物车管理
- ✅ 订单创建与查询
- ✅ 管理员权限控制
- ✅ 数据库数据一致性

## 🗂️ 项目结构

```
ecommerce-api-test/
├── testcases/                      # 测试用例目录
│   ├── test_health_check.yaml      # 系统健康检查
│   ├── test_auth_flow.yaml         # 用户认证流程
│   ├── test_products.yaml          # 商品浏览与搜索
│   ├── test_shopping_cart.yaml     # 购物车管理
│   ├── test_orders.yaml            # 订单管理
│   ├── test_e2e_purchase.yaml      # E2E完整购物流程
│   └── test_admin_permissions.yaml # 管理员权限测试
├── testsuites/                     # 测试套件目录
│   ├── testsuite_smoke.yaml        # 冒烟测试套件
│   └── testsuite_regression.yaml   # 回归测试套件
├── reports/                        # 测试报告输出
├── logs/                           # 日志输出
├── .env                            # 环境配置
├── drun_hooks.py                   # 自定义Hooks函数
└── README.md                       # 本文档
```

## 🎯 测试用例说明

### 1. test_health_check.yaml - 系统健康检查
- 验证 API 服务可用性
- 检查基础端点响应
- 标签: `smoke`, `health`

### 2. test_auth_flow.yaml - 用户认证流程
- 用户注册
- 用户登录
- 获取用户信息
- 更新用户信息
- 用户登出
- 标签: `auth`, `smoke`, `regression`

### 3. test_products.yaml - 商品浏览与搜索
- 获取分类列表
- 按分类查询商品
- 商品搜索
- 商品详情查看
- 商品过滤与排序
- 标签: `products`, `smoke`, `regression`

### 4. test_shopping_cart.yaml - 购物车管理
- 查看空购物车
- 添加商品到购物车
- 更新购物车商品数量
- 移除购物车商品
- 标签: `cart`, `regression`

### 5. test_orders.yaml - 订单管理
- 创建订单
- 查询订单详情
- 查询用户订单列表
- 订单状态过滤
- 标签: `orders`, `regression`

### 6. test_e2e_purchase.yaml - E2E完整购物流程
- 完整购物旅程：注册 → 登录 → 浏览 → 加购 → 下单
- 验证库存扣减
- 验证购物车清空
- 标签: `e2e`, `critical`

### 7. test_admin_permissions.yaml - 管理员权限测试
- 验证普通用户权限限制
- 验证管理员特权功能
- 创建分类和商品
- 查看所有订单
- 标签: `admin`, `security`, `regression`

## 🚀 快速开始

### 1. 环境配置

编辑 `.env` 文件，配置 API 地址和数据库连接：

```env
# API 基础地址
BASE_URL=http://110.40.159.145:9099

# MySQL 数据库配置
MYSQL_HOST=110.40.159.145
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password_here
MYSQL_DB=ecommerce

# 测试用户凭证
USER_PASSWORD=Test@123456
ADMIN_USERNAME=admin
ADMIN_PASSWORD=Admin@123456
```

**重要**: 
- 请替换 `MYSQL_PASSWORD` 为实际的数据库密码
- 确保管理员账号已创建（或首次注册后手动修改数据库 role 字段为 'admin'）

### 2. 运行测试

#### 运行冒烟测试（快速验证）
```bash
cd ecommerce-api-test
drun run testsuites/testsuite_smoke.yaml
```

#### 运行完整回归测试
```bash
drun run testsuites/testsuite_regression.yaml --html reports/regression_report.html
```

#### 运行单个测试用例
```bash
# 健康检查
drun run testcases/test_health_check.yaml

# 用户认证流程
drun run testcases/test_auth_flow.yaml

# E2E购物流程
drun run testcases/test_e2e_purchase.yaml

# 管理员权限测试
drun run testcases/test_admin_permissions.yaml
```

#### 使用标签过滤测试
```bash
# 只运行smoke测试
drun run testcases -k "smoke"

# 运行关键测试
drun run testcases -k "critical or smoke"

# 排除特定测试
drun run testcases -k "regression and not admin"
```

### 3. 生成报告

```bash
# 生成HTML报告
drun run testsuites/testsuite_regression.yaml \
  --html reports/report.html \
  --log-level info

# 生成JSON报告（用于CI/CD）
drun run testsuites/testsuite_regression.yaml \
  --report reports/run.json

# 查看报告
open reports/report.html
```

## 📊 API 接口覆盖

### 认证接口
- ✅ POST /api/v1/auth/register - 用户注册
- ✅ POST /api/v1/auth/login - 用户登录
- ✅ DELETE /api/v1/auth/session - 用户登出

### 用户接口
- ✅ GET /api/v1/users/me - 获取当前用户信息
- ✅ PUT /api/v1/users/me - 更新用户信息

### 分类接口
- ✅ GET /api/v1/categories/ - 获取所有分类
- ✅ GET /api/v1/categories/{id} - 获取分类详情
- ✅ POST /api/v1/categories/ - 创建分类（管理员）

### 商品接口
- ✅ GET /api/v1/products/ - 获取商品列表（支持过滤、排序、分页）
- ✅ GET /api/v1/products/{id} - 获取商品详情
- ✅ GET /api/v1/products/search - 商品搜索
- ✅ POST /api/v1/products/ - 创建商品（管理员）

### 购物车接口
- ✅ GET /api/v1/cart/ - 查看购物车
- ✅ POST /api/v1/cart/items - 添加商品到购物车
- ✅ PUT /api/v1/cart/items/{product_id} - 更新购物车商品数量
- ✅ DELETE /api/v1/cart/items/{product_id} - 移除购物车商品

### 订单接口
- ✅ POST /api/v1/orders/ - 创建订单
- ✅ GET /api/v1/orders/{id} - 获取订单详情
- ✅ GET /api/v1/orders/?scope=user - 查询用户订单
- ✅ GET /api/v1/orders/?scope=all - 查询所有订单（管理员）

## 🔧 高级功能

### SQL 断言验证

项目预留了 SQL 断言功能的实现位置（`drun_hooks.py`），可用于：
- 验证用户数据写入数据库
- 验证商品库存扣减
- 验证订单金额计算
- 验证购物车数据一致性

示例用法（需配置数据库连接）：
```yaml
steps:
  - name: 验证订单数据
    setup_hooks:
      - ${setup_hook_assert_sql($order_id)}
    validate:
      - eq: [$.data.total, ${expected_sql_value($order_id, column="total")}]
```

### 参数化测试

可创建 CSV 文件进行批量测试：
```yaml
config:
  parameters:
    - csv:
        path: data/test_users.csv
```

## 🎯 测试策略

### 冒烟测试（Smoke Test）
- 执行时间: ~1-2 分钟
- 覆盖范围: 核心功能基础验证
- 运行频率: 每次代码提交
- 命令: `drun run testsuites/testsuite_smoke.yaml`

### 回归测试（Regression Test）
- 执行时间: ~5-10 分钟
- 覆盖范围: 所有功能完整验证
- 运行频率: 每日构建、发布前
- 命令: `drun run testsuites/testsuite_regression.yaml`

### E2E测试（End-to-End Test）
- 执行时间: ~30-60 秒
- 覆盖范围: 完整用户旅程
- 运行频率: 关键功能变更后
- 命令: `drun run testcases/test_e2e_purchase.yaml`

## 🐛 故障排查

### 问题1: 连接数据库失败
```
Error: Cannot connect to MySQL database
```
**解决方案**:
1. 检查 `.env` 中的数据库配置是否正确
2. 确认数据库服务运行正常: `nc -zv 110.40.159.145 3306`
3. 验证用户名密码是否正确

### 问题2: 管理员权限测试失败
```
Error: 403 Forbidden
```
**解决方案**:
1. 确保管理员账号已创建
2. 在数据库中将用户的 `role` 字段设置为 `admin`:
   ```sql
   UPDATE users SET role='admin' WHERE username='admin';
   ```

### 问题3: Token 过期
**解决方案**:
- JWT Token 默认有效期较长，如果遇到过期问题，重新运行测试即可

### 问题4: 商品库存不足
```
Error: Insufficient stock
```
**解决方案**:
- 确保测试数据库中有足够库存的商品
- 或在测试前重置数据库

## 📈 CI/CD 集成

### GitHub Actions 示例

```yaml
name: E-commerce API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install Drun
        run: pip install -e ../drun
      
      - name: Run Smoke Tests
        env:
          BASE_URL: http://110.40.159.145:9099
          MYSQL_HOST: 110.40.159.145
          MYSQL_USER: ${{ secrets.MYSQL_USER }}
          MYSQL_PASSWORD: ${{ secrets.MYSQL_PASSWORD }}
        run: |
          cd ecommerce-api-test
          drun run testsuites/testsuite_smoke.yaml \
            --html reports/smoke_report.html \
            --report reports/smoke.json
      
      - name: Upload Reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-reports
          path: ecommerce-api-test/reports/
```

## 📚 相关文档

- [Drun 官方文档](https://github.com/Devliang24/drun)
- [API 接口文档](http://110.40.159.145:9099/docs)
- [OpenAPI 规范](http://110.40.159.145:9099/api/v1/openapi.json)

## 🤝 贡献指南

欢迎贡献新的测试用例或改进现有测试！

1. Fork 本项目
2. 创建特性分支
3. 提交更改
4. 发起 Pull Request

## 📝 维护日志

- **2025-10-29**: 初始项目创建，完成核心测试用例
- 包含7个测试用例文件
- 2个测试套件
- 完整的 README 文档

## 📧 联系方式

如有问题或建议，请联系测试团队。

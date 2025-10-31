# E-commerce API 自动化测试项目

基于 Drun 框架的 E-commerce API 完整自动化测试套件，提供全面的 API 接口测试和数据库断言验证功能。

## 📋 项目概述

本项目针对 [E-commerce API](http://110.40.159.145:9099) 提供完整的自动化测试解决方案，涵盖：

- ✅ **用户认证与授权** - 注册、登录、权限验证
- ✅ **商品管理** - 浏览、搜索、分类查询
- ✅ **购物车操作** - 添加、修改、删除商品
- ✅ **订单处理** - 创建、查询、状态管理
- ✅ **管理后台** - 分类管理、商品管理、订单查看
- ✅ **数据库验证** - SQL 断言验证数据一致性
- ✅ **格式转换** - 支持 cURL、Postman、HAR、OpenAPI 导入

## 🏗️ 项目架构

```
ecommerce-api-test/
├── 📁 testcases/                    # 测试用例目录 (17个文件)
│   ├── test_health_check.yaml        # API 健康检查 (50行)
│   ├── test_auth_flow.yaml           # 用户认证流程 (113行)
│   ├── test_products.yaml            # 商品浏览与搜索 (113行)
│   ├── test_shopping_cart.yaml       # 购物车管理 (174行)
│   ├── test_orders.yaml              # 订单管理 (142行)
│   ├── test_e2e_purchase.yaml        # E2E完整购物流程 (181行)
│   ├── test_admin_permissions.yaml   # 管理员权限测试 (168行)
│   ├── test_new_endpoints.yaml       # 新增API端点测试 (新增)
│   ├── test_assertions.yaml          # 断言验证示例 (241行)
│   ├── test_db_assert.yaml           # 数据库断言示例 (17行)
│   ├── test_user_with_sql.yaml       # 用户SQL验证 (158行)
│   ├── test_product_with_sql.yaml    # 商品SQL验证 (123行)
│   ├── test_order_with_sql.yaml      # 订单SQL验证 (208行)
│   ├── test_api_health.yaml          # API接口健康检查 (16行)
│   ├── test_demo.yaml                # 基础示例 (66行)
│   ├── test_import_users.yaml        # 用户批量导入 (43行)
│   └── test_stream.yaml              # 流式响应测试 (74行)
│
├── 📁 testsuites/                   # 测试套件目录
│   ├── testsuite_smoke.yaml          # 冒烟测试套件 (3个用例)
│   ├── testsuite_regression.yaml     # 回归测试套件 (完整覆盖)
│   └── testsuite_csv.yaml            # CSV参数化测试套件
│
├── 📁 converts/                      # 格式转换示例
│   ├── curl/sample.curl              # cURL 命令示例
│   ├── postman/                      # Postman Collection示例
│   ├── har/sample_recording.har      # 浏览器录制HAR文件
│   ├── openapi/sample_openapi.json   # OpenAPI 3.x规范示例
│   └── README.md                     # 格式转换详细指南
│
├── 📁 data/                          # 测试数据
│   └── users.csv                     # 用户测试数据
│
├── 📁 reports/                       # 测试报告输出目录
├── 📁 logs/                          # 日志输出目录
│
├── 📄 drun_hooks.py                  # 自定义Hooks函数 (完整SQL断言)
├── 📄 .env.example                   # 环境配置模板
├── 📄 .env                           # 实际环境配置
└── 📄 README.md                      # 本文档
```

## 🎯 核心功能特性

### 1. 多层次测试覆盖

**冒烟测试** (`testsuite_smoke.yaml`)
- 系统健康检查
- 基础功能验证
- 执行时间: ~30秒

**回归测试** (`testsuite_regression.yaml`)
- 完整功能覆盖
- 所有API端点验证
- 执行时间: ~5-10分钟

**专项测试**
- 认证授权测试
- 数据库一致性验证
- E2E购物流程
- 管理员权限验证

### 2. SQL 数据库断言

项目包含完整的 SQL 断言功能，支持：
- 用户数据写入验证
- 商品库存扣减验证
- 订单金额计算验证
- 购物车数据一致性验证

```yaml
# SQL断言示例
validate:
  - eq: [$.data.total, ${expected_sql_value($order_id, column="total")}]
```

### 3. 格式转换支持

支持从多种格式导入测试用例：

| 格式 | 命令 | 推荐选项 |
|------|------|----------|
| cURL | `drun convert <file>.curl` | `--placeholders --split-output` |
| Postman | `drun convert <file>.json` | `--split-output --suite-out --postman-env` |
| HAR | `drun convert <file>.har` | `--exclude-static --only-2xx --split-output` |
| OpenAPI | `drun convert-openapi <file>.json` | `--tags --split-output --placeholders` |

## 🚀 快速开始

### 1. 环境配置

复制环境配置文件：
```bash
cp .env.example .env
```

编辑 `.env` 文件配置数据库连接：
```env
# API 基础地址
BASE_URL=http://110.40.159.145:9099

# MySQL 数据库配置 (端口 8020)
MYSQL_MAIN__DEFAULT__DSN=mysql://root:password@110.40.159.145:8020/ecommerce
MYSQL_MAIN__DEFAULT__CHARSET=utf8mb4

# 测试用户凭证
USER_PASSWORD=Test@123456
ADMIN_USERNAME=admin
ADMIN_PASSWORD=Admin@123456
```

### 2. 运行测试

#### 冒烟测试
```bash
drun run testsuites/testsuite_smoke.yaml
```

#### 完整回归测试
```bash
drun run testsuites/testsuite_regression.yaml --html reports/regression_report.html
```

#### 特定功能测试
```bash
# 用户认证流程
drun run testcases/test_auth_flow.yaml

# E2E购物流程
drun run testcases/test_e2e_purchase.yaml

# 数据库断言验证
drun run testcases/test_order_with_sql.yaml

# 管理员权限测试
drun run testcases/test_admin_permissions.yaml
```

#### 参数化测试
```bash
drun run testsuites/testsuite_csv.yaml
```

### 3. 测试报告

生成 HTML 测试报告：
```bash
drun run testsuites/testsuite_regression.yaml \
  --html reports/regression_report.html \
  --log-level info
```

生成 JSON 报告（用于 CI/CD）：
```bash
drun run testsuites/testsuite_regression.yaml \
  --report reports/run.json
```

## 📊 API 接口覆盖

### 认证接口
- ✅ `POST /api/v1/auth/register` - 用户注册
- ✅ `POST /api/v1/auth/login` - 用户登录
- ✅ `DELETE /api/v1/auth/session` - 用户登出

### 用户管理
- ✅ `GET /api/v1/users/me` - 获取当前用户信息
- ✅ `PUT /api/v1/users/me` - 更新用户信息

### 分类管理
- ✅ `GET /api/v1/categories/` - 获取所有分类
- ✅ `GET /api/v1/categories/{category_id}` - 获取分类详情
- ✅ `POST /api/v1/categories/` - 创建分类（管理员）

### 商品管理
- ✅ `GET /api/v1/products/` - 获取商品列表（支持过滤、排序、分页）
- ✅ `GET /api/v1/products/{id}` - 获取商品详情
- ✅ `POST /api/v1/products/search` - 商品搜索（JSON请求体）
- ✅ `POST /api/v1/products/quick-search` - 快速商品搜索
- ✅ `POST /api/v1/products/` - 创建商品（管理员）

### 购物车操作
- ✅ `GET /api/v1/cart/` - 查看购物车
- ✅ `POST /api/v1/cart/items` - 添加商品到购物车
- ✅ `PUT /api/v1/cart/items/{product_id}` - 更新购物车商品数量
- ✅ `DELETE /api/v1/cart/items/{product_id}` - 移除购物车商品
- ✅ `POST /api/v1/cart/add` - 兼容性添加商品接口
- ✅ `DELETE /api/v1/cart/remove/{product_id}` - 兼容性移除商品接口

### 订单管理
- ✅ `POST /api/v1/orders/` - 创建订单
- ✅ `GET /api/v1/orders/{id}` - 获取订单详情
- ✅ `GET /api/v1/orders/?scope=user` - 查询用户订单
- ✅ `GET /api/v1/orders/?scope=all` - 查询所有订单（管理员）
- ✅ `POST /api/v1/orders/checkout` - 订单结账
- ✅ `POST /api/v1/orders/search` - 订单搜索（支持状态过滤）
- ✅ `POST /api/v1/orders/admin/search` - 管理员高级订单搜索

## 🔧 高级功能

### 1. 自定义 Hooks 函数

`drun_hooks.py` 提供丰富的自定义函数：

**模板辅助函数**
```yaml
# 时间戳
headers: { X-Timestamp: ${ts()} }

# UUID生成
email: user_${uid()}@example.com

# 短UUID生成
username: user_${short_uid(8)}
```

**SQL断言函数**
```yaml
# 验证订单数据
validate:
  - eq: [$.data.total, ${expected_sql_value($order_id, column="total")}]

# 验证库存扣减
validate:
  - eq: [$.data.stock, ${get_product_stock($product_id)}]
```

### 2. 标签过滤

```bash
# 只运行smoke测试
drun run testcases -k "smoke"

# 运行关键测试
drun run testcases -k "critical or smoke"

# 排除管理员测试
drun run testcases -k "regression and not admin"
```

### 3. 格式转换示例

#### 从 cURL 导入
```bash
drun convert converts/curl/sample.curl \
  --outfile testcases/from_curl.yaml \
  --placeholders \
  --split-output
```

#### 从 Postman 导入
```bash
drun convert converts/postman/sample_collection.json \
  --postman-env converts/postman/sample_environment.json \
  --split-output \
  --suite-out testsuites/from_postman.yaml \
  --placeholders
```

#### 从 HAR 导入
```bash
drun convert converts/har/sample_recording.har \
  --exclude-static \
  --only-2xx \
  --split-output \
  --outfile testcases/from_har.yaml
```

#### 从 OpenAPI 导入
```bash
drun convert-openapi converts/openapi/sample_openapi.json \
  --tags users,orders \
  --split-output \
  --base-url http://localhost:8000 \
  --outfile testcases/from_openapi.yaml
```

## 📈 测试策略

### 测试分层策略

| 测试类型 | 覆盖范围 | 执行时间 | 运行频率 | 目标 |
|----------|----------|----------|----------|------|
| **冒烟测试** | 核心功能 | ~30秒 | 每次提交 | 快速验证系统可用性 |
| **回归测试** | 全功能覆盖 | ~5-10分钟 | 每日构建 | 确保功能完整性 |
| **E2E测试** | 业务流程 | ~1分钟 | 版本发布 | 验证关键用户旅程 |
| **专项测试** | 特定功能 | ~2-5分钟 | 功能变更 | 深度测试特定模块 |

### 质量指标

- **API覆盖率**: 100% (所有公开接口)
- **功能覆盖率**: 95%+ (核心业务流程)
- **断言覆盖率**: 90%+ (状态码、数据结构、业务逻辑)
- **数据库验证**: 完整的数据一致性检查

## 🐛 故障排查

### 常见问题解决方案

#### 1. 数据库连接失败
```bash
Error: Cannot connect to MySQL database
```
**解决方案**:
1. 检查 `.env` 中的数据库配置
2. 确认端口使用 `8020`（非默认3306）
3. 验证数据库服务运行: `nc -zv 110.40.159.145 8020`

#### 2. 管理员权限测试失败
```bash
Error: 403 Forbidden
```
**解决方案**:
```sql
-- 在数据库中设置管理员权限
UPDATE users SET role='admin' WHERE username='admin';
```

#### 3. SQL断言执行失败
```bash
Error: SQL assertion failed
```
**解决方案**:
1. 确认 `MYSQL_*` 环境变量配置正确，例如 `MYSQL_MAIN__DEFAULT__DSN`
2. 检查数据库连接权限
3. 验证SQL语句语法

#### 4. Token过期问题
**解决方案**:
- 重新运行登录测试获取新Token
- 检查Token自动刷新机制

## 🔄 CI/CD 集成

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
          MYSQL_MAIN__DEFAULT__DSN: ${{ secrets.MYSQL_MAIN_DEFAULT_DSN }}
        run: |
          cd ecommerce-api-test
          drun run testsuites/testsuite_smoke.yaml \
            --html reports/smoke_report.html

      - name: Upload Reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-reports
          path: ecommerce-api-test/reports/
```

### 测试报告集成

- **HTML报告**: 可视化测试结果，适合开发团队查看
- **JSON报告**: 机器可读格式，适合CI/CD系统解析
- **日志文件**: 详细的执行过程记录，便于问题诊断

## 📊 项目统计

- **测试用例**: 17个YAML文件
- **测试套件**: 3个套件文件
- **代码行数**: 2,000+行测试代码
- **API覆盖**: 21个核心接口（包含新增端点）
- **数据库表**: 6个业务表验证
- **转换示例**: 4种格式（cURL、Postman、HAR、OpenAPI）

## 📚 相关文档

- [Drun 官方文档](https://github.com/Devliang24/drun)
- [API 接口文档](http://110.40.159.145:9099/docs)
- [OpenAPI 规范](http://110.40.159.145:9099/api/v1/openapi.json)
- [格式转换详细指南](./converts/README.md)

## 🤝 贡献指南

欢迎贡献新的测试用例或改进现有测试！

### 贡献流程
1. Fork 本项目
2. 创建特性分支: `git checkout -b feature/amazing-feature`
3. 提交更改: `git commit -m 'Add amazing feature'`
4. 推送分支: `git push origin feature/amazing-feature`
5. 发起 Pull Request

### 代码规范
- 测试用例命名遵循 `test_[feature]_[scenario].yaml` 格式
- 使用有意义的步骤描述
- 添加适当的断言验证
- 保持配置文件简洁清晰

## 📝 版本历史

### v2.5.0 (2025-10-30)
- 🆕 新增`test_new_endpoints.yaml`测试用例，覆盖最新API端点
- 📝 更新API接口文档，新增6个端点覆盖
- 🔧 修复分类详情端点参数名称不一致问题
- 📊 API覆盖率从15个提升到21个核心接口

### v2.4.0 (2025-10-30)
- ✨ 完成项目重构和文档优化
- 🧹 清理冗余文档文件
- 🔧 完善环境配置和数据库连接

### v1.0.0 (2025-10-29)
- 🎉 初始项目创建
- ✅ 完成16个核心测试用例
- ✅ 实现3个测试套件
- ✅ 集成SQL断言功能
- ✅ 支持4种格式转换

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 📧 邮箱: test-team@example.com
- 🐛 问题反馈: [GitHub Issues](https://github.com/Devliang24/drun/issues)
- 📖 文档: [项目Wiki](https://github.com/Devliang24/drun/wiki)

---

**⭐ 如果这个项目对您有帮助，请给我们一个 Star！**

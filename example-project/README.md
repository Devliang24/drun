# Drun Example Project

这是一个完整的 Drun 项目示例，展示了如何组织和使用 Drun 进行 API 测试。

## 📁 目录结构

```
example-project/
├── README.md              # 本文件
├── drun_hooks.py          # 自定义钩子函数
├── testcases/             # 测试用例目录
│   ├── test_auth.yaml
│   ├── test_cart.yaml
│   ├── test_orders.yaml
│   └── ...
├── testsuites/            # 测试套件目录
│   ├── testsuite_smoke.yaml
│   ├── testsuite_regression.yaml
│   └── testsuite_permissions.yaml
├── logs/                  # 测试运行日志（自动生成）
└── reports/               # 测试报告（自动生成）
```

## 🚀 快速开始

### 1. 安装 Drun

```bash
pip install drun
```

### 2. 配置环境变量

复制项目根目录的 `.env` 文件到此目录（可选）：

```bash
cp ../.env .
```

或者设置环境变量：

```bash
export BASE_URL=http://localhost:8000
export USER_USERNAME=testuser
export USER_PASSWORD=testpass
```

### 3. 运行测试

#### 运行单个测试用例

```bash
drun run testcases/test_auth.yaml
```

#### 运行测试套件

```bash
drun run testsuites/testsuite_smoke.yaml
```

#### 运行所有测试

```bash
drun run testcases/
```

#### 使用标签过滤

```bash
drun run testcases/ --tags smoke
drun run testcases/ --tags "smoke,critical"
```

## 📝 测试用例说明

### `testcases/` 目录

包含各个功能模块的测试用例：

- **test_auth.yaml** - 用户认证测试（登录、注册）
- **test_cart.yaml** - 购物车功能测试
- **test_orders.yaml** - 订单管理测试
- **test_catalog.yaml** - 商品目录测试
- **test_user_profile.yaml** - 用户资料测试
- **test_e2e_purchase.yaml** - 端到端购买流程测试

### `testsuites/` 目录

包含不同场景的测试套件：

- **testsuite_smoke.yaml** - 冒烟测试套件（快速验证核心功能）
- **testsuite_regression.yaml** - 回归测试套件（全面测试）
- **testsuite_permissions.yaml** - 权限测试套件

## 🔧 自定义钩子

`drun_hooks.py` 文件包含自定义的钩子函数，用于：

- 数据准备
- 自定义断言
- 测试前后的清理工作
- 动态数据生成

查看文件了解更多详情。

## 📊 查看报告

测试运行后，报告会自动生成在 `reports/` 目录：

```bash
# 在浏览器中打开最新的报告
open reports/report-*.html  # macOS
xdg-open reports/report-*.html  # Linux
start reports/report-*.html  # Windows
```

## 📚 更多文档

- [Drun CLI 文档](../docs/CLI.md)
- [测试用例编写指南](../docs/EXAMPLES.md)
- [参考手册](../docs/REFERENCE.md)
- [CI/CD 集成](../docs/CI_CD.md)

## 💡 提示

1. **环境隔离**：建议为不同环境（开发、测试、生产）创建不同的 `.env` 文件
2. **版本控制**：`logs/` 和 `reports/` 目录已在 `.gitignore` 中，不会被提交
3. **钩子函数**：可以在 `drun_hooks.py` 中添加自定义逻辑
4. **参数化**：使用 `config.parameters` 实现数据驱动测试

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用与 Drun 相同的许可证。


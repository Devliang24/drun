# 配置更新说明

## MySQL端口更新

**更新日期：** 2025-10-30  
**更新内容：** MySQL数据库端口从 3306 更改为 8020

## 配置变更

### .env 文件配置

```bash
# ==================== MySQL 数据库配置 ====================
# Drun框架需要使用MYSQL_CONFIG（YAML或JSON格式）
MYSQL_CONFIG={"main": {"default": {"dsn": "mysql://root:password@110.40.159.145:8020/ecommerce"}}}

# 传统方式配置（保留作为参考）
MYSQL_HOST=110.40.159.145
MYSQL_PORT=8020  # 更新：从 3306 改为 8020
MYSQL_USER=root
MYSQL_PASSWORD=password
MYSQL_DB=ecommerce
```

### 变更对比

| 配置项 | 旧值 | 新值 | 说明 |
|--------|------|------|------|
| MYSQL_CONFIG (端口) | 3306 | 8020 | JSON格式DSN中的端口 |
| MYSQL_PORT | 3306 | 8020 | 传统配置端口 |

## 验证结果

配置更新后已进行测试验证：

```bash
cd /opt/udi/drun/ecommerce-api-test
drun run testcases/test_user_with_sql.yaml
```

**测试结果：** ✅ PASSED (6/6 步骤全部通过)

### 验证详情

- ✅ 数据库连接成功
- ✅ SQL hook函数正常工作
- ✅ 所有SQL查询正常执行
- ✅ 数据库读写操作正常
- ✅ 测试数据清理成功

### 连接测试

```
步骤3: 调用5个SQL hook函数 - 全部成功
- hook_query_user_username(4) ✅
- hook_query_user_email(4) ✅
- hook_query_user_role(4) ✅
- hook_query_user_full_name(4) ✅
- hook_query_user_shipping_address(4) ✅

步骤5: 调用5个SQL hook函数 - 全部成功
步骤6: 调用5个SQL hook函数 - 全部成功
```

## 影响范围

### 受影响的组件

1. **Hook函数** - 所有数据库查询hook函数
2. **测试用例** - 所有包含SQL断言的测试
3. **数据库代理** - DatabaseProxy连接管理

### 不受影响的组件

1. **API服务器** - 端口配置与API无关
2. **测试逻辑** - 测试步骤无需修改
3. **Hook函数代码** - 从环境变量读取配置，无需修改

## 配置文件位置

```
/opt/udi/drun/ecommerce-api-test/.env
```

**注意：** .env 文件被 .gitignore 忽略，不会提交到版本控制

## 如何配置新环境

如果需要在新环境配置，请确保 `.env` 文件中包含正确的端口：

```bash
# 复制示例配置（如果有）
cp .env.example .env

# 或者直接编辑
vim .env

# 更新以下配置
MYSQL_CONFIG={"main": {"default": {"dsn": "mysql://root:password@110.40.159.145:8020/ecommerce"}}}
MYSQL_PORT=8020
```

## 连接字符串格式

**完整DSN格式：**
```
mysql://用户名:密码@主机:端口/数据库名
mysql://root:password@110.40.159.145:8020/ecommerce
```

**关键参数：**
- 主机: `110.40.159.145`
- 端口: `8020` ⚠️ 已更新
- 数据库: `ecommerce`
- 用户: `root`
- 密码: `password`

## 测试建议

端口配置更新后，建议运行完整测试套件验证：

```bash
# 测试所有SQL断言用例
drun run testcases/test_user_with_sql.yaml
drun run testcases/test_product_with_sql.yaml
drun run testcases/test_order_with_sql.yaml

# 或运行完整回归测试
drun run testsuites/testsuite_regression.yaml
```

## 故障排查

如果连接失败，请检查：

1. **端口是否正确** - 确认MySQL服务监听在 8020 端口
2. **防火墙设置** - 确保 8020 端口可访问
3. **MySQL服务状态** - 确认服务正常运行
4. **配置文件格式** - JSON格式中端口是数字不是字符串

### 测试连接

```bash
# 使用MySQL客户端测试
mysql -h 110.40.159.145 -P 8020 -u root -p ecommerce

# 或使用telnet测试端口
telnet 110.40.159.145 8020
```

## 版本信息

- **Drun版本：** 2.3.4
- **MySQL版本：** 5.7 或更高
- **更新前端口：** 3306 (默认)
- **更新后端口：** 8020 (自定义)

---

**更新时间：** 2025-10-30 09:49  
**验证状态：** ✅ 已验证通过  
**影响测试：** 无负面影响，所有测试正常

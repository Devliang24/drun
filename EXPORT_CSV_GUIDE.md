# CSV 导出功能使用指南

## 功能概述

drun 现在支持将 API 响应中的数组数据导出为 CSV 文件，类似 Postman 的数据导出功能。

## 配置语法

### 基础用法

```yaml
export:
  csv:
    data: $.data.users           # 必填：JMESPath 表达式
    file: data/users.csv         # 必填：输出文件路径
```

### 完整配置

```yaml
export:
  csv:
    data: $.data.orders          # 必填：数组数据源
    file: data/orders.csv        # 必填：输出文件路径
    columns: [id, name, amount]  # 可选：指定导出列（默认：全部）
    encoding: utf-8              # 可选：文件编码（默认：utf-8）
    mode: overwrite              # 可选：overwrite | append（默认：overwrite）
    delimiter: ","               # 可选：分隔符（默认：逗号）
```

## 使用场景

### 场景1：基础导出

```yaml
config:
  name: 导出用户数据
  base_url: https://api.example.com

steps:
  - name: 获取并导出用户列表
    request:
      method: GET
      path: /api/users
    export:
      csv:
        data: $.data.users
        file: data/users.csv
    validate:
      - eq: [status_code, 200]
```

### 场景2：提取 + 导出 + 验证

```yaml
steps:
  - name: 获取用户列表
    request:
      method: GET
      path: /api/users
    extract:
      userCount: $.data.total           # 提取到变量
      firstUserId: $.data.users[0].id
    export:
      csv:
        data: $.data.users               # 导出到文件
        file: data/users.csv
    validate:
      - gt: [$userCount, 0]              # 使用提取的变量
      - eq: [status_code, 200]
```

### 场景3：选择特定列

```yaml
steps:
  - name: 导出订单摘要
    request:
      method: GET
      path: /api/orders
    export:
      csv:
        data: $.data.orders
        file: reports/orders_summary.csv
        columns: [orderId, customerName, totalAmount, status]
```

**输出示例** (`orders_summary.csv`):
```csv
orderId,customerName,totalAmount,status
1001,Alice,299.99,completed
1002,Bob,149.50,pending
```

### 场景4：分页追加导出

```yaml
config:
  name: 分页导出产品数据
  base_url: https://api.example.com
  parameters:
    - page: [1, 2, 3, 4, 5]

steps:
  - name: 导出第 $page 页产品
    request:
      method: GET
      path: /api/products?page=$page&limit=100
    export:
      csv:
        data: $.data.items
        file: data/all_products.csv
        mode: append                     # 追加模式
    validate:
      - eq: [status_code, 200]
```

### 场景5：动态文件名

```yaml
steps:
  - name: 导出每日报表
    request:
      method: GET
      path: /api/reports/daily
    export:
      csv:
        data: $.data.records
        file: reports/daily_${now()}.csv  # 使用内置函数
```

### 场景6：过滤后导出

```yaml
steps:
  - name: 导出活跃用户
    request:
      method: GET
      path: /api/users
    export:
      csv:
        data: $.data.users[?status=='active']  # JMESPath 过滤
        file: data/active_users.csv
```

### 场景7：根级数组

```yaml
steps:
  - name: 导出产品列表
    request:
      method: GET
      path: /api/products
    export:
      csv:
        data: $                          # 响应直接是数组
        file: data/products.csv
```

### 场景8：自定义分隔符（TSV）

```yaml
steps:
  - name: 导出为 TSV 格式
    request:
      method: GET
      path: /api/data
    export:
      csv:
        data: $.items
        file: data/output.tsv
        delimiter: "\t"                   # Tab 分隔
```

## data 字段支持的写法

| 写法 | 说明 | 示例 |
|------|------|------|
| `$.path.to.array` | 标准嵌套路径 | `$.data.users` |
| `$[index]` | 数组索引 | `$.items[0]` |
| `$[*]` | 所有数组元素 | `$.users[*]` |
| `$[start:end]` | 数组切片 | `$.items[0:10]` |
| `$[?expr]` | 条件过滤 | `$.users[?age > 18]` |
| `$[*].[a,b]` | 字段投影 | `$.users[*].[id, name]` |
| `$` | 根级数组 | `$`（响应直接是数组） |
| `$.stream_events` | 流式响应 | 特殊字段 |

## 日志输出

```
[STEP 1/1] 获取用户列表
[REQ] GET https://api.example.com/api/users
[RESP] 200 OK (245ms)
[EXTRACT] userCount = 150 from $.data.total
[EXPORT CSV] 150 rows → data/users.csv
[VALIDATE] status_code == 200 ✓
```

## 错误处理

### 错误1：data 不是数组

```yaml
export:
  csv:
    data: $.data.user          # 返回对象而非数组
    file: data/user.csv
```

**错误信息**：
```
ValueError: export.csv.data 必须返回数组，实际类型：dict
```

### 错误2：指定的列不存在

```yaml
export:
  csv:
    data: $.data.users
    file: data/users.csv
    columns: [id, name, nonexistent]
```

**错误信息**：
```
ValueError: export.csv.columns 指定的列不存在：{'nonexistent'}
可用列：['id', 'username', 'email', 'age', 'role']
```

### 错误3：空数组处理

```yaml
export:
  csv:
    data: $.data.users         # users 是 []
    file: data/users.csv
    columns: [id, name]
```

**结果**：创建只有 header 的空文件
```csv
id,name
```

## 配置对比

```yaml
# 字段语义清晰，操作对称
extract:                        # 提取：响应 → 变量（内存）
  userId: $.data.id
  userName: $.data.name
  
export:                         # 导出：响应 → 文件（磁盘）
  csv:
    data: $.data.users
    file: data/users.csv
    
validate:                       # 验证：断言检查
  - eq: [status_code, 200]
  - gt: [$userId, 0]
```

## 技术细节

- **路径解析**：与 CSV 参数化使用相同的路径解析逻辑（相对于项目根目录）
- **模板支持**：文件路径支持 `${now()}` 等动态变量
- **JMESPath 引擎**：复用现有的 `_eval_extract()` 方法，支持所有 JMESPath 语法
- **CSV 标准**：使用 Python 标准库 `csv.DictWriter`
- **错误友好**：清晰的错误提示和数据验证

## 与 extract 的区别

| 特性 | extract | export |
|------|---------|--------|
| 目标 | 内存变量 | 磁盘文件 |
| 数据类型 | 任意类型 | 数组（列表） |
| 用途 | 临时使用 | 持久化存储 |
| 验证 | 无 | 类型和列名验证 |
| 示例 | `userId: $.data.id` | `csv: {data: $.data.users, file: users.csv}` |

## 常见问题

### Q: 如何导出嵌套数组？

A: 使用 JMESPath 展平数组：
```yaml
export:
  csv:
    data: $.departments[*].employees[*]  # 展平所有部门的员工
    file: data/all_employees.csv
```

### Q: 如何导出多个数组到不同文件？

A: 在多个 step 中分别导出：
```yaml
steps:
  - name: 导出用户
    request:
      method: GET
      path: /api/data
    export:
      csv:
        data: $.users
        file: data/users.csv
  
  - name: 导出订单
    request:
      method: GET
      path: /api/data
    export:
      csv:
        data: $.orders
        file: data/orders.csv
```

### Q: 如何处理中文列名？

A: CSV 会自动使用响应中的字段名作为列名：
```json
{
  "data": {
    "用户列表": [
      {"用户ID": 1, "用户名": "张三"}
    ]
  }
}
```

```yaml
export:
  csv:
    data: $.data.用户列表
    file: data/users.csv
```

输出：
```csv
用户ID,用户名
1,张三
```

## 下一步

- 查看完整示例：`testcases/test_export_csv.yaml`
- 了解更多 JMESPath 语法：https://jmespath.org/
- 参考 CSV 参数化导入功能：`testcases/test_import_users.yaml`

# 环境变量中的 JSON 数组支持

## 功能说明

从本版本开始，`${ENV()}` 函数支持自动解析环境变量中的 JSON 数组和对象。

## 使用示例

### 1. 在 .env 文件中定义数组

```env
# 支持 Python 格式（单引号）
BATCH_NUMBER=['Z258180041', 'Z258180042', 'Z258180043']

# 也支持标准 JSON 格式（双引号）
BATCH_NUMBER_JSON=["Z258180041", "Z258180042", "Z258180043"]

# 支持 JSON 对象
CONFIG={"timeout": 30, "retry": 3}

# 普通字符串保持不变
API_KEY=your-secret-key-here
```

### 2. 在测试用例中使用

```yaml
name: 批量处理测试
config:
  base_url: http://192.168.121.121:8100

steps:
  - name: 启动多个批次
    request:
      method: POST
      path: /api/v1/dispatcher/start-batches
      headers:
        Authorization: Bearer ${ENV(API_KEY)}
        Content-Type: application/json
      json:
        batchNumbers: ${ENV(BATCH_NUMBER)}  # 自动解析为数组
        machineIp: 10.11.10.43
```

### 3. 实际效果

**修复前**（错误）：
```json
{
  "batchNumbers": "['Z258180041', 'Z258180042', 'Z258180043']",
  "machineIp": "10.11.10.43"
}
```
❌ 服务器返回错误：`batchNumbers must be an array`

**修复后**（正确）：
```json
{
  "batchNumbers": ["Z258180041", "Z258180042", "Z258180043"],
  "machineIp": "10.11.10.43"
}
```
✅ 服务器正确接收数组类型

## 支持的格式

### 数组格式

```env
# Python 格式（单引号）
ITEMS=['item1', 'item2', 'item3']

# JSON 格式（双引号）
ITEMS=["item1", "item2", "item3"]

# 数字数组
NUMBERS=[1, 2, 3, 4, 5]

# 混合类型
MIXED=["string", 123, true, null]
```

### 对象格式

```env
# 简单对象
CONFIG={"key": "value", "count": 10}

# 嵌套对象
NESTED={"outer": {"inner": "value"}}

# 包含数组的对象
COMPLEX={"items": ["a", "b", "c"], "count": 3}
```

### 字符串格式（保持不变）

```env
# 普通字符串不受影响
NAME=John Doe
URL=https://api.example.com
TOKEN=abc123xyz
```

## 技术细节

- **自动检测**：只有以 `[` 或 `{` 开头的字符串才会尝试解析
- **容错处理**：解析失败时自动降级为原始字符串
- **格式支持**：同时支持标准 JSON 和 Python 列表格式
- **向后兼容**：不影响现有的字符串类型环境变量

## 常见问题

### Q: 为什么我的数组还是字符串？

A: 确保环境变量值以 `[` 开头并以 `]` 结尾：

```env
# ✓ 正确
ARRAY=['a', 'b', 'c']

# ✗ 错误（会被当作普通字符串）
ARRAY=a,b,c
```

### Q: 可以在数组中使用特殊字符吗？

A: 可以，但需要确保 JSON 格式正确：

```env
# ✓ 正确
PATHS=["/api/v1", "/api/v2"]

# ✓ 正确（转义引号）
MESSAGES=["He said \"Hello\"", "She replied"]
```

### Q: 复杂对象会被正确解析吗？

A: 是的，只要符合 JSON 格式：

```env
# ✓ 正确
CONFIG={"api": {"base": "https://api.com", "version": "v1"}, "timeout": 30}
```

## 实现原理

修改了 `drun/templating/engine.py` 中的 `ENV()` 函数：

1. 检测环境变量值是否以 `[` 或 `{` 开头
2. 尝试使用 `json.loads()` 解析
3. 如果失败，尝试将单引号转换为双引号后再解析
4. 仍然失败则返回原始字符串

这确保了最大的兼容性和容错性。

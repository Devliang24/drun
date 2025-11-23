# 环境变量的智能类型转换

## 功能说明

从本版本开始，`${ENV()}` 函数支持自动识别并转换环境变量的类型，包括：
- JSON 数组和对象
- 数字（整数、浮点数）
- 布尔值（true/false）
- null 值
- 普通字符串（保持不变）

## 使用示例

### 1. 在 .env 文件中定义各种类型

```env
# 数组（支持 Python 和 JSON 格式）
BATCH_NUMBER=['Z258180041', 'Z258180042', 'Z258180043']
BATCH_NUMBER_JSON=["Z258180041", "Z258180042", "Z258180043"]

# JSON 对象
CONFIG={"timeout": 30, "retry": 3}

# 数字（自动转换为 int 或 float）
USER_ID=23
PRICE=19.99
NEGATIVE_NUM=-42

# 布尔值（不区分大小写）
IS_ACTIVE=true
IS_ENABLED=false

# null 值
NULL_VALUE=null

# 普通字符串保持不变
API_KEY=your-secret-key-here
USERNAME=john_doe
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

### 1. 数组格式

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

### 2. 对象格式

```env
# 简单对象
CONFIG={"key": "value", "count": 10}

# 嵌套对象
NESTED={"outer": {"inner": "value"}}

# 包含数组的对象
COMPLEX={"items": ["a", "b", "c"], "count": 3}
```

### 3. 数字格式

```env
# 整数（自动转换为 int）
USER_ID=23
NEGATIVE=-42
ZERO=0

# 浮点数（自动转换为 float）
PRICE=19.99
TAX_RATE=0.08
NEGATIVE_FLOAT=-3.14
```

### 4. 布尔值格式

```env
# 不区分大小写
IS_ACTIVE=true
IS_ENABLED=false
DEBUG=TRUE
PRODUCTION=FALSE
```

### 5. null 值格式

```env
# 转换为 Python 的 None
NULL_VALUE=null
EMPTY=NULL
```

### 6. 字符串格式（保持不变）

```env
# 普通字符串不受影响
NAME=John Doe
URL=https://api.example.com
TOKEN=abc123xyz
EMAIL=test@example.com
MIXED_TEXT=user_123  # 包含数字但不是纯数字
```

## 技术细节

- **智能检测**：自动识别值的类型特征
  - 数组/对象：以 `[` 或 `{` 开头
  - 布尔值：`true`/`false`（不区分大小写）
  - null：`null`（不区分大小写）
  - 数字：纯数字或带小数点的数字
  - 字符串：其他所有情况
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

修改了 `drun/templating/engine.py` 中的 `_try_parse_json()` 函数：

1. **JSON 结构**：检测是否以 `[` 或 `{` 开头，尝试解析为数组/对象
2. **布尔值**：检测 `true`/`false`（不区分大小写），转换为 Python 的 `True`/`False`
3. **null 值**：检测 `null`（不区分大小写），转换为 Python 的 `None`
4. **整数**：检测纯数字字符串（包括负数），转换为 `int`
5. **浮点数**：检测包含小数点的数字，转换为 `float`
6. **字符串**：其他所有情况保持为原始字符串

这确保了最大的兼容性、容错性和便利性。

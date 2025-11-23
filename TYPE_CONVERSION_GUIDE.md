# 环境变量智能类型转换指南

## 问题背景

在 API 测试中，经常会遇到类型不匹配的问题：

```
❌ [VALIDATION] $.data.id eq '23' => actual=23 | FAIL
```

原因：
- `.env` 文件中的值都是字符串：`USER_ID=23`（字符串 "23"）
- API 返回的是真实类型：`{"id": 23}`（数字 23）
- Python 严格的类型检查：`23 != "23"`

## 解决方案

从本版本开始，`${ENV()}` 函数会自动识别并转换环境变量的类型！

## 自动转换示例

### 数字类型

**.env 文件：**
```env
USER_ID=23
PRICE=19.99
NEGATIVE=-42
```

**自动转换为：**
```python
USER_ID → 23 (int)
PRICE → 19.99 (float)
NEGATIVE → -42 (int)
```

**测试用例：**
```yaml
validate:
  - eq: [$.data.id, ${ENV(USER_ID)}]  # ✓ 23 == 23
  - eq: [$.price, ${ENV(PRICE)}]      # ✓ 19.99 == 19.99
```

### 布尔值类型

**.env 文件：**
```env
IS_ACTIVE=true
DEBUG=false
PRODUCTION=TRUE  # 不区分大小写
```

**自动转换为：**
```python
IS_ACTIVE → True (bool)
DEBUG → False (bool)
PRODUCTION → True (bool)
```

**测试用例：**
```yaml
validate:
  - eq: [$.is_active, ${ENV(IS_ACTIVE)}]  # ✓ True == True
```

### null 值类型

**.env 文件：**
```env
OPTIONAL_FIELD=null
```

**自动转换为：**
```python
OPTIONAL_FIELD → None
```

**测试用例：**
```yaml
validate:
  - eq: [$.optional, ${ENV(OPTIONAL_FIELD)}]  # ✓ None == None
```

### 数组类型

**.env 文件：**
```env
# Python 格式（单引号）
BATCH_IDS=['id1', 'id2', 'id3']

# JSON 格式（双引号）
TAGS=["tag1", "tag2"]
```

**自动转换为：**
```python
BATCH_IDS → ['id1', 'id2', 'id3'] (list)
TAGS → ['tag1', 'tag2'] (list)
```

**测试用例：**
```yaml
json:
  batchIds: ${ENV(BATCH_IDS)}  # ✓ 发送真实数组
```

### 对象类型

**.env 文件：**
```env
CONFIG={"timeout": 30, "retry": 3}
```

**自动转换为：**
```python
CONFIG → {'timeout': 30, 'retry': 3} (dict)
```

### 字符串类型（保持不变）

**.env 文件：**
```env
USERNAME=john_doe
EMAIL=test@example.com
API_KEY=abc123xyz
MIXED_TEXT=user_123  # 包含数字但不是纯数字
```

**保持为字符串：**
```python
USERNAME → 'john_doe' (str)
EMAIL → 'test@example.com' (str)
API_KEY → 'abc123xyz' (str)
MIXED_TEXT → 'user_123' (str)
```

## 实际应用场景

### 场景 1：用户 ID 验证

**.env：**
```env
REGISTERED_USER_ID=23
```

**测试用例：**
```yaml
steps:
  - name: 获取用户信息
    request:
      method: GET
      path: /api/v1/users/me
    validate:
      - eq: [$.data.id, ${ENV(REGISTERED_USER_ID)}]  # ✓ 现在能正确比较
```

**修复前：**
```
❌ [VALIDATION] $.data.id eq '23' => actual=23 | FAIL
```

**修复后：**
```
✓ [VALIDATION] $.data.id eq 23 => actual=23 | PASS
```

### 场景 2：批量操作

**.env：**
```env
BATCH_NUMBER=['Z001', 'Z002', 'Z003']
```

**测试用例：**
```yaml
steps:
  - name: 批量处理
    request:
      method: POST
      path: /api/v1/batch/process
      json:
        batchNumbers: ${ENV(BATCH_NUMBER)}  # ✓ 发送真实数组
```

**发送的请求体：**
```json
{
  "batchNumbers": ["Z001", "Z002", "Z003"]  ✓ 数组
}
```

而不是：
```json
{
  "batchNumbers": "['Z001', 'Z002', 'Z003']"  ✗ 字符串
}
```

## 转换规则

| .env 值 | 自动转换为 | Python 类型 |
|---------|-----------|------------|
| `23` | `23` | `int` |
| `-42` | `-42` | `int` |
| `19.99` | `19.99` | `float` |
| `true` / `TRUE` | `True` | `bool` |
| `false` / `FALSE` | `False` | `bool` |
| `null` / `NULL` | `None` | `NoneType` |
| `['a','b']` | `['a','b']` | `list` |
| `{"k":"v"}` | `{'k':'v'}` | `dict` |
| `hello` | `'hello'` | `str` |
| `user_123` | `'user_123'` | `str` |

## 注意事项

1. **纯数字才转换**：`123` → `int`，但 `user_123` 保持为字符串
2. **小数点识别**：`19.99` → `float`，但 `19` → `int`
3. **大小写不敏感**：`true`、`TRUE`、`True` 都转换为 `True`
4. **容错处理**：无法解析时返回原字符串，不会报错
5. **向后兼容**：现有的字符串环境变量完全不受影响

## 技术实现

修改了 `drun/templating/engine.py` 中的 `_try_parse_json()` 函数，按以下顺序尝试解析：

1. JSON 数组/对象（`[...]` 或 `{...}`）
2. 布尔值（`true`/`false`）
3. null 值（`null`）
4. 整数（纯数字）
5. 浮点数（包含小数点）
6. 字符串（其他所有情况）

这确保了智能转换的同时保持最大的兼容性。

## 总结

✅ **优点：**
- 无需修改现有测试用例
- 自动处理类型转换
- 向后兼容
- 智能识别

✅ **解决的问题：**
- 数字比较失败
- 数组字符串化
- 布尔值类型不匹配
- 需要手动类型转换

🎉 **现在你可以直接在 .env 中使用自然的值格式，框架会自动处理类型转换！**

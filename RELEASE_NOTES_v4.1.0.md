# Drun v4.1.0 发布说明

发布日期：2025-11-23

## 🎉 重大更新

### 环境变量智能类型转换

从 v4.1.0 开始，`${ENV()}` 函数支持自动识别并转换环境变量的类型，无需手动处理类型不匹配问题！

## ✨ 新增功能

### 1. 自动类型转换

环境变量现在会根据其值的格式自动转换为正确的类型：

- **整数**：`USER_ID=23` → `23` (int)
- **浮点数**：`PRICE=19.99` → `19.99` (float)
- **布尔值**：`IS_ACTIVE=true` → `True` (bool)
- **null 值**：`NULL_VALUE=null` → `None`
- **JSON 数组**：`ITEMS=['a','b','c']` → `['a','b','c']` (list)
- **JSON 对象**：`CONFIG={"key":"value"}` → `{'key':'value'}` (dict)
- **字符串**：`NAME=John` → `'John'` (str, 保持不变)

### 2. 解决的核心问题

**问题：** 环境变量中的数字字符串无法与 API 返回的数字类型正确匹配

```
❌ 修复前：
.env: REGISTERED_USER_ID=23 (字符串)
API:  $.data.id = 23 (数字)
验证: [VALIDATION] $.data.id eq '23' => actual=23 | FAIL

✅ 修复后：
.env: REGISTERED_USER_ID=23
自动: 23 (int)
API:  $.data.id = 23 (数字)
验证: [VALIDATION] $.data.id eq 23 => actual=23 | PASS
```

## 📖 使用示例

### 示例 1：数字类型验证

```env
# .env
USER_ID=23
PRICE=19.99
```

```yaml
# test.yaml
validate:
  - eq: [$.data.id, ${ENV(USER_ID)}]      # ✓ 自动转换为 int
  - eq: [$.price, ${ENV(PRICE)}]          # ✓ 自动转换为 float
```

### 示例 2：数组类型请求

```env
# .env
BATCH_NUMBER=['Z001', 'Z002', 'Z003']
```

```yaml
# test.yaml
request:
  method: POST
  json:
    batchNumbers: ${ENV(BATCH_NUMBER)}  # ✓ 发送真实数组
```

**请求体（修复后）：**
```json
{
  "batchNumbers": ["Z001", "Z002", "Z003"]  ✓ 数组类型
}
```

### 示例 3：布尔值和 null

```env
# .env
IS_ACTIVE=true
OPTIONAL_FIELD=null
```

```yaml
# test.yaml
validate:
  - eq: [$.is_active, ${ENV(IS_ACTIVE)}]        # ✓ True
  - eq: [$.optional, ${ENV(OPTIONAL_FIELD)}]    # ✓ None
```

## 🔄 向后兼容性

✅ **完全向后兼容**
- 现有测试用例无需任何修改
- 普通字符串保持不变
- 包含数字的文本（如 `user_123`）不会被误转换
- 解析失败时安全降级为原字符串

## 📚 新增文档

1. **EXAMPLE_JSON_ARRAYS.md** - 更新为"环境变量的智能类型转换"
2. **TYPE_CONVERSION_GUIDE.md** - 详细的使用指南和实战示例

## 🔧 技术改进

### 核心修改

**文件：** `drun/templating/engine.py`

**函数：** `_try_parse_json()`

**转换顺序：**
1. JSON 数组/对象（`[...]` 或 `{...}`）
2. 布尔值（`true`/`false`，不区分大小写）
3. null 值（`null`，不区分大小写）
4. 整数（纯数字字符串，包括负数）
5. 浮点数（包含小数点的数字）
6. 字符串（其他所有情况）

## 🎯 适用场景

- API 返回数字 ID，需要与环境变量比较
- 需要发送 JSON 数组到 API
- 布尔值标志位的测试
- 可选字段的 null 值测试
- 批量数据处理

## ⚡ 性能影响

- **无性能损失**：仅在环境变量解析时执行一次
- **智能缓存**：渲染后的值会被缓存
- **容错设计**：解析失败立即返回，不会阻塞

## 📋 完整变更日志

### 新增 (Added)
- ✨ 环境变量自动类型转换（整数、浮点数、布尔值、null）
- ✨ JSON 数组和对象自动解析（支持 Python 和 JSON 格式）
- 📄 TYPE_CONVERSION_GUIDE.md 使用指南

### 改进 (Improved)
- 🔧 增强 `_try_parse_json()` 函数，支持更多类型识别
- 📝 更新 EXAMPLE_JSON_ARRAYS.md 文档

### 修复 (Fixed)
- 🐛 修复环境变量数字字符串与 API 数字类型比较失败的问题
- 🐛 修复数组环境变量被当作字符串发送的问题

## 🙏 致谢

感谢社区用户反馈的类型不匹配问题，这促使我们实现了这个智能转换功能。

## 📦 升级指南

### 从 v4.0.0 升级

```bash
pip install --upgrade drun
```

**无需修改任何代码！** 现有的测试用例将自动受益于新的类型转换功能。

### 验证版本

```bash
drun --version
# 输出: drun 4.1.0
```

## 🔗 相关链接

- [GitHub Repository](https://github.com/your-org/drun)
- [完整文档](./README.md)
- [类型转换指南](./TYPE_CONVERSION_GUIDE.md)
- [示例说明](./EXAMPLE_JSON_ARRAYS.md)

---

**版本号：** 4.1.0  
**发布日期：** 2025-11-23  
**重要程度：** ⭐⭐⭐⭐⭐ (强烈推荐升级)

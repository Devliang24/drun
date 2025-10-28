# contains_all 和 match_regex_all 断言使用指南

## 简介

新增了两个批量断言操作符，用于验证数组中所有元素是否满足特定条件：

- **`contains_all`**: 检查列表中所有元素是否都包含指定字符串
- **`match_regex_all`**: 检查列表中所有元素是否都匹配指定正则表达式

## 使用方法

### 1. 基本语法

```yaml
extract:
  # 提取数组字段
  all_model_names: "$.data.items[*].model_name"

validate:
  # 断言所有元素都包含指定字符串
  - contains_all: [$all_model_names, "Embedding"]
  
  # 断言所有元素都匹配正则表达式
  - match_regex_all: [$all_model_names, "^Deepexi-Embedding"]
```

### 2. 完整示例

```yaml
config:
  name: 测试 Embedding 模型列表
  base_url: https://api.example.com

steps:
  - name: 获取模型列表
    request:
      method: GET
      path: /api/v2/model
      params:
        category: Embeddings
        page_size: 12
    extract:
      # 提取所有 model_name
      all_model_names: "$.data.items[*].model_name"
      # 提取所有 category
      all_categories: "$.data.items[*].category"
      # 提取所有 tenant_id
      all_tenant_ids: "$.data.items[*].tenant_id"
    validate:
      - eq: [status_code, 200]
      
      # 断言所有 model_name 都包含 "Embedding"
      - contains_all: [$all_model_names, "Embedding"]
      
      # 断言所有 category 都包含 "Embedding"
      - contains_all: [$all_categories, "Embedding"]
      
      # 断言所有 tenant_id 都是 "dgi"
      - contains_all: [$all_tenant_ids, "dgi"]
      
      # 断言所有 model_name 都以 "Deepexi-Embedding" 开头
      - match_regex_all: [$all_model_names, "^Deepexi-Embedding"]
      
      # 断言所有 model_name 都包含连字符
      - match_regex_all: [$all_model_names, "-"]
```

## 操作符详解

### contains_all

**功能**: 检查列表中每个元素是否都包含指定的子字符串。

**参数**:
- 第一个参数：列表（从响应中提取的数组）
- 第二个参数：期望包含的字符串

**示例**:
```yaml
# 检查所有用户名都包含 "test"
- contains_all: [$all_usernames, "test"]

# 检查所有邮箱都包含 "@example.com"
- contains_all: [$all_emails, "@example.com"]
```

**行为**:
- 如果列表为空或不是列表类型，断言失败
- 如果任何一个元素不包含指定字符串，断言失败
- 只有当所有元素都包含指定字符串时，断言才通过

### match_regex_all

**功能**: 检查列表中每个元素是否都匹配指定的正则表达式。

**参数**:
- 第一个参数：列表（从响应中提取的数组）
- 第二个参数：正则表达式模式（字符串）

**示例**:
```yaml
# 检查所有 ID 都是数字格式
- match_regex_all: [$all_ids, "^\\d+$"]

# 检查所有邮箱格式正确
- match_regex_all: [$all_emails, "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"]

# 检查所有 URL 都以 https 开头
- match_regex_all: [$all_urls, "^https://"]

# 检查所有日期格式为 YYYY-MM-DD
- match_regex_all: [$all_dates, "^\\d{4}-\\d{2}-\\d{2}$"]
```

**行为**:
- 如果列表为空或不是列表类型，断言失败
- 如果任何一个元素不匹配正则表达式，断言失败
- 只有当所有元素都匹配正则表达式时，断言才通过

## 使用场景

### 场景 1: 验证 API 返回的所有记录符合命名规范
```yaml
validate:
  # 所有模型名称都以公司前缀开头
  - match_regex_all: [$all_model_names, "^CompanyName-"]
```

### 场景 2: 验证分页数据的一致性
```yaml
validate:
  # 所有记录都属于同一租户
  - contains_all: [$all_tenant_ids, "tenant-123"]
```

### 场景 3: 验证数据过滤结果
```yaml
validate:
  # 所有类别都包含搜索关键词
  - contains_all: [$all_categories, $search_keyword]
```

### 场景 4: 验证数据格式
```yaml
validate:
  # 所有手机号格式正确
  - match_regex_all: [$all_phones, "^1[3-9]\\d{9}$"]
  
  # 所有金额都是正数
  - match_regex_all: [$all_prices, "^\\d+(\\.\\d{1,2})?$"]
```

## 与传统方式对比

### 传统方式（逐个断言）
```yaml
validate:
  - contains: ["$.data.items[0].model_name", "Embedding"]
  - contains: ["$.data.items[1].model_name", "Embedding"]
  - contains: ["$.data.items[2].model_name", "Embedding"]
  - contains: ["$.data.items[3].model_name", "Embedding"]
  - contains: ["$.data.items[4].model_name", "Embedding"]
```

**缺点**:
- 需要知道数组长度
- 代码冗长重复
- 数组长度变化时需要修改

### 新方式（批量断言）
```yaml
extract:
  all_model_names: "$.data.items[*].model_name"
validate:
  - contains_all: [$all_model_names, "Embedding"]
```

**优点**:
- 一行代码完成所有检查
- 自动适应任意长度的数组
- 更清晰易读

## 注意事项

1. **必须先提取**：在使用 `contains_all` 或 `match_regex_all` 之前，必须先在 `extract` 部分提取数组
2. **变量引用**：使用 `$variable_name` 引用提取的变量
3. **正则转义**：在 YAML 中使用正则表达式时，需要对反斜杠进行转义（`\\d` 而不是 `\d`）
4. **空数组**：如果提取的数组为空，断言会失败

## 错误排查

### 错误：Unknown comparator: contains_all
**原因**: drun 版本过旧，不支持新操作符
**解决**: 更新到最新版本或重新安装：`pip install -e . --force-reinstall --no-deps`

### 错误：actual=None
**原因**: 变量未正确提取或变量名拼写错误
**解决**: 检查 extract 部分是否正确，确认变量名匹配

### 错误：'in <string>' requires string as left operand, not list
**原因**: 使用了错误的操作符或参数顺序
**解决**: 确保使用 `contains_all` 而不是 `contains`，参数顺序正确

## 实现细节

新操作符在 `/opt/udi/drun/drun/runner/assertions.py` 中实现：

```python
def op_contains_all(a: Any, b: Any) -> bool:
    """Check if all elements in list a contain string b"""
    if not isinstance(a, list):
        return False
    if not b:
        return False
    return all(str(b) in str(item) for item in a)

def op_match_regex_all(a: Any, b: Any) -> bool:
    """Check if all elements in list a match regex pattern b"""
    if not isinstance(a, list):
        return False
    pattern = str(b)
    return all(bool(re.search(pattern, str(item))) for item in a)
```

# regex vs match_regex_all 对比指南

## 概述

- **`regex`**: 用于单个值的正则表达式匹配
- **`match_regex_all`**: 用于列表中所有元素的正则表达式匹配

## 基本语法对比

### regex - 单个值匹配
```yaml
# 语法：regex: [字段路径, 正则表达式]
- regex: ["$.data.items[0].model_name", "^Deepexi-Embedding"]
```

### match_regex_all - 批量匹配
```yaml
# 语法：match_regex_all: [变量(列表), 正则表达式]
- match_regex_all: [$all_model_names, "^Deepexi-Embedding"]
```

## 详细对比示例

### 场景 1: 检查单个字段是否匹配正则

```yaml
steps:
  - name: 测试单个值
    request:
      method: GET
      path: /api/model/123
    validate:
      # ✅ 使用 regex - 检查单个 model_name
      - regex: ["$.model_name", "^Deepexi-Embedding"]
      - regex: ["$.id", "^\\d+$"]
      - regex: ["$.category", "Embedding"]
      - regex: ["$.version", "^v\\d+\\.\\d+\\.\\d+$"]
```

**适用场景：**
- 验证单个字段的格式（ID、版本号、邮箱等）
- 从响应中提取一个值并验证其模式
- 不需要遍历数组

---

### 场景 2: 检查数组中所有元素是否匹配正则

```yaml
steps:
  - name: 测试批量值
    request:
      method: GET
      path: /api/models
    extract:
      all_model_names: "$.data.items[*].model_name"
      all_ids: "$.data.items[*].id"
      all_emails: "$.data.users[*].email"
    validate:
      # ✅ 使用 match_regex_all - 检查所有 model_name
      - match_regex_all: [$all_model_names, "^Deepexi-Embedding"]
      - match_regex_all: [$all_ids, "^\\d+$"]
      - match_regex_all: [$all_emails, "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"]
```

**适用场景：**
- 验证列表中所有元素的格式一致性
- 批量数据验证
- 确保分页数据符合规范

---

## 实际案例对比

### 案例 1: 验证模型命名规范

```yaml
# ❌ 错误：使用 regex 检查数组（只会检查数组本身的字符串表示）
- regex: ["$.data.items[*].model_name", "Embedding"]  # 不会遍历每个元素

# ✅ 方式1：使用 regex 逐个检查（繁琐）
- regex: ["$.data.items[0].model_name", "^Deepexi-Embedding"]
- regex: ["$.data.items[1].model_name", "^Deepexi-Embedding"]
- regex: ["$.data.items[2].model_name", "^Deepexi-Embedding"]
# ... 需要写很多行

# ✅ 方式2：使用 match_regex_all（推荐）
extract:
  all_model_names: "$.data.items[*].model_name"
validate:
  - match_regex_all: [$all_model_names, "^Deepexi-Embedding"]  # 一行搞定
```

---

### 案例 2: 验证 ID 格式

#### 单个 ID 验证
```yaml
validate:
  # 检查单个 ID 是否为纯数字
  - regex: ["$.data.id", "^\\d+$"]
  
  # 检查单个 UUID 格式
  - regex: ["$.request_id", "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"]
```

#### 批量 ID 验证
```yaml
extract:
  all_ids: "$.data.items[*].id"
  all_request_ids: "$.logs[*].request_id"
validate:
  # 检查所有 ID 是否为纯数字
  - match_regex_all: [$all_ids, "^\\d+$"]
  
  # 检查所有 UUID 格式
  - match_regex_all: [$all_request_ids, "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"]
```

---

### 案例 3: 验证日期时间格式

```yaml
# 单个日期验证
validate:
  - regex: ["$.created_at", "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}"]
  - regex: ["$.updated_at", "^\\d{4}-\\d{2}-\\d{2}"]

# 批量日期验证
extract:
  all_timestamps: "$.events[*].timestamp"
  all_dates: "$.records[*].date"
validate:
  - match_regex_all: [$all_timestamps, "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}"]
  - match_regex_all: [$all_dates, "^\\d{4}-\\d{2}-\\d{2}$"]
```

---

### 案例 4: 验证 URL 格式

```yaml
# 单个 URL 验证
validate:
  - regex: ["$.avatar_url", "^https://"]
  - regex: ["$.api_endpoint", "^https?://[a-zA-Z0-9.-]+"]

# 批量 URL 验证
extract:
  all_image_urls: "$.images[*].url"
  all_api_urls: "$.services[*].endpoint"
validate:
  - match_regex_all: [$all_image_urls, "^https://"]
  - match_regex_all: [$all_api_urls, "^https?://[a-zA-Z0-9.-]+/api/"]
```

---

## 常用正则表达式模式

### 数字和 ID
```yaml
# 纯数字
- regex: ["$.id", "^\\d+$"]
- match_regex_all: [$all_ids, "^\\d+$"]

# 数字范围（1-999）
- regex: ["$.count", "^[1-9]\\d{0,2}$"]

# 正数（支持小数）
- regex: ["$.price", "^\\d+(\\.\\d{1,2})?$"]

# 负数和正数
- regex: ["$.balance", "^-?\\d+(\\.\\d{1,2})?$"]
```

### 字符串模式
```yaml
# 以特定前缀开头
- regex: ["$.model_name", "^Deepexi-"]
- match_regex_all: [$all_names, "^Model-"]

# 以特定后缀结尾
- regex: ["$.filename", "\\.txt$"]
- match_regex_all: [$all_files, "\\.(jpg|png|gif)$"]

# 包含特定子串
- regex: ["$.description", "important"]
- match_regex_all: [$all_tags, "tag_"]

# 完全匹配
- regex: ["$.status", "^active$"]
- match_regex_all: [$all_statuses, "^(active|pending)$"]
```

### 日期和时间
```yaml
# ISO 8601 日期时间
- regex: ["$.timestamp", "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}"]

# 日期 YYYY-MM-DD
- regex: ["$.date", "^\\d{4}-\\d{2}-\\d{2}$"]

# 时间 HH:MM:SS
- regex: ["$.time", "^\\d{2}:\\d{2}:\\d{2}$"]

# Unix 时间戳（10位或13位）
- regex: ["$.created_time", "^\\d{10,13}$"]
```

### 邮箱和 URL
```yaml
# 邮箱
- regex: ["$.email", "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"]

# URL
- regex: ["$.website", "^https?://"]
- regex: ["$.api_url", "^https://[a-zA-Z0-9.-]+/api/v\\d+/"]

# 域名
- regex: ["$.domain", "^[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"]
```

### 手机号和身份证
```yaml
# 中国手机号
- regex: ["$.phone", "^1[3-9]\\d{9}$"]

# 中国身份证（18位）
- regex: ["$.id_card", "^\\d{17}[\\dXx]$"]

# 固定电话（带区号）
- regex: ["$.landline", "^0\\d{2,3}-?\\d{7,8}$"]
```

---

## 性能对比

### regex（单个值）
- **性能**: 快速，单次匹配
- **适用**: 1-10 个字段验证
- **优点**: 直观，不需要提取变量

### match_regex_all（批量）
- **性能**: 一次遍历所有元素
- **适用**: 10+ 个元素验证
- **优点**: 代码简洁，维护方便

**示例对比：**
```yaml
# 验证 100 个 model_name

# ❌ 使用 regex（需要 100 行）
- regex: ["$.data.items[0].model_name", "pattern"]
- regex: ["$.data.items[1].model_name", "pattern"]
# ... 98 more lines
- regex: ["$.data.items[99].model_name", "pattern"]

# ✅ 使用 match_regex_all（只需 3 行）
extract:
  all_model_names: "$.data.items[*].model_name"
validate:
  - match_regex_all: [$all_model_names, "pattern"]
```

---

## 决策树：选择哪个操作符？

```
需要验证正则表达式匹配？
│
├─ 是单个值？
│  └─ 使用 regex
│     例: - regex: ["$.field", "pattern"]
│
└─ 是列表/数组？
   │
   ├─ 只有 1-3 个元素？
   │  └─ 可以使用 regex（逐个）
   │     例: - regex: ["$.items[0]", "pattern"]
   │
   └─ 有 3+ 个元素？
      └─ 使用 match_regex_all（推荐）
         例: - match_regex_all: [$list, "pattern"]
```

---

## 错误排查

### 常见错误 1: 转义问题
```yaml
# ❌ 错误：单个反斜杠
- regex: ["$.id", "^\d+$"]  # YAML 解析错误

# ✅ 正确：双反斜杠
- regex: ["$.id", "^\\d+$"]
```

### 常见错误 2: 对数组使用 regex
```yaml
# ❌ 错误：regex 不会遍历数组
- regex: ["$.data.items[*].name", "pattern"]

# ✅ 正确：使用 match_regex_all
extract:
  all_names: "$.data.items[*].name"
validate:
  - match_regex_all: [$all_names, "pattern"]
```

### 常见错误 3: 忘记提取变量
```yaml
# ❌ 错误：直接使用 JSONPath
- match_regex_all: ["$.data.items[*].name", "pattern"]  # 失败

# ✅ 正确：先提取再断言
extract:
  all_names: "$.data.items[*].name"
validate:
  - match_regex_all: [$all_names, "pattern"]
```

---

## 完整测试示例

```yaml
config:
  name: regex vs match_regex_all 完整示例
  base_url: https://api.example.com

steps:
  - name: 全面对比测试
    request:
      method: GET
      path: /api/models
    extract:
      # 提取列表数据
      all_model_names: "$.data.items[*].model_name"
      all_ids: "$.data.items[*].id"
      all_emails: "$.data.items[*].creator_email"
      all_dates: "$.data.items[*].created_at"
    validate:
      # === 单个值验证（使用 regex） ===
      - regex: ["$.data.items[0].model_name", "^Deepexi-"]
      - regex: ["$.data.items[0].id", "^\\d+$"]
      - regex: ["$.data.items[1].model_name", "WW3XZ5$"]
      - regex: ["$.data.total", "^\\d+$"]
      
      # === 批量验证（使用 match_regex_all） ===
      - match_regex_all: [$all_model_names, "^Deepexi-Embedding"]
      - match_regex_all: [$all_ids, "^\\d+$"]
      - match_regex_all: [$all_emails, "@example\\.com$"]
      - match_regex_all: [$all_dates, "^\\d{4}-\\d{2}-\\d{2}"]
```

---

## 总结

| 特性 | regex | match_regex_all |
|------|-------|-----------------|
| **目标** | 单个值 | 列表中所有值 |
| **语法** | `[字段路径, 模式]` | `[$变量, 模式]` |
| **前置要求** | 无 | 需要先 extract |
| **代码行数** | 每个值1行 | 1行检查所有 |
| **性能** | 单次快速 | 批量高效 |
| **适用场景** | 1-3个字段 | 3+个元素 |
| **维护性** | 数量多时难维护 | 易于维护 |

**选择建议：**
- 单个或少数字段 → 使用 `regex`
- 批量验证、数组元素 → 使用 `match_regex_all`

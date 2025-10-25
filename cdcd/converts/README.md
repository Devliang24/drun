# 格式转换目录

本目录包含 Drun 支持的所有格式转换示例文件，帮助你快速将现有 API 资产迁移为 Drun 测试用例。

## 📁 文件清单

```
converts/
├── README.md                      # 本文档
├── curl/
│   └── sample.curl                # cURL 命令示例（3 个命令）
├── postman/
│   ├── sample_collection.json     # Postman Collection v2.1 示例
│   └── sample_environment.json    # Postman 环境变量示例
├── har/
│   └── sample_recording.har       # 浏览器录制的 HAR 文件示例
└── openapi/
    └── sample_openapi.json        # OpenAPI 3.x 规范示例
```

## 1. cURL 转 YAML

### 示例文件
- `curl/sample.curl` - 包含 3 个 cURL 命令示例（GET、POST、带认证的 GET）

### 基础转换

```bash
# 单文件转换
drun convert converts/curl/sample.curl --outfile testcases/from_curl.yaml

# 脱敏并使用变量占位符
drun convert converts/curl/sample.curl \
  --outfile testcases/from_curl.yaml \
  --redact Authorization,Cookie \
  --placeholders

# 分割为多个文件（每个 cURL 命令生成一个文件）
drun convert converts/curl/sample.curl \
  --split-output \
  --outfile testcases/from_curl.yaml
```

### 常用选项
- `--redact Authorization`: 脱敏认证头
- `--placeholders`: 将敏感信息转换为变量（推荐）
- `--split-output`: 多条命令分割为多个文件
- `--into testcases/existing.yaml`: 追加到现有用例

### 注意事项
- cURL 文件必须使用 `.curl` 后缀
- 支持多条命令（换行分隔）
- 自动解析 `-H`、`-d`、`--data-raw` 等选项

## 2. Postman 转 YAML

### 示例文件
- `postman/sample_collection.json` - Collection v2.1 示例（包含文件夹分组）
- `postman/sample_environment.json` - 环境变量示例（base_url、token 等）

### 基础转换

```bash
# 转换为单个用例文件
drun convert converts/postman/sample_collection.json \
  --outfile testcases/from_postman.yaml

# 分割输出并生成测试套件（推荐）
drun convert converts/postman/sample_collection.json \
  --split-output \
  --suite-out testsuites/from_postman.yaml \
  --redact Authorization \
  --placeholders

# 导入环境变量
drun convert converts/postman/sample_collection.json \
  --postman-env converts/postman/sample_environment.json \
  --outfile testcases/from_postman.yaml \
  --placeholders
```

### 常用选项
- `--postman-env`: 导入环境变量到 `config.variables`
- `--split-output`: 每个请求生成独立文件
- `--suite-out`: 同时生成引用型测试套件
- `--redact` + `--placeholders`: 脱敏并变量化

### 注意事项
- 支持 Collection v2.0 和 v2.1
- 文件夹结构会保留在用例名称中
- {{variable}} 语法会转换为 $variable

## 3. HAR 转 YAML

### 示例文件
- `har/sample_recording.har` - 浏览器录制示例（包含静态资源、不同状态码）

### 如何录制 HAR
1. 打开 Chrome DevTools (F12)
2. 切换到 Network 标签
3. 勾选 "Preserve log"
4. 执行要录制的操作
5. 右键点击请求列表 → "Save all as HAR with content"

### 基础转换

```bash
# 基础转换（自动过滤静态资源）
drun convert converts/har/sample_recording.har \
  --outfile testcases/from_har.yaml

# 仅保留成功响应（2xx 状态码）
drun convert converts/har/sample_recording.har \
  --exclude-static \
  --only-2xx \
  --outfile testcases/from_har.yaml

# 使用正则排除特定 URL
drun convert converts/har/sample_recording.har \
  --exclude-pattern '(\.png$|\.css$|/cdn/)' \
  --outfile testcases/from_har.yaml

# 分割输出
drun convert converts/har/sample_recording.har \
  --exclude-static \
  --split-output \
  --outfile testcases/from_har.yaml
```

### 常用选项
- `--exclude-static`: 过滤图片、CSS、JS、字体等（默认开启）
- `--only-2xx`: 仅保留 2xx 状态码的响应
- `--exclude-pattern`: 正则排除特定 URL 或 mimeType
- `--split-output`: 每个请求生成独立文件

### 注意事项
- HAR 文件通常包含大量噪音，建议使用过滤选项
- 导入后需要手动整理业务步骤
- Cookie 和 Session 信息需要手动处理

## 4. OpenAPI 转 YAML

### 示例文件
- `openapi/sample_openapi.json` - OpenAPI 3.x 规范示例（包含 tags、认证配置）

### 基础转换

```bash
# 转换全部接口
drun convert-openapi converts/openapi/sample_openapi.json \
  --outfile testcases/from_openapi.yaml

# 按 tag 过滤
drun convert-openapi converts/openapi/sample_openapi.json \
  --tags users,orders \
  --outfile testcases/from_openapi.yaml

# 分割输出（推荐）
drun convert-openapi converts/openapi/sample_openapi.json \
  --split-output \
  --outfile testcases/from_openapi.yaml \
  --redact Authorization \
  --placeholders

# 指定 base_url
drun convert-openapi converts/openapi/sample_openapi.json \
  --base-url http://localhost:8000 \
  --outfile testcases/from_openapi.yaml
```

### 常用选项
- `--tags`: 按标签过滤接口（逗号分隔）
- `--split-output`: 每个 Operation 生成独立文件
- `--base-url`: 覆盖规范中的 servers
- `--redact` + `--placeholders`: 脱敏并变量化

### 注意事项
- 支持 OpenAPI 3.0.x 和 3.1.x
- 自动从 schema 生成示例请求体
- 需要手动补充测试数据和断言
- Security schemes 会转换为认证配置

## 通用选项说明

### 脱敏选项
- `--redact Authorization,Cookie`: 将指定 header 值替换为 `***`
- `--placeholders`: 将敏感信息提取到 `config.variables` 并引用

### 输出选项
- `--outfile`: 指定输出文件路径
- `--split-output`: 将多个请求分割为独立文件
- `--into`: 追加到现有 YAML 文件（仅 cURL、Postman、HAR）

### 套件选项
- `--suite-out`: 生成引用测试套件（需配合 `--split-output`）

## 最佳实践

1. **始终使用 `--placeholders`**: 自动将敏感信息（token、密钥）提取为变量
2. **大型资产使用 `--split-output`**: 便于管理和维护
3. **HAR 文件务必过滤**: 使用 `--exclude-static`、`--only-2xx` 减少噪音
4. **转换后补充内容**:
   - 添加有意义的断言（不仅仅是状态码）
   - 补充变量提取逻辑（extract）
   - 整理业务步骤命名
5. **脱敏处理**: 提交到版本控制前使用 `--redact` 保护敏感信息

## 快速参考

| 格式 | 命令 | 推荐选项 |
|------|------|----------|
| cURL | `drun convert <file>.curl` | `--placeholders --split-output` |
| Postman | `drun convert <file>.json` | `--split-output --suite-out --postman-env` |
| HAR | `drun convert <file>.har` | `--exclude-static --only-2xx --split-output` |
| OpenAPI | `drun convert-openapi <file>.json` | `--tags --split-output --placeholders` |

## 更多文档

- 完整转换指南: [docs/FORMAT_CONVERSION.md](../docs/FORMAT_CONVERSION.md)
- CLI 参数详解: [docs/CLI.md](../docs/CLI.md)
- 项目主文档: [README.md](../README.md)

## 需要帮助？

- 查看示例文件了解格式结构
- 运行 `drun convert --help` 查看完整选项
- 参考 `docs/FORMAT_CONVERSION.md` 获取详细说明

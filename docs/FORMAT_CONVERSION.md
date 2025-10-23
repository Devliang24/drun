# 🔄 格式转换攻略（Convert & Export）

本页整理 `drun convert` / `drun export` 的常用场景与参数组合，帮助你把 cURL / Postman / HAR / OpenAPI 等资产快速迁移为 YAML 测试，或从 YAML 导出命令复现实验结果。

注意：使用 `drun convert` 时，必须“文件在前，选项在后”，且不支持无选项转换（至少提供一个选项，如 `--outfile`/`--split-output`/`--redact`/`--placeholders`）。

> 温馨提示：命令详尽参数说明见 `docs/CLI.md` 的相关章节；此处聚焦高频组合、最佳实践与排查思路，文档风格参考 `docs/CI_CD.md`。

## 快速开始

```bash
# cURL → Case：脱敏 + 变量占位
drun convert requests.curl \
  --outfile testcases/from_curl.yaml \
  --redact Authorization,Cookie \
  --placeholders

# Postman → 多文件 + Testsuite
drun convert api_collection.json \
  --split-output \
  --suite-out testsuites/testsuite_postman.yaml \
  --postman-env postman_env.json \
  --redact Authorization \
  --placeholders

# HAR → 过滤静态资源 + 仅保留 2xx
drun convert recording.har \
  --exclude-static \
  --only-2xx \
  --outfile testcases/from_har.yaml

# OpenAPI → 按 tag 拆分 Case
drun convert-openapi spec/openapi/ecommerce_api.json \
  --tags users,orders \
  --split-output \
  --outfile testcases/from_openapi.yaml \
  --redact Authorization \
  --placeholders

# YAML → cURL（脱敏/选步/一行输出）
drun export curl testcases/test_auth.yaml \
  --steps "1,2" \
  --redact Authorization \
  --with-comments
```

## 资产导入场景

### 1. cURL 文本 / `.curl`
- **用途**：从浏览器 Network 面板或文档复制的 cURL 命令快速成型。
- **常用参数**：
  - `--outfile` / `--into`：写入新文件或追加到既有用例。
  - `--split-output`：多条 cURL 拆成多个 Case（文件名 `*_stepN.yaml`）。
  - `--redact` + `--placeholders`：脱敏并写入 `config.variables`。
- **建议**：统一放入 `assets/curl/`，每次导入后补充断言、提取逻辑。

### 2. Postman Collection
- **用途**：团队已有 Postman 资产迁移。
- **常用参数**：
  - `--split-output`：每个请求生成单独 Case。
  - `--suite-out`：同时生成引用 Testsuite，便于批量运行。
  - `--postman-env`：导入 Postman 环境变量，自动写入 `config.variables`。
- **建议**：搭配 `--placeholders`/`--redact` 做脱敏；导入后补充断言与提取。

### 3. HAR 录屏
- **用途**：浏览器录制多步流程，导出 HAR 后批量生成 Case。
- **常用参数**：
  - `--exclude-static`：过滤图片、字体等静态资源。
  - `--only-2xx`：仅保留 2xx 响应，排除错误与重定向噪音。
  - `--exclude-pattern`：通过正则忽略特定 URL 或 mimeType。
- **建议**：HAR 受噪音影响大，导入后按业务步骤整理与合并。

### 4. OpenAPI (3.x)
- **用途**：契约驱动测试，针对业务接口批量生成基础 Case。
- **常用参数**：
  - `--tags` / `--paths`（CLI 中详见）控制生成范围。
  - `--split-output`：每个 Operation 生成独立文件。
  - `--redact` / `--placeholders`：确保密钥、token 不落盘。
- **建议**：导入后补充示例数据、断言、提取逻辑，并按模块拆分目录。

## 脱敏与变量占位

| 选项 | 说明 | 适用场景 |
|------|------|-----------|
| `--redact Authorization,Cookie` | 输出中将指定 header 值替换为 `***` | 资产存档、分享示例 |
| `--placeholders` | 将敏感 header 提升到 `config.variables` 并写成 `$var` | 多环境配置、CI/CD |
| `--postman-env xxx.json` | 将 Postman 环境变量写入 `config.variables` | Postman → Drun |

> 如果 `--redact` 与 `--placeholders` 同时使用，优先占位写入变量，再由生成的 YAML 自动引用。

## 导出工作流

| 场景 | 命令 | 说明 |
|------|------|------|
| 调试单步 | `drun export curl testcases/test.yaml --steps 2` | 仅导出第 2 步，便于复现问题 |
| 分享命令 | `--with-comments --multiline` | 注释标明 Case/Step，易读多行格式 |
| Shell 兼容 | `--shell ps` | 为 PowerShell 使用 `` ` `` 续行 |
| 脱敏查看 | `--redact Authorization` | 分享给他人时隐藏敏感头 |

## 常见问题排查

1. **导入成功但断言缺失**：自动生成的用例仅保留基础请求结构，请补充关键字段断言与提取逻辑。
2. **HAR 导入过多噪音**：结合 `--exclude-static`、`--only-2xx`、`--exclude-pattern`，导入后可手动删除冗余步骤。
3. **转换后 base_url 缺失**：为 Case 填写 `config.base_url` 或通过 `.env` 注入 `BASE_URL`。
4. **Postman 环境变量未生效**：确认 `--postman-env` 指向正确 JSON，并检查导入后 `config.variables`。
5. **命令提示“Refusing to read”**：cURL 文本请使用 `.curl` 后缀（或 `-` 表示 stdin）。

## 补充资料

- CLI 参数总览：`docs/CLI.md`（`drun convert` / `drun export` 章节）
- 实战示例：`docs/EXAMPLES.md`（格式转换与导出工作流）、`examples/` 目录
- 组合示例：`spec/openapi/ecommerce_api.json`（OpenAPI → YAML）

如需补充更多转换方案或遇到特殊资产类型，请整理案例后提 PR 或 Issue。

# 📚 完整参考（Reference）

本页收录 DSL、内置函数、项目自带 hooks 与环境变量等参考信息。

## DSL 完整语法

（按需补充 DSL 的更完整描述与约定）

## 内置函数

| 函数 | 说明 | 示例 |
|------|------|------|
| `ENV(key, default?)` | 读取环境变量；支持默认值 | `${ENV(BASE_URL)}`、`${ENV(TIMEOUT, 30)}` |
| `now()` | 当前 UTC 时间（ISO 8601） | `${now()}` → `2025-01-15T08:30:00` |
| `uuid()` | 生成标准 UUID v4 | `${uuid()}` → `550e8400-e29b-...` |
| `random_int(min, max)` | 生成范围内随机整数 | `${random_int(1, 100)}` → `42` |
| `base64_encode(s)` | Base64 编码字符串或字节 | `${base64_encode('hello')}` |
| `hmac_sha256(key, msg)` | HMAC-SHA256 哈希（十六进制） | `${hmac_sha256($secret, $data)}` |

> 说明：以上函数由框架内置提供（`drun/templating/builtins.py`）。`ENV()` 用于读取操作系统环境变量。

## 项目自带辅助函数与 Hooks

根目录 `README.md`/`drun_hooks.py` 中包含示例，可直接使用或按需修改。

模板辅助函数（在 `${}` 中调用）：

| 函数 | 说明 | 示例 |
|------|------|------|
| `ts()` | Unix 时间戳（秒） | `${ts()}` |
| `md5(s)` | MD5 哈希（十六进制） | `${md5('hello')}` |
| `uid()` | 32 字符十六进制 UUID | `${uid()}` |
| `short_uid(n=8)` | 短 UUID（默认 8 字符） | `${short_uid(12)}` |
| `sign(key, ts)` | 签名示例（MD5 组合） | `${sign($api_key, $ts)}` |
| `uuid4()` | 标准 UUID v4 | `${uuid4()}` |
| `echo(x)` | 回显输入值（调试） | `${echo('test')}` |
| `sum_two_int(a, b)` | 两数相加 | `${sum_two_int(1, 2)}` |

生命周期 Hooks（在 `setup_hooks/teardown_hooks` 使用）：

| Hook 函数 | 用途 | 参数 | 示例 |
|-----------|------|------|------|
| `setup_hook_sign_request` | 添加 MD5 签名头（X-Timestamp、X-Signature） | `$request` | `${setup_hook_sign_request($request)}` |
| `setup_hook_hmac_sign` | 添加 HMAC-SHA256 签名头（需 APP_SECRET） | `$request` | `${setup_hook_hmac_sign($request)}` |
| `setup_hook_api_key` | 注入 API Key 头（X-API-Key） | `$request` | `${setup_hook_api_key($request)}` |
| `teardown_hook_assert_status_ok` | 断言响应状态码为 200 | `$response` | `${teardown_hook_assert_status_ok($response)}` |
| `teardown_hook_capture_request_id` | 提取响应 request_id 为变量 | `$response` | `${teardown_hook_capture_request_id($response)}` |

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DRUN_ENV` | 环境名称 | - |
| `DRUN_HOOKS_FILE` | 自定义 hooks 文件路径 | `drun_hooks.py` |
| `DRUN_NOTIFY` | 默认通知渠道 | - |
| `DRUN_NOTIFY_ONLY` | 通知策略 | `failed` |
| `NOTIFY_TOPN` | 通知失败用例数量 | `5` |
| `FEISHU_WEBHOOK` | 飞书 Webhook URL | - |
| `FEISHU_SECRET` | 飞书签名密钥 | - |
| `FEISHU_STYLE` | 飞书消息风格 | `text` |
| `SMTP_HOST` | SMTP 服务器 | - |
| `SMTP_PORT` | SMTP 端口 | `465` |
| `SMTP_SSL` | 是否使用 SSL | `true` |
| `SMTP_USER` | SMTP 用户 | - |
| `SMTP_PASS` | SMTP 密码 | - |
| `MAIL_FROM` | 发件人 | - |
| `MAIL_TO` | 收件人（逗号分隔） | - |
| `NOTIFY_HTML_BODY` | 邮件 HTML 正文 | `true` |
| `DINGTALK_WEBHOOK` | 钉钉 Webhook URL | - |
| `DINGTALK_SECRET` | 钉钉签名密钥 | - |
| `DINGTALK_AT_MOBILES` | 钉钉 @提醒电话号码 | - |
| `DINGTALK_AT_ALL` | 钉钉全员 @ | `false` |
| `DINGTALK_STYLE` | 钉钉消息风格（text/markdown） | `text` |
| `MYSQL_DSN` | MySQL 连接串 | - |
| `MYSQL_HOST` | MySQL 主机 | `127.0.0.1` |
| `MYSQL_PORT` | MySQL 端口 | `3306` |
| `MYSQL_USER` | MySQL 用户 | - |
| `MYSQL_PASSWORD` | MySQL 密码 | - |
| `MYSQL_DB` | MySQL 数据库 | - |

> 提示：未配置 `DRUN_NOTIFY` 时，若环境中存在 `FEISHU_WEBHOOK`、`DINGTALK_WEBHOOK` 或 `SMTP_HOST`/`MAIL_TO`，会自动启用飞书、钉钉或邮件通知渠道。

> 提示：自 0.3.0 起，Hooks 文件统一使用 `drun_hooks.py`（可通过 `DRUN_HOOKS_FILE` 覆盖）。旧版的 `arun_hooks.py`/`ARUN_HOOKS_FILE` 不再加载，请按以下步骤迁移：
> 1. 将旧文件 `arun_hooks.py` 改名为 `drun_hooks.py`。
> 2. 如果脚本或 CI 中设置了 `ARUN_HOOKS_FILE=/path/to/arun_hooks.py`，改成 `DRUN_HOOKS_FILE=/path/to/drun_hooks.py`。
> 3. 重新运行 `drun run ...`，确保 `${hook(...)}`
>    调用恢复正常。

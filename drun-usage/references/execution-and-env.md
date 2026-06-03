# Execution And Env

适用于设计 `drun r` 命令、解释运行目标写法、环境加载优先级、`-vars`、`-failfast`、`-persist-env`、日志和排障参数。

## 运行目标写法

`drun r` 支持文件、目录、简写文件名，以及 `<path>:<case[,case]>` 形式的 case 选择器。

```bash
drun r tcases -env dev
drun r test_login -env dev
drun r tcases/tc_login.yaml -env dev
drun r tsuites/ts_login_flow.yaml -env dev
drun r tcases:登录,查询资料 -env dev
drun r tcases -env dev -k "smoke and not slow"
```

说明：

- `test_login` 这类无扩展名写法会优先在 `tcases/`、`tsuites/` 里搜索
- `:case1,case2` 按 case 名精确匹配
- case 选择器只负责过滤；实际执行顺序仍按文件发现顺序和源文件内 case 顺序，不按 `:case2,case1` 的书写顺序重排
- 选择器未命中时，错误信息会回显 `requested=[...] available=[...]`
- 如果命中了重复 case 名，当前实现会全部执行并给 warning
- `-k` 按 tags 表达式过滤，适合 smoke / regression / slow 这类分组

## 运行前后输出

`drun r` 在真正执行第一个 Case 前会输出 `[RUN PLAN]`，用于确认 target、环境文件、Base URL 状态、匹配 Case 数、Case Instance（用例实例）数、tag filter、产物路径和日志/脱敏模式。执行结束后会输出 Summary、Failed Cases（如有）和 `[ARTIFACTS]`，方便直接找到报告、日志和 snippets。

## 预览执行计划（dry-run）

`drun r -dry-run` 在**不发送 HTTP 请求、不执行 hooks、不生成报告**的前提下预览整个执行计划：

```bash
drun r tcases -dry-run
drun r tcases -env dev -dry-run
drun r tcases -k smoke -dry-run -dry-run-limit 50
```

输出内容：
- `[PLAN]`：匹配的文件数、Case 数、参数展开实例数
- `[CASE #N]`：每个 Case 的来源文件、tags、参数组合、step 预览
- `[SUMMARY]`：最终统计

规则：
- 不强制要求 `.env`，缺失时标记 `(not set / unresolved)`
- 参数实例超过 `-dry-run-limit`（默认 20）时截断并提示
- 内置函数（`${uuid()}`、`${random_int()}`）和上一步 `extract` 的变量不渲染，保留原样
- invoke 目标不递归展开
- 与其他输出 flag（`-html`、`-report` 等）不互斥，一起传时 dry-run 模式无声忽略

## 环境文件选择与合并

运行时环境文件选择顺序：

1. `-env-file /path/to/file`
2. `.env.<env>`，例如 `-env dev` 对应 `.env.dev`
3. 当前目录下的 `.env`

环境变量实际合并顺序是低到高：

1. 命名 YAML 环境：`env/dev.yaml`、`envs/dev.yaml`、`environments/dev.yaml`，或 `env.yaml` / `env.yml` 中的 `dev:` 段
2. 选中的环境文件：`-env-file` / `.env.<env>` / `.env`
3. OS 环境中的 `ENV_*`、`BASE_URL`、`SYSTEM_NAME`、`PROJECT_NAME`

也就是说，`-env dev` 既可能加载 `env/dev.yaml`，也可能加载 `.env.dev`；后者优先级更高。

## 最小示例

```yaml
config:
  name: 登录
  base_url: ${ENV(BASE_URL)}

steps:
  - name: 登录
    request:
      method: POST
      path: /api/login
      body:
        username: ${ENV(USERNAME)}
        password: ${ENV(PASSWORD)}
    extract:
      token: $.data.token
      user_id: $.data.user_id
    check:
      - eq: [status_code, 200]
```

```bash
drun r tcases/tc_login.yaml -env dev
drun r tcases/tc_login.yaml -env-file .env.local
drun r tcases/tc_login.yaml -env dev -vars tenant=blue
drun r tcases/tc_login.yaml -env dev -failfast
drun r tcases/tc_login.yaml -env dev -persist-env .env.runtime
drun r tcases/tc_login.yaml -env dev -secrets mask -response-headers
drun r tcases/tc_login.yaml -env dev -log-level DEBUG -httpx-logs -log-file logs/debug.log
```

## `-vars`、`-failfast`、`-persist-env`

- `-vars k=v` 用于补运行时变量，适合临时覆盖 `base_url`、租户、token、动态参数
- `-failfast` 在首个失败 case 后停止，适合排查链路问题
- `-persist-env` 会把 step `extract` 结果写回指定文件
  - 目标是 `.env` / `.env.runtime` 时写成 `TOKEN=...`
  - 目标是 `.yaml` / `.yml` 时写进 `variables:` 段
  - 变量名会自动转成大写下划线，例如 `refreshToken -> REFRESH_TOKEN`

## 日志、敏感信息和排障参数

- `-secrets plain|mask` 控制日志和报告里是否展示敏感值；给用户示例时默认建议 `-secrets mask`
- `-response-headers` 会额外记录响应头，适合排查鉴权、网关、trace id
- `-httpx-logs` 打开 httpx 内部日志，适合排查连接、重定向、TLS 等问题
- `-log-file logs/run.log` 指定日志文件；项目模式下不传也会默认写入 `logs/`
- `-log-level DEBUG` 适合短时间排障，不建议作为 CI 默认配置

## 实战建议

- 单接口调试时优先 `tcases/tc_xxx.yaml`
- 多文件链路优先 `tsuites/ts_xxx.yaml`
- 如果只是补一个 `base_url`，可以直接 `-vars base_url=https://api.example.com`
- 如果 `.env` 缺失，但你明确想走 YAML 环境或 OS 环境，仍然可以使用 `-env dev`
- 需要排查 token 是否过期时，优先用 `-secrets mask -response-headers`，避免把真实 token 写进日志

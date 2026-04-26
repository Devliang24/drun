# Execution And Env

适用于设计 `drun run` 命令、解释运行目标写法、环境加载优先级、`-vars`、`-failfast`、`-persist-env`、日志和排障参数。

## 运行目标写法

`drun run` 支持文件、目录、简写文件名，以及 `<path>:<case[,case]>` 形式的 case 选择器。

```bash
drun run testcases -env dev
drun run test_login -env dev
drun run testcases/test_login.yaml -env dev
drun run testsuites/testsuite_login_flow.yaml -env dev
drun run testcases:登录,查询资料 -env dev
drun run testcases -env dev -k "smoke and not slow"
```

说明：

- `test_login` 这类无扩展名写法会优先在 `testcases/`、`testsuites/` 里搜索
- `:case1,case2` 按 case 名精确匹配
- case 选择器只负责过滤；实际执行顺序仍按文件发现顺序和源文件内 case 顺序，不按 `:case2,case1` 的书写顺序重排
- 选择器未命中时，错误信息会回显 `requested=[...] available=[...]`
- 如果命中了重复 case 名，当前实现会全部执行并给 warning
- `-k` 按 tags 表达式过滤，适合 smoke / regression / slow 这类分组

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
    validate:
      - eq: [status_code, 200]
```

```bash
drun run testcases/test_login.yaml -env dev
drun run testcases/test_login.yaml -env-file .env.local
drun run testcases/test_login.yaml -env dev -vars tenant=blue
drun run testcases/test_login.yaml -env dev -failfast
drun run testcases/test_login.yaml -env dev -persist-env .env.runtime
drun run testcases/test_login.yaml -env dev -secrets mask -response-headers
drun run testcases/test_login.yaml -env dev -log-level DEBUG -httpx-logs -log-file logs/debug.log
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

- 单接口调试时优先 `testcases/test_xxx.yaml`
- 多文件链路优先 `testsuites/testsuite_xxx.yaml`
- 如果只是补一个 `base_url`，可以直接 `-vars base_url=https://api.example.com`
- 如果 `.env` 缺失，但你明确想走 YAML 环境或 OS 环境，仍然可以使用 `-env dev`
- 需要排查 token 是否过期时，优先用 `-secrets mask -response-headers`，避免把真实 token 写进日志

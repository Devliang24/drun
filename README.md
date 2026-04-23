# Drun：现代 HTTP API 测试框架

[中文](README.md) | [English](README.en.md)

[![Version](https://img.shields.io/badge/version-7.2.15-blue.svg)](https://github.com/Devliang24/drun)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

`Drun` 是一个面向 HTTP API 的 YAML 驱动测试框架。你可以用简洁的 YAML 描述接口、变量提取、断言、套件编排和报告输出，把接口验证、调试和 CI/CD 串成一条可维护的链路。

## 核心能力

- YAML DSL：通过 `config`、`steps`、`extract`、`validate`、`caseflow` 编写测试。
- 模板系统：支持 `$var`、`${ENV(KEY)}`、`${uuid()}` 等动态表达式。
- 丰富断言：内置 `eq`、`contains`、`regex`、`len_eq`、`gt` 等校验。
- 测试编排：支持测试套件、`invoke` 调用、步骤 `repeat`、标签过滤。
- 延时步骤：支持 `sleep: 2000` 这类显式等待 DSL，单位为毫秒。
- 结果输出：支持 HTML、JSON、Allure 报告，以及日志、代码片段导出。
- 调试友好：支持 `drun q` 快速发请求，支持从 cURL、Postman、HAR、OpenAPI 转换用例。

## 安装

推荐 Python 3.10+。

```bash
pip install drun
```

如果你使用 `uv`：

```bash
uv venv
source .venv/bin/activate
uv pip install drun
```

## 快速开始

### 1. 初始化项目

```bash
drun init myproject
cd myproject
```

默认会生成类似结构：

```text
myproject/
├── testcases/
├── testsuites/
├── data/
├── converts/
├── logs/
├── reports/
├── snippets/
├── .env
└── Dhook.py
```

### 2. 配置环境变量

`.env`

```bash
BASE_URL=https://api.example.com
API_KEY=demo-token
```

### 3. 编写第一个测试

`testcases/test_user_api.yaml`

```yaml
config:
  name: 用户接口测试
  base_url: ${ENV(BASE_URL)}
  tags: [smoke, user]

steps:
  - name: 创建用户
    request:
      method: POST
      path: /users
      headers:
        Authorization: Bearer ${ENV(API_KEY)}
      body:
        username: test_${uuid()}
        email: test@example.com
    extract:
      userId: $.data.id
    validate:
      - eq: [status_code, 201]
      - regex: [$.data.id, '^\d+$']

  - name: 查询用户
    request:
      method: GET
      path: /users/${ENV(USER_ID)}
      headers:
        Authorization: Bearer ${ENV(API_KEY)}
    validate:
      - eq: [status_code, 200]
```

### 4. 执行测试

```bash
drun run testcases/test_user_api.yaml -env dev
drun run test_user_api -env dev
drun run testcases -env dev -k "smoke and not slow"
drun run test_user_api -env dev -html reports/report.html
```

说明：

- 支持省略 `.yaml` 扩展名。
- 单文件临时运行时，默认只在当前目录输出一个日志文件。
- 脚手架项目运行时，会默认输出到 `logs/`、`reports/`、`snippets/`。

## 常用写法

### 单用例文件

```yaml
config:
  name: 登录接口
  base_url: ${ENV(BASE_URL)}

steps:
  - name: 登录
    request:
      method: POST
      path: /login
      body:
        username: admin
        password: pass123
    extract:
      token: $.data.token
    validate:
      - eq: [status_code, 200]
```

### 套件文件

```yaml
config:
  name: 冒烟套件

caseflow:
  - name: 登录
    invoke: test_login
  - name: 查询资料
    invoke: test_profile
```

### 数据驱动

```yaml
config:
  name: 批量注册
  parameters:
    - csv:
        path: data/users.csv

steps:
  - name: 注册 $username
    request:
      method: POST
      path: /register
      body:
        username: $username
        email: $email
    validate:
      - eq: [status_code, 201]
```

### 重复执行

```yaml
steps:
  - name: 重试健康检查
    repeat: 3
    request:
      method: GET
      path: /health
    validate:
      - eq: [status_code, 200]
```

### 延时步骤

```yaml
steps:
  - name: 等待服务稳定
    sleep: 2000

  - name: 按变量等待
    sleep: ${wait_ms}
```

## 常用命令

### 运行与调试

```bash
drun run PATH -env dev
drun q https://api.example.com/ping
drun q https://api.example.com/users -X POST -d '{"name":"alice"}'
drun tags testcases
drun check testcases
drun fix testcases
```

### 格式转换

```bash
drun convert sample.curl -outfile out.yaml
drun convert-openapi spec/openapi/ecommerce_api.json -outdir converted
drun export curl testcases/test_user_api.yaml -outfile request.sh
```

### 报告服务

```bash
drun server
drun server -port 8080
```

启动后可浏览测试报告列表并查看详情页。

## 报告与输出

- HTML：适合本地查看与分享。
- JSON：适合流水线消费。
- Allure：适合集成到测试平台。
- Snippets：自动生成 Shell 或 Python 请求脚本，便于复现请求。

示例：

```bash
drun run testcases -env dev -html reports/report.html
drun run testcases -env dev -allure-results allure-results
allure serve allure-results
```

## 从源码开发

```bash
git clone https://github.com/Devliang24/drun.git
cd drun
pip install -e ".[dev]"
python -m pytest -q
python -m build
python -m drun.cli --version
```

仓库主目录说明：

- `drun/`：核心实现。
- `tests/`：回归测试。
- `spec/`：示例 OpenAPI 规范。
- `CHANGELOG.md`：版本历史。
- `AGENTS.md`：贡献者约定与本地开发说明。

## 适用场景

- HTTP API 回归测试
- 冒烟测试与发布验证
- 测试数据驱动执行
- 接口调试与请求复现
- CI/CD 中的接口质量门禁

## 贡献

欢迎提交 issue 或 PR。提交前建议至少执行以下命令：

```bash
python -m pytest -q
python -m build
drun --help
```

如果你在仓库内协作开发，请先阅读 `AGENTS.md`。

## License

MIT

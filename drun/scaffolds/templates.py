"""
Drun 项目脚手架模板内容
用于 drun init 命令生成项目结构
"""

# 测试用例模板：HTTP 功能演示
DEMO_TESTCASE = """config:
  name: HTTP 测试功能演示
  base_url: ${ENV(BASE_URL)}
  tags: [demo, smoke]
  variables:
    test_data: test_value_${short_uid(6)}
    user_agent: Drun-Test-Client

steps:
  - name: GET 请求 - 查询参数
    request:
      method: GET
      url: /get?page=1&limit=10
      headers:
        User-Agent: $user_agent
    validate:
      - eq: [status_code, 200]
      - eq: [$.args.page, 1]
      - eq: [$.args.limit, 10]
      - contains: [$.headers.User-Agent, Drun-Test-Client]

  - name: POST 请求 - 提交 JSON 数据
    request:
      method: POST
      url: /post
      headers:
        Content-Type: application/json
      body:
        username: ${ENV(USER_USERNAME)}
        data: $test_data
        timestamp: ${ts()}
    extract:
      posted_data: $.json.data
      posted_username: $.json.username
    validate:
      - eq: [status_code, 200]
      - eq: [$.json.username, test_user]
      - eq: [$.json.data, $test_data]
      - contains: [headers.Content-Type, application/json]

  - name: Basic 认证请求
    request:
      method: GET
      url: /basic-auth/${ENV(USER_USERNAME)}/${ENV(USER_PASSWORD)}
      auth:
        type: basic
        username: ${ENV(USER_USERNAME)}
        password: ${ENV(USER_PASSWORD)}
    validate:
      - eq: [status_code, 200]
      - eq: [$.authenticated, true]
      - eq: [$.user, test_user]

  - name: 响应延迟测试
    request:
      method: GET
      url: /delay/1
    validate:
      - eq: [status_code, 200]
      - lt: [$elapsed_ms, 2000]
      - gt: [$elapsed_ms, 900]

  - name: 不同状态码测试
    request:
      method: GET
      url: /status/201
    validate:
      - eq: [status_code, 201]
"""

# 测试用例模板：简单健康检查
HEALTH_TESTCASE = """config:
  name: API 健康检查
  base_url: ${ENV(BASE_URL)}
  tags: [smoke, health]

steps:
  - name: 检查服务状态
    request:
      method: GET
      url: /get
    validate:
      - eq: [status_code, 200]
      - contains: [headers.Content-Type, application/json]
      - eq: [$.url, https://httpbin.org/get]
"""

# 测试套件模板
DEMO_TESTSUITE = """config:
  name: 冒烟测试套件
  tags: [smoke]

testcases:
  - name: API 健康检查
    testcase: testcases/test_api_health.yaml

  - name: 认证流程测试
    testcase: testcases/test_demo.yaml
"""

# CSV 数据示例
CSV_USERS_SAMPLE = """username,email,password,role
alice,alice@example.com,P@ssw0rd123,member
bob,bob@example.com,P@ssw0rd123,admin
carol,carol@example.com,P@ssw0rd123,guest
"""

# 基于 CSV 的数据驱动用例示例
CSV_DATA_TESTCASE = """config:
  name: "数据驱动：CSV 示例"
  base_url: ${ENV(BASE_URL)}
  tags: [demo, csv]
  parameters:
    - csv:
        path: ../data/users.csv
        strip: true

steps:
  - name: 提交注册请求
    request:
      method: POST
      url: /anything/register
      headers:
        Content-Type: application/json
      body:
        username: $username
        email: $email
        password: $password
        role: $role
        source: csv-demo
    extract:
      echoed_username: $.json.username
      echoed_role: $.json.role
    validate:
      - eq: [status_code, 200]
      - eq: [$.json.username, $username]
      - eq: [$.json.email, $email]
      - eq: [$.json.role, $role]
      - eq: [$.json.source, csv-demo]

  - name: 校验回显头部
    request:
      method: GET
      url: /anything/verify
      headers:
        X-Demo-User: $echoed_username
        X-User-Role: $role
    validate:
      - eq: [status_code, 200]
      - eq: [$.headers.X-Demo-User, $echoed_username]
      - eq: [$.headers.X-User-Role, $role]
"""

# CSV 示例测试套件
CSV_DATA_TESTSUITE = """config:
  name: 数据驱动示例套件
  tags: [csv, demo]

testcases:
  - name: CSV 参数化注册
    testcase: testcases/test_import_users.yaml
"""

# cURL 示例文件
SAMPLE_CURL = """# 示例 1: GET 请求（带查询参数）
curl -X GET 'https://api.example.com/api/v1/products?category=electronics&limit=10' \\
  -H 'Accept: application/json'

# 示例 2: POST 请求（带 JSON body 和认证）
curl -X POST 'https://api.example.com/api/v1/auth/login' \\
  -H 'Content-Type: application/json' \\
  -H 'Accept: application/json' \\
  --data-raw '{
    "username": "test_user",
    "password": "test_pass123"
  }'

# 示例 3: 带 Authorization header 的 GET 请求
curl -X GET 'https://api.example.com/api/v1/users/me' \\
  -H 'Accept: application/json' \\
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'

# 转换命令示例:
# drun convert converts/curl/sample.curl --outfile testcases/from_curl.yaml --redact Authorization --placeholders
"""

# Postman Collection 示例模板
SAMPLE_POSTMAN_COLLECTION = """{
  "info": {
    "name": "Drun Sample API Collection",
    "_postman_id": "12345678-1234-1234-1234-123456789012",
    "description": "Drun 格式转换示例 - Postman Collection v2.1\\n\\n转换命令:\\ndrun convert converts/postman/sample_collection.json --split-output --suite-out testsuites/from_postman.yaml --postman-env converts/postman/sample_environment.json --placeholders",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "用户管理",
      "item": [
        {
          "name": "获取用户列表",
          "request": {
            "method": "GET",
            "header": [
              {
                "key": "Accept",
                "value": "application/json"
              }
            ],
            "url": {
              "raw": "{{base_url}}/api/v1/users?page=1&limit=10",
              "host": ["{{base_url}}"],
              "path": ["api", "v1", "users"],
              "query": [
                {"key": "page", "value": "1"},
                {"key": "limit", "value": "10"}
              ]
            }
          }
        },
        {
          "name": "创建用户",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Authorization",
                "value": "Bearer {{token}}"
              },
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\\n  \\"username\\": \\"test_user\\",\\n  \\"email\\": \\"test@example.com\\",\\n  \\"password\\": \\"password123\\"\\n}"
            },
            "url": {
              "raw": "{{base_url}}/api/v1/users",
              "host": ["{{base_url}}"],
              "path": ["api", "v1", "users"]
            }
          }
        },
        {
          "name": "获取用户详情",
          "request": {
            "method": "GET",
            "header": [
              {
                "key": "Authorization",
                "value": "Bearer {{token}}"
              }
            ],
            "url": {
              "raw": "{{base_url}}/api/v1/users/{{user_id}}",
              "host": ["{{base_url}}"],
              "path": ["api", "v1", "users", "{{user_id}}"]
            }
          }
        }
      ]
    },
    {
      "name": "健康检查",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{base_url}}/health",
          "host": ["{{base_url}}"],
          "path": ["health"]
        }
      }
    }
  ]
}
"""

# Postman Environment 示例模板
SAMPLE_POSTMAN_ENVIRONMENT = """{
  "name": "Development Environment",
  "values": [
    {
      "key": "base_url",
      "value": "http://localhost:8000",
      "enabled": true
    },
    {
      "key": "token",
      "value": "your-api-token-here",
      "enabled": true
    },
    {
      "key": "user_id",
      "value": "123",
      "enabled": true
    },
    {
      "key": "api_key",
      "value": "your-api-key-here",
      "enabled": true
    }
  ],
  "_postman_variable_scope": "environment"
}
"""

# HAR 文件示例模板
SAMPLE_HAR = """{
  "log": {
    "version": "1.2",
    "creator": {
      "name": "Drun Sample HAR",
      "version": "1.0"
    },
    "entries": [
      {
        "startedDateTime": "2025-01-01T00:00:00.000Z",
        "time": 145,
        "request": {
          "method": "GET",
          "url": "http://localhost:8000/api/v1/products?category=electronics",
          "httpVersion": "HTTP/1.1",
          "headers": [
            {"name": "Accept", "value": "application/json"},
            {"name": "User-Agent", "value": "Mozilla/5.0"}
          ],
          "queryString": [
            {"name": "category", "value": "electronics"}
          ],
          "cookies": [],
          "headersSize": -1,
          "bodySize": 0
        },
        "response": {
          "status": 200,
          "statusText": "OK",
          "httpVersion": "HTTP/1.1",
          "headers": [
            {"name": "Content-Type", "value": "application/json"}
          ],
          "cookies": [],
          "content": {
            "size": 150,
            "mimeType": "application/json",
            "text": "{\\"success\\": true, \\"data\\": [\\"item1\\", \\"item2\\"]}"
          },
          "redirectURL": "",
          "headersSize": -1,
          "bodySize": 150
        },
        "cache": {},
        "timings": {
          "send": 0,
          "wait": 145,
          "receive": 0
        }
      },
      {
        "startedDateTime": "2025-01-01T00:00:01.000Z",
        "time": 89,
        "request": {
          "method": "POST",
          "url": "http://localhost:8000/api/v1/auth/login",
          "httpVersion": "HTTP/1.1",
          "headers": [
            {"name": "Content-Type", "value": "application/json"}
          ],
          "queryString": [],
          "cookies": [],
          "headersSize": -1,
          "bodySize": 50,
          "postData": {
            "mimeType": "application/json",
            "text": "{\\"username\\": \\"test\\", \\"password\\": \\"pass123\\"}"
          }
        },
        "response": {
          "status": 200,
          "statusText": "OK",
          "httpVersion": "HTTP/1.1",
          "headers": [
            {"name": "Content-Type", "value": "application/json"}
          ],
          "cookies": [],
          "content": {
            "size": 100,
            "mimeType": "application/json",
            "text": "{\\"success\\": true, \\"data\\": {\\"token\\": \\"abc123\\"}}"
          },
          "redirectURL": "",
          "headersSize": -1,
          "bodySize": 100
        },
        "cache": {},
        "timings": {
          "send": 0,
          "wait": 89,
          "receive": 0
        }
      },
      {
        "startedDateTime": "2025-01-01T00:00:02.000Z",
        "time": 12,
        "request": {
          "method": "GET",
          "url": "http://localhost:8000/static/logo.png",
          "httpVersion": "HTTP/1.1",
          "headers": [],
          "queryString": [],
          "cookies": [],
          "headersSize": -1,
          "bodySize": 0
        },
        "response": {
          "status": 200,
          "statusText": "OK",
          "httpVersion": "HTTP/1.1",
          "headers": [
            {"name": "Content-Type", "value": "image/png"}
          ],
          "cookies": [],
          "content": {
            "size": 5000,
            "mimeType": "image/png"
          },
          "redirectURL": "",
          "headersSize": -1,
          "bodySize": 5000
        },
        "cache": {},
        "timings": {
          "send": 0,
          "wait": 12,
          "receive": 0
        }
      },
      {
        "startedDateTime": "2025-01-01T00:00:03.000Z",
        "time": 234,
        "request": {
          "method": "GET",
          "url": "http://localhost:8000/api/v1/orders/999",
          "httpVersion": "HTTP/1.1",
          "headers": [
            {"name": "Authorization", "value": "Bearer abc123"}
          ],
          "queryString": [],
          "cookies": [],
          "headersSize": -1,
          "bodySize": 0
        },
        "response": {
          "status": 404,
          "statusText": "Not Found",
          "httpVersion": "HTTP/1.1",
          "headers": [
            {"name": "Content-Type", "value": "application/json"}
          ],
          "cookies": [],
          "content": {
            "size": 50,
            "mimeType": "application/json",
            "text": "{\\"success\\": false, \\"error\\": \\"Order not found\\"}"
          },
          "redirectURL": "",
          "headersSize": -1,
          "bodySize": 50
        },
        "cache": {},
        "timings": {
          "send": 0,
          "wait": 234,
          "receive": 0
        }
      }
    ]
  }
}
"""

# OpenAPI 规范示例模板
SAMPLE_OPENAPI = """{
  "openapi": "3.0.3",
  "info": {
    "title": "Drun Sample API",
    "description": "Drun 格式转换示例 - OpenAPI 3.0 规范\\n\\n转换命令:\\ndrun convert-openapi converts/openapi/sample_openapi.json --tags users --split-output --outfile testcases/from_openapi.yaml --placeholders",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "http://localhost:8000",
      "description": "Development server"
    }
  ],
  "tags": [
    {"name": "users", "description": "用户管理"},
    {"name": "orders", "description": "订单管理"}
  ],
  "paths": {
    "/api/v1/users": {
      "get": {
        "tags": ["users"],
        "summary": "获取用户列表",
        "operationId": "listUsers",
        "parameters": [
          {
            "name": "page",
            "in": "query",
            "schema": {"type": "integer", "default": 1}
          },
          {
            "name": "limit",
            "in": "query",
            "schema": {"type": "integer", "default": 10}
          }
        ],
        "responses": {
          "200": {
            "description": "成功",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "success": {"type": "boolean"},
                    "data": {
                      "type": "array",
                      "items": {"$ref": "#/components/schemas/User"}
                    }
                  }
                }
              }
            }
          }
        }
      },
      "post": {
        "tags": ["users"],
        "summary": "创建用户",
        "operationId": "createUser",
        "security": [{"bearerAuth": []}],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {"$ref": "#/components/schemas/UserInput"}
            }
          }
        },
        "responses": {
          "201": {
            "description": "创建成功",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "success": {"type": "boolean"},
                    "data": {"$ref": "#/components/schemas/User"}
                  }
                }
              }
            }
          }
        }
      }
    },
    "/api/v1/users/{userId}": {
      "get": {
        "tags": ["users"],
        "summary": "获取用户详情",
        "operationId": "getUser",
        "security": [{"bearerAuth": []}],
        "parameters": [
          {
            "name": "userId",
            "in": "path",
            "required": true,
            "schema": {"type": "integer"}
          }
        ],
        "responses": {
          "200": {
            "description": "成功",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "success": {"type": "boolean"},
                    "data": {"$ref": "#/components/schemas/User"}
                  }
                }
              }
            }
          },
          "404": {
            "description": "用户不存在"
          }
        }
      }
    },
    "/api/v1/orders": {
      "get": {
        "tags": ["orders"],
        "summary": "获取订单列表",
        "operationId": "listOrders",
        "security": [{"bearerAuth": []}],
        "responses": {
          "200": {
            "description": "成功"
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "User": {
        "type": "object",
        "properties": {
          "id": {"type": "integer"},
          "username": {"type": "string"},
          "email": {"type": "string", "format": "email"},
          "full_name": {"type": "string"},
          "is_active": {"type": "boolean"}
        }
      },
      "UserInput": {
        "type": "object",
        "required": ["username", "email", "password"],
        "properties": {
          "username": {"type": "string", "example": "test_user"},
          "email": {"type": "string", "format": "email", "example": "test@example.com"},
          "password": {"type": "string", "example": "password123"},
          "full_name": {"type": "string", "example": "Test User"}
        }
      }
    },
    "securitySchemes": {
      "bearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT"
      }
    }
  }
}
"""

# converts 目录说明文档
CONVERTS_README = """# 格式转换目录

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
drun convert converts/curl/sample.curl \\
  --outfile testcases/from_curl.yaml \\
  --redact Authorization,Cookie \\
  --placeholders

# 分割为多个文件（每个 cURL 命令生成一个文件）
drun convert converts/curl/sample.curl \\
  --split-output \\
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
drun convert converts/postman/sample_collection.json \\
  --outfile testcases/from_postman.yaml

# 分割输出并生成测试套件（推荐）
drun convert converts/postman/sample_collection.json \\
  --split-output \\
  --suite-out testsuites/from_postman.yaml \\
  --redact Authorization \\
  --placeholders

# 导入环境变量
drun convert converts/postman/sample_collection.json \\
  --postman-env converts/postman/sample_environment.json \\
  --outfile testcases/from_postman.yaml \\
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
drun convert converts/har/sample_recording.har \\
  --outfile testcases/from_har.yaml

# 仅保留成功响应（2xx 状态码）
drun convert converts/har/sample_recording.har \\
  --exclude-static \\
  --only-2xx \\
  --outfile testcases/from_har.yaml

# 使用正则排除特定 URL
drun convert converts/har/sample_recording.har \\
  --exclude-pattern '(\\.png$|\\.css$|/cdn/)' \\
  --outfile testcases/from_har.yaml

# 分割输出
drun convert converts/har/sample_recording.har \\
  --exclude-static \\
  --split-output \\
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
drun convert-openapi converts/openapi/sample_openapi.json \\
  --outfile testcases/from_openapi.yaml

# 按 tag 过滤
drun convert-openapi converts/openapi/sample_openapi.json \\
  --tags users,orders \\
  --outfile testcases/from_openapi.yaml

# 分割输出（推荐）
drun convert-openapi converts/openapi/sample_openapi.json \\
  --split-output \\
  --outfile testcases/from_openapi.yaml \\
  --redact Authorization \\
  --placeholders

# 指定 base_url
drun convert-openapi converts/openapi/sample_openapi.json \\
  --base-url http://localhost:8000 \\
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
"""

# .env 环境配置模板
ENV_TEMPLATE = """# ==================== API 基础配置 ====================
# 选项 1: httpbin.org - 专为 HTTP 测试设计，功能全面（推荐）
BASE_URL=https://httpbin.org

# 选项 2: JSONPlaceholder - 模拟 RESTful API，更稳定
# BASE_URL=https://jsonplaceholder.typicode.com

# 选项 3: 本地服务
# BASE_URL=http://localhost:8000

# 测试用户凭证（用于 Basic Auth 演示）
USER_USERNAME=test_user
USER_PASSWORD=test_password

# ==================== 数据库配置（可选）====================
# 用于 SQL 验证功能
# MYSQL_HOST=localhost
# MYSQL_PORT=3306
# MYSQL_USER=root
# MYSQL_PASSWORD=password
# MYSQL_DB=test_database

# ==================== 系统信息 ====================
# 系统名称（用于通知标题和报告）
SYSTEM_NAME=我的测试系统

# ==================== 通知配置 ====================
# 启用通知渠道：drun run --notify feishu,email,dingtalk
# 通知策略（环境变量）：DRUN_NOTIFY_ONLY=failed|always（默认 failed）

# ---- 飞书通知 ----
# FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxxxx
# FEISHU_SECRET=your-secret-key                          # 可选，启用签名验证
# FEISHU_MENTION=13800138000,ou_user_id                  # 可选，@用户（手机号或 open_id）
# FEISHU_STYLE=card                                      # 消息样式：text 或 card（推荐）
# REPORT_URL=https://ci.example.com/artifacts/report.html # 可选，报告链接（card 模式显示按钮）

# ---- 钉钉通知 ----
# DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxxxxxxxxx
# DINGTALK_SECRET=your-secret-key                        # 可选，启用签名验证
# DINGTALK_AT_MOBILES=13800138000,13900139000            # 可选，@指定手机号（逗号分隔）
# DINGTALK_AT_ALL=false                                  # 可选，@所有人（true/false）
# DINGTALK_STYLE=markdown                                # 消息样式：text 或 markdown（推荐，支持加粗、链接等）
# DINGTALK_TITLE=Drun 测试结果                            # 可选，markdown 模式的标题

# ---- 邮件通知 ----
# SMTP_HOST=smtp.example.com                             # SMTP 服务器地址
# SMTP_PORT=465                                          # SMTP 端口（465 for SSL，587 for TLS）
# SMTP_USER=noreply@example.com                          # SMTP 用户名
# SMTP_PASS=your-app-password                            # SMTP 密码或应用专用密码
# MAIL_FROM=noreply@example.com                          # 发件人地址
# MAIL_TO=qa@example.com,dev@example.com                 # 收件人（逗号分隔多个）
"""

# drun_hooks.py 模板（基于当前项目的实际文件）
HOOKS_TEMPLATE = '''"""
Drun Hooks 示例文件

此文件包含可在测试用例中使用的自定义函数：
1. 模板辅助函数：在 ${} 表达式中调用，用于生成数据
2. 生命周期 Hooks：在 setup_hooks/teardown_hooks 中使用

使用方法：
- 模板函数: ${ts()}, ${uid()}, ${md5($password)}
- Hooks 函数: setup_hooks: [${setup_hook_sign_request($request)}]
"""
import time
import hmac
import hashlib
import uuid


# ==================== 模板辅助函数 ====================

def ts() -> int:
    """返回当前 Unix 时间戳（秒）

    用法: ${ts()}
    示例: headers: { X-Timestamp: ${ts()} }
    """
    return int(time.time())


def uid() -> str:
    """生成完整的 UUID（带连字符）

    用法: ${uid()}
    示例: email: user_${uid()}@example.com
    """
    return str(uuid.uuid4())


def short_uid(length: int = 8) -> str:
    """生成短 UUID（去除连字符，截取指定长度）

    参数:
        length: 返回的字符串长度（默认 8）

    用法: ${short_uid(12)}
    示例: username: user_${short_uid(8)}
    """
    return str(uuid.uuid4()).replace("-", "")[:length]


def md5(text: str) -> str:
    """计算字符串的 MD5 哈希值

    用法: ${md5($password)}
    示例: headers: { X-Sign: ${md5($timestamp + $secret)} }
    """
    return hashlib.md5(str(text).encode("utf-8")).hexdigest()


def sha256(text: str) -> str:
    """计算字符串的 SHA256 哈希值

    用法: ${sha256($data)}
    """
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


# ==================== 生命周期 Hooks ====================

def setup_hook_sign_request(request: dict, variables: dict = None, env: dict = None) -> dict:
    """请求签名 Hook 示例：添加 HMAC-SHA256 签名

    此 Hook 会：
    1. 生成当前时间戳
    2. 使用 APP_SECRET 对请求进行签名
    3. 添加 X-Timestamp 和 X-Signature 头

    使用方法:
        steps:
          - name: 调用需要签名的接口
            setup_hooks:
              - ${setup_hook_sign_request($request)}
            request:
              method: POST
              url: /api/secure/endpoint

    参数:
        request: 当前请求对象（方法、URL、headers 等）
        variables: 当前会话变量
        env: 环境变量

    返回:
        dict: 返回的变量会注入到当前步骤的变量作用域
    """
    env = env or {}
    secret = env.get("APP_SECRET", "default-secret-key").encode()

    method = request.get("method", "GET")
    url = request.get("url", "")
    timestamp = str(int(time.time()))

    # 计算签名：HMAC-SHA256(method|url|timestamp)
    message = f"{method}|{url}|{timestamp}".encode()
    signature = hmac.new(secret, message, hashlib.sha256).hexdigest()

    # 添加签名相关的 headers
    headers = request.setdefault("headers", {})
    headers["X-Timestamp"] = timestamp
    headers["X-Signature"] = signature

    # 可选：返回签名信息供后续步骤使用
    return {
        "last_signature": signature,
        "last_timestamp": timestamp,
    }


def teardown_hook_log_response(response: dict, variables: dict = None, env: dict = None):
    """响应日志 Hook 示例：记录响应关键信息

    使用方法:
        steps:
          - name: 创建订单
            teardown_hooks:
              - ${teardown_hook_log_response($response)}

    参数:
        response: 响应对象（status_code、body 等）
        variables: 当前会话变量
        env: 环境变量
    """
    status = response.get("status_code")
    body = response.get("body", {})

    # 可以在这里添加自定义日志逻辑
    print(f"[Hook] Response: status={status}, body_keys={list(body.keys() if isinstance(body, dict) else [])}")


def teardown_hook_validate_status(response: dict, variables: dict = None, env: dict = None):
    """响应验证 Hook 示例：确保状态码为 2xx

    使用方法:
        steps:
          - name: 调用接口
            teardown_hooks:
              - ${teardown_hook_validate_status($response)}
    """
    status = response.get("status_code", 0)
    if not (200 <= status < 300):
        raise AssertionError(f"Expected 2xx status code, got {status}")


# ==================== Suite 级别 Hooks ====================

def suite_setup():
    """Suite 开始前的准备工作

    使用方法（在测试套件中）:
        config:
          setup_hooks:
            - ${suite_setup()}
    """
    print("[Suite Hook] Suite setup: 准备测试环境...")
    # 可以在这里执行：
    # - 清理测试数据库
    # - 初始化测试数据
    # - 启动 mock 服务
    return {}


def suite_teardown():
    """Suite 结束后的清理工作

    使用方法（在测试套件中）:
        config:
          teardown_hooks:
            - ${suite_teardown()}
    """
    print("[Suite Hook] Suite teardown: 清理测试环境...")
    # 可以在这里执行：
    # - 清理测试数据
    # - 停止 mock 服务
    # - 生成额外报告


def case_setup():
    """Case 开始前的准备工作

    使用方法（在测试用例中）:
        config:
          setup_hooks:
            - ${case_setup()}
    """
    print("[Case Hook] Case setup: 准备用例数据...")
    return {}


def case_teardown():
    """Case 结束后的清理工作

    使用方法（在测试用例中）:
        config:
          teardown_hooks:
            - ${case_teardown()}
    """
    print("[Case Hook] Case teardown: 清理用例数据...")
'''

# .gitignore 模板
GITIGNORE_TEMPLATE = """# 报告和日志
reports/
logs/
allure-results/
*.log

# 环境配置（包含敏感信息）
.env
.env.*
!.env.example

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
.pytest_cache/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# 临时文件
*.tmp
*.bak
*.orig
"""

# README.md 项目文档模板
README_TEMPLATE = """# Drun API 测试项目

本项目使用 [Drun](https://github.com/Devliang24/drun) 框架进行 HTTP API 自动化测试。

## 📁 项目结构

```
.
├── testcases/              # 测试用例目录
│   ├── test_demo.yaml      # 完整认证流程示例
│   ├── test_api_health.yaml # 健康检查示例
│   └── test_import_users.yaml # CSV 参数化用例
├── testsuites/             # 测试套件目录
│   ├── testsuite_smoke.yaml # 冒烟测试套件
│   └── testsuite_csv.yaml  # CSV 示例套件
├── data/                   # 数据文件目录
│   └── users.csv           # CSV 参数数据
├── converts/               # 格式转换源文件
│   ├── sample.curl         # cURL 命令示例
│   └── README.md           # 转换命令说明
├── reports/                # HTML/JSON 报告输出
├── logs/                   # 日志文件输出
├── .env                    # 环境变量配置
├── drun_hooks.py           # 自定义 Hooks 函数
└── README.md               # 本文档
```

## 🚀 快速开始

### 1. 安装 Drun

```bash
pip install -e /path/to/drun
# 或者从 GitHub 安装（如果已发布）
# pip install drun
```

### 2. 配置环境变量

编辑 `.env` 文件，设置你的 API 基础地址：

```env
BASE_URL=http://localhost:8000
USER_USERNAME=test_user
USER_PASSWORD=test_pass123
```

### 3. 运行测试

```bash
# 运行单个测试用例
drun run testcases/test_api_health.yaml

# 运行整个测试目录
drun run testcases

# 运行测试套件
drun run testsuites/testsuite_smoke.yaml

# 运行 CSV 数据驱动示例
drun run testcases/test_import_users.yaml

# 或运行 CSV 套件（包含相同用例）
drun run testsuites/testsuite_csv.yaml

# 使用标签过滤
drun run testcases -k "smoke and not slow"

# 生成 HTML 报告
drun run testcases --html reports/report.html

# 启用详细日志
drun run testcases --log-level debug
```

> 提示：未显式指定 `--env-file` 时会自动读取当前目录的 `.env`。如果需要加载其他文件，可运行如 `drun run testcases --env-file configs/staging.env`。

### 4. 查看报告

测试运行后，查看生成的报告：

```bash
# HTML 报告（浏览器打开）
open reports/report-*.html

# JSON 报告（供 CI/CD 集成）
cat reports/run.json
```

## 📊 数据驱动示例（CSV）

- CSV 数据文件：`data/users.csv`
- 对应用例：`testcases/test_import_users.yaml`
- 示例套件：`testsuites/testsuite_csv.yaml`
- 默认假设 `BASE_URL` 指向 [httpbin](https://httpbin.org)，以便 `/anything` 接口回显请求数据。

运行命令：

```bash
drun run testcases/test_import_users.yaml

# 或运行套件
drun run testsuites/testsuite_csv.yaml
```

> 疑似失败时，可检查 CSV 内容与环境变量是否匹配，例如确认 `BASE_URL` 是否对外提供 `/anything` 接口。

## 📝 编写测试用例

### 基本结构

```yaml
config:
  name: 测试用例名称
  base_url: ${ENV(BASE_URL)}
  tags: [smoke, p0]

steps:
  - name: 步骤名称
    request:
      method: GET
      url: /api/endpoint
    validate:
      - eq: [status_code, 200]
      - eq: [$.data.status, "success"]
```

### 变量和提取

```yaml
steps:
  - name: 登录
    request:
      method: POST
      url: /api/auth/login
      body:
        username: ${ENV(USER_USERNAME)}
        password: ${ENV(USER_PASSWORD)}
    extract:
      token: $.data.access_token  # 提取 token
    validate:
      - eq: [status_code, 200]

  - name: 访问受保护资源
    request:
      method: GET
      url: /api/users/me
      headers:
        Authorization: Bearer $token  # 使用提取的 token
    validate:
      - eq: [status_code, 200]
```

### 使用 Hooks

```yaml
steps:
  - name: 调用需要签名的接口
    setup_hooks:
      - ${setup_hook_sign_request($request)}
    request:
      method: POST
      url: /api/secure/endpoint
    validate:
      - eq: [status_code, 200]
```

## 🔄 格式转换

将现有的 API 请求转换为 Drun 测试用例：

### cURL 转 YAML

```bash
drun convert converts/curl/sample.curl \\
  --outfile testcases/from_curl.yaml \\
  --redact Authorization \\
  --placeholders
```

### Postman Collection 转 YAML

```bash
drun convert your_collection.json \\
  --split-output \\
  --suite-out testsuites/from_postman.yaml \\
  --redact Authorization \\
  --placeholders
```

### HAR 文件转 YAML

```bash
drun convert recording.har \\
  --exclude-static \\
  --only-2xx \\
  --outfile testcases/from_har.yaml
```

更多转换选项请查看 `converts/README.md`。

## 🏷️ 标签管理

查看项目中使用的所有标签：

```bash
drun tags testcases
```

使用标签过滤测试：

```bash
# 运行 smoke 测试
drun run testcases -k "smoke"

# 排除 slow 测试
drun run testcases -k "not slow"

# 组合条件
drun run testcases -k "(smoke or regression) and not flaky"
```

## 🔍 验证和检查

验证 YAML 文件语法：

```bash
drun check testcases
```

自动修复格式问题：

```bash
drun fix testcases
```

## 📊 CI/CD 集成

### GitHub Actions 示例

```yaml
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install Drun
        run: pip install -e /path/to/drun

      - name: Run Tests
        env:
          BASE_URL: ${{ secrets.API_BASE_URL }}
          USER_USERNAME: ${{ secrets.TEST_USERNAME }}
          USER_PASSWORD: ${{ secrets.TEST_PASSWORD }}
        run: |
          drun run testcases \\
            --html reports/report.html \\
            --report reports/run.json

      - name: Upload Reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-reports
          path: reports/
```

## 📚 更多资源

- [Drun 官方文档](https://github.com/Devliang24/drun)
- [完整参考文档](https://github.com/Devliang24/drun/blob/main/docs/REFERENCE.md)
- [格式转换指南](https://github.com/Devliang24/drun/blob/main/docs/FORMAT_CONVERSION.md)
- [CI/CD 集成示例](https://github.com/Devliang24/drun/blob/main/docs/CI_CD.md)

## 🐛 问题排查

### 常见问题

1. **找不到 .env 文件**
   - 确保 `.env` 文件在项目根目录
   - 使用 `--env-file` 指定路径

2. **BASE_URL 缺失**
   - 检查 `.env` 文件中是否配置了 `BASE_URL`
   - 或通过 `--vars base_url=http://...` 传递

3. **变量未定义**
   - 检查变量名拼写
   - 确认变量在 `config.variables` 或 `extract` 中定义

### 启用调试日志

```bash
drun run testcases --log-level debug --httpx-logs --env-file .env
```

## 📄 许可证

本项目使用 MIT 许可证。
"""

# .gitkeep 文件内容（用于保留空目录）
GITKEEP_CONTENT = "# This file keeps the directory in version control\n"

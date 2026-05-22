import {
  BookOpen,
  Bug,
  CheckCircle2,
  Code2,
  FileJson2,
  FileText,
  GitBranch,
  PlayCircle,
  Repeat2,
  ServerCog,
  Terminal,
  Wrench,
} from 'lucide-react';

export type CodeSample = {
  language: string;
  code: string;
  title?: string;
};

export type ArticleSection = {
  id: string;
  title: string;
  body: string[];
  code?: CodeSample;
  kind?: 'normal' | 'tip' | 'warning';
};

export type ArticlePage = {
  id: string;
  path: string;
  title: string;
  description: string;
  icon: typeof BookOpen;
  sections: ArticleSection[];
};

export type DocGroup = {
  title: string;
  pages: string[];
};

export type AgentSkillPrompt = {
  title: string;
  when: string;
  prompt: string;
};

export type AgentSkillContent = {
  title: string;
  description: string;
  positioning: string[];
  triggerScenarios: Array<{
    title: string;
    text: string;
  }>;
  outputRules: string[];
  boundaries: string[];
  promptExamples: AgentSkillPrompt[];
  sampleOutput: CodeSample;
};

export const homeYaml = `config:
  name: 用户接口冒烟
  base_url: \${ENV(BASE_URL)}

steps:
  - name: 创建用户
    request:
      method: POST
      path: /users
      body:
        username: test_\${uuid()}
    extract:
      userId: $.data.id
    validate:
      - eq: [status_code, 201]`;

export const homeCli = `$ drun check testcases
Checked 8 file(s): 8 OK

$ drun run testcases -env dev
[RUN] files: 8 | cases: 6
[CASE] passed: 6 | failed: 0
[STEP] passed: 18 | failed: 0`;

export const agentSkillContent: AgentSkillContent = {
  title: 'Drun Agent Skill',
  description: '给 Codex / AI Agent 使用的 Drun 深度使用技能说明，帮助它稳定产出可运行 YAML、CLI 命令和排障建议。',
  positioning: [
    'drun-usage 是仓库内的本地 skill，面向“让 Agent 帮我写、解释、调试 Drun 用例”的场景。',
    '它不是新的 CLI 功能，也不是普通用户必须安装的插件；它是让 AI 协作者理解 Drun DSL、命令和约束的操作说明。',
    '使用时可以直接在提示词里点名 drun-usage skill，并给出接口、链路、错误日志或迁移输入。',
  ],
  triggerScenarios: [
    { title: '编写或改写 YAML', text: '单接口 Case、文件上传、登录链路、参数化和 caseflow 编排。' },
    { title: '解释高级 DSL', text: 'invoke、invoke_case_name(s)、repeat、sleep、hooks、request.files、response.save_body_to。' },
    { title: '设计运行命令', text: 'drun run、drun q、环境加载、-vars、-persist-env、报告和 snippet 输出。' },
    { title: '转换与迁移', text: '从 cURL、HAR、Postman、OpenAPI 起步，转换后补 validate、extract 和环境变量。' },
    { title: '排障与修复', text: '分析 drun check / drun run 输出，定位 YAML path，给出修复后的片段。' },
    { title: '报告与复现', text: '解释 JSON、HTML、Allure、snippet、server 和响应体保存的使用方式。' },
  ],
  outputRules: [
    '默认中文输出。',
    '先给可执行 YAML 或 CLI 命令，再补关键字段解释。',
    '优先围绕单接口调试、登录后链路、文件上传与报告输出给示例。',
    '如果只问单个点，只回答该点，不输出整本手册。',
  ],
  boundaries: [
    '不虚构未实现 DSL、兼容字段或旧命令。',
    'step 只能三选一：request、invoke、sleep。',
    'YAML 请求字段使用 request.path 和 request.body，避免写成 request.url 或 request.json。',
    '参数化入口是 config.parameters，顶层 parameters 无效。',
    '旧 cases: 套件不再作为推荐写法；旧 loop / foreach 请改用 repeat。',
  ],
  promptExamples: [
    {
      title: '写单接口 Drun YAML',
      when: '已有接口方法、路径、请求体和预期结果时使用。',
      prompt:
        '请使用 drun-usage skill，帮我为 POST /login 写一个 Drun YAML，用 ${ENV(BASE_URL)} 和 ${ENV(API_KEY)}，断言 status_code=200，并提取 token。',
    },
    {
      title: '组织登录后链路',
      when: '需要把多个独立 Case 串成业务流程时使用。',
      prompt:
        '请使用 drun-usage skill，帮我把登录、查询用户资料、提交订单组织成 caseflow，用 invoke 调用独立 case，并给出运行命令。',
    },
    {
      title: '排查 check / run 错误',
      when: '拿到 drun check 或 drun run 报错，需要定位和修复时使用。',
      prompt: '请使用 drun-usage skill，分析这个 drun check 报错，指出 YAML path、错误原因、修复后的 YAML 片段。',
    },
    {
      title: '从 cURL / OpenAPI 迁移',
      when: '已有调试请求或接口规范，希望沉淀成 Drun Case 时使用。',
      prompt: '请使用 drun-usage skill，把下面这段 cURL 转成 Drun YAML，并补充 validate、extract 和 -env dev 运行命令。',
    },
    {
      title: '生成运行与报告命令',
      when: '需要一次性确定环境变量、报告、snippet 等运行参数时使用。',
      prompt:
        '请使用 drun-usage skill，帮我设计一条 drun run 命令：使用 dev 环境、覆盖 tenant=blue、输出 HTML/JSON 报告，并生成 curl snippet。',
    },
    {
      title: '解释已有 YAML 风险',
      when: '评审已有用例，想确认字段含义和 DSL 约束时使用。',
      prompt: '请使用 drun-usage skill，解释下面这个 Drun YAML 每个字段的作用，并指出可能违反 DSL 约束的地方。',
    },
  ],
  sampleOutput: {
    title: 'Agent 输出形态',
    language: 'text',
    code: `可执行 YAML / CLI 命令
→ 关键字段解释
→ 常见坑与修复建议

示例输出会优先落到：
- testcases/test_login.yaml
- drun check testcases/test_login.yaml
- drun run testcases/test_login.yaml -env dev`,
  },
};

const commonOutput = `Checked 1 file(s): 1 OK, 0 failed, 0 error(s).

[SUMMARY]
Cases Pass Rate  100.00%
Steps Pass Rate  100.00%`;

export const docPages: ArticlePage[] = [
  {
    id: 'getting-started',
    path: '/docs/getting-started',
    title: '快速开始',
    description: '从安装、初始化项目、配置环境变量，到写出第一个可运行 Case。',
    icon: PlayCircle,
    sections: [
      {
        id: 'when',
        title: '适用场景',
        body: ['第一次使用 Drun，或者你想用最短路径验证本地环境、项目结构和 YAML Case 是否能跑通。'],
      },
      {
        id: 'minimal',
        title: '最小示例',
        body: ['安装后先初始化项目，再对生成的 `testcases` 目录执行检查和运行。'],
        code: {
          title: '安装与初始化',
          language: 'bash',
          code: `pip install drun
drun init myproject
cd myproject
drun check testcases
drun run testcases -env dev`,
        },
      },
      {
        id: 'full',
        title: '完整示例',
        body: ['创建 `.env.dev` 保存环境变量，再编写一个登录 Case。请求成功后提取 token，后续 Step 可以直接使用 `$token`。'],
        code: {
          title: 'testcases/test_login.yaml',
          language: 'yaml',
          code: `config:
  name: 登录接口
  base_url: \${ENV(BASE_URL)}
  tags: [smoke, auth]

steps:
  - name: 登录并提取 token
    request:
      method: POST
      path: /login
      headers:
        Authorization: Bearer \${ENV(API_KEY)}
      body:
        username: demo
        password: pass123
    extract:
      token: $.data.token
    validate:
      - eq: [status_code, 200]
      - contains: [$.message, success]`,
        },
      },
      {
        id: 'command',
        title: '运行命令',
        body: ['建议先跑 `drun check` 清理 YAML 作者错误，再跑 `drun run`。'],
        code: {
          language: 'bash',
          code: `drun check testcases/test_login.yaml
drun run testcases/test_login.yaml -env dev
drun run test_login -env dev`,
        },
      },
      {
        id: 'output',
        title: '预期输出',
        body: ['检查通过后，运行摘要会显示 Case 和 Step 的通过率。脚手架项目会默认写入日志、报告和 snippet。'],
        code: {
          language: 'text',
          code: commonOutput,
        },
      },
      {
        id: 'practice',
        title: '完整练习：从 0 写第一个 Case',
        body: ['新项目建议先只沉淀一个登录接口。确认环境、路径、请求体、状态码断言和 token 提取都正确后，再继续扩展链路。'],
        code: {
          title: '创建环境文件',
          language: 'bash',
          code: `drun init demo-api
cd demo-api
cat > .env.dev <<'EOF'
BASE_URL=https://api.example.com
API_KEY=demo-token
EOF

drun check testcases/test_login.yaml
drun run testcases/test_login.yaml -env dev`,
        },
      },
      {
        id: 'pitfalls',
        title: '常见坑',
        body: [
          '环境变量文件建议按环境命名为 `.env.dev`、`.env.test`，运行时用 `-env dev` 选择。',
          '请求路径写在 `request.path`，不要写成 `request.url`。',
          'JSON 请求体写在 `request.body`，不要写成 `request.json`。',
        ],
        kind: 'warning',
      },
    ],
  },
  {
    id: 'yaml-dsl',
    path: '/docs/yaml-dsl',
    title: 'YAML DSL 基础',
    description: '理解 `config`、`steps`、`request`、`extract`、`validate` 的最小闭环。',
    icon: Code2,
    sections: [
      {
        id: 'when',
        title: '适用场景',
        body: ['当你准备把一个 HTTP 调试请求沉淀成稳定测试时，先用 DSL 的五个核心块描述“请求、提取、断言”。'],
      },
      {
        id: 'minimal',
        title: '最小示例',
        body: ['一个最小 Request Step 只需要 `name`、`request.method`、`request.path` 和一个基础断言。'],
        code: {
          language: 'yaml',
          code: `config:
  name: 健康检查
  base_url: \${ENV(BASE_URL)}

steps:
  - name: 查询健康状态
    request:
      method: GET
      path: /health
    validate:
      - eq: [status_code, 200]`,
        },
      },
      {
        id: 'full',
        title: '完整示例',
        body: ['真实 Case 通常会包含请求头、请求体、提取变量和多条断言。`extract` 写出的变量可被后续 Step 通过 `$变量名` 复用。'],
        code: {
          language: 'yaml',
          code: `config:
  name: 用户创建与查询
  base_url: \${ENV(BASE_URL)}

steps:
  - name: 创建用户
    request:
      method: POST
      path: /users
      headers:
        Authorization: Bearer \${ENV(API_KEY)}
      body:
        username: test_\${uuid()}
        email: user@example.com
    extract:
      userId: $.data.id
    validate:
      - eq: [status_code, 201]
      - regex: [$.data.id, '^\\d+$']

  - name: 查询用户
    request:
      method: GET
      path: /users/$userId
    validate:
      - eq: [status_code, 200]
      - eq: [$.data.id, $userId]`,
        },
      },
      {
        id: 'command',
        title: '运行命令',
        body: ['单文件调试时可直接指定 YAML 文件；稳定后再放进目录批量运行。'],
        code: {
          language: 'bash',
          code: `drun check testcases/test_user_api.yaml
drun run testcases/test_user_api.yaml -env dev
drun run testcases -env dev -k smoke`,
        },
      },
      {
        id: 'output',
        title: '预期输出',
        body: ['当断言都通过时，Step 和 Case 都会计为 passed；任一断言失败会让对应 Step 失败。'],
        code: {
          language: 'text',
          code: `[CASE] 用户创建与查询 passed
[STEP] 创建用户 passed
[STEP] 查询用户 passed`,
        },
      },
      {
        id: 'pitfalls',
        title: '常见坑',
        body: [
          '每个 Step 只能有一个执行目标：`request`、`invoke`、`sleep` 三选一。',
          '`validate` 和 `extract` 与 `request` 同级，不要缩进到 `request` 下面。',
          '响应体路径使用 `$.data.id` 这类 JSONPath，不要写成 `body.data.id`。',
        ],
        kind: 'warning',
      },
    ],
  },
  {
    id: 'request',
    path: '/docs/request',
    title: '请求写法',
    description: '掌握 method、path、headers、body、data、files、auth、stream 的常用组合。',
    icon: Terminal,
    sections: [
      {
        id: 'when',
        title: '适用场景',
        body: ['当接口需要请求头、JSON body、表单、上传文件、认证或流式响应时，把请求控制字段集中写在 `request` 下。'],
      },
      {
        id: 'minimal',
        title: '最小示例',
        body: ['普通 JSON 请求使用 `request.body`。Drun 会把它作为请求 payload 发送并写入报告。'],
        code: {
          language: 'yaml',
          code: `steps:
  - name: 创建用户
    request:
      method: POST
      path: /users
      body:
        username: demo
        email: demo@example.com
    validate:
      - eq: [status_code, 201]`,
        },
      },
      {
        id: 'full',
        title: '完整示例',
        body: ['文件上传时，二进制文件放 `request.files`，普通 multipart 字段放 `request.data`。如果接口返回大文件，可配合 `response.save_body_to` 保存。'],
        code: {
          language: 'yaml',
          code: `steps:
  - name: 上传头像
    request:
      method: POST
      path: /users/$userId/avatar
      auth:
        type: bearer
        token: $token
      data:
        source: web
      files:
        avatar: data/avatar.png
    validate:
      - eq: [status_code, 200]

  - name: 下载头像
    request:
      method: GET
      path: /users/$userId/avatar
      stream: true
    response:
      save_body_to: downloads/avatar.png
    validate:
      - eq: [status_code, 200]`,
        },
      },
      {
        id: 'command',
        title: '运行命令',
        body: ['上传场景建议先单文件运行，确认本地路径和环境变量都正确。'],
        code: {
          language: 'bash',
          code: `drun check testcases/test_upload_avatar.yaml
drun run testcases/test_upload_avatar.yaml -env dev -snippet curl`,
        },
      },
      {
        id: 'output',
        title: '预期输出',
        body: ['运行成功后，报告里能看到脱敏后的 request 信息；保存响应体的 Step 会在目标路径写出文件。'],
        code: {
          language: 'text',
          code: `[STEP] 上传头像 passed
[STEP] 下载头像 passed
[OUTPUT] Saved response body to downloads/avatar.png`,
        },
      },
      {
        id: 'pitfalls',
        title: '常见坑',
        body: [
          '`request.files` 和普通 JSON `body` 不要混用；multipart 普通字段放到 `request.data`。',
          '文件路径要相对当前项目可解析，CI 中要确认测试数据也被提交。',
          '敏感 header 建议来自环境变量，不要直接写真实密钥。',
        ],
        kind: 'warning',
      },
    ],
  },
  {
    id: 'templating',
    path: '/docs/templating',
    title: '模板变量',
    description: '使用 `$var`、`${ENV(KEY)}`、`${uuid()}`，并理解严格渲染失败。',
    icon: FileText,
    sections: [
      {
        id: 'when',
        title: '适用场景',
        body: ['当请求需要环境隔离、随机数据、跨 Step 变量传递时，用模板表达式替代写死值。'],
      },
      {
        id: 'minimal',
        title: '最小示例',
        body: ['`${ENV(BASE_URL)}` 从环境文件读取，`${uuid()}` 生成运行期值，`$token` 引用前面提取出的变量。'],
        code: {
          language: 'yaml',
          code: `config:
  base_url: \${ENV(BASE_URL)}

steps:
  - name: 查询资料
    request:
      method: GET
      path: /profile
      headers:
        Authorization: Bearer $token
      body:
        trace_id: \${uuid()}`,
        },
      },
      {
        id: 'full',
        title: '完整示例',
        body: ['推荐把基础地址、密钥、租户等放到 `.env.dev`，把业务变量通过 `extract` 传递。'],
        code: {
          language: 'yaml',
          code: `config:
  name: 模板变量示例
  base_url: \${ENV(BASE_URL)}

steps:
  - name: 登录
    request:
      method: POST
      path: /login
      body:
        username: \${ENV(USERNAME)}
        password: \${ENV(PASSWORD)}
    extract:
      token: $.data.token
    validate:
      - eq: [status_code, 200]

  - name: 创建订单
    request:
      method: POST
      path: /orders
      headers:
        Authorization: Bearer $token
      body:
        request_id: \${uuid()}
        sku: SKU-001
    validate:
      - eq: [status_code, 201]`,
        },
      },
      {
        id: 'command',
        title: '运行命令',
        body: ['命令行变量适合覆盖一次性参数，环境文件适合长期配置。'],
        code: {
          language: 'bash',
          code: `drun run testcases/test_order.yaml -env dev
drun run testcases/test_order.yaml -env dev -vars sku=SKU-002`,
        },
      },
      {
        id: 'output',
        title: '预期输出',
        body: ['变量解析成功时，请求会使用渲染后的值；严格渲染失败时会直接指出缺失变量名。'],
        code: {
          language: 'text',
          code: `Strict render failed: missing variable 'token'
Hint: extract token before using $token, or pass it with -vars token=...`,
        },
      },
      {
        id: 'pitfalls',
        title: '常见坑',
        body: [
          '不要在示例里提交真实 `.env` 密钥。',
          '使用 `$token` 前必须先通过 `extract` 或 `-vars` 提供它。',
          '表达式拼写错误会在严格渲染阶段暴露，先跑 `drun check` 再运行。',
        ],
        kind: 'warning',
      },
    ],
  },
  {
    id: 'assertions-extract',
    path: '/docs/assertions-extract',
    title: '断言与提取',
    description: '用状态码、JSONPath 和常用断言把接口结果变成可维护的检查点。',
    icon: CheckCircle2,
    sections: [
      {
        id: 'when',
        title: '适用场景',
        body: ['当你不只想确认接口“能返回”，还要确认字段值、结构、长度、业务状态和后续变量传递时使用。'],
      },
      {
        id: 'minimal',
        title: '最小示例',
        body: ['用 `eq` 检查 HTTP 状态码，再用 JSONPath 检查响应体字段。'],
        code: {
          language: 'yaml',
          code: `validate:
  - eq: [status_code, 200]
  - eq: [$.data.enabled, true]`,
        },
      },
      {
        id: 'full',
        title: '完整示例',
        body: ['提取出的 `userId` 会进入运行上下文，后续 Step 可直接 `$userId`。'],
        code: {
          language: 'yaml',
          code: `steps:
  - name: 创建用户
    request:
      method: POST
      path: /users
      body:
        username: demo_\${uuid()}
    extract:
      userId: $.data.id
    validate:
      - eq: [status_code, 201]
      - regex: [$.data.id, '^\\d+$']
      - contains: [$.message, success]

  - name: 校验用户详情
    request:
      method: GET
      path: /users/$userId
    validate:
      - eq: [status_code, 200]
      - eq: [$.data.id, $userId]`,
        },
      },
      {
        id: 'command',
        title: '运行命令',
        body: ['调试提取失败时，先输出 JSON 报告，查看响应体和 StepResult。'],
        code: {
          language: 'bash',
          code: `drun run testcases/test_user_detail.yaml -env dev -report reports/user-detail.json`,
        },
      },
      {
        id: 'output',
        title: '预期输出',
        body: ['断言通过会进入 passed；提取失败或路径不存在会让当前 Step 失败，并在报告中保留定位信息。'],
        code: {
          language: 'text',
          code: `[ASSERT] eq status_code 200 passed
[EXTRACT] userId <- $.data.id`,
        },
      },
      {
        id: 'pitfalls',
        title: '常见坑',
        body: [
          'JSONPath 从 `$` 开始，例如 `$.data.id`。',
          '用于后续请求的变量建议在同一个 Case 内明确提取，减少外部依赖。',
          '断言太少会让用例只能检查“接口没挂”，不能证明业务正确。',
        ],
        kind: 'tip',
      },
    ],
  },
  {
    id: 'parameters',
    path: '/docs/parameters',
    title: '参数化',
    description: '使用 `config.parameters`、CSV、product、zip 组织数据驱动测试。',
    icon: Repeat2,
    sections: [
      {
        id: 'when',
        title: '适用场景',
        body: ['当同一条 Case 需要用多组用户、订单、区域或组合数据重复执行时，把数据放进 `config.parameters`。'],
      },
      {
        id: 'minimal',
        title: '最小示例',
        body: ['最小参数化直接在 YAML 中声明变量列表。每组参数会生成一个 Case 实例。'],
        code: {
          language: 'yaml',
          code: `config:
  name: 多用户查询
  parameters:
    - user_id: [1, 2, 3]

steps:
  - name: 查询用户 $user_id
    request:
      method: GET
      path: /users/$user_id
    validate:
      - eq: [status_code, 200]`,
        },
      },
      {
        id: 'full',
        title: '完整示例',
        body: ['CSV 适合维护大批量数据；product 适合笛卡尔组合；zip 适合按行对齐组合。'],
        code: {
          language: 'yaml',
          code: `config:
  name: 商品区域组合校验
  parameters:
    - csv:
        path: data/users.csv
    - product:
        sku: [SKU-001, SKU-002]
        region: [cn, us]
    - zip:
        order_id: [A100, A101]
        expected_status: [paid, shipped]

steps:
  - name: 查询订单 $order_id
    request:
      method: GET
      path: /orders/$order_id
    validate:
      - eq: [status_code, 200]
      - eq: [$.data.status, $expected_status]`,
        },
      },
      {
        id: 'command',
        title: '运行命令',
        body: ['参数化用例建议先跑 `check`，尤其是 CSV 路径和变量名。'],
        code: {
          language: 'bash',
          code: `drun check testcases/test_orders.yaml
drun run testcases/test_orders.yaml -env dev`,
        },
      },
      {
        id: 'output',
        title: '预期输出',
        body: ['运行摘要中的 Case 数会按参数展开后的实例数统计。'],
        code: {
          language: 'text',
          code: `[RUN] Matched cases: 8
[CASE] Total: 8 Passed: 8 Failed: 0`,
        },
      },
      {
        id: 'pitfalls',
        title: '常见坑',
        body: [
          '参数化入口是 `config.parameters`，顶层 `parameters` 无效。',
          'CSV 表头要和 YAML 中使用的变量名一致。',
          'zip 模式下各列表长度应保持一致，避免数据错位。',
        ],
        kind: 'warning',
      },
    ],
  },
  {
    id: 'composition',
    path: '/docs/composition',
    title: '组合复用',
    description: '用 `caseflow`、`invoke`、`repeat`、`sleep` 和 hooks 组织业务链路。',
    icon: GitBranch,
    sections: [
      {
        id: 'when',
        title: '适用场景',
        body: ['当单个业务链路包含登录、查询、提交、校验多个 Case 时，用 suite 文件描述顺序，而不是把所有请求堆在一个大 YAML 里。'],
      },
      {
        id: 'minimal',
        title: '最小示例',
        body: ['`caseflow` 里的每一项通过 `invoke` 调用已有 Case。'],
        code: {
          language: 'yaml',
          code: `config:
  name: 登录后链路

caseflow:
  - name: 获取登录态
    invoke: test_login

  - name: 查询用户资料
    invoke: test_profile`,
        },
      },
      {
        id: 'full',
        title: '完整示例',
        body: ['当被调用 YAML 中有多个 Case，可以用 `invoke_case_name` 或 `invoke_case_names` 精确选择。`repeat` 和 `sleep` 适合轮询或等待异步任务。'],
        code: {
          language: 'yaml',
          code: `config:
  name: 下单后校验链路

caseflow:
  - name: 登录
    invoke: test_auth
    invoke_case_name: 登录成功

  - name: 创建订单
    invoke: test_order
    invoke_case_names: [创建普通订单, 创建优惠订单]

  - name: 等待订单入库
    sleep: 2000

  - name: 轮询订单状态
    invoke: test_order_status
    repeat: 3`,
        },
      },
      {
        id: 'command',
        title: '运行命令',
        body: ['套件文件和普通 Case 一样用 `drun run` 执行。'],
        code: {
          language: 'bash',
          code: `drun check testsuites/smoke.yaml
drun run testsuites/smoke.yaml -env dev -failfast`,
        },
      },
      {
        id: 'output',
        title: '预期输出',
        body: ['报告会保留每个 invoke 展开后的 Case 和 Step，便于定位失败发生在哪个业务片段。'],
        code: {
          language: 'text',
          code: `[CASEFLOW] 登录 passed
[CASEFLOW] 创建订单 passed
[CASEFLOW] 轮询订单状态 passed`,
        },
      },
      {
        id: 'practice',
        title: '完整练习：登录后业务链路',
        body: ['登录后链路不要写成一个巨大的 YAML。把登录、资料查询、业务动作拆成独立 Case，再由 suite 表达执行顺序。'],
        code: {
          language: 'yaml',
          code: `config:
  name: 登录后冒烟链路

caseflow:
  - name: 登录成功
    invoke: test_auth
    invoke_case_name: 登录成功

  - name: 查询用户资料
    invoke: test_profile

  - name: 提交业务动作
    invoke: test_submit_order

  - name: 等待异步处理
    sleep: 2000

  - name: 查询处理结果
    invoke: test_order_status
    repeat: 3`,
        },
      },
      {
        id: 'pitfalls',
        title: '常见坑',
        body: [
          '`invoke`、`request`、`sleep` 不能放在同一个 step 中。',
          '`invoke_case_name` 选不到 Case 时，优先检查被调用文件里的 `config.name`。',
          '显式等待用 `sleep`，不要写成空请求或临时接口。',
        ],
        kind: 'warning',
      },
    ],
  },
  {
    id: 'execution-env',
    path: '/docs/execution-env',
    title: '运行与环境',
    description: '掌握 `drun run`、`drun check`、环境文件、CLI 变量和运行控制参数。',
    icon: ServerCog,
    sections: [
      {
        id: 'when',
        title: '适用场景',
        body: ['当你要在本地、测试环境、CI 中运行同一批 Case，并通过不同环境变量切换目标系统时使用。'],
      },
      {
        id: 'minimal',
        title: '最小示例',
        body: ['目标可以是单个 YAML、目录，或省略 `.yaml` 的文件名。'],
        code: {
          language: 'bash',
          code: `drun check testcases
drun run testcases -env dev
drun run test_login -env dev`,
        },
      },
      {
        id: 'full',
        title: '完整示例',
        body: ['用 `-vars` 临时覆盖变量，用 `-failfast` 在首个失败处停下，用 `-persist-env` 写回提取变量。'],
        code: {
          language: 'bash',
          code: `drun run testcases -env dev \\
  -vars tenant=blue region=cn \\
  -failfast \\
  -persist-env`,
        },
      },
      {
        id: 'command',
        title: '运行命令',
        body: ['日常建议把检查和运行拆成两个命令，CI 中也更容易定位 YAML 作者错误。'],
        code: {
          language: 'bash',
          code: `drun check testcases
drun run testcases -env test -report reports/result.json -html reports/report.html`,
        },
      },
      {
        id: 'output',
        title: '预期输出',
        body: ['`drun check` 聚合输出 YAML 问题；`drun run` 执行真实请求并输出运行摘要。'],
        code: {
          language: 'text',
          code: `Checked 8 file(s): 8 OK, 0 failed, 0 error(s).
[ENV] Using environment: test -> .env.test
[RUN] Discovered files: 8 | Matched cases: 8`,
        },
      },
      {
        id: 'pitfalls',
        title: '常见坑',
        body: [
          '运行目录和数据文件相对路径要保持一致，CI 中尤其要注意工作目录。',
          '`-vars` 适合一次性覆盖，不建议长期替代环境文件。',
          '真实密钥应放到 CI secrets 或本地环境文件，不要提交到仓库。',
        ],
        kind: 'tip',
      },
    ],
  },
  {
    id: 'reports',
    path: '/docs/reports',
    title: '报告与输出',
    description: '生成 HTML、JSON、Allure、snippet，并保存响应体或导出 CSV。',
    icon: FileJson2,
    sections: [
      {
        id: 'when',
        title: '适用场景',
        body: ['当你需要给团队查看运行结果、给 CI 归档、复现失败请求或保存二进制响应时使用。'],
      },
      {
        id: 'minimal',
        title: '最小示例',
        body: ['HTML 给人看，JSON 给自动化系统消费，snippet 给失败复现。'],
        code: {
          language: 'bash',
          code: `drun run testcases -env dev -html reports/report.html
drun run testcases -env dev -report reports/result.json
drun run testcases -env dev -snippet curl`,
        },
      },
      {
        id: 'full',
        title: '完整示例',
        body: ['文件下载、导出接口和数组响应可以在 YAML 中声明保存目标。'],
        code: {
          language: 'yaml',
          code: `steps:
  - name: 下载发票
    request:
      method: GET
      path: /orders/$orderId/invoice
      stream: true
    response:
      save_body_to: downloads/invoice.pdf
    validate:
      - eq: [status_code, 200]

  - name: 导出用户列表
    request:
      method: GET
      path: /users
    export:
      csv: exports/users.csv
    validate:
      - eq: [status_code, 200]`,
        },
      },
      {
        id: 'command',
        title: '运行命令',
        body: ['如果要接入 Allure，输出 Allure results 目录，再由 CI 负责生成最终报告。'],
        code: {
          language: 'bash',
          code: `drun run testcases -env dev \\
  -html reports/report.html \\
  -report reports/result.json \\
  -allure-results allure-results \\
  -snippet curl`,
        },
      },
      {
        id: 'output',
        title: '预期输出',
        body: ['脚手架项目默认会组织日志、报告和 snippet；临时单文件运行默认更克制，只输出必要日志。'],
        code: {
          language: 'text',
          code: `[REPORT] JSON: reports/result.json
[REPORT] HTML: reports/report.html
[SNIPPET] curl snippets/20260522`,
        },
      },
      {
        id: 'pitfalls',
        title: '常见坑',
        body: [
          '报告会尽量避免暴露原始二进制内容；需要文件时用 `response.save_body_to`。',
          'snippet 用于复现请求，不适合长期保存真实密钥。',
          'HTML 报告页面修改后需要额外做浏览器验收。',
        ],
        kind: 'tip',
      },
    ],
  },
  {
    id: 'debug-migration',
    path: '/docs/debug-migration',
    title: '调试与迁移',
    description: '用 `drun q` 打通请求，再从 cURL、HAR、Postman、OpenAPI 迁移到 YAML。',
    icon: Wrench,
    sections: [
      {
        id: 'when',
        title: '适用场景',
        body: ['当你手里已有 cURL、接口规范或抓包文件，想快速变成可维护 Drun Case 时使用。'],
      },
      {
        id: 'minimal',
        title: '最小示例',
        body: ['先用 `drun q` 确认请求能打通，再决定是否落成 YAML。'],
        code: {
          language: 'bash',
          code: `drun q https://api.example.com/ping
drun q https://api.example.com/users -X POST -d '{"name":"alice"}'`,
        },
      },
      {
        id: 'full',
        title: '完整示例',
        body: ['从已有资产转换后，通常还要补充 `extract`、`validate`、环境变量和 caseflow。'],
        code: {
          language: 'bash',
          code: `drun convert sample.curl -outfile converts/sample.yaml
drun convert api.har -outfile converts/api.yaml
drun convert-openapi spec/openapi/ecommerce_api.json \\
  -output-mode split \\
  -outfile converts/ecommerce.yaml
drun export curl testcases/test_user_api.yaml -outfile request.curl`,
        },
      },
      {
        id: 'command',
        title: '运行命令',
        body: ['转换完成后先检查 YAML，再单文件运行。'],
        code: {
          language: 'bash',
          code: `drun check converts/ecommerce.yaml
drun run converts/ecommerce.yaml -env dev`,
        },
      },
      {
        id: 'output',
        title: '预期输出',
        body: ['转换输出是起点，不是终点。你应该看到 YAML 文件生成，然后继续补断言和变量。'],
        code: {
          language: 'text',
          code: `[CONVERT] Wrote converts/ecommerce.yaml
Checked 1 file(s): 1 OK, 0 failed, 0 error(s).`,
        },
      },
      {
        id: 'practice',
        title: '完整练习：从 cURL / OpenAPI 迁移',
        body: ['迁移流程是“先转换，再检查，再补断言”。转换产物能帮你起步，但最终测试资产需要替换真实密钥、补充变量和业务断言。'],
        code: {
          language: 'bash',
          code: `drun convert sample.curl -outfile converts/sample.yaml
drun convert-openapi spec/openapi/ecommerce_api.json \\
  -output-mode split \\
  -outfile converts/ecommerce.yaml

drun check converts/ecommerce.yaml
drun run converts/ecommerce.yaml -env dev
drun export curl testcases/test_user_api.yaml -outfile request.curl`,
        },
      },
      {
        id: 'pitfalls',
        title: '常见坑',
        body: [
          '转换工具不会知道你的业务断言，需要人工补 `validate`。',
          '从 cURL 转出来的真实 token 要替换成 `${ENV(API_KEY)}`。',
          'OpenAPI 生成的是骨架，适合批量起步，不等于完整测试资产。',
        ],
        kind: 'warning',
      },
    ],
  },
  {
    id: 'troubleshooting',
    path: '/docs/troubleshooting',
    title: '排障指南',
    description: '理解 `DRUN-YAML-xxx` 诊断、常见写错方式和优化前后输出。',
    icon: Bug,
    sections: [
      {
        id: 'when',
        title: '适用场景',
        body: ['当 `drun check` 或 `drun run` 发现 YAML/DSL 作者错误时，根据错误码、文件位置、Path、hint 和 example 快速修正。'],
      },
      {
        id: 'minimal',
        title: '最小示例',
        body: ['`request.url` 是常见误写，Drun 应提示你改成 `request.path`。'],
        code: {
          title: '优化前后：request.url',
          language: 'text',
          code: `优化前:
FAIL: testcases/test_demo.yaml -> Failed to load testcases/test_demo.yaml
steps.0.request.url
  Extra inputs are not permitted

优化后:
DRUN-YAML-003 Invalid request field: request.url
File: testcases/test_demo.yaml:8
Path: steps[0].request.url

Use request.path instead of request.url.

Example:
  request:
    method: GET
    path: /api/users`,
        },
      },
      {
        id: 'full',
        title: '完整示例',
        body: ['顶层 `parameters` 也是常见错误。参数化必须写在 `config.parameters`。'],
        code: {
          title: '优化前后：parameters',
          language: 'text',
          code: `优化前:
FAIL: testcases/test_users.yaml -> Invalid top-level 'parameters'.
Move case parameters under 'config.parameters'.

优化后:
DRUN-YAML-006 Invalid parameter location
File: testcases/test_users.yaml:2
Path: parameters

Move parameters under config.parameters.

Example:
  config:
    name: User cases
    parameters:
      - user_id: [1, 2, 3]`,
        },
      },
      {
        id: 'command',
        title: '运行命令',
        body: ['日常先批量检查目录；运行时仍保持首个阻断错误快速退出。'],
        code: {
          language: 'bash',
          code: `drun check testcases
drun run testcases -env dev`,
        },
      },
      {
        id: 'output',
        title: '预期输出',
        body: ['多文件检查会聚合输出，每个文件最多显示 5 条错误，并给出总数。'],
        code: {
          title: '多文件聚合',
          language: 'text',
          code: `FAIL testcases/test_a.yaml
  DRUN-YAML-004 request.json is not supported
  DRUN-YAML-007 Invalid check syntax: body.id

FAIL testcases/test_b.yaml
  DRUN-YAML-011 Step cannot combine request and sleep

Checked 8 file(s): 6 OK, 2 failed, 3 error(s).`,
        },
      },
      {
        id: 'practice',
        title: '完整练习：用 check 修作者错误',
        body: ['团队批量写 YAML 后，先用 `drun check` 清掉字段写错、缩进错误和旧 DSL 写法，再运行真实请求。'],
        code: {
          language: 'text',
          code: `$ drun check testcases
FAIL testcases/test_a.yaml
  DRUN-YAML-003 Invalid request field: request.url
  DRUN-YAML-004 request.json is not supported

FAIL testcases/test_b.yaml
  DRUN-YAML-006 Invalid parameter location

Checked 10 file(s): 8 OK, 2 failed, 3 error(s).

$ drun check testcases
Checked 10 file(s): 10 OK, 0 failed, 0 error(s).`,
        },
      },
      {
        id: 'pitfalls',
        title: '常见坑',
        body: [
          '`request.json` 改为 `request.body`。',
          '`body.id` 改为 `$.data.id` 这类 JSONPath。',
          '`request`、`invoke`、`sleep` 一个 Step 里只能保留一个。',
        ],
        kind: 'warning',
      },
    ],
  },
];

export const docGroups: DocGroup[] = [
  { title: '入门', pages: ['getting-started', 'yaml-dsl', 'request'] },
  { title: '核心能力', pages: ['templating', 'assertions-extract', 'parameters', 'composition'] },
  { title: '运行与输出', pages: ['execution-env', 'reports', 'debug-migration', 'troubleshooting'] },
];

export const featureCards = [
  { title: '用户指南', text: '从安装到实战链路，按用户学习路径组织。', icon: BookOpen },
  { title: 'YAML DSL', text: '用可读 YAML 描述请求、变量、断言和编排。', icon: Code2 },
  { title: '诊断排障', text: 'drun check 输出稳定错误码、定位、hint 和示例。', icon: Bug },
  { title: '报告输出', text: 'HTML、JSON、Allure、snippet 和响应体保存。', icon: FileJson2 },
];

export function findPage(path: string): ArticlePage | undefined {
  return docPages.find((page) => page.path === path);
}

export function pageById(id: string): ArticlePage | undefined {
  return docPages.find((page) => page.id === id);
}

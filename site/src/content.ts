import {
  BookOpen,
  Bug,
  CheckCircle2,
  Code2,
  FileJson2,
  FileText,
  GitBranch,
  Layers3,
  PlayCircle,
  Repeat2,
  Terminal,
  Wrench,
} from 'lucide-react';

export type CodeSample = {
  language: string;
  code: string;
};

export type DocPage = {
  id: string;
  title: string;
  kicker: string;
  icon: typeof BookOpen;
  summary: string;
  bullets: string[];
  sample: CodeSample;
};

export type Tutorial = {
  id: string;
  title: string;
  summary: string;
  steps: string[];
  sample: CodeSample;
};

export const navItems = [
  { id: 'home', label: '首页' },
  { id: 'docs', label: '文档' },
  { id: 'tutorials', label: '教程' },
  { id: 'troubleshooting', label: '排障' },
];

export const heroYaml = `config:
  name: 用户接口冒烟
  base_url: \${ENV(BASE_URL)}
  tags: [smoke, user]

steps:
  - name: 创建用户
    request:
      method: POST
      path: /users
      headers:
        Authorization: Bearer \${ENV(API_KEY)}
      body:
        username: test_\${uuid()}
    extract:
      userId: $.data.id
    validate:
      - eq: [status_code, 201]

  - name: 查询用户
    request:
      method: GET
      path: /users/$userId
    validate:
      - eq: [status_code, 200]`;

export const cliOutput = `$ drun run testcases -env dev -k smoke

[ENV] Using environment: dev -> .env.dev
[RUN] Discovered files: 8 | Matched cases: 6
[CASE] Total: 6 Passed: 6 Failed: 0
[STEP] Total: 18 Passed: 18 Failed: 0

[SUMMARY]
Cases Pass Rate  100.00%
Steps Pass Rate  100.00%`;

export const docs: DocPage[] = [
  {
    id: 'quick-start',
    title: '快速开始',
    kicker: 'README 精简路径',
    icon: PlayCircle,
    summary: '从安装、初始化项目、配置环境到执行第一个 YAML Case。',
    bullets: ['Python 3.10+', 'pip install drun', 'drun init 生成脚手架', 'run/check/server 常用入口'],
    sample: {
      language: 'bash',
      code: `pip install drun
drun init myproject
cd myproject
drun run testcases/test_user_api.yaml -env dev`,
    },
  },
  {
    id: 'dsl-core',
    title: 'DSL Core',
    kicker: 'YAML 作者体验',
    icon: Code2,
    summary: '用 config、steps、request、extract、validate 描述 HTTP API 测试。',
    bullets: ['每个 Step 只有一个执行目标', 'request.body 承载 JSON payload', 'extract 使用 $.data.id', 'validate 使用稳定断言语法'],
    sample: {
      language: 'yaml',
      code: `steps:
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
      - eq: [status_code, 200]`,
    },
  },
  {
    id: 'composition',
    title: '组合复用',
    kicker: 'caseflow / invoke',
    icon: GitBranch,
    summary: '把登录、查询、下单等 Case 拆开，再用 caseflow 和 invoke 组织链路。',
    bullets: ['invoke 复用现有 Case', 'invoke_case_name 选择目标 Case', 'repeat 控制重复执行', 'sleep 表达显式等待'],
    sample: {
      language: 'yaml',
      code: `config:
  name: 登录后链路

caseflow:
  - name: 登录
    invoke: test_login

  - name: 查询资料
    invoke: test_profile
    repeat: 2`,
    },
  },
  {
    id: 'execution-env',
    title: '运行与环境',
    kicker: 'run / env / vars',
    icon: Terminal,
    summary: '掌握运行目标、环境文件、CLI 变量、failfast 和运行期变量持久化。',
    bullets: ['支持文件、目录和省略扩展名', '-env 选择 .env.dev', '-vars 覆盖运行变量', '-persist-env 写回提取变量'],
    sample: {
      language: 'bash',
      code: `drun run testcases -env dev
drun run test_login -env dev
drun run testcases:登录,查询资料 -env dev
drun run testcases -env dev -vars tenant=blue -failfast`,
    },
  },
  {
    id: 'reports',
    title: '报告与输出',
    kicker: 'HTML / JSON / Allure',
    icon: FileJson2,
    summary: '运行后生成日志、HTML/JSON/Allure 报告和可复现请求 snippet。',
    bullets: ['脚手架项目默认输出 logs/reports/snippets', '临时单文件默认只写日志', 'response.save_body_to 保存二进制响应', 'export.csv 导出响应数组'],
    sample: {
      language: 'bash',
      code: `drun run testcases -env dev -html reports/report.html
drun run testcases -env dev -report reports/result.json
drun run testcases -env dev -allure-results allure-results
drun run testcases -env dev -snippet python`,
    },
  },
  {
    id: 'debug-convert',
    title: '调试与转换',
    kicker: 'q / convert / export',
    icon: Wrench,
    summary: '先用 drun q 打通请求，再从 cURL、HAR、Postman、OpenAPI 迁移到 YAML。',
    bullets: ['drun q 快速试请求', 'convert 导入 cURL/HAR/Postman', 'convert-openapi 起骨架', 'export curl 反推请求'],
    sample: {
      language: 'bash',
      code: `drun q https://api.example.com/ping
drun q https://api.example.com/users -X POST -d '{"name":"alice"}'
drun convert sample.curl -outfile out.yaml
drun export curl testcases/test_user_api.yaml -outfile request.curl`,
    },
  },
];

export const featureCards = [
  { title: 'YAML DSL', text: '用可读 YAML 描述请求、变量、断言和编排。', icon: FileText },
  { title: '断言与提取', text: '内置 eq、contains、regex、len_eq、gt 等常用断言。', icon: CheckCircle2 },
  { title: 'invoke 编排', text: '把 Case 拆小，再用 caseflow 组织完整业务链路。', icon: Layers3 },
  { title: 'repeat / sleep', text: '表达轮询、重试前等待和稳定性检查。', icon: Repeat2 },
  { title: '报告输出', text: 'HTML、JSON、Allure、日志和代码片段一站输出。', icon: FileJson2 },
  { title: '作者诊断', text: 'drun check 输出 DRUN-YAML-xxx 错误码和修复建议。', icon: Bug },
];

export const tutorials: Tutorial[] = [
  {
    id: 'first-case',
    title: '从 0 写第一个 Drun Case',
    summary: '适合第一次接触 Drun 的用户：初始化项目、配置 BASE_URL、写一个登录请求。',
    steps: ['安装 drun 并初始化脚手架', '在 .env 写 BASE_URL 和 API_KEY', '创建 testcases/test_login.yaml', '执行 drun check，再执行 drun run'],
    sample: {
      language: 'yaml',
      code: `config:
  name: 第一个登录 Case
  base_url: \${ENV(BASE_URL)}

steps:
  - name: 登录
    request:
      method: POST
      path: /login
      headers:
        Authorization: Bearer \${ENV(API_KEY)}
      body:
        username: demo
        password: pass123
    validate:
      - eq: [status_code, 200]`,
    },
  },
  {
    id: 'invoke-flow',
    title: '用 invoke 组织登录后链路',
    summary: '把登录、查询资料、业务动作拆成独立 Case，再通过 caseflow 串起来。',
    steps: ['登录 Case 负责提取 token', '业务 Case 通过环境或持久化变量复用 token', '套件文件只描述执行顺序', '失败时从报告定位具体 Step'],
    sample: {
      language: 'yaml',
      code: `caseflow:
  - name: 获取登录态
    invoke: test_login

  - name: 查询用户资料
    invoke: test_profile

  - name: 提交业务动作
    invoke: test_submit_order`,
    },
  },
  {
    id: 'check-diagnostics',
    title: '用 drun check 修 YAML 作者错误',
    summary: '先聚合清理 YAML/DSL 错误，再运行测试，减少调试往返。',
    steps: ['对 testcases 运行 drun check', '按 DRUN-YAML-xxx 错误码定位问题', '根据 hint 和 example 修复', '再执行 drun run'],
    sample: {
      language: 'text',
      code: `DRUN-YAML-003 Invalid request field: request.url
File: testcases/test_demo.yaml:8
Path: steps[0].request.url

Use request.path instead of request.url.`,
    },
  },
  {
    id: 'convert-openapi',
    title: '从 cURL / OpenAPI 迁移到 Drun',
    summary: '把已有调试资产转成 YAML，再逐步补充变量、断言和编排。',
    steps: ['用 drun q 验证单个请求', '从 cURL 或 OpenAPI 转出 YAML', '补充 extract 和 validate', '用 export curl 生成复现脚本'],
    sample: {
      language: 'bash',
      code: `drun convert sample.curl -outfile converts/sample.yaml
drun convert-openapi spec/openapi/ecommerce_api.json \\
  -output-mode split \\
  -outfile converts/ecommerce.yaml`,
    },
  },
];

export const diagnostics = [
  ['DRUN-YAML-003', 'request.url 写错字段', '改为 request.path。'],
  ['DRUN-YAML-004', 'request.json 不支持', 'JSON payload 放到 request.body。'],
  ['DRUN-YAML-006', 'parameters 位置错误', '使用 config.parameters。'],
  ['DRUN-YAML-007', 'body 路径语法错误', 'validate / extract 使用 $.data.id。'],
  ['DRUN-YAML-011', 'Step 执行目标错误', 'request、invoke、sleep 只能三选一。'],
  ['DRUN-YAML-014', 'Step 间距不符合规则', '多个 step item 之间增加空行。'],
];

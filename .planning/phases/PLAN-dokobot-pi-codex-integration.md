# Plan: 在 Pi Agent 和 Codex 中集成 Dokobot（通过 skill + extension + plugin）

## Goal
让 `pi` 和 Codex 在用户发起"读网页 / 抓内容 / 网页搜索 / 下载图片"任务时，能通过 Dokobot CLI 调用真实 Chrome 完成；同时给两个 Agent 暴露 `/doko`（或 `/dokobot`）slash command，Agent 端只看见 skill + 命令，零额外配置成本。

## Context

- **当前问题**：
  - `dokobot` CLI 已装（`/opt/homebrew/bin/dokobot`，v2.11.0），但 Pi 和 Codex 都没有把 Dokobot 注册为可调用的能力
  - Codex 端 `~/.codex/skills/dokobot/SKILL.md` 已存在（v2.3.5，作者写好的官方 skill），但这只是 skill，不是 slash command
  - Pi 端 `~/.pi/agent/skills/` 和 `~/.agents/skills/` 下都没有 dokobot；Pi 也缺一个 `/doko` 命令和 custom tools
  - 用户在 Codex 里输 `/doko` 或 `/dobo` 都不显示——因为没有 plugin 命令

- **相关文件/路径**（调研结果）：
  - 已有：`/Users/liang/.codex/skills/dokobot/SKILL.md`（带 openclaw 兼容 metadata）
  - 已有：`/opt/homebrew/bin/dokobot`（CLI v2.11.0）
  - 待创建：`/Users/liang/.pi/agent/extensions/dokobot.ts`（Pi extension，命令 + tools）
  - 待创建：`/Users/liang/ai-work/drun/.pi/skills/dokobot/SKILL.md`（本仓库 Pi skill 软链源——可选用）
  - 待创建：`/Users/liang/.codex/skills/dokobot/commands/doko.md`（Codex command 描述文件——可选用）
  - 可选：个人 Codex plugin `~/plugins/dokobot/`

- **决策参考**（来自 `.planning/STATE.md`、AGENTS.md）：
  - 沿用 GSD 工作流（plan → execute → review）
  - 行为变更要带测试/验证；纯配置/集成类任务不要求单测，但每个 task 必须有明确 verify 步骤
  - Skill / 命令 / Extension 都属于"用户可见能力"变更，需要更新 skill 文档——本任务中暂不需要改 `drun-usage/`，但 Pi 的 `~/.pi/agent/` 和 Codex 的 `~/.codex/` 不在本仓库 git 控制下，改动不进 CHANGELOG

- **关键事实**：
  - Pi 默认 skill 路径：`~/.pi/agent/skills/`、`~/.agents/skills/`（`/opt/homebrew/lib/node_modules/@earendil-works/pi-coding-agent/docs/skills.md`）
  - Pi 默认 extension 路径：`~/.pi/agent/extensions/*.ts`
  - Pi extension 通过 `pi.registerCommand` 注册命令，通过 `pi.registerTool` 注册工具
  - Codex slash command 不存在于普通 skill 里；要走 plugin → `.codex-plugin/plugin.json` + `commands/<name>.md`
  - Codex 有 `~/.codex/.tmp/plugins/.agents/skills/plugin-creator/scripts/create_basic_plugin.py` 提供脚手架
  - Pi 加载 skill 时只用 `name` + `description`，其他 frontmatter 字段会被忽略——所以软链 Codex 官方 skill 是安全的

## 开放问题（需用户先答）

### Q1. Slash command 的命名
- (A) `/doko`（短，类 `/doko <url>`）
- (B) `/dokobot`（长，类 `/dokobot <url>`）
- (C) 两套都注册（`/doko` + `/dokobot` 互为别名）
- **推荐：A**（与 Dokobot 官网示例一致，最短；与现有 skill 名区分；和 `~/.codex/skills/dokobot/` 同名但属于"命令"和"skill 目录"两个层面，不冲突）

### Q2. 覆盖范围
- (A) 只在 Pi 注册
- (B) 只在 Codex 注册
- (C) Pi + Codex 都注册
- **推荐：C**（用户提问"在 pi agent 以及 codex 只用通过 skills 或者 插件使用"，明确要双端）

### Q3. Codex 端：直接改 `~/.codex/` 还是建 personal plugin
- (A) 直接在 `~/.codex/skills/dokobot/commands/` 下加 `doko.md`，最简
- (B) 建 personal plugin `~/plugins/dokobot/` + `~/.agents/plugins/marketplace.json` 注册——Codex 官方推荐形式
- **推荐：B**（更清晰、可移植；不污染 `~/.codex/skills/` 既有结构；和 Cloudflare/Vercel/Figma 官方 plugin 同形式）

### Q4. Pi 端：是否要 custom tools
- (A) 只做 `/doko` slash command，命令背后是 bash 拼 CLI
- (B) 同时注册 `dokobot_read` / `dokobot_search` / `dokobot_download_images` / `dokobot_list` / `dokobot_close` custom tools，Agent 可以在 ReAct 循环里像"工具"一样被调用
- (C) Tools + 一个封装工具 `dokobot_url_to_text`，把 `read` 的结果直接转成 Agent 可消费的纯文本
- **推荐：C**（Tools 形式对 Agent 最自然；封装 `read` 为纯文本最常用；slash command 给人类用户手动触发用）

### Q5. Remote 模式支持
- (A) 只支持 Local，需要时让用户自己用 `dokobot config` 设 API key
- (B) 默认 Local，但 extension 自动检测 `DOKO_API_KEY` 环境变量，命中则走 Remote
- **推荐：B**（零配置 fallback 是 Local；检测到 env 就用 Remote，行为可预期）

### Q6. skill 软链策略
- (A) `~/.pi/agent/skills/dokobot → ~/.codex/skills/dokobot`（Pi 软链到 Codex）
- (B) `~/.codex/skills/dokobot → ~/.pi/agent/skills/dokobot`（Codex 软链到 Pi）
- (C) 软链到一个 canonical 源（如 `~/.agents/skills/dokobot`），两边都软链到它
- **推荐：C**（最不容易出循环；canonical 在 `~/.agents/skills/` 也是大多数 agent 工具默认尊重的路径；Codex 既有 skill 内容已经写得很好，作为 canonical 没必要改）

## Tasks

### Task 1: 前置依赖检查（环境层）
**Files:** 无
**Action:**
```bash
dokobot --version                 # 期望: 2.11.0
which dokobot                     # 期望: /opt/homebrew/bin/dokobot 或 npm 全局
ls ~/.codex/skills/dokobot/SKILL.md   # 期望: 存在
ls ~/.pi/agent 2>/dev/null         # 期望: 存在
ls ~/.agents 2>/dev/null          # 期望: 存在
dokobot doko list 2>&1 | head -5   # 期望: 列已连接浏览器；如果报"no extension"就停下提示用户装扩展
```
**Verify:** 全部命令成功；`dokobot doko list` 能列出至少一台 Chrome（说明 Chrome 扩展已装且启用了 Remote Control）。如果没装，告诉用户：
```bash
# 1. 装 Chrome 扩展（Dokobot → Chrome Web Store）
# 2. 扩展里点 "Enable Remote Control"
# 3. 回到 Terminal 跑 dokobot doko list
```
不擅自装扩展——这是必须用户亲手做的安全动作。

**Complexity:** S

### Task 2: 在 `~/.agents/skills/` 建 canonical Dokobot skill（软链 Codex 既有）
**Files:**
- 创建软链：`/Users/liang/.agents/skills/dokobot → /Users/liang/.codex/skills/dokobot`
- 创建软链：`/Users/liang/.pi/agent/skills/dokobot → /Users/liang/.agents/skills/dokobot`

**Action:**
```bash
mkdir -p ~/.agents/skills ~/.pi/agent/skills
ln -sfn ~/.codex/skills/dokobot ~/.agents/skills/dokobot
ln -sfn ~/.agents/skills/dokobot ~/.pi/agent/skills/dokobot
ls -la ~/.pi/agent/skills/dokobot ~/.agents/skills/dokobot
# 期望: 两个都是符号链接，指向 .agents/skills/dokobot → .codex/skills/dokobot
```

**理由**:
- `~/.codex/skills/dokobot/SKILL.md` 是 Dokobot 官方写好的 v2.3.5，含 openclaw 兼容 metadata，不重写
- Pi 加载 skill 只用 `name`+`description`，多余 frontmatter 字段被忽略——软链安全
- 用三层链（`~/.pi/agent/skills/` → `~/.agents/skills/` → `~/.codex/skills/`）让 Pi 通过 `~/.agents/` 的发现也命中

**Verify:**
```bash
# 1. 软链存在且能读到内容
readlink ~/.agents/skills/dokobot    # 期望: /Users/liang/.codex/skills/dokobot
readlink ~/.pi/agent/skills/dokobot  # 期望: /Users/liang/.agents/skills/dokobot
test -f ~/.pi/agent/skills/dokobot/SKILL.md && echo "OK"

# 2. 用 pi 打开，触发 skill 列表
pi --list-skills 2>&1 | rg -i dokobot
# 期望: 出现 dokobot skill
```

**Complexity:** S

### Task 3: 在 Pi 注册 `/doko` 命令 + custom tools（Pi extension）
**Files:** `/Users/liang/.pi/agent/extensions/dokobot.ts`（新建）

**Action:**
1. 新建 `dokobot.ts`，导出 default function
2. 通过 `pi.registerCommand("doko", { handler })` 注册 slash command：
   - `/doko <url>` → `dokobot read --local <url>`
   - `/doko search <query>` → `dokobot search --local <query>`
   - `/doko images <url>` → `dokobot download images --local <url>`
   - `/doko list` → `dokobot doko list`
   - `/doko close <sessionId>` → `dokobot doko close <sessionId>`
   - 无参数 → 打印 usage（提示 `/doko <url>` / `/doko search <q>` / 等）
3. 通过 `pi.registerTool(...)` 注册 5 个 custom tools：
   - `dokobot_read` 参数 `{ url, local?: boolean, session_id?, screens?, timeout? }`
   - `dokobot_search` 参数 `{ query, local?: boolean }`
   - `dokobot_download_images` 参数 `{ url, local?: boolean, format?, max?, min_width?, out_dir? }`
   - `dokobot_list` 参数 `{}`
   - `dokobot_close` 参数 `{ session_id }`
4. 工具执行逻辑：`spawnSync("dokobot", [...args], { encoding: "utf-8" })`
5. 远程模式探测：执行前读 `process.env.DOKO_API_KEY`，命中则所有命令去掉 `--local`
6. 错误处理：
   - 命令不存在 (`enoent`) → 返回 `dokobot CLI not found. Run: npm i -g @dokobot/cli`
   - `dokobot doko list` 输出空 → 提示用户启用 Chrome 扩展 + Remote Control
7. 不输出任何 `DOKO_API_KEY` / `DOKO_*` env 值

**Verify:**
```bash
# 1. extension 加载不报错
pi -e ~/.pi/agent/extensions/dokobot.ts --help 2>&1 | head -20
# 期望: 正常启动，能看到 /doko 命令

# 2. /doko list 能列设备
pi -e ~/.pi/agent/extensions/dokobot.ts
# 在 pi 里: /doko list
# 期望: 输出 dokobot doko list 的结果

# 3. /doko <url> 能读网页
# 在 pi 里: /doko https://dokobot.ai/zh-CN/use-cases
# 期望: 返回纯文本（页面正文 Markdown 化）
```

**Complexity:** M

### Task 4: 在 Codex 建 personal plugin `~/plugins/dokobot/`
**Files:**（新建）
- `~/plugins/dokobot/.codex-plugin/plugin.json`
- `~/plugins/dokobot/skills/dokobot/SKILL.md`（软链到 `~/.codex/skills/dokobot/SKILL.md`）
- `~/plugins/dokobot/commands/doko.md`
- `~/plugins/dokobot/.app.json`（可选；Codex app 集成需要）

**Action:**
1. `mkdir -p ~/plugins/dokobot/.codex-plugin ~/plugins/dokobot/skills/dokobot ~/plugins/dokobot/commands`
2. 写 `~/plugins/dokobot/.codex-plugin/plugin.json`，参照 cloudflare plugin 模板：
   ```json
   {
     "name": "dokobot",
     "version": "0.1.0",
     "description": "Dokobot — read web pages via your real Chrome browser. Use when you need to fetch JavaScript-rendered pages, logged-in content, search the web, or download images.",
     "author": { "name": "liang" },
     "homepage": "https://dokobot.ai",
     "license": "MIT",
     "keywords": ["browser", "scraping", "search", "web", "ai-agent"],
     "skills": "./skills/",
     "commands": "./commands/",
     "interface": {
       "displayName": "Dokobot",
       "shortDescription": "Read any web page through your real Chrome",
       "longDescription": "...",
       "developerName": "liang",
       "category": "Developer Tools",
       "capabilities": ["Interactive", "Read"],
       "defaultPrompt": [
         "用 dokobot 读一下 https://example.com"
       ]
     }
   }
   ```
3. 软链 skill：`ln -sfn ~/.codex/skills/dokobot ~/plugins/dokobot/skills/dokobot`
4. 写 `commands/doko.md`，参照 cloudflare 的 `commands/build-mcp.md` 模板：
   ```markdown
   ---
   description: 用 Dokobot 读取、搜索、抓取网页（通过你的真实 Chrome）。把 $ARGUMENTS 当作主操作。
   argument-hint: [url-or-action]
   allowed-tools: [Bash]
   ---

   # /doko

   用户输入: $ARGUMENTS

   ## 解析
   - 以 `search ` 开头 → 调 `dokobot search --local <去掉 "search " 的部分>`
   - 以 `images ` 开头 → 调 `dokobot download images --local <...>`
   - 以 `list` 开头 → 调 `dokobot doko list`
   - 以 `close ` 开头 → 调 `dokobot doko close <sessionId>`
   - 其他（含 URL）→ 调 `dokobot read --local <URL>`

   ## Local vs Remote
   - 默认 Local（免费）
   - 如果检测到 `DOKO_API_KEY` 环境变量，去掉 `--local`，走 Remote

   ## 不要做的
   - 不要把 `DOKO_API_KEY` 的值打印到输出
   - 不要在没有确认的情况下把长文本会话续接超过 5 屏

   ## 执行
   直接 bash 调 dokobot CLI，把结果完整返回给用户。
   ```
5. 更新 `~/.agents/plugins/marketplace.json`：
   ```bash
   # 先看是否已有该文件
   [ -f ~/.agents/plugins/marketplace.json ] || echo '{"name":"liang-personal","interface":{"displayName":"liang Personal"},"plugins":[]}' > ~/.agents/plugins/marketplace.json
   # 用 Python 安全追加（避免破坏 JSON）
   python3 -c "
   import json, os, pathlib
   p = pathlib.Path(os.path.expanduser('~/.agents/plugins/marketplace.json'))
   data = json.loads(p.read_text())
   if not any(e.get('name') == 'dokobot' for e in data['plugins']):
       data['plugins'].append({
           'name': 'dokobot',
           'source': {'source': 'local', 'path': './plugins/dokobot'},
           'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'},
           'category': 'Developer Tools'
       })
       p.write_text(json.dumps(data, indent=2, ensure_ascii=False))
       print('appended')
   else:
       print('already present')
   "
   ```

**Verify:**
```bash
# 1. 目录结构
find ~/plugins/dokobot -maxdepth 4 -type f -o -type l
# 期望: 看到 plugin.json, SKILL.md (link), commands/doko.md

# 2. JSON 合法
python3 -m json.tool ~/plugins/dokobot/.codex-plugin/plugin.json > /dev/null && echo "plugin.json valid"
python3 -m json.tool ~/.agents/plugins/marketplace.json > /dev/null && echo "marketplace valid"

# 3. Codex 能扫到 plugin
# 启动 Codex app，从 plugin 列表里能看到 "Dokobot"
# 启用后，在 composer 输入框能调用 /doko https://example.com
```

**Complexity:** M

### Task 5: 端到端验证
**Files:** 无
**Action:** 跑四组真实验证：
1. **本地 CLI 直调**：
   ```bash
   dokobot --version             # 期望: 2.11.0
   dokobot doko list             # 期望: 列出 Chrome
   dokobot read --local https://dokobot.ai/zh-CN/use-cases  # 期望: 页面正文
   ```
2. **Pi 端**：
   - 启动 `pi`
   - 输 `/doko https://dokobot.ai/zh-CN/use-cases` → 看到正文
   - 输 `/doko search 最新 AI Agent 工具` → 看到搜索结果
   - 输 `/doko list` → 看到设备列表
   - 在 ReAct 循环里让 pi "用 dokobot_read 工具读这个页面" → 看到调用
3. **Codex 端**：
   - 启动 Codex app
   - plugin 列表里看到 Dokobot → 启用
   - 输 `/doko https://dokobot.ai/zh-CN/use-cases` → 看到正文
   - 输 `/doko search 最新 AI Agent 工具` → 看到搜索结果
4. **安全验证**：
   - 在插件命令文档里 grep `DOKO_API_KEY` 值 → 不应出现
   - Pi extension 文件 grep `process.env` → 只读 `DOKO_API_KEY`，不写

**Verify:** 上面四组全部通过；如果任何一组失败，按 diagnose 流程定位。

**Complexity:** S

### Task 6: 写一份本机 README，记录安装/使用方式
**Files:** `/Users/liang/ai-work/drun/.planning/phases/notes/dokobot-integration.md`（新建，只在本仓库 planning 内做记录，**不进 git**）

**Action:**
把 Task 1–5 的最终命令清单、安装步骤、验证脚本、Codex app handoff（`View dokobot` / `Share dokobot` deeplink）写进 notes，方便以后重装系统或换机时恢复。

**Verify:**
```bash
# 1. 文件存在
test -f /Users/liang/ai-work/drun/.planning/phases/notes/dokobot-integration.md && echo OK
# 2. 文档里有 4 个核心命令：dokobot read / search / download images / doko list
rg "dokobot (read|search|download images|doko list)" /Users/liang/ai-work/drun/.planning/phases/notes/dokobot-integration.md
```

**Complexity:** S

## Verification（整体）

- [ ] `dokobot doko list` 列出至少一台 Chrome
- [ ] `~/.pi/agent/skills/dokobot` 软链存在，pi 启动时能看到 dokobot skill
- [ ] Pi 端 `/doko <url>` 工作，返回页面正文
- [ ] Pi 端 `/doko search <q>` 工作
- [ ] Pi 端 custom tool `dokobot_read` 在 ReAct 循环里可被 Agent 调用
- [ ] Codex plugin 列表里能看到 Dokobot
- [ ] Codex 端 `/doko <url>` 工作
- [ ] 远程模式（设 `DOKO_API_KEY` 后）能跑通
- [ ] `DOKO_API_KEY` 在任何输出中不出现
- [ ] 关闭 Chrome 扩展时给出明确"启用 Remote Control"提示，不静默失败
- [ ] `.planning/phases/notes/dokobot-integration.md` 写完

## Self-check

- ✓ **Completeness**: 覆盖 Pi 端（skill + extension + commands + tools）和 Codex 端（personal plugin + commands + marketplace），含本地/远程两种模式
- ✓ **Minimality**: 6 个 task 各管一摊，Task 1/5 是验证类，Task 2 是软链（最低成本），Task 3/4 是新增文件
- ✓ **Order**: Task 1（前置） → Task 2（skill 可见） → Task 3（Pi 可调用） → Task 4（Codex 可调用） → Task 5（端到端） → Task 6（文档沉淀）
- ✓ **Testability**: 每个 task 都有具体 verify 命令；Task 5 端到端覆盖 4 个真实场景
- ✓ **Risk**:
  1. **软链破坏 Pi skill 解析**——已确认 Pi 只看 `name`+`description`，多余 frontmatter 安全
  2. **`dokobot doko list` 列空**——Task 1 显式要求停下来提示用户，不擅自装扩展
  3. **Codex plugin 命名冲突**——用 `dokobot` 名，先 check `~/.agents/plugins/marketplace.json` 是否有同名条目
  4. **远程模式误触发**——Task 3 显式声明"只读 `DOKO_API_KEY` 是否存在，不读值"，避免密钥泄露
  5. **Pi extension TS 编译错误**——用 jiti 即时加载，不预编译；任务 3 verify 直接用 `pi -e` 跑

## 范围外

- 不装 Chrome 扩展（用户必须亲手做安全动作）
- 不在 `~/.codex/config.toml` 加任何配置（task 4 的 personal plugin 自带 marketplace.json 发现机制）
- 不改 `drun-usage/` skill（这是 drun 自身用法的 skill，跟 Dokobot 集成无关）
- 不进 CHANGELOG（这次改动完全在 `~/.pi/agent/`、`~/.codex/`、`~/plugins/`、本仓库 `.planning/` 下，drun 自身代码未变）
- 不发布 npm 包（本地个人配置）

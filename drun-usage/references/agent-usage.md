# Agent Usage

适用于在 pi、Claude Code、Codex CLI 或其他 Agent Skills 兼容工具中启用 `drun-usage`。

## 推荐结构

`drun-usage` 是一个标准 skill 目录：

```text
drun-usage/
├── SKILL.md
└── references/
```

## pi coding agent

全局启用：

```bash
mkdir -p ~/.agents/skills
ln -s /path/to/drun/drun-usage ~/.agents/skills/drun-usage
```

也可以放到 pi 专用目录：

```bash
mkdir -p ~/.pi/agent/skills
ln -s /path/to/drun/drun-usage ~/.pi/agent/skills/drun-usage
```

项目内启用：

```bash
mkdir -p .agents/skills
ln -s /path/to/drun/drun-usage .agents/skills/drun-usage
```

启用后重启 pi，或在交互界面执行 `/reload`。需要强制触发时可使用：

```text
/skill:drun-usage 帮我写一个登录后查询用户信息的 drun YAML
```

## Claude Code

Claude Code 常见全局 skill 目录是 `~/.claude/skills`：

```bash
mkdir -p ~/.claude/skills
ln -s /path/to/drun/drun-usage ~/.claude/skills/drun-usage
```

如果项目内维护 Claude Code skill，可放在项目约定的 `.claude/skills` 目录：

```bash
mkdir -p .claude/skills
ln -s /path/to/drun/drun-usage .claude/skills/drun-usage
```

重启 Claude Code 或刷新上下文后使用。

## Codex / OpenAI coding agents

Codex 环境的 skill 发现目录可能随版本和配置变化。如果当前 Codex harness 支持 Agent Skills，可把 `drun-usage` 放到它配置的 skills 目录，例如：

```text
~/.codex/skills/drun-usage
```

如果当前环境不会自动发现 skills，就在项目 `AGENTS.md` 或用户提示中显式要求：

```text
当用户提到 drun YAML、drun run、drun check、drun q、drun convert 或 drun 排障时，请先读取 drun-usage/SKILL.md，并按其中 reference 执行。
```

## 通用 Agent 使用方式

任何不能自动发现 skill 的 Agent，都可以用显式提示触发：

```text
请先读取 drun-usage/SKILL.md。然后帮我写一个 drun YAML，并给出 drun check 和 drun run 命令。
```

排障时可以这样说：

```text
请先读取 drun-usage/SKILL.md。这个 drun YAML 报错了，请按 drun 的当前 DSL 修复，不要使用未实现字段。
```

## 推荐工作流

1. 用户描述接口、请求体和期望结果。
2. Agent 读取 `drun-usage/SKILL.md` 和必要 reference。
3. Agent 生成完整 YAML。
4. Agent 给出 `drun check` 命令。
5. Agent 给出 `drun run` 命令。
6. 如果运行失败，用户把错误贴回 Agent，Agent 按 troubleshooting 和 anti-patterns 修复。

# Maintenance

适用于维护者或 Agent 在修改 drun 用户可见能力时判断是否需要同步 `drun-usage`。

## 何时必须检查 drun-usage

以下变更需要检查并按需更新本 skill：

- CLI 命令、参数、默认行为或帮助输出变化。
- YAML DSL 字段、字段位置、默认值、兼容 alias 或废弃字段变化。
- `check`、`extract`、`caseflow`、`invoke`、`invoke_case_name`、`invoke_case_names`、`repeat`、`sleep` 行为变化。
- Request Step 的 `request.files`、`request.auth`、`request.stream`、`response.save_body_to`、`export.csv` 行为变化。
- 报告、JSON、HTML、Allure、snippet、`drun server` 输出或目录行为变化。
- YAML 诊断错误码、错误提示、hint、example 或修复建议变化。
- `drun q`、`convert`、`convert-openapi`、`export curl` 行为变化。

## 改什么内容时更新哪些 reference

| 变更类型 | 需要检查的 reference |
| --- | --- |
| CLI 命令或参数 | `cli-cheatsheet.md`、`execution-and-env.md`、相关专题 reference |
| YAML DSL 字段 | `yaml-fields.md`、`dsl-core.md`、`anti-patterns.md`、`recipes.md` |
| Step Lifecycle / Executable Target | `composition-and-reuse.md`、`dsl-core.md`、`yaml-fields.md` |
| `check` / `extract` 行为 | `dsl-core.md`、`yaml-fields.md`、`recipes.md`、`troubleshooting.md` |
| `caseflow` / `invoke` 行为 | `composition-and-reuse.md`、`recipes.md`、`troubleshooting.md` |
| `repeat` / `sleep` 行为 | `composition-and-reuse.md`、`yaml-fields.md`、`anti-patterns.md` |
| 报告 / snippet / server | `reports-and-outputs.md`、`cli-cheatsheet.md`、`recipes.md` |
| 错误码或诊断提示 | `troubleshooting.md`、`anti-patterns.md` |
| `drun q` / convert / export curl | `debug-convert-export.md`、`cli-cheatsheet.md`、`recipes.md` |
| Agent 安装方式 | `agent-usage.md`、`SKILL.md` |

## 维护原则

- 以当前仓库实现和测试为准；README 与实现冲突时，跟实现。
- 保持 `SKILL.md` 精简，详细说明优先放到 `references/`。
- 不虚构未实现 DSL、旧命令或兼容字段。
- 示例默认中文，优先给可运行 YAML 和 CLI 命令。
- 示例中的 token、Cookie、密码等敏感值使用 `${ENV(...)}`。
- 命令示例涉及敏感信息时优先使用 `-secrets mask` 或 `-redact Authorization,Cookie`。
- 不要把讨论过但未实现的命名如 `ext`、`checked`、`checkpoints` 当作 YAML 字段推荐。

## 建议验证

修改 skill 后至少运行：

```bash
/Users/liang/ai-work/.venv/bin/python -m pytest tests/test_drun_usage_skill.py -q
```

如果同时修改了 drun 行为，运行全量测试：

```bash
/Users/liang/ai-work/.venv/bin/python -m pytest -q
```

如需核对 CLI 帮助：

```bash
/Users/liang/ai-work/.venv/bin/python -m drun.cli --help
```

遵循仓库发布约定：版本发布只走 GitHub Action；除非用户明确要求，不在本地执行发布打包检查。

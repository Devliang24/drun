# Repository Guidelines

## 项目结构与模块划分
`drun/` 是主包目录。常见改动点包括：`commands/` 负责 CLI 子命令，`loader/` 与 `templating/` 负责 YAML 和环境变量解析，`runner/` 负责执行流程，`reporter/` 与 `server/` 负责报告输出和查看，`importers/`、`exporters/` 负责格式转换。测试代码位于 `tests/`，通常按功能拆分为 `tests/test_*.py`。示例接口规范放在 `spec/openapi/`。

## 构建、测试与开发命令
统一使用共享虚拟环境 `/Users/liang/ai-work/.venv`，不要在仓库内重新创建 `.venv`。在本仓库中执行命令时，优先直接调用该环境的解释器：

```bash
/Users/liang/ai-work/.venv/bin/pip install -e ".[dev]"
/Users/liang/ai-work/.venv/bin/python -m pytest -q
/Users/liang/ai-work/.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
/Users/liang/ai-work/.venv/bin/python -m drun.cli --help
make clean
```

`pytest` 适合做快速回归；`unittest discover` 与仓库现有测试组织方式一致。清理产物可使用 `make clean`、`make clean-build`、`make clean-test` 或 `make clean-reports`。

## 本地开发与调试
本地开发目录统一位于 `/Users/liang/ai-work`，当前仓库路径为 `/Users/liang/ai-work/drun`。调试、运行脚本、执行测试时默认使用 `/Users/liang/ai-work/.venv`，例如：

```bash
cd /Users/liang/ai-work/drun
source /Users/liang/ai-work/.venv/bin/activate
python -m pytest -q
python -m drun.cli --version
```

如果脚本中需要写死解释器路径，也应使用 `/Users/liang/ai-work/.venv/bin/python`，保证本地开发和自动化执行环境一致。

## 发布约定
版本发布严格只走 GitHub Action，不做本地打包校验。需要发版时，只修改版本号、提交、创建版本 tag 并推送到远端，由 `.github/workflows/publish-pypi.yml` 负责构建、校验和发布。默认不要在本地执行 `python -m build`、`twine check` 或其他发布前打包检查，除非用户明确要求。

## 代码风格与命名约定
遵循现有 Python 风格：4 空格缩进、PEP 8 布局、公共逻辑补充类型标注。新增模块优先使用 `from __future__ import annotations`。模块、函数、辅助方法使用 `snake_case`，类名使用 `PascalCase`，常量使用 `UPPER_SNAKE_CASE`。测试类通常以 `Tests` 结尾。仓库未强制配置格式化工具，因此请保持与周边文件一致的导入顺序、注释风格和代码排版。

## 测试规范
任何行为变更都应补充或更新对应的 `tests/test_*.py`。当前测试主要基于 `unittest.TestCase`，通常通过 `pytest` 执行；CLI 场景常使用 `typer.testing.CliRunner`，隔离依赖优先使用 `unittest.mock`。避免真实网络请求，优先使用 mock、临时目录和最小化输入样例。虽然仓库没有覆盖率门槛，但新参数、YAML 解析、报告输出等改动应带回归测试。

## Skill 文档维护
仓库内的 `drun-usage/` 是面向 `drun` 深度使用场景的本地 skill。涉及用户可见能力变更时，除了代码和测试，还要评估是否需要同步补充或修正该 skill 说明。重点包括：

- CLI 命令、参数、默认行为或输出目录变化，如 `run`、`q`、`convert`、`convert-openapi`、`export curl`、`server`
- YAML DSL、模板渲染、环境加载、参数化、`caseflow` / `invoke` / `repeat` / `sleep` / `request.files` 的行为或约束变化
- 报告、snippet、导入导出、排障提示等会直接影响用户使用方式的变更

维护时遵循现有结构：`SKILL.md` 保持精简，具体说明优先落到 `references/` 下对应文件；纯内部重构且不影响使用方式时，可以不更新该 skill。

## 提交与 Pull Request 规范
近期提交采用 Conventional Commits 风格，例如 `feat:`、`fix:`、`refactor:`、`ci:`、`chore:`。提交标题使用祈使句并直接说明变更，例如 `feat: support invoke case selection`。PR 需要说明用户可见影响、是否同步更新文档或 CLI 帮助，并列出已执行的验证命令。只有在修改 HTML 报告或 FastAPI 报告页面时才需要附截图。

## 安全与配置提示
不要提交 `.env`、本地日志、报告目录或其他生成文件；这些路径已在 `.gitignore` 中处理。测试、文档和截图中不要暴露真实密钥，YAML 示例和变更说明统一使用脱敏值。

## GSD 工作流（强制）

本仓库**强制使用 GSD（Get Shit Done）工作流**进行所有非平凡改动。GSD 是 **pi agent 全局能力**，装在 `~/.pi/agent/` 下，所有使用 pi 的项目都能用，不只限本仓库。

**工作流三步走：**

1. **规划** — 在 pi 中输入 `/skill:gsd-plan <任务>`，按 5 步流程（读上下文 → 研究 → 拆解 → 自检 → 审批）输出 `.planning/phases/PLAN-*.md`
2. **执行** — 审批后输入 `/skill:gsd-execute`，逐任务执行，每个任务一个原子 conventional commit
3. **审查** — 完成后输入 `/skill:gsd-review`，按 Bug/安全/质量/测试/性能五维度审查

**可用命令：**

| 命令 | 作用 |
|------|------|
| `/skill:gsd-plan` 或 `/plan` | 规划任务 |
| `/skill:gsd-execute` 或 `/execute` | 执行计划 |
| `/skill:gsd-review` 或 `/review` | 审查代码 |
| `/gsd:state` | 查看 `.planning/STATE.md` 项目状态 |

**GSD 文件在哪（user-level）：**

- skills: `~/.pi/agent/skills/gsd-{plan,execute,review}/`
- prompts: `~/.pi/agent/prompts/{plan,execute,review}.md`
- extension: `~/.pi/agent/extensions/gsd-state.ts`

**在新机器上启用 GSD：**

```bash
mkdir -p ~/.pi/agent/{skills,prompts,extensions}
# 从 gsd-pi 安装包获取（详见 gsd-pi 仓库 README），
# 或从已有机器复制上面 3 类文件即可。
```

pi 启动时会自动从 `~/.pi/agent/` 发现并加载这些 skills。

**强制范围：**

- 任何涉及 ≥ 2 个文件、≥ 1 个新接口、≥ 1 个新测试文件的改动
- 任何 refactor、new feature、breaking change
- 任何需要 review 的 PR

**豁免范围：**

- 单行 typo 修复
- 单文件文档补全
- 紧急 hotfix（事后补 plan）

**禁止跳过规划直接执行复杂任务。**

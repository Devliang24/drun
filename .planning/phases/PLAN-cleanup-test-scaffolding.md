# Plan: 清理脚手架文件（含 tests/ 空白文件 + init 产物）

## Goal
删除仓库里所有**脚手架性质的文件**：空的 `tests/` 占位文件 + `drun init` 写到用户项目里的 demo 文件。这些文件不属于 drun 自身的源码或测试。

## Context
- **两类脚手架**：
  1. **tests/ 下的空白脚手架**：0 字节空文件、空目录
  2. **`drun init` 写出的 demo 文件**：`tcases/`、`tsuites/`、`data/users.csv`、`converts/sample.curl`、`Dhook.py` — 这些是 `drun/cli.py:1969-1971` 写给用户项目的，**自身代码在 `scaffolds/templates.py`**

- **Research findings**：
  - `tests/__init__.py`：0 字节，pytest 不需要空 `__init__.py` 来发现测试
  - `tests/helpers/`、`tests/fixtures/`：空目录
  - `tcases/tc_*.yaml`、`tsuites/ts_smoke.yaml`：**与 `drun/scaffolds/templates.py` 中的 `DEMO_TESTCASE`/`HEALTH_TESTCASE`/`CSV_DATA_TESTCASE`/`DEMO_TESTSUITE` 字符串常量内容重复**
  - `data/users.csv`、`converts/sample.curl`、`Dhook.py`：同上，对应 `CSV_USERS_SAMPLE`/`SAMPLE_CURL`/`HOOKS_TEMPLATE`
  - 测试**不直接加载** `tcases/` 和 `tsuites/` 下的真实文件（所有引用都是 tmpdir 内的虚拟路径）
  - README、drun-usage/skill 文档中**仍引用** `tcases/` 和 `tsuites/`，但引用的是目录结构概念（用户项目里应该有），不是仓库里的具体文件

## Tasks

### Task 1: 删除 `tests/` 下的空白脚手架
**Files:**
- `tests/__init__.py` (delete)
- `tests/helpers/` (delete dir)
- `tests/fixtures/` (delete dir)

**Action:**
- `__init__.py` 是 0 字节空文件
- `helpers/` 和 `fixtures/` 是空目录
- pytest 不需要 `__init__.py`
- 无 `import tests` 引用（grep 全部匹配都是 `from tests.cli_runner`）

**Verify:**
```bash
# 1. 文件已删除
test ! -f tests/__init__.py && test ! -d tests/helpers && test ! -d tests/fixtures && echo "DELETED"

# 2. pytest 仍能收集所有测试
/Users/liang/ai-work/.venv/bin/python -m pytest tests/ --collect-only -q | tail -5
# 期望: 显示 24 tests collected，无错误
```

**Complexity:** S

### Task 2: 删除 `drun init` 写出的 demo 文件（git rm）
**Files:**
- `tcases/tc_api_health.yaml` (git rm)
- `tcases/tc_demo.yaml` (git rm)
- `tcases/tc_import_users.yaml` (git rm)
- `tsuites/ts_smoke.yaml` (git rm)
- `data/users.csv` (git rm)
- `converts/sample.curl` (git rm)
- `Dhook.py` (git rm)

**Action:**
- 这些文件被 `drun init` 命令在用户新建项目时写入
- 仓库里保留它们是**冗余**的 — 真实 source of truth 在 `drun/scaffolds/templates.py`
- 测试不直接 load 这些文件
- 用 `git rm` 删除（这些被 git 跟踪）
- 如果目录变空也一并删除（`tcases/`、`tsuites/`、`data/`、`converts/`）

**Verify:**
```bash
# 1. 仓库里没有这些文件
test ! -f tcases/tc_demo.yaml && test ! -f tsuites/ts_smoke.yaml && test ! -f Dhook.py && echo "DELETED"

# 2. `drun init` 仍然能用（这才是验证它们确实是冗余的）
cd /tmp && rm -rf test_init && mkdir test_init && cd test_init
/Users/liang/ai-work/.venv/bin/python -m drun.cli init --force
# 期望: 成功创建 tcases/ts_smoke.yaml 等
test -f tcases/tc_demo.yaml && echo "init still works"
cd /Users/liang/ai-work/drun

# 3. drun/scaffolds/templates.py 内容未改
git diff --stat drun/scaffolds/templates.py
# 期望: 空输出
```

**Complexity:** S

### Task 3: 完整回归测试
**Files:** 无
**Action:** 跑全量测试，确认两类脚手架清理都不影响 drun 自身的测试
**Verify:**
```bash
/Users/liang/ai-work/.venv/bin/python -m pytest tests/ -q
# 期望: 全部通过
```

**Complexity:** S

## Verification (整体)
- [ ] `tests/__init__.py` 已删除
- [ ] `tests/helpers/` 已删除
- [ ] `tests/fixtures/` 已删除
- [ ] 7 个 init demo 文件已 git rm
- [ ] 4 个空目录（如果空了）已删除
- [ ] 24 个 test_*.py 全部通过
- [ ] `drun init` 在临时目录里仍能成功生成 demo 文件
- [ ] `drun/scaffolds/templates.py` 未修改（source of truth 保留）
- [ ] Git 工作树干净

## Self-check
- ✓ **Completeness**: 覆盖两类脚手架（空白文件 + init demo）
- ✓ **Minimality**: 三个 task 各自单一职责
- ✓ **Order**: 先删 tests 空白 → 再删 init demo → 最后跑测试
- ✓ **Testability**: 全部 task 都有具体 verify 命令
- ✓ **风险**: 删 init demo 文件是安全的，因为 source of truth 在 scaffolds 包里，`drun init` 重新生成它们

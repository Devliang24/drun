# Drun 项目命名规范

本文档定义了 Drun 项目中所有命名的官方规范，确保代码库、文档和品牌使用的一致性。

---

## 📋 命名规范总览

| 使用场景 | 规范 | 示例 | 说明 |
|---------|------|------|------|
| **包名/模块名** | 全小写 | `drun` | 符合 PEP 8 规范 |
| **CLI 命令** | 全小写 | `drun run`, `drun convert` | 命令行工具惯例 |
| **Python 导入** | 全小写 | `from drun import ...` | Python 导入路径 |
| **文件名** | 全小写+下划线 | `drun_hooks.py`, `test_*.yaml` | 文件系统命名 |
| **目录名** | 全小写 | `drun/`, `testcases/`, `testsuites/` | 目录结构 |
| **文档标题** | 首字母大写 | `# Drun`, `## Drun 学习课程` | Markdown 标题 |
| **品牌名称** | 首字母大写 | `Drun 是一个...`, `Drun 团队` | 营销/描述性文本 |
| **环境变量前缀** | 全大写 | `DRUN_ENV`, `DRUN_HOOKS_FILE` | POSIX 环境变量惯例 |
| **代码注释/文档字符串** | 首字母大写 | `"""Drun 项目脚手架..."""` | Python docstring |
| **配置文件** | 全小写 | `pyproject.toml: name = "drun"` | 包管理器配置 |
| **Git 仓库/URL** | 全小写 | `github.com/user/drun` | URL 惯例 |
| **PyPI 包名** | 全小写 | `pip install drun` | PyPI 命名规范 |

---

## 🎯 详细规范说明

### 1. 技术标识符（全小写 `drun`）

**适用场景**：所有技术性、机器可读的标识符

#### 包名和模块名
```toml
# pyproject.toml
[project]
name = "drun"
```

```python
# Python 导入
from drun import __version__
from drun.cli import app
from drun.runner import Runner
```

#### CLI 命令
```bash
drun run testcases/
drun convert requests.curl
drun check testcases/
drun init my-project
```

#### 文件和目录名
```
drun/                    # 源码目录
drun_hooks.py           # Hooks 文件
test_*.yaml             # 测试用例
suite_*.yaml            # 测试套件
```

> **迁移提示**：如果你的项目还保留 `arun_hooks.py`，请将其重命名为 `drun_hooks.py`，并将任何 `ARUN_HOOKS_FILE` 环境变量更新为 `DRUN_HOOKS_FILE`，以符合新版命名规范。

#### 配置和脚本
```toml
[project.scripts]
drun = "drun.cli:app"
```

```yaml
# GitHub Actions
- name: Install drun
  run: pip install drun
```

---

### 2. 品牌名称（首字母大写 `Drun`）

**适用场景**：面向用户的文档、营销材料、描述性文本

#### 文档标题
```markdown
# Drun

## Drun 学习课程

### Drun 快速开始指南
```

#### 描述性文本
```markdown
Drun 是一个极简、强大、生产就绪的 HTTP API 测试框架。

欢迎使用 Drun！本文档将帮助你快速上手。

Drun 支持多种格式转换...
```

#### 版权和许可
```
Copyright (c) 2025 Drun Contributors
```

#### 代码注释和文档字符串
```python
"""
Drun 项目脚手架模板内容
用于 drun init 命令生成项目结构
"""

def example():
    """示例函数：演示 Drun 的用法"""
    pass
```

#### 帮助文本和用户消息
```python
_APP_HELP = f"drun v{version} · Drun 是零代码 HTTP API 测试框架"

typer.echo("欢迎使用 Drun！")
```

---

### 3. 环境变量（全大写 `DRUN_*`）

**适用场景**：所有环境变量，遵循 POSIX 惯例

#### 官方环境变量
```bash
DRUN_ENV=production          # 环境标识
DRUN_HOOKS_FILE=hooks.py     # Hooks 文件路径
DRUN_NOTIFY=true             # 启用通知
DRUN_NOTIFY_ONLY=failure     # 仅失败时通知
```

0.2.x → 0.3.x 迁移示例：

```bash
mv arun_hooks.py drun_hooks.py
export DRUN_HOOKS_FILE=/absolute/path/to/drun_hooks.py
```

#### 在代码中引用
```python
env_val = os.environ.get("DRUN_HOOKS_FILE")
```

#### 在文档中说明
```markdown
通过环境变量 `DRUN_ENV` 可以指定运行环境。
```

---

## ✅ 正确示例

### 文档示例
```markdown
# Drun 快速开始

Drun 是一个零代码 HTTP API 测试框架。

## 安装

```bash
pip install drun
```

## 运行测试

```bash
drun run testcases/
```

## 环境变量

- `DRUN_ENV`: 指定运行环境
- `DRUN_HOOKS_FILE`: 自定义 Hooks 文件路径
```

### 代码示例
```python
"""
Drun 核心运行器模块
"""
from drun.loader import load_case
from drun.runner import Runner

def run_test():
    """运行 Drun 测试用例"""
    runner = Runner()
    # 使用环境变量
    env = os.environ.get("DRUN_ENV", "dev")
    runner.run(env=env)
```

---

## ❌ 错误示例

### 错误：在技术标识符中使用大写
```toml
# ❌ 错误
[project]
name = "Drun"  # 应该是 "drun"

[project.scripts]
Drun = "drun.cli:app"  # 应该是 "drun"
```

```bash
# ❌ 错误
Drun run testcases/  # 应该是 "drun run"
```

### 错误：在品牌名称中使用全小写
```markdown
# ❌ 错误
# drun 快速开始  # 标题应该是 "Drun"

drun 是一个测试框架...  # 句首应该是 "Drun"
```

### 错误：环境变量使用小写
```bash
# ❌ 错误
drun_env=production  # 应该是 "DRUN_ENV"
```

---

## 🔍 特殊场景处理

### 1. 句首的品牌名称
句首始终使用首字母大写 `Drun`：
```markdown
Drun 支持多种格式转换。
Drun 可以将 cURL 命令转换为 YAML 测试用例。
```

### 2. 代码块中的命令
代码块中的命令使用小写 `drun`：
```bash
drun run testcases/
drun convert requests.curl
```

### 3. 混合场景
在同一段落中可能同时出现两种形式：
```markdown
Drun 提供了 `drun convert` 命令来转换格式。
使用 `drun run` 命令运行测试，Drun 会自动生成报告。
```

### 4. URL 和链接
URL 中使用小写：
```markdown
https://github.com/yourorg/drun
https://pypi.org/project/drun/
```

### 5. 文件内容中的引用
模板文件中的品牌名称使用首字母大写：
```python
SAMPLE_README = """# Drun API 测试项目

欢迎使用 Drun！

## 快速开始

```bash
drun run testcases/
```
"""
```

---

## 📚 参考标准

本命名规范遵循以下业界标准：

1. **PEP 8** - Python 代码风格指南
   - 包名和模块名使用全小写
   - 常量使用全大写

2. **POSIX** - 环境变量命名惯例
   - 环境变量使用全大写加下划线

3. **PyPI** - Python 包索引命名规范
   - 包名使用全小写，可使用连字符或下划线

4. **开源项目最佳实践**
   - 技术标识符：小写（如 `django`, `flask`, `pytest`）
   - 品牌名称：首字母大写（如 Django, Flask, Pytest）

---

## 🔄 版本历史

- **v1.0** (2025-01-23): 初始版本，定义 drun/Drun/DRUN 三种形式的使用规范

---

## 📞 问题反馈

如果在使用过程中发现命名不一致的情况，请：
1. 参考本文档确认正确用法
2. 提交 Issue 或 PR 修正
3. 在团队内部讨论特殊场景的处理方式

---

**由 Drun 团队维护 · 最后更新：2025-01-23**

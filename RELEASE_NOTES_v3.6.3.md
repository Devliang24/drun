# Release Notes - drun v3.6.3

## 发布日期
2025-11-17

## 版本类型
**紧急Bug修复版本** (Patch Release)

## 修复内容

### 🐛 严重Bug修复

**问题：** v3.6.2 中的流式响应完全无法工作，所有流式API调用都会失败并返回错误：
```
'Response' object does not support the context manager protocol
```

**根本原因：** 
在 `drun/engine/http.py` 的 `_parse_sse_stream` 方法中，错误地使用了嵌套的 `with response:` 语句。而 `response` 对象已经在外层的 `with self.client.stream() as resp:` 上下文管理器中，导致重复使用 with 语句触发协议错误。

**修复方案：**
移除了 `_parse_sse_stream` 方法中第35行的 `with response:` 语句及其缩进，直接使用 response 对象进行迭代。

### 📝 代码变更

**修改文件：**
- `drun/engine/http.py` - 修复流式响应解析逻辑
- `pyproject.toml` - 更新版本号到 3.6.3

**Git提交：**
- Commit: `adfd5ef`
- Tag: `v3.6.3`

## 影响范围

### ✅ 修复后的功能
- 流式SSE响应解析正常工作
- Progressive content tracking 功能正常
- OpenAI格式的流式API调用正常
- 所有使用 `stream: true` 的测试用例正常执行

### ⚠️ v3.6.2 受影响的功能
v3.6.2 版本中，所有使用流式响应的功能都无法正常工作，建议立即升级到 v3.6.3。

## 升级指南

### 从 v3.6.2 升级

**使用 pip 安装：**
```bash
pip install --upgrade drun
```

**从源码安装：**
```bash
cd /path/to/drun
git pull origin main
git checkout v3.6.3
pip install -e .
```

**验证版本：**
```bash
drun --version
# 输出: drun version 3.6.3
```

## 测试验证

### ✅ 已通过的测试
1. 流式响应解析单元测试
2. Progressive content extraction 测试
3. OpenAI格式流式响应测试
4. 模块导入测试
5. 实际API流式调用测试

### 测试结果
```
✓ Parse completed without error
✓ Events parsed: 4
✓ Progressive content chunks: 2
✓ Final content matches expected
✓ All tests passed! Streaming fix verified.
```

## 兼容性

### 向后兼容性
- ✅ 完全向后兼容 v3.6.0 和 v3.6.1
- ✅ 修复 v3.6.2 引入的回归bug
- ✅ 所有现有测试用例继续工作
- ✅ API接口保持不变

### Python版本
- Python >= 3.10

### 依赖要求
无变化，与 v3.6.2 保持一致。

## GitHub发布

- **Repository:** https://github.com/Devliang24/drun
- **Tag:** v3.6.3
- **Commit:** adfd5ef
- **Release URL:** https://github.com/Devliang24/drun/releases/tag/v3.6.3

## 下一步计划

v3.6.3 是一个紧急修复版本。未来版本规划：
- v3.6.4: 可能的其他小bug修复
- v3.7.0: 计划的新功能增强

## 致谢

感谢用户报告此问题并提供测试用例，帮助我们快速定位和修复bug。

---

**重要提示：** 如果您正在使用 v3.6.2，强烈建议立即升级到 v3.6.3 以修复流式响应功能。

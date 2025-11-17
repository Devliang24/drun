# 流式响应显示改进

## 改进概述

优化了流式响应的显示方式，使用户更容易理解实际生成的内容，而不是被大量技术细节淹没。

## 改进内容

### 1. 控制台日志优化

**改进前：**
```
[STREAM] 8 events received
[STREAM] event[0]: {完整的JSON结构...}
[STREAM] event[1]: {完整的JSON结构...}
...
[STREAM] event[7]: {完整的JSON结构...}
```

**改进后：**
```
[STREAM] 收到 8 个事件
[STREAM] Chunk 1 (866ms): '你好'
[STREAM] Chunk 2 (899ms): '你好！有什么我可以'
[STREAM] Chunk 3 (936ms): '你好！有什么我可以帮你的吗'
[STREAM] Chunk 4 (969ms): '你好！有什么我可以帮你的吗？😊'
[STREAM] 完成 (1022ms)，最终内容：
你好！有什么我可以帮你的吗？😊
```

**特点：**
- 只显示包含实际内容的chunk（跳过空内容和元数据事件）
- 显示累积的内容而非增量
- 最后汇总显示完整内容

### 2. HTML报告优化

**改进前：**
- 默认显示"事件列表"视图，包含大量技术细节
- 用户需要点击切换到"合并内容"才能看到实际内容
- 4个Tab：事件列表、合并内容、原始SSE、JSON数组

**改进后：**
- **完全移除"事件列表"Tab和视图**
- 默认展示"合并内容"视图（最直观）
- 3个Tab：**合并内容**（默认） → 原始SSE → JSON数组
- 需要调试时可以查看"原始SSE"或"JSON数组"

## 技术实现

### 文件修改

1. **drun/engine/http.py**
   - 在 `_parse_sse_stream()` 方法中添加 `progressive_content` 提取逻辑
   - 识别OpenAI格式的流式响应（`choices[0].delta.content`）
   - 累积内容并记录每个chunk的时间戳

2. **drun/runner/runner.py**
   - 更新流式响应日志显示逻辑
   - 使用 `progressive_content` 数据显示内容进度
   - 保留回退逻辑：如果内容提取失败，显示首尾事件

3. **drun/reporter/html_reporter.py**
   - 移除"事件列表"视图构建代码
   - 移除"事件列表"Tab按钮
   - 将"合并内容"设为默认视图
   - 调整Tab顺序和样式

## 兼容性

- ✅ 完整的 `stream_events` 数据结构保持不变
- ✅ 提取和验证功能不受影响（`$.stream_events[*]`、`$.stream_summary.*`）
- ✅ 支持非标准格式的回退机制
- ✅ 所有现有测试用例继续工作

## 测试验证

已通过以下验证：
- ✅ Python语法检查
- ✅ 模块导入测试
- ✅ 内容提取逻辑测试
- ✅ HTML报告生成测试

## 使用示例

运行包含流式响应的测试：
```bash
drun run test_stream_api.yaml
```

查看改进后的输出：
- 控制台将显示清晰的内容累积过程
- HTML报告默认显示合并后的完整内容
- 需要调试时可切换到"原始SSE"或"JSON数组"视图

# 流式响应支持 - 功能说明

## 概述

drun 现已支持 Server-Sent Events (SSE) 流式响应的测试和断言。本功能支持测试 OpenAI、Claude 等 LLM API 的流式聊天接口。

## 核心特性

### 1. SSE 协议解析
- 自动解析 `data:` 行格式的 SSE 流
- 支持 JSON 事件数据解析
- 识别 `[DONE]` 结束标记
- 记录每个事件的时间戳（相对于请求开始时间）

### 2. 数据提取
支持通过 JMESPath 提取流式数据：

```yaml
extract:
  # 提取第一个事件的内容
  first_content: $.stream_events[0].data.choices[0].delta.content
  
  # 提取最后一个事件的完成原因
  finish_reason: $.stream_events[-1].data.choices[0].finish_reason
  
  # 提取事件总数
  event_count: $.stream_summary.event_count
  
  # 提取首包时间
  first_chunk_ms: $.stream_summary.first_chunk_ms
```

### 3. 断言能力
支持对流式响应的各个维度进行断言：

```yaml
validate:
  # HTTP 状态码
  - eq: [status_code, 200]
  
  # 事件数量
  - gt: [$.stream_summary.event_count, 0]
  - len_eq: [$.stream_events, 15]
  
  # 事件内容
  - contains: [$.stream_events[0].data.choices[0].delta.content, "Hello"]
  
  # 性能指标
  - lt: [$.stream_summary.first_chunk_ms, 500]  # 首包 < 500ms
  - lt: [$elapsed_ms, 5000]  # 总耗时 < 5s
```

### 4. HTML 报告展示
提供优雅的多视图展示：

#### 📋 事件列表（默认视图）
- 时间线风格，每个事件独立卡片
- 显示序号、相对时间戳、事件类型
- 最后一个事件自动高亮标记
- JSON 内容格式化显示

#### 📝 合并内容
- 自动提取所有 `delta.content` 并拼接
- 适合查看 LLM 的完整回复文本

#### 🔧 原始 SSE
- 保留完整的 `data:` 格式
- 用于调试 SSE 解析问题

#### { } JSON 数组
- 将所有事件序列化为 JSON 数组
- 便于复制后用于其他工具分析

**交互特性：**
- 标签页一键切换，无需滚动
- 智能复制：根据当前视图自动选择最佳格式
- 统计徽章：事件数量、首包时间
- ES5 兼容，支持 `file://` 协议

## 使用方法

### 基础示例

```yaml
config:
  name: 流式聊天测试
  base_url: https://api.openai.com

steps:
  - name: 流式对话
    request:
      method: POST
      url: /v1/chat/completions
      headers:
        Authorization: Bearer ${ENV(OPENAI_API_KEY)}
      body:
        model: "gpt-4"
        messages:
          - role: user
            content: "Hello, how are you?"
        stream: true       # 关键：在 body 中设置 stream: true
      
      # 启用流式处理
      stream: true         # 关键：在 request 中启用流式模式
      stream_timeout: 30   # 可选：流式超时（秒）
    
    extract:
      first_word: $.stream_events[0].data.choices[0].delta.content
      finish_reason: $.stream_events[-1].data.choices[0].finish_reason
      total_events: $.stream_summary.event_count
    
    validate:
      - eq: [status_code, 200]
      - gt: [$total_events, 0]
      - eq: [$finish_reason, "stop"]
      - lt: [$.stream_summary.first_chunk_ms, 1000]
```

### 运行测试

```bash
# 运行流式测试
drun run testcases/test_stream_demo.yaml --env-file .env

# 生成 HTML 报告查看流式数据
drun run testcases/test_stream_demo.yaml --html reports/stream_report.html --env-file .env
```

## 数据结构

### 响应对象结构

```python
{
    "status_code": 200,
    "headers": {...},
    "is_stream": True,
    "elapsed_ms": 1234.5,
    
    # 解析后的事件列表
    "stream_events": [
        {
            "index": 0,
            "timestamp_ms": 120.5,  # 相对时间
            "event": "message",
            "data": {"choices": [{"delta": {"content": "Hello"}}]}
        },
        {
            "index": 1,
            "timestamp_ms": 145.2,
            "event": "message",
            "data": {"choices": [{"delta": {"content": " world"}}]}
        },
        {
            "index": 14,
            "timestamp_ms": 1234.5,
            "event": "done",
            "data": None  # [DONE] 标记
        }
    ],
    
    # 原始 SSE 文本块（可选，用于调试）
    "stream_raw_chunks": [
        "data: {\"choices\":[...]}\n\n",
        "data: [DONE]\n\n"
    ],
    
    # 统计摘要
    "stream_summary": {
        "event_count": 15,
        "first_chunk_ms": 120.5,
        "last_chunk_ms": 1234.5
    }
}
```

### 提取路径参考

| 路径 | 说明 |
|------|------|
| `$.stream_events` | 完整事件列表 |
| `$.stream_events[0]` | 第一个事件 |
| `$.stream_events[-1]` | 最后一个事件 |
| `$.stream_events[*].data.choices[0].delta.content` | 所有内容片段 |
| `$.stream_summary.event_count` | 事件总数 |
| `$.stream_summary.first_chunk_ms` | 首包时间（ms） |
| `$.stream_summary.last_chunk_ms` | 末包时间（ms） |
| `$elapsed_ms` | 总耗时（ms） |

## 高级用法

### 内容拼接

```yaml
extract:
  # 使用 Hook 函数拼接所有内容片段
  full_response: ${merge_stream_content($stream_events)}
```

在 `drun_hooks.py` 中定义：

```python
def merge_stream_content(events, **kwargs):
    """合并所有流式事件的内容"""
    contents = []
    for event in events:
        data = event.get("data", {})
        if isinstance(data, dict):
            try:
                content = data["choices"][0]["delta"]["content"]
                if content:
                    contents.append(content)
            except (KeyError, IndexError):
                pass
    return "".join(contents)
```

### 性能监控

```yaml
validate:
  # 首包时间：检测服务响应速度
  - lt: [$.stream_summary.first_chunk_ms, 500]
  
  # 总耗时：检测完整响应时间
  - lt: [$elapsed_ms, 10000]
  
  # 事件间隔：确保流畅性
  - lt: [${max_event_interval($stream_events)}, 2000]
```

### 错误处理

```yaml
validate:
  # 验证没有错误事件
  - not_contains: [$.stream_events[*].event, "error"]
  
  # 验证正常结束
  - eq: [$.stream_events[-1].event, "done"]
```

## 技术细节

### 向后兼容
- `stream=False`（默认）时，完全保持现有行为
- 非流式响应不受任何影响

### 安全性
- 流式数据遵循 `--mask-secrets` 脱敏策略
- 敏感信息在日志和报告中自动脱敏

### 性能优化
- HTML 报告中，超过 100 个事件时建议使用分页
- 视图懒加载，切换时才渲染

### 浏览器兼容性
- 纯 ES5 JavaScript，无外部依赖
- 支持 IE11+ 及所有现代浏览器
- 支持 `file://` 协议本地查看

## 已知限制

1. **非标准 SSE 格式**：仅支持标准 `data:` 格式，其他格式需要自定义解析
2. **大数据量**：超过 1000 个事件可能影响报告加载速度
3. **二进制流**：不支持二进制流式数据，仅支持文本/JSON

## 故障排查

### 问题：流式请求超时
```
Error: Request timeout after 30s
```

**解决方案**：增加 `stream_timeout`
```yaml
request:
  stream: true
  stream_timeout: 60  # 增加到 60 秒
```

### 问题：SSE 解析失败
```
Error: Failed to parse SSE event
```

**解决方案**：
1. 检查 API 返回的 Content-Type 是否为 `text/event-stream`
2. 使用 `--log-level debug` 查看原始响应
3. 检查原始 SSE 格式是否符合标准

### 问题：提取变量为 None
```
[EXTRACT] content = None from $.stream_events[0].data.content
```

**解决方案**：检查 JMESPath 路径是否正确
```yaml
# OpenAI 格式
extract:
  content: $.stream_events[0].data.choices[0].delta.content
  
# 其他格式可能不同，先检查实际数据结构
```

## 测试示例

完整测试用例见：`testcases/test_stream_demo.yaml`

验证测试：
```bash
python test_stream_feature.py
```

## 相关文件

- `drun/models/request.py` - 请求模型（添加 stream 字段）
- `drun/engine/http.py` - HTTP 客户端（SSE 解析器）
- `drun/reporter/html_reporter.py` - HTML 报告（流式面板）
- `drun/runner/runner.py` - 测试运行器（流式响应处理）
- `testcases/test_stream_demo.yaml` - 示例用例

## 贡献

欢迎提交 Issue 和 PR 来改进流式响应支持！

---

**版本**: v2.2.0+
**作者**: Drun Team
**日期**: 2024

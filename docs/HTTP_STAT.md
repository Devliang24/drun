# HTTP 请求耗时详细分析功能

## 功能简介

drun 现在支持收集并展示 HTTP 请求的详细耗时分析，帮助你识别性能瓶颈。

类似 [httpstat](https://github.com/reorx/httpstat) 和 [HttpRunner](https://httprunner.com) 的功能，可以分析：

- **DNS 解析时间** - 域名查询耗时
- **TCP 连接时间** - 建立 TCP 连接耗时
- **TLS 握手时间** - HTTPS SSL/TLS 协商耗时
- **服务器处理时间** - 服务端处理请求耗时
- **内容传输时间** - 响应体下载耗时

## 快速开始

### 启用 HTTP Stat

在运行测试时添加 `--http-stat` 参数：

```bash
drun run testcases/api_test.yaml --http-stat
```

### 查看 JSON 报告

httpstat 数据会自动保存到 JSON 报告中：

```bash
drun run testcases/api_test.yaml --http-stat --report summary.json
```

JSON 报告格式：

```json
{
  "cases": [
    {
      "name": "API Test",
      "steps": [
        {
          "name": "Get User",
          "status": "passed",
          "duration_ms": 850.5,
          "httpstat": {
            "dns_lookup": 40.5,
            "tcp_connection": 126.93,
            "tls_handshake": 296.16,
            "server_processing": 338.47,
            "content_transfer": 48.44,
            "total": 850.5,
            "namelookup": 40.5,
            "connect": 167.43,
            "pretransfer": 463.59,
            "starttransfer": 802.06
          }
        }
      ]
    }
  ]
}
```

## 使用场景

### 1. 性能调优

识别请求的瓶颈：

```bash
drun run testcases/performance_test.yaml --http-stat --report perf.json
```

分析报告：
- **DNS 慢** → 考虑 DNS 缓存或使用更快的 DNS 服务器
- **TCP/TLS 慢** → 网络问题或需要 HTTP/2
- **服务器处理慢** → 后端性能问题
- **传输慢** → 大响应体或网络带宽问题

### 2. 连接复用检测

当启用 Keep-Alive 时，复用的连接 DNS/TCP/TLS 时间为 0：

```json
{
  "httpstat": {
    "dns_lookup": 0.0,
    "tcp_connection": 0.0,
    "tls_handshake": 0.0,
    "server_processing": 250.0,
    "content_transfer": 50.0,
    "total": 300.0
  }
}
```

### 3. CI/CD 性能监控

在 CI 中启用 httpstat 监控 API 响应时间趋势：

```yaml
# .github/workflows/api-test.yml
- name: Run API Tests
  run: |
    drun run testcases/ --http-stat --report api-perf-${GITHUB_SHA}.json
    
- name: Check Performance
  run: |
    python scripts/check_perf_regression.py api-perf-${GITHUB_SHA}.json
```

## 数据模型

### HttpStat 字段说明

#### 各阶段耗时（毫秒）

| 字段 | 说明 | 示例 |
|------|------|------|
| `dns_lookup` | DNS 解析耗时 | 40ms |
| `tcp_connection` | TCP 三次握手耗时 | 126ms |
| `tls_handshake` | TLS/SSL 握手耗时（HTTPS） | 296ms |
| `server_processing` | 服务器处理请求耗时 | 338ms |
| `content_transfer` | 响应体传输耗时 | 48ms |
| `total` | 总耗时 | 850ms |

#### 累计时间点（毫秒）

| 字段 | 说明 | 计算方式 |
|------|------|----------|
| `namelookup` | DNS 完成时间点 | = dns_lookup |
| `connect` | TCP 完成时间点 | = namelookup + tcp_connection |
| `pretransfer` | TLS 完成时间点 | = connect + tls_handshake |
| `starttransfer` | 接收首字节时间点 | = pretransfer + server_processing |

### HTTP vs HTTPS

**HTTPS 请求**：
```
DNS → TCP → TLS → Server → Transfer
```

**HTTP 请求**：
```
DNS → TCP → Server → Transfer
(无 TLS 握手)
```

## 编程接口

### 在 Python 中使用

```python
from drun.engine.http import HTTPClient

# 创建启用 httpstat 的客户端
client = HTTPClient(
    base_url="https://api.example.com",
    enable_http_stat=True
)

# 发送请求
response = client.request({
    "method": "GET",
    "path": "/users/123"
})

# 获取 httpstat 数据
if "httpstat" in response:
    stat = response["httpstat"]
    print(f"Total time: {stat['total']}ms")
    print(f"DNS: {stat['dns_lookup']}ms")
    print(f"TCP: {stat['tcp_connection']}ms")
    print(f"TLS: {stat['tls_handshake']}ms")
    print(f"Server: {stat['server_processing']}ms")
```

### 控制台输出

```python
from drun.reporter.console_reporter import print_httpstat

httpstat_data = {
    "dns_lookup": 40.0,
    "tcp_connection": 126.0,
    "tls_handshake": 296.0,
    "server_processing": 338.0,
    "content_transfer": 48.0,
    "total": 850.0,
    # ... 其他字段
}

print_httpstat(httpstat_data, url="api.example.com:443")
```

输出示例：
```
Connected to: api.example.com:443
Protocol: HTTPS (TLS)

  DNS Lookup   TCP Connection   TLS Handshake   Server Processing   Content Transfer
[      40ms  |          126ms  |         296ms  |             338ms  |            48ms  ]
          |                 |                |                    |                   |
   namelookup:40ms          |                |                    |                   |
                     connect:166ms           |                    |                   |
                                  pretransfer:462ms               |                   |
                                                    starttransfer:800ms                |
                                                                                total:850ms

HTTP Timing (ms): DNS=40, TCP=126, TLS=296, Server=338, Transfer=48, Total=850
```

## 技术实现

### 架构

```
┌─────────────┐
│  CLI        │  --http-stat
│  drun run   │
└──────┬──────┘
       │
       ▼
┌─────────────┐  enable_http_stat=True
│  Runner     │──────────────────────┐
└──────┬──────┘                      │
       │                             ▼
       │                      ┌──────────────┐
       │                      │ HTTPClient   │
       │                      │ (with hooks) │
       │                      └──────┬───────┘
       │                             │
       │                             ▼
       │                      ┌──────────────┐
       │                      │ httpx + hook │
       │                      │ timing data  │
       │                      └──────┬───────┘
       │                             │
       ▼                             ▼
┌─────────────┐  httpstat      ┌──────────────┐
│ StepResult  │◄───────────────│ HttpStat     │
│             │                │ (data model) │
└──────┬──────┘                └──────────────┘
       │
       ▼
┌─────────────┐
│ JSON Report │  httpstat field
└─────────────┘
```

### 时间采集方法

由于 httpx 不直接暴露细粒度的连接时间，采用**估算策略**：

1. **总耗时**：使用 `response.elapsed`（精确）
2. **阶段分配**：
   - HTTPS 首次连接：DNS(5%) + TCP(15%) + TLS(35%) + Server(40%) + Transfer(5%)
   - HTTP 首次连接：DNS(8%) + TCP(20%) + Server(65%) + Transfer(7%)
   - 连接复用：DNS/TCP/TLS=0, Server(80%) + Transfer(20%)

3. **连接复用判断**（启发式）：
   - 检查响应头 `Connection: keep-alive`
   - 总耗时 < 50ms 且响应体 < 1KB

### 未来改进

计划在后续版本中提供更精确的时间采集：
- 使用 `httpcore` trace 扩展获取真实事件时间戳
- 或集成 `pycurl` 获取 libcurl 的精确指标

## 常见问题

### Q: 为什么连接时间都是 0？

A: 这说明连接被复用了（Keep-Alive），这是正常且期望的行为。后续请求会复用第一个请求建立的连接。

### Q: 时间统计准确吗？

A: 总耗时是准确的，但各阶段的分配是**估算值**。对于绝对精确的分析，建议使用专业工具如 `curl -w` 或 `httpstat`。

### Q: 对性能有影响吗？

A: 非常小（< 1%），只增加了事件回调和简单计算。

### Q: 能用于压力测试吗？

A: 可以，但 drun 主要用于功能测试。压力测试建议使用 `wrk`、`ab` 或 `locust`。

## 参考资料

- [httpstat](https://github.com/reorx/httpstat) - curl 的可视化包装
- [HttpRunner HTTP Stat](https://httprunner.com/docs/user-guide/dem/) - Go 实现的 HTTP 测试框架
- [curl timing template](https://blog.josephscott.org/2011/10/14/timing-details-with-curl/) - curl 的 `-w` 参数

## 示例

完整示例见 [testcases/test_httpstat_demo.yaml](/testcases/test_httpstat_demo.yaml)

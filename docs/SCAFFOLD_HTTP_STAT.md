# 脚手架 HTTP Stat 功能集成

## 更新内容总结

已成功将 HTTP Stat 功能集成到 `drun init` 脚手架中，用户在初始化新项目时将自动获得性能分析相关的示例和文档。

## 新增文件

### 1. testcases/test_performance.yaml

**位置**: `testcases/test_performance.yaml`

**内容**: HTTP 性能分析示例测试用例，包含：
- 快速响应测试（带性能阈值断言）
- 延迟响应测试（验证延迟时间）
- POST 请求性能测试（JSON 数据）

**使用方式**:
```bash
# 普通运行
drun run testcases/test_performance.yaml

# 启用 HTTP Stat
drun run testcases/test_performance.yaml --http-stat --report perf.json
```

## 更新的文档

### 2. README.md（项目根目录）

#### 更新 1: 运行测试部分
添加了 `--http-stat` 参数的使用示例：
```bash
# 启用 HTTP 耗时分析（性能调优）
drun run testcases --http-stat --report reports/perf.json
```

并添加了详细说明：
> **性能分析**：使用 `--http-stat` 参数可以收集每个 HTTP 请求的详细耗时（DNS解析、TCP连接、TLS握手、服务器处理、内容传输），帮助识别性能瓶颈。

#### 更新 2: 项目结构说明
在 testcases 目录中添加了性能测试文件：
```
├── testcases/              # 测试用例目录
│   ├── test_demo.yaml      # 完整认证流程示例
│   ├── test_api_health.yaml # 健康检查示例
│   ├── test_performance.yaml # HTTP 性能分析示例  ← 新增
│   ├── test_db_assert.yaml # 数据库断言示例
│   └── test_import_users.yaml # CSV 参数化用例
```

#### 更新 3: CI/CD 集成部分
在 GitHub Actions 示例中添加了 `--http-stat` 参数：
```yaml
- name: Run Tests
  run: |
    drun run testcases \
      --html reports/report.html \
      --report reports/run.json \
      --http-stat  ← 新增
```

#### 更新 4: 新增性能监控示例章节
添加了完整的性能监控示例章节，包括：

**CI 管道示例**:
```yaml
- name: Run Performance Tests
  run: |
    drun run testcases \
      --http-stat \
      --report reports/perf-${{ github.sha }}.json

- name: Check Performance Regression
  run: |
    python scripts/check_perf.py reports/perf-${{ github.sha }}.json \
      --threshold 2000 \
      --baseline reports/baseline.json
```

**JSON 数据格式示例**:
```json
{
  "httpstat": {
    "dns_lookup": 40.5,
    "tcp_connection": 126.93,
    "tls_handshake": 296.16,
    "server_processing": 338.47,
    "content_transfer": 42.31,
    "total": 846.18
  }
}
```

**性能监控应用场景**:
- 性能基线对比
- 慢请求告警（如总耗时 > 2s）
- 性能趋势图表
- 瓶颈分析（DNS慢？TLS慢？服务器慢？）

## 代码更新

### 3. drun/scaffolds/templates.py

新增模板常量 `PERF_TESTCASE`，完整的 HTTP 性能分析测试用例模板。

### 4. drun/scaffolds/__init__.py

添加 `PERF_TESTCASE` 到导出列表：
```python
from .templates import (
    # ... 其他导入
    PERF_TESTCASE,  # 新增
    # ...
)

__all__ = [
    # ...
    "PERF_TESTCASE",  # 新增
    # ...
]
```

### 5. drun/cli.py

在 `init_project` 函数中添加性能测试文件创建：
```python
# testcases/test_performance.yaml
_write_template("testcases/test_performance.yaml", scaffolds.PERF_TESTCASE)
```

## 使用效果

当用户运行 `drun init myproject` 时，将自动获得：

1. ✅ **性能测试示例文件** (`testcases/test_performance.yaml`)
2. ✅ **README 中的 HTTP Stat 使用说明**
3. ✅ **CI/CD 性能监控示例**
4. ✅ **性能回归检测指导**

## 验证

```bash
# 1. 初始化新项目
drun init testproject

# 2. 查看生成的文件
ls testproject/testcases/test_performance.yaml

# 3. 运行性能测试（需先配置 .env 中的 BASE_URL）
cd testproject
drun run testcases/test_performance.yaml --http-stat

# 4. 查看 README 中的性能分析说明
grep -A10 "性能分析" README.md
```

## 相关文档

- [HTTP Stat 完整文档](HTTP_STAT.md)
- [主 README](../README.md)
- [格式转换文档](FORMAT_CONVERSION.md)
- [CI/CD 集成](CI_CD.md)

## 总结

HTTP Stat 功能现已完全集成到 drun 脚手架中，新用户将自动获得：
- 📊 开箱即用的性能测试示例
- 📖 完整的使用文档和最佳实践
- 🔧 CI/CD 集成示例
- 🎯 性能监控和回归检测指导

这确保了每个使用 drun 的项目都能轻松进行性能分析和监控！ 🚀

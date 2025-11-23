# 钉钉通知中包含测试报告指南

## 功能说明

钉钉通知现在支持在消息中添加可点击的测试报告链接，方便团队成员直接查看详细测试结果。

## 使用方式

### 方式 1：配置公网可访问的报告 URL（推荐）

#### 1.1 在 .env 中配置 REPORT_URL

```env
# 钉钉通知配置
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
DINGTALK_SECRET=SECxxx
DINGTALK_STYLE=markdown
DINGTALK_TITLE=API测试结果

# 报告 URL（公网可访问）
REPORT_URL=https://ci.example.com/artifacts/report.html
```

#### 1.2 运行测试并生成报告

```bash
# 生成 HTML 报告
drun run testcases --html reports/report.html --notify dingtalk

# 或使用自定义报告名称
drun run testcases --html reports/$(date +%Y%m%d-%H%M%S).html --notify dingtalk
```

#### 1.3 上传报告到服务器

**选项 A：使用 CI/CD 自动上传**

```yaml
# GitHub Actions 示例
- name: Run Tests
  run: |
    drun run testcases --html reports/report.html --notify dingtalk
  
- name: Upload Report
  uses: actions/upload-artifact@v3
  with:
    name: test-report
    path: reports/report.html

- name: Set Report URL
  run: |
    REPORT_URL="https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }}"
    echo "REPORT_URL=$REPORT_URL" >> $GITHUB_ENV
```

**选项 B：上传到对象存储（OSS/S3）**

```bash
# 阿里云 OSS 示例
drun run testcases --html reports/report.html
ossutil cp reports/report.html oss://my-bucket/reports/$(date +%Y%m%d-%H%M%S).html
```

**选项 C：使用 HTTP 服务器**

```bash
# 在报告目录启动 HTTP 服务器
cd reports
python3 -m http.server 8080

# 配置 REPORT_URL（如果有公网 IP）
# REPORT_URL=http://your-ip:8080/report.html
```

### 方式 2：CI/CD 环境自动配置

#### 2.1 GitHub Actions

```yaml
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install Dependencies
        run: pip install -e .
      
      - name: Run Tests with Report
        env:
          DINGTALK_WEBHOOK: ${{ secrets.DINGTALK_WEBHOOK }}
          DINGTALK_SECRET: ${{ secrets.DINGTALK_SECRET }}
          DINGTALK_STYLE: markdown
          REPORT_URL: https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }}
        run: |
          drun run testcases \
            --html reports/report.html \
            --notify dingtalk \
            --notify-only failed
      
      - name: Upload Report Artifact
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-report-${{ github.run_number }}
          path: reports/report.html
```

#### 2.2 GitLab CI

```yaml
test:
  stage: test
  script:
    - pip install -e .
    - drun run testcases --html reports/report.html --notify dingtalk
  variables:
    DINGTALK_WEBHOOK: $DINGTALK_WEBHOOK
    DINGTALK_SECRET: $DINGTALK_SECRET
    REPORT_URL: $CI_JOB_URL/artifacts/file/reports/report.html
  artifacts:
    when: always
    paths:
      - reports/
    expire_in: 30 days
```

### 方式 3：使用内网文件服务器

如果团队有内网文件服务器（如 Nginx、Apache）：

```bash
# 1. 生成报告
drun run testcases --html reports/report-$(date +%Y%m%d-%H%M%S).html

# 2. 复制到文件服务器
cp reports/report-*.html /var/www/html/test-reports/

# 3. 配置 REPORT_URL（内网地址）
export REPORT_URL=http://fileserver.internal/test-reports/report-20251123.html

# 4. 重新运行（或在 .env 中配置）
drun run testcases --notify dingtalk
```

## 钉钉通知效果

配置 `REPORT_URL` 后，钉钉通知将显示：

```markdown
### 电商API测试结果

【测试结果】电商API测试框架 执行完成：总 5 | 通过 4 | 失败 1 | 跳过 0 | 3.2s

步骤统计：总 15 | 通过 14 | 失败 1

失败步骤详情：
1. [用户认证流程测试] 获取当前用户信息
   • 错误: status_code eq 200 (actual=404)
   • 耗时: 1256.1ms

执行文件: testcases/test_user.yaml

报告: https://ci.example.com/artifacts/report.html

[📊 查看详细报告](https://ci.example.com/artifacts/report.html)
```

点击"📊 查看详细报告"链接即可打开详细的 HTML 测试报告。

## 完整配置示例

### 本地开发环境

```env
# .env
BASE_URL=http://localhost:8080

# 钉钉通知
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
DINGTALK_SECRET=SECxxx
DINGTALK_STYLE=markdown
DINGTALK_TITLE=API测试结果
DRUN_NOTIFY_ONLY=failed

# 报告 URL（本地不配置，仅显示本地路径）
# REPORT_URL=
```

运行：
```bash
drun run testcases --html reports/report.html --notify dingtalk
```

### CI/CD 环境

```env
# .env.ci
BASE_URL=https://api-staging.example.com

# 钉钉通知
DINGTALK_WEBHOOK=${DINGTALK_WEBHOOK}
DINGTALK_SECRET=${DINGTALK_SECRET}
DINGTALK_STYLE=markdown
DINGTALK_TITLE=API自动化测试
DRUN_NOTIFY_ONLY=always

# 报告 URL（由 CI 系统动态设置）
REPORT_URL=${CI_REPORT_URL}
```

运行：
```bash
export CI_REPORT_URL="https://ci.example.com/jobs/${CI_JOB_ID}/artifacts/report.html"
drun run testcases --html reports/report.html --notify dingtalk
```

## 高级用法

### 动态生成报告 URL

```bash
#!/bin/bash
# deploy-and-test.sh

# 生成唯一的报告名称
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
REPORT_FILE="reports/report-${TIMESTAMP}.html"

# 运行测试
drun run testcases --html "$REPORT_FILE"

# 上传到 OSS
ossutil cp "$REPORT_FILE" "oss://my-bucket/reports/report-${TIMESTAMP}.html"

# 设置报告 URL 并发送通知
export REPORT_URL="https://my-bucket.oss-cn-hangzhou.aliyuncs.com/reports/report-${TIMESTAMP}.html"

# 手动触发钉钉通知（如果之前没有发送）
# 或重新运行测试
drun run testcases --notify dingtalk --notify-only always
```

### 多环境配置

```bash
# 开发环境
export ENV=dev
export REPORT_URL=http://dev-reports.internal/latest.html
drun run testcases --env-file .env.dev --notify dingtalk

# 测试环境
export ENV=test
export REPORT_URL=http://test-reports.internal/latest.html
drun run testcases --env-file .env.test --notify dingtalk

# 生产环境（仅失败通知）
export ENV=prod
export REPORT_URL=https://prod-reports.example.com/latest.html
drun run testcases --env-file .env.prod --notify dingtalk --notify-only failed
```

## 故障排查

### 问题 1：报告链接无法访问

**原因**：报告 URL 配置错误或权限不足

**解决**：
1. 检查 `REPORT_URL` 是否正确
2. 确认 URL 可公网访问（或团队网络内可访问）
3. 检查防火墙和权限设置

### 问题 2：报告链接没有出现在钉钉消息中

**原因**：
- 没有配置 `REPORT_URL`
- `DINGTALK_STYLE` 不是 `markdown`

**解决**：
```env
DINGTALK_STYLE=markdown  # 必须是 markdown 格式
REPORT_URL=https://...   # 配置报告 URL
```

### 问题 3：钉钉显示"链接无法访问"

**原因**：钉钉机器人可能无法访问某些内网地址

**解决**：
- 使用公网可访问的 URL
- 或配置 VPN/代理
- 或使用钉钉支持的文件存储服务

## 最佳实践

1. **CI/CD 集成**：在 CI/CD 管道中自动生成并上传报告
2. **报告命名**：使用时间戳或构建号命名报告，避免覆盖
3. **存储管理**：定期清理旧报告，避免存储空间浪费
4. **权限控制**：确保报告 URL 有适当的访问权限
5. **失败通知**：配置 `DRUN_NOTIFY_ONLY=failed` 减少通知干扰

## 相关配置

| 环境变量 | 必需 | 说明 | 示例 |
|---------|------|------|------|
| `REPORT_URL` | ❌ | 报告公网 URL | `https://ci.example.com/reports/latest.html` |
| `DINGTALK_STYLE` | ❌ | 消息格式（markdown 支持链接） | `markdown` |
| `DINGTALK_TITLE` | ❌ | 通知标题 | `API测试结果` |
| `DRUN_NOTIFY_ONLY` | ❌ | 通知策略 | `failed` 或 `always` |

## 总结

通过配置 `REPORT_URL` 环境变量，可以在钉钉通知中添加可点击的测试报告链接，方便团队成员快速查看详细测试结果。推荐在 CI/CD 环境中使用，结合 artifacts 或对象存储服务，实现自动化测试报告分发。

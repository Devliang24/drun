# Drun v4.1.2 发布说明

发布日期：2025-11-23

## ✨ 功能增强

### 钉钉 Markdown 消息格式优化

显著改进钉钉通知的 Markdown 格式，提供更美观、更易读的消息展示。

**改进前（纯文本）：**
```
【测试结果】HC-MPC 执行完成：总 1 | 通过 1 | 失败 0 | 跳过 0 | 0.3s
步骤统计：总 1 | 通过 1 | 失败 0
执行文件: testcases\test_change_status.yaml
报告: reports/hc-mpc-20251123-195613.html
```

**改进后（Markdown）：**
```markdown
### 【测试结果】HC-MPC

**执行时间**: 0.3s

**用例统计**: 总数 1 | ✅ 通过 1 | ❌ 失败 0 | ⏭ 跳过 0

**步骤统计**: 总数 1 | ✅ 通过 1 | ❌ 失败 0

---

**执行文件: testcases\test_change_status.yaml**

---

📊 **报告**: `reports/hc-mpc-20251123-195613.html`

📝 **日志**: `logs/hc-mpc-20251123-195613.log`
```

**钉钉显示效果：**
- 🎨 标题使用大号字体
- ✅ 统计信息带表情符号
- 📊 使用分割线分隔内容
- 💡 代码块显示路径
- 📱 清晰的层次结构

### 新增功能

1. **build_markdown_message() 函数**
   - 专门为 Markdown 格式设计的消息生成器
   - 使用钉钉支持的 Markdown 语法
   - 自动格式化失败详情、报告链接等

2. **智能格式选择**
   - 根据 `DINGTALK_STYLE` 配置自动选择格式
   - `markdown` - 使用富文本格式（推荐）
   - `text` - 使用纯文本格式（向后兼容）

3. **表情符号增强**
   - ✅ 通过测试
   - ❌ 失败测试
   - ⏭ 跳过测试
   - 📊 报告链接
   - 📝 日志链接

4. **失败详情优化**
   - 使用 Markdown 加粗标题
   - 列表格式显示错误详情
   - 代码块包裹错误信息
   - 显示步骤耗时

## 🔧 配置说明

### 启用 Markdown 格式

在 `.env` 文件中配置：

```env
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
DINGTALK_SECRET=SECxxx
DINGTALK_STYLE=markdown  # 启用 Markdown 格式
DINGTALK_TITLE=API测试结果
```

### 使用纯文本格式

```env
DINGTALK_STYLE=text  # 或不配置（默认为 text）
```

## 📦 使用示例

```bash
# 运行测试并发送 Markdown 格式通知
drun run testcases --html reports/report.html --notify dingtalk

# 仅失败时发送通知
drun run testcases --notify dingtalk --notify-only failed
```

## 🔄 升级指南

### 从 v4.1.1 升级

```bash
pip install --upgrade drun
```

**配置建议：**
```env
# 推荐配置 - 启用 Markdown 格式获得更好的显示效果
DINGTALK_STYLE=markdown
```

### 验证版本

```bash
drun --version
# 输出: drun 4.1.2
```

## 📋 完整变更日志

### 新增 (Added)
- ✨ 新增 `build_markdown_message()` 函数生成富文本格式
- 🎨 添加表情符号提升可读性（✅ ❌ ⏭ 📊 📝）
- 📝 使用 Markdown 标题、加粗、列表、分割线等语法

### 改进 (Improved)
- 🔧 根据 `DINGTALK_STYLE` 自动选择文本或 Markdown 格式
- 💡 改进失败详情显示，使用代码块包裹错误信息
- 🎯 优化报告和日志链接的显示方式
- 📱 提升消息在钉钉中的可读性和视觉效果

### 兼容性
- ✅ 完全向后兼容
- ✅ `DINGTALK_STYLE=text` 用户不受影响
- ✅ 未配置 `DINGTALK_STYLE` 的用户保持纯文本格式
- ✅ 仅 `DINGTALK_STYLE=markdown` 的用户受益

## 🎯 适用场景

- 团队协作：更清晰的测试结果展示
- CI/CD 集成：自动化测试结果通知
- 失败跟踪：突出显示失败用例和错误信息
- 报告分享：直观的统计信息展示

## 💡 最佳实践

### 推荐配置

```env
# .env
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
DINGTALK_SECRET=SECxxx
DINGTALK_STYLE=markdown          # 使用 Markdown 格式
DINGTALK_TITLE=API自动化测试结果
DRUN_NOTIFY_ONLY=failed          # 仅失败时通知
REPORT_URL=https://ci.example.com/reports/latest.html
```

### CI/CD 集成

```yaml
# GitHub Actions
- name: Run Tests
  env:
    DINGTALK_STYLE: markdown
    REPORT_URL: ${{ steps.upload.outputs.artifact-url }}
  run: |
    drun run testcases \
      --html reports/report.html \
      --notify dingtalk \
      --notify-only failed
```

## 🔗 相关链接

- [GitHub Repository](https://github.com/Devliang24/drun)
- [钉钉报告集成指南](./DINGTALK_REPORT_GUIDE.md)
- [v4.1.1 发布说明](./RELEASE_NOTES_v4.1.1.md)
- [v4.1.0 发布说明](./RELEASE_NOTES_v4.1.0.md)

---

**版本号：** 4.1.2  
**发布日期：** 2025-11-23  
**重要程度：** ⭐⭐⭐ (推荐升级)  
**类型：** Feature Enhancement  
**亮点：** 大幅提升钉钉通知的视觉效果和可读性

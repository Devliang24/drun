# Drun v4.1.1 发布说明

发布日期：2025-11-23

## 🐛 Bug 修复

### 钉钉通知签名参数传递问题

修复了钉钉通知在使用加签验证时无法正常发送的问题。

**问题描述：**
- 当配置 `DINGTALK_SECRET` 时，签名参数通过 `params` 传递会覆盖 URL 中的 `access_token`
- 导致钉钉 API 返回错误：`缺少参数 access_token`

**修复方案：**
- 将签名参数（`timestamp` 和 `sign`）直接附加到 URL
- 避免使用 `params` 参数覆盖查询字符串

**受影响版本：** v4.0.0 - v4.1.0

**修复提交：** 8e8cf13

## ✨ 新增功能

### 钉钉通知支持测试报告链接

在钉钉通知消息中添加可点击的测试报告链接，方便团队快速查看详细结果。

**功能特性：**
- 支持 `REPORT_URL` 环境变量配置公网报告地址
- Markdown 格式自动添加"📊 查看详细报告"可点击链接
- 自动识别 HTTP/HTTPS URL
- 兼容本地路径显示

**使用示例：**

```env
# .env 配置
REPORT_URL=https://ci.example.com/reports/latest.html
DINGTALK_STYLE=markdown
```

```bash
# 运行测试并生成报告
drun run testcases --html reports/report.html --notify dingtalk
```

**钉钉消息效果：**
```markdown
【测试结果】执行完成：总 5 | 通过 4 | 失败 1 | 3.2s

报告: https://ci.example.com/reports/latest.html

[📊 查看详细报告](https://ci.example.com/reports/latest.html)
```

**新增文档：** DINGTALK_REPORT_GUIDE.md

**功能提交：** ca1f0df

## 🔧 改进

### 消息格式优化

- 在通知消息开头添加"【测试结果】"标识
- 支持配置了关键词验证的钉钉机器人
- 提升消息可读性

## 📚 文档更新

- 新增 `DINGTALK_REPORT_GUIDE.md` - 详细的测试报告集成指南
- 包含 CI/CD 集成示例（GitHub Actions、GitLab CI）
- 对象存储上传方案（OSS、S3）
- 内网文件服务器配置
- 完整的故障排查指南

## 🔄 升级指南

### 从 v4.1.0 升级

```bash
pip install --upgrade drun
```

**无需修改配置！** 现有的钉钉通知配置将自动工作。

### 启用报告链接（可选）

在 `.env` 文件中添加：

```env
REPORT_URL=https://your-server.com/reports/latest.html
```

### 验证版本

```bash
drun --version
# 输出: drun 4.1.1
```

## 📦 完整变更日志

### 修复 (Fixed)
- 🐛 修复钉钉通知签名参数传递导致 `access_token` 被覆盖的问题
- 🐛 修复配置加签密钥后通知无法发送的问题

### 新增 (Added)
- ✨ 钉钉通知支持 `REPORT_URL` 环境变量
- ✨ Markdown 格式消息自动添加可点击报告链接
- 📄 新增 DINGTALK_REPORT_GUIDE.md 详细文档

### 改进 (Improved)
- 🎨 通知消息添加"【测试结果】"标识
- 🔧 优化 URL 参数处理逻辑
- 📝 改进代码注释和文档

## 🙏 致谢

感谢社区用户反馈钉钉通知的问题，帮助我们快速定位并修复。

## 🔗 相关链接

- [GitHub Repository](https://github.com/Devliang24/drun)
- [钉钉报告集成指南](./DINGTALK_REPORT_GUIDE.md)
- [完整文档](./README.md)
- [v4.1.0 发布说明](./RELEASE_NOTES_v4.1.0.md)

---

**版本号：** 4.1.1  
**发布日期：** 2025-11-23  
**重要程度：** ⭐⭐⭐⭐ (推荐升级，修复关键 bug)  
**类型：** Bug Fix + Feature Enhancement

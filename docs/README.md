# 📚 文档索引（Docs Index）

欢迎查阅 Drun 文档集合。以下是常用文档入口：

- 快速上手（主仓库 README 顶部的“快速开始”）
- 命令行工具（CLI）：docs/CLI.md
  - drun run（运行测试）
  - drun check（语法/风格检查）
  - drun fix（一键修复）
  - drun convert（格式转换）
  - drun export（导出 cURL）
- 完整参考（Reference）：docs/REFERENCE.md
  - DSL 概念与结构
  - 内置函数
  - 项目 Hooks 与辅助函数
  - 环境变量
- 命名规范（Naming Convention）：docs/NAMING_CONVENTION.md
  - 包名/模块名/CLI 命令规范
  - 品牌名称/文档标题规范
  - 环境变量命名规范
  - 正确与错误示例
- 变更日志（Changelog）：CHANGELOG.md
- 实战示例（Examples）：docs/EXAMPLES.md
  - 登录流程与 Token 注入
  - E2E 购物流程
  - 参数化（压缩）
  - 签名 Hooks 示例
  - 格式转换与导出工作流
  - 测试套件（Testsuite，引用用例）
- CI/CD 集成：docs/CI_CD.md
  - GitHub Actions / GitLab CI / Jenkins
  - 最佳实践（掩码、制品、分层）

建议阅读顺序
- 先通过“快速开始”跑通第一个测试
- 查阅 docs/CLI.md 了解常用命令
- 参考 docs/EXAMPLES.md 扩展到更复杂的场景
- 在流水线中集成见 docs/CI_CD.md
- 需要详尽语法与函数说明时查 docs/REFERENCE.md

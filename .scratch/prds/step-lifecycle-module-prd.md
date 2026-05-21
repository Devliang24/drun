# PRD：加深 Step Lifecycle Module

Labels: `ready-for-agent`

## Problem Statement

Drun 用户依赖一个 Case 来按顺序执行多个 Step。每个 Step 只有一个 Executable Target：request、invoke 或 sleep。当前 Step Lifecycle 主要集中在更宽泛的 case runner 实现里。对维护者来说，这让 Step 行为很难安全修改：repeat、skip、hooks、request 执行、invoke 执行、sleep 执行、extract、validate、response 保存、export、计时、错误处理和 StepResult 组装，都藏在一个过宽且偏 Shallow 的 Interface 后面。

用户希望代码架构更容易理解，也更适合未来 agent 安全修改。当前主要摩擦是：新增或修改一个 Step Lifecycle 行为时，需要理解太多 case runner 细节；测试一个单独 Step 规则时，也经常需要驱动整个 Case。

## Solution

创建一个更 Deep 的 Step Lifecycle Module，由它拥有“一个 Step 如何执行并产出 StepResult”的路径。case runner 保留 case 级职责：准备 case 变量、运行 case 级 hooks、按顺序遍历 steps、收集 StepResult，并组装最终 Case 结果。

Step Lifecycle Module 接收当前 Step 及其执行上下文，然后返回 `list[StepResult]`。返回列表是刻意设计：Request Step 或 Sleep Step 通常产出一个 StepResult；repeat 和 invoke 则天然可能产出多个 StepResult。

Request Step、Invoke Step、Sleep Step 应成为 Step Lifecycle seam 后面的内部 Adapter。它们不应该定义三套彼此独立的公开生命周期。repeat、skip、step hooks、repeat metadata、错误转 StepResult、failfast 处理等共享生命周期规则，应集中在一个地方。

本 PRD 不改变 YAML DSL 语义、CLI 参数、报告结构或退出码行为。它主要是一个带回归测试的深模块重构。

## User Stories

1. As a drun maintainer, I want Step Lifecycle 行为集中在一个 Module 中, so that 修改 Step 执行行为时有更好的 Locality。
2. As a drun maintainer, I want case runner 只负责编排 Case, so that 它不需要知道 request、invoke、sleep 的所有细节。
3. As a drun maintainer, I want request、invoke、sleep 共用一个 Step Lifecycle seam, so that 共享生命周期规则不会在多个 Executable Target 中重复。
4. As a drun maintainer, I want 一个 Step 返回一个或多个 StepResult, so that repeat 和 invoke 能自然适配同一个 Interface。
5. As a drun maintainer, I want repeat 处理位于 Step Lifecycle Module 内部, so that repeat metadata 能一致地应用到所有 Executable Target。
6. As a drun maintainer, I want skip 处理位于 Step Lifecycle Module 内部, so that 被跳过的 request、invoke、sleep 都产生一致的 StepResult。
7. As a drun maintainer, I want skip 表达式错误转换为 failed StepResult, so that Case 执行行为保持稳定。
8. As a drun maintainer, I want repeat 表达式错误转换为 failed StepResult, so that 失败形状保持一致。
9. As a drun maintainer, I want repeat 为 0 时产生 skipped StepResult, so that 现有报告行为不变。
10. As a drun maintainer, I want Step Lifecycle Module 尊重 failfast, so that case runner 不需要理解 target-specific failure。
11. As a drun maintainer, I want Request Step 的 setup hooks 属于 Step Lifecycle, so that hooks 顺序保持不变。
12. As a drun maintainer, I want Request Step 的 teardown hooks 属于 Step Lifecycle, so that hook 失败继续影响 StepResult。
13. As a drun maintainer, I want Sleep Step hooks 属于 Step Lifecycle, so that sleep 是一等 Step。
14. As a drun maintainer, I want Invoke Step 执行使用同一个生命周期结果契约, so that 被 invoke 的 Case steps 不需要在 case runner 中特殊处理。
15. As a drun maintainer, I want invoke 选择失败产生 failed StepResult, so that 当前用户可见失败行为保持不变。
16. As a drun maintainer, I want 被 invoke 的 Case 失败能标记父 Case 失败, so that 失败传播保持稳定。
17. As a drun maintainer, I want request 渲染保持兼容当前模板行为, so that 现有 YAML Case 继续可运行。
18. As a drun maintainer, I want request headers 清理和 token header 行为保持不变, so that 现有 Request Step 不回归。
19. As a drun maintainer, I want request retry 仍属于 request Executable Target 行为, so that retry 语义不泄漏回 case runner。
20. As a drun maintainer, I want response extraction 像现在一样更新 session variables, so that 后续 Step 能继续使用提取值。
21. As a drun maintainer, I want extract 值继续持久化到配置的环境输出, so that 依赖持久化变量的工作流继续可用。
22. As a drun maintainer, I want validate 结果继续使用现有 AssertionResult 形状, so that 报告结构不变。
23. As a drun maintainer, I want response body 保存继续产生相同的 StepResult response 字段, so that 二进制响应工作流稳定。
24. As a drun maintainer, I want CSV export 行为保持不变, so that 数据导出用例继续可用。
25. As a drun maintainer, I want request cURL 生成保持不变, so that 调试输出和报告字段稳定。
26. As a drun maintainer, I want streaming response 字段被继续保留, so that 流式响应报告不回归。
27. As a drun maintainer, I want secret masking 行为保持不变, so that 日志和报告继续遵守当前 reveal-secrets 行为。
28. As a drun maintainer, I want StepResult timing 行为保持稳定, so that 重构前后的报告汇总可比较。
29. As a drun maintainer, I want case runner 仍然在 Case 结束后关闭 HTTP client, so that 资源管理安全。
30. As a drun maintainer, I want case-level setup 和 teardown hooks 留在 Step Lifecycle Module 外部, so that Step Lifecycle 只拥有 step-level 关注点。
31. As a drun maintainer, I want Step Lifecycle 测试能直接覆盖 request、invoke、sleep, so that 不需要构造完整 CLI run 也能捕获回归。
32. As a drun maintainer, I want 现有 case runner 测试继续有意义, so that 重构能证明行为兼容。
33. As a drun maintainer, I want 新 Module 保持小 Interface, so that 未来 agent 能快速理解 Step 执行。
34. As a drun maintainer, I want target-specific 代码藏在内部 Adapter 后面, so that 未来新增 Executable Target 不需要继续扩大 case runner。
35. As a drun maintainer, I want 不产生用户可见 CLI 行为变化, so that 这个重构无需迁移说明即可发布。
36. As a drun user, I want 现有 Request Step 在重构后行为不变, so that 我的 YAML Case 继续可用。
37. As a drun user, I want 现有 Invoke Step 在重构后行为不变, so that Case 复用继续可用。
38. As a drun user, I want 现有 Sleep Step 在重构后行为不变, so that 等待类工作流继续可用。
39. As a drun user, I want repeat 和 skip 的报告表现不变, so that 我能比较新旧运行结果。
40. As a drun user, I want failure message 和 status 保持稳定, so that 围绕 drun 输出构建的自动化不被破坏。

## Implementation Decisions

- 构建一个 package-internal 的 Deep Module：Step Lifecycle Module；它不是公开扩展点。
- Step Lifecycle Interface 应切在 Step 层级，而不是 Executable Target 层级。
- Step Lifecycle Interface 应返回 `list[StepResult]`。
- Request Step、Invoke Step、Sleep Step 应作为 Step Lifecycle seam 后面的内部 Adapter。
- case runner 保留 case 级职责：case 变量初始化、case 级 hooks、step 顺序、聚合状态、耗时、Case 结果组装。
- step 级职责迁移到 Step Lifecycle seam 后面：step variables、repeat、skip、step-level hooks、target dispatch、target errors、extract、validate、StepResult shaping、failfast signaling。
- case-level setup 和 teardown hooks 不迁移到 Step Lifecycle Module。
- 当前用户可见 YAML DSL 不改变。
- 当前报告模型不改变。
- 当前 CLI 行为和退出码行为不改变。
- 第一轮重构中，Step Lifecycle Module 可以暂时复用现有 runner helpers；长期方向是收窄 runner Interface。
- invoke Adapter 应减少当前 `runner: Any` 回调形状带来的泄漏；如果更小的上下文能表达所需行为，就不要把任意 runner internals 暴露给 invoke。
- 重构应增量推进。建议第一条 vertical slice 先迁移 Sleep Step 生命周期行为，再迁移 Request Step，最后迁移 Invoke Step；每个 slice 后保持测试绿色。
- 新 Module 应通过 deletion test：删除 Step Lifecycle Module 后，repeat、skip、hooks、target dispatch、StepResult shaping 会重新散回 case runner 或多个 target Adapter。
- Module 命名应使用项目 glossary 中的领域词：Step Lifecycle。

## Testing Decisions

- 好测试应验证 Step Lifecycle seam 和 case runner seam 的外部行为，不验证私有 helper 的调用顺序。
- Step Lifecycle 测试应断言 request、invoke、sleep 三类 Executable Target 的 StepResult 输出。
- Step Lifecycle 测试应覆盖 repeat metadata、repeat 为 0、repeat 表达式错误、skip 为 true、skip 原因字符串、skip 表达式、skip 表达式错误、failfast 行为。
- Step Lifecycle 测试应覆盖 request 成功、request 错误、retry 耗尽、extract、validate 失败、response body 保存失败，以及当前已有的 masked report-safe request/response 字段行为。
- Step Lifecycle 测试应覆盖 sleep 成功、sleep 表达式渲染、sleep 表达式失败、sleep repeat、sleep skip、sleep hook 错误。
- Step Lifecycle 测试应覆盖 invoke 路径解析失败、被 invoke YAML 加载失败、选择的 Case 不存在、选择的 Case 成功、被 invoke Case 失败、重复 invoke、failfast 传播。
- case runner 回归测试应验证混合 request、sleep、invoke 的 Case 仍产出相同 CaseInstanceResult 形状。
- 现有测试先例包括 repeat step tests、sleep step tests、invoke case selection tests、binary response tests、request files tests、run output tests。
- 全量回归继续使用共享虚拟环境执行。
- 测试避免真实网络请求，优先使用 fake HTTP client 和 mocks。
- 除非重构改变用户可见输出，否则 CLI 不需要新增大范围测试；用户可见输出变化不在本 PRD 范围内。

## Out of Scope

- 改变 YAML DSL 语法。
- 新增 Executable Target。
- 改变 CLI 参数或退出码语义。
- 改变 JSON、HTML 或 Allure 报告结构。
- 重设计 Request Projection。
- 重设计 Run Session。
- 重设计 Report Publishing。
- 改变通知行为。
- 改变环境加载行为。
- 改变 YAML 诊断行为。
- 引入新的运行时依赖。
- 改变本地打包或发布流程。

## Further Notes

- 本 PRD 来自架构复盘的优先建议：先处理 Step Lifecycle，因为它集中最多执行期知识，也提供最清晰的测试 seam。
- 相关 glossary 已记录在 `CONTEXT.md`：Case、Step、Executable Target、Step Lifecycle、Request Step、Invoke Step、Sleep Step、StepResult。
- 设计讨论中的推荐形状是：一个 Step 进入 Step Lifecycle，输出零个、一个或多个 StepResult。按当前行为，repeat 为 0 会产生一个 skipped StepResult，而不是空列表。
- 最大架构风险是一次迁移太多。建议使用小 vertical slice：每迁移一类行为，就保持测试绿色。
- 原计划发布到 GitHub issue，但本地环境当前没有 GitHub CLI，也没有 GitHub token。此 Markdown 文件是可直接发布的 PRD artifact，并已标记 `ready-for-agent`。

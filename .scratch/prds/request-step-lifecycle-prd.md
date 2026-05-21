# PRD：迁移 Request Step 到 Step Lifecycle Module

Labels: `ready-for-agent`

## Problem Statement

Drun 已经把 Sleep Step 的 Step Lifecycle 迁移到独立 Module，但 Request Step 仍然留在 case runner 的大实现中。Request Step 是最复杂的 Executable Target：它包含 request 渲染、headers 清理、token 注入、setup hooks、HTTP 请求、retry、response logging、extract、env 持久化、export.csv、response.save_body_to、validate、teardown hooks、masking、cURL 生成、StepResult shaping。

从维护者视角看，case runner 仍然偏 Shallow：Interface 看起来是“运行 Case”，Implementation 却需要理解大量 Request Step 细节。新增或修改 Request Step 行为时，容易误伤 repeat、skip、hooks、report 字段、binary/streaming response、secret masking 等路径。

用户已确认下一条 vertical slice 做 Request Step -> Step Lifecycle。目标是继续加深 Step Lifecycle Module，让 case runner 更接近“按顺序收集 StepResult”的角色。

## Solution

扩展 Step Lifecycle Module，使它支持 Request Step。Request Step 与 Sleep Step 一样，通过同一个 StepLifecycle Interface 输入 Step 上下文，输出 `StepLifecycleResult`。该结果对象包含 `results: list[StepResult]` 和可选 `last_response`。

第一条 TDD tracer bullet 推荐覆盖 Request Step 的核心闭环：request success + validate + extract。它证明 Step Lifecycle seam 能完成“发送请求 -> 接收响应 -> validate -> extract -> 产出 StepResult”的完整行为。

实现时允许 Step Lifecycle Module 暂时复用现有 runner helpers，避免一次性设计过度。迁移完成后，case runner 不再直接持有 Request Step 的大段执行逻辑；它只负责把 StepLifecycle 返回的 StepResult 收集到 CaseInstanceResult 中，并用 `last_response` 更新 case-level teardown hooks 的输入。

本 PRD 不改变 YAML DSL、CLI 参数、报告结构、退出码、环境加载、通知行为或发布流程。

## User Stories

1. As a drun maintainer, I want Request Step 执行进入 Step Lifecycle Module, so that case runner 不再承载 request 细节。
2. As a drun maintainer, I want Request Step 与 Sleep Step 共用 StepLifecycle Interface, so that Step Lifecycle seam 更稳定。
3. As a drun maintainer, I want request success + validate + extract 能直接通过 Step Lifecycle 测试, so that Request Step 核心闭环有独立行为保障。
4. As a drun maintainer, I want Request Step repeat 行为保持不变, so that 一个 Step 能继续产出多个 StepResult。
5. As a drun maintainer, I want Request Step skip 行为保持不变, so that skip 仍然产出 skipped StepResult。
6. As a drun maintainer, I want Request Step repeat=0 行为保持不变, so that 仍然产出 skipped StepResult。
7. As a drun maintainer, I want Request Step repeat 表达式错误行为保持不变, so that 仍然产出 failed StepResult。
8. As a drun maintainer, I want Request Step skip 表达式错误行为保持不变, so that 仍然产出 failed StepResult。
9. As a drun maintainer, I want Request Step setup hooks 顺序保持不变, so that hooks 可继续修改 step/session variables。
10. As a drun maintainer, I want Request Step teardown hooks 顺序保持不变, so that teardown failure 继续影响 StepResult。
11. As a drun maintainer, I want request 渲染继续使用 strict template rendering, so that 未解析变量仍在请求前失败。
12. As a drun maintainer, I want request headers cleanup 保持不变, so that 空 Authorization 或 `Bearer none` 仍被移除。
13. As a drun maintainer, I want token 自动注入 Authorization header 行为保持不变, so that 现有 token 工作流不回归。
14. As a drun maintainer, I want Request Step retry 行为保持不变, so that 请求失败时仍按当前 retry/backoff 执行。
15. As a drun maintainer, I want Request Step request error 继续产出 failed StepResult, so that 网络错误报告稳定。
16. As a drun maintainer, I want Request Step response logging 行为保持不变, so that log 内容不因迁移丢失。
17. As a drun maintainer, I want streaming response 字段保持不变, so that SSE/stream 报告不回归。
18. As a drun maintainer, I want binary response 字段保持不变, so that body_size、content_type、body_bytes_b64 等仍可用于报告。
19. As a drun maintainer, I want extract 行为保持不变, so that 后续 Step 继续能使用提取变量。
20. As a drun maintainer, I want extract 值继续写入 envmap, so that runtime 变量传播不变。
21. As a drun maintainer, I want extract 值继续持久化到 env/yaml 文件, so that 跨运行复用变量不变。
22. As a drun maintainer, I want export.csv 行为保持不变, so that 数据导出用例不回归。
23. As a drun maintainer, I want response.save_body_to 行为保持不变, so that 二进制响应保存不回归。
24. As a drun maintainer, I want save_body_to 失败继续标记 StepResult failed, so that 文件保存错误不被吞掉。
25. As a drun maintainer, I want validate 行为保持不变, so that AssertionResult shape 不变。
26. As a drun maintainer, I want validate failure 继续标记 Request Step failed, so that Case status 聚合不变。
27. As a drun maintainer, I want cURL 生成保持不变, so that report/debug 仍能显示相同 cURL。
28. As a drun maintainer, I want secret masking 保持不变, so that reveal_secrets 配置继续生效。
29. As a drun maintainer, I want Request Step duration_ms 保持不变, so that报告 summary 可比较。
30. As a drun maintainer, I want failfast 行为保持不变, so that Request Step 失败后 case runner 仍按配置停止。
31. As a drun maintainer, I want case runner 只消费 StepLifecycleResult, so that Request Step 内部变化不再扩散到 case runner。
32. As a drun maintainer, I want Request Step 迁移后仍通过现有 request files 测试, so that multipart 上传路径不回归。
33. As a drun maintainer, I want Request Step 迁移后仍通过 binary response 测试, so that保存响应体路径不回归。
34. As a drun maintainer, I want Request Step 迁移后仍通过 repeat step 测试, so that repeat/skip 路径稳定。
35. As a drun maintainer, I want Request Step 迁移后仍通过 run output 测试, so that CLI run 产物路径稳定。
36. As a drun user, I want 现有 Request Step YAML 不需要改写, so that 重构对用户透明。
37. As a drun user, I want Request Step 报告字段不改变, so that 现有 report 消费方不需要改。
38. As a drun user, I want Request Step 失败信息不改变, so that 现有排障习惯不被破坏。
39. As a drun user, I want validate/extract 行为不改变, so that 现有接口测试断言继续可信。
40. As a future agent, I want Request Step 行为有独立测试 seam, so that 我能安全修改 request 执行细节。

## Implementation Decisions

- 扩展现有 Step Lifecycle Module，支持 Request Step。
- 不创建独立公开 Request Step lifecycle；Request Step 是 Step Lifecycle 内部 Adapter。
- StepLifecycle Interface 继续保持 step-level：输入 Step 上下文，输出 `StepLifecycleResult`。
- `StepLifecycleResult` 至少包含 `results: list[StepResult]` 和可选 `last_response`。
- 第一条 TDD tracer bullet 使用 Request Step success + validate + extract。
- 第一条 tracer bullet 不同时覆盖 repeat/skip；repeat/skip 作为第二条 vertical slice。
- case runner 仍负责 Case 级职责：case variables、case hooks、step 顺序、HTTP client 生命周期、CaseInstanceResult 聚合。
- Step Lifecycle 不创建或关闭 HTTP client；case runner 创建并关闭 client，Request Step Adapter 只使用传入 client。
- `StepLifecycleContext` 第一版直接接收 case runner 创建的 HTTP client 作为 borrowed runtime dependency；本 PRD 不额外抽 request adapter/callable，后续若 HTTP 执行边界稳定再单独评估。
- Step Lifecycle Module 接收 request 执行需要的上下文，并继续通过 `StepLifecycleResult.results` 返回 StepResult。
- 迁移实现包含 extract 后写入 envmap 与 persist_env_file 的逻辑；首个 tracer bullet 只断言 extract 可进入上下文/envmap，文件持久化由后续测试或现有回归覆盖。
- Request Step 迁移不得用 StepResult.response 反推 case-level teardown response；StepLifecycle 需通过 `StepLifecycleResult.last_response` 向 case runner 暴露 raw response metadata，供 case-level teardown hooks 使用。
- `StepLifecycleResult.last_response` 是内部运行期数据，可包含未脱敏 raw response；它只允许被 case runner 用作 case-level teardown 输入，不得直接写入 StepResult 或 report。
- Request Step 迁移第一轮可以复用 runner helpers，避免同时重设计 Request Projection。
- 若迁移后 request render/headers/token/body/curl 仍明显臃肿，再单独抽 Request Projection Module。
- 本 PRD 允许 StepLifecycle 内部提取私有 helper，但不新增独立 Request Projection Module。
- 不改变 StepResult model。
- 不改变 AssertionResult model。
- 不改变 YAML DSL。
- 不改变 CLI 行为。
- 不改变 report JSON/HTML/Allure schema。
- 不改变 notification 行为。
- 不改变 env loading/persist 行为。
- 不引入新依赖。
- 优先小步迁移：request success 闭环 -> request repeat/skip -> request error/retry -> extract/persist/export/save_body/stream/binary 边界。
- 实施前置步骤：先将现有 Sleep Step lifecycle 返回值从 `list[StepResult]` 调整为 `StepLifecycleResult`，并保持现有 Sleep 行为测试通过。

## Testing Decisions

- 测试行为，不测私有 helper 调用顺序。
- 新增/扩展 Step Lifecycle 测试，直接覆盖 Request Step success + validate + extract。
- 使用 fake HTTP client，不发真实网络请求。
- 保留现有 Runner.run_case 回归测试，证明 case runner seam 行为不变。
- 复用现有测试先例：repeat step tests、request files tests、binary response tests、run output tests、template engine tests。
- Request Step lifecycle 测试应覆盖：
  - request success -> passed StepResult
  - validate pass/fail -> AssertionResult 与 StepResult status
  - extract -> context/envmap 更新
  - repeat -> 多 StepResult + repeat metadata
  - skip -> skipped StepResult
  - request error/retry exhausted -> failed StepResult
  - setup hook error -> failed StepResult
  - teardown hook error -> failed StepResult
  - response.save_body_to failure -> failed StepResult
  - binary/streaming response report-safe fields
- CLI 测试仅在用户可见输出改变时新增；本 PRD 不计划改变输出。
- 每条 vertical slice 后运行相关测试，再跑全量 pytest。
- 全量回归命令使用共享虚拟环境。

## Out of Scope

- 迁移 Invoke Step。
- 设计最终 Request Projection Module。
- 改写 HTTPClient。
- 改写 TemplateEngine。
- 改写 validators/assertions。
- 改写 extract 语法。
- 改变 YAML DSL。
- 改变 CLI 参数、退出码或报告 schema。
- 改变通知、snippet、Allure、HTML report 发布流程。
- 新增运行时依赖。
- 本地打包或发布流程。

## Further Notes

- 本 PRD 是 Step Lifecycle 总 PRD 后的第二条 vertical slice。第一条 Sleep Step 已完成并推送。
- 当前最重要目标不是完美 Interface，而是让 Request Step 从 case runner 中迁移出来，并保持行为全绿。
- Request Step 是最大 Executable Target；迁移后 `Runner.run_case` 会显著变薄。
- Request Step 迁移会自然暴露 Request Projection Module 的真实边界，但不要在同一 slice 中强行完成。
- GitHub issue 发布被当前环境阻塞：未检测到 `gh` CLI，也无 `GITHUB_TOKEN`。此 Markdown 是可发布 PRD artifact，已带 `ready-for-agent` 标签。

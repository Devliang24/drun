# Drun 上下文

本上下文描述 drun 在 YAML DSL 作者体验与执行模型中的领域语言。它只记录领域词汇，不记录实现方案。

## Language

**Case（用例）**:
一个由 YAML 定义的测试用例，包含 `config`、可选参数，以及按顺序执行的 steps。
_Avoid_: scenario, test object, 测试对象

**Case Instance（用例实例）**:
一个 Case 在具体参数集下的一次运行实例。无参数化时，一个 Case 通常产生一个 Case Instance；有 `config.parameters` 时，一个 Case 会展开为多个 Case Instance。
_Avoid_: test run item, parameter row result, 参数行结果

**Step（步骤）**:
用例中的一个有序执行项。一个 Step 必须且只能拥有一个 Executable Target：request、invoke 或 sleep。
_Avoid_: action, operation, 动作, 操作

**Executable Target（执行目标）**:
让一个 Step 产生实际工作的唯一目标类型：request、invoke 或 sleep。
_Avoid_: action type, operation mode, 执行模式

**Step Lifecycle（步骤生命周期）**:
一个 Step 从生命周期决策开始，经过 Executable Target 工作，最终形成已记录 StepResult 的路径。
_Avoid_: step runner, step handler, 步骤处理器

**Request Step（请求步骤）**:
Executable Target 为 `request` 的 Step，用于发送 HTTP 请求，并可从响应中 check 或 extract。
_Avoid_: HTTP action, HTTP 操作

**Invoke Step（调用步骤）**:
Executable Target 为 `invoke` 的 Step，用于加载另一个 YAML Case，并把它作为当前 Case 的一部分执行。
_Avoid_: nested case call, 嵌套用例调用

**Sleep Step（等待步骤）**:
Executable Target 为 `sleep` 的 Step，用于按配置的毫秒数等待，且不能携带 check 或 extract 等 request-only 字段。
_Avoid_: delay action, 延迟动作

**StepResult（步骤结果）**:
一个已执行 Step 的运行期结果记录，包含状态、耗时、检查结果、请求与响应信息、错误信息等。
_Avoid_: step output, 步骤输出

**Step Outcome（步骤产出）**:
Request Step 在收到响应后形成 StepResult 之前的响应后处理结果，包含 check、extract、persist、export、response.save_body_to 和 StepResult 所需字段。
_Avoid_: post processor, result builder, 后处理器

## Example Dialogue

Dev: “这个 Case 有三个 Step：一个 Request Step、一个 Sleep Step、一个 Invoke Step。”

Domain expert: “对。每个 Step 都经过同一个 Step Lifecycle，但只有一个 Executable Target 处于激活状态。”

Dev: “所以 repeat 和 skip 属于 Step Lifecycle，而不是只属于 request 执行？”

Domain expert: “是的。Request、invoke、sleep 的区别在 Executable Target；它们最终都通过同一个 Step Lifecycle 产生已记录的 StepResult。”

Dev: “Request Step 的 check、extract、persist、export 和 response.save_body_to 都算 Step Outcome 吗？”

Domain expert: “对。Step Lifecycle 负责时机和顺序，Step Outcome 负责响应后处理并给 StepResult 提供结果字段。”

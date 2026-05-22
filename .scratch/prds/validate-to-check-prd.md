# PRD：将 validate 全面更名为 check

Labels: `ready-for-agent`

## Problem Statement

Drun 用户在 YAML Case 中使用 `validate` 来描述响应断言，但这个词容易被理解成 YAML schema 校验、配置校验或运行前校验。实际语义是：Request Step 收到响应后，对 `status_code`、headers 或响应 body 表达式执行检查，并把结果写入 StepResult 与报告。

用户希望 DSL 更短、更贴近实际动作。经过命名讨论，用户明确更在意字段短，并接受 `drun check` CLI 命令与 YAML `check` 字段在不同上下文中共存。因此，`validate` 应全面更名为 `check`。

本 PRD 是一次明确的 breaking change：不保留 `validate` YAML 字段兼容，不保留 `-validate` CLI 参数兼容，内部模型、执行日志、报告结构和文档语言也一起迁移到 `check` / `checks`。

## Solution

Drun 的用户可见语言统一改为 `check`。YAML Step 使用 `check` 字段表达响应检查；`drun q` 使用 `-check` 参数表达快速请求后的检查；报告结构使用 `checks` 表达 StepResult 的检查结果列表。

旧 YAML `validate` 不再被接受，但 loader 必须给专门迁移诊断，而不是普通 unknown field。诊断使用稳定错误码 `DRUN-YAML-012`，告诉用户 `validate` 已更名为 `check`，并给出最小修复示例。

旧 CLI `-validate` 不再被接受，但 CLI 输出应明确提示使用 `-check`。内部命名从 `Validator`、`validators`、`evaluate_validators` 等迁移到 `Check`、`checks`、`evaluate_checks`。报告里的 `asserts` / `AssertionResult` 也同步改为 `checks` / `CheckResult`。单条结果字段继续保留 `check`，即 `checks[].check` 表示被检查对象。

## User Stories

1. As a Drun YAML author, I want to write `check` instead of `validate`, so that the Step reads like a short response checking rule.
2. As a Drun YAML author, I want `check` to support the same comparators that `validate` used to support, so that I can migrate existing assertions without relearning operators.
3. As a Drun YAML author, I want `check` to work with `status_code`, headers, and response body expressions, so that existing response checks remain expressible.
4. As a Drun YAML author, I want body checks to keep using `$` JSONPath-like syntax, so that expression behavior stays consistent.
5. As a Drun YAML author, I want a clear error when I accidentally write `validate`, so that I know the exact migration.
6. As a Drun YAML author, I want the error for `validate` to show file, line, YAML path, hint, and example, so that I can fix the Case quickly.
7. As a Drun YAML author, I want `validate` and `check` not to coexist on the same Step, so that there is no precedence ambiguity.
8. As a Drun YAML author, I want Sleep Step incompatibility messages to mention `check`, so that request-only field rules use the new language.
9. As a Drun YAML author, I want request-only nesting diagnostics to mention `check`, so that indentation fixes match the new field.
10. As a Drun YAML author, I want generated scaffold YAML to use `check`, so that new projects start with the new DSL.
11. As a Drun CLI user, I want `drun q` to accept `-check`, so that quick requests use the same vocabulary as YAML.
12. As a Drun CLI user, I want `drun q -check` to accept the same expression format as the old `-validate`, so that the migration is mechanical.
13. As a Drun CLI user, I want old `-validate` usage to fail with a migration hint, so that I do not have to guess the replacement.
14. As a Drun CLI user, I want `drun q` exported YAML to emit `check`, so that generated Case files use the new DSL.
15. As a Drun CLI user, I want quick request output to say `Check` instead of `Validate`, so that terminal logs match the new command option.
16. As a Drun user reading run logs, I want validation log lines to become check log lines, so that output terminology is consistent.
17. As a Drun user reading JSON reports, I want StepResult to contain `checks`, so that report data matches YAML language.
18. As a Drun user reading HTML reports, I want the checks table to be labeled with check terminology, so that UI and YAML match.
19. As a Drun user reading Allure output, I want check attachments and failure details to use check terminology, so that report consumers see one vocabulary.
20. As a Drun user receiving notifications, I want failed check messages to use check terminology, so that failure summaries are consistent.
21. As a Drun user using snippets, I want snippet generation to preserve the new check language, so that reproduction assets stay aligned.
22. As a Drun user importing or converting requests, I want generated YAML to use `check`, so that all generated examples use the new DSL.
23. As a Drun user exporting cURL or running report tools, I want no unrelated behavior changes, so that only the check naming changes.
24. As a Drun user migrating old Cases, I want `validate` rejection to be deterministic, so that CI fails with a useful message.
25. As a Drun maintainer, I want the internal model to use `Check`, so that code terminology matches the public DSL.
26. As a Drun maintainer, I want Step models to expose `checks`, so that Step lifecycle code does not carry legacy `validators` naming.
27. As a Drun maintainer, I want Step Outcome to own check evaluation, so that response post-processing remains behind the Step Outcome seam.
28. As a Drun maintainer, I want check evaluation to stay isolated in a deep module, so that comparator behavior can be tested directly.
29. As a Drun maintainer, I want `CheckResult` to replace `AssertionResult`, so that result schemas use the new vocabulary.
30. As a Drun maintainer, I want report code to consume `StepResult.checks`, so that report structure no longer leaks old `asserts` naming.
31. As a Drun maintainer, I want all diagnostics and hints to mention `check`, so that loader author experience is coherent.
32. As a Drun maintainer, I want old `validate` to receive a dedicated diagnostic code, so that migration errors are easy to search.
33. As a Drun maintainer, I want tests to assert public behavior rather than private helper names, so that implementation can evolve safely.
34. As a Drun maintainer, I want old test fixtures updated to `check`, so that the test suite documents the new DSL.
35. As a Drun maintainer, I want breaking schema changes to be explicit in tests, so that accidental compatibility does not creep back in.
36. As a Drun docs reader, I want README examples to use `check`, so that the first copy-paste path is current.
37. As a Drun docs reader, I want troubleshooting pages to explain `validate` to `check`, so that old examples from memory are easy to fix.
38. As a Drun Agent Skill user, I want `drun-usage` examples to use `check`, so that AI-generated YAML follows the new DSL.
39. As a Drun Agent Skill user, I want the skill boundaries to warn against `validate`, so that generated answers do not use legacy fields.
40. As a future agent, I want one consistent vocabulary from YAML to reports, so that automated refactors do not have to map validate/assert/check concepts.

## Implementation Decisions

- This is a public breaking change, not an internal-only refactor.
- YAML Step field `validate` is replaced by `check`.
- Old YAML `validate` is rejected with dedicated diagnostic code `DRUN-YAML-012`.
- `DRUN-YAML-012` message says `validate has been renamed to check`, includes file/line when available, YAML path, hint, and a short `check` example.
- `validate` is not kept as an alias.
- If both legacy `validate` and new `check` appear, the loader reports the legacy rename diagnostic rather than merging both fields.
- Quick request CLI replaces `-validate` with `-check`.
- Old CLI `-validate` is not supported; CLI should emit a clear “use -check instead” hint where Typer allows it.
- Quick request YAML generation emits `check`.
- Internal check definition module uses `Check` and `normalize_checks`.
- Request Step models expose `checks`.
- Step Outcome evaluates checks after response capture and before StepResult recording.
- Check evaluation returns `CheckResult` objects.
- StepResult exposes `checks`.
- Report schema uses `checks` instead of `asserts`.
- Single check result item keeps the field name `check` for the checked expression or target.
- Comparator names and expression syntax do not change.
- Log prefix changes from validation terminology to check terminology.
- HTML, JSON, Allure, notifier, snippet, run output, server, docs, examples, scaffolds, import/convert output, and the local skill all use check terminology.
- Update domain glossary language from validate to check while preserving Step Lifecycle and Step Outcome seams.
- Existing ADRs about internal refactors not changing public behavior do not apply to this PRD because the user explicitly requested a breaking public rename.

## Testing Decisions

- Good tests should verify user-visible behavior and schema contracts, not private helper call order.
- Loader tests should cover successful `check`, rejected `validate`, rejected request-nested `check`, rejected Sleep Step `check`, and invalid body path syntax under `check`.
- Diagnostic tests should assert `DRUN-YAML-012`, path, hint, example, and best-effort line behavior for legacy `validate`.
- CLI tests should cover `drun q -check`, generated YAML using `check`, terminal output saying `Check`, and legacy `-validate` failure hint.
- Step Outcome tests should cover check pass, check fail, rendered expected values, unresolved variables, and Case failure propagation.
- Report tests should cover JSON StepResult `checks`, HTML check table labels, Allure attachment/failure wording, notifier failure message, and run output summaries.
- Conversion/import tests should assert generated YAML uses `check`.
- Documentation/skill checks should search for remaining user-facing `validate` examples and allow only explicit migration warnings.
- Prior test patterns to follow include existing YAML loader diagnostics tests, quick request CLI tests, Step Lifecycle/Step Outcome tests, run output tests, and report tests.
- Full regression should use the shared virtual environment commands already documented in repository guidelines.

## Out of Scope

- Changing comparator names.
- Changing response body expression syntax.
- Changing `extract`, `export`, `response.save_body_to`, hooks, repeat, skip, invoke, sleep, or request semantics.
- Changing `drun check` command name.
- Adding a compatibility mode for legacy `validate`.
- Adding an automatic fixer for `validate` to `check`.
- Changing environment loading, persistence, or secret masking behavior.
- Changing release automation or local packaging process.
- Adding new runtime dependencies.

## Further Notes

- The key product decision is that short field naming matters more than avoiding the `drun check` / YAML `check` naming overlap.
- The accepted distinction is: `drun check` checks YAML authoring errors; Step `check` checks HTTP response results.
- This PRD intentionally replaces both old public language families: `validate` in inputs and `asserts` in outputs.
- Because report schema changes are included, downstream report consumers must treat this as a breaking release.
- GitHub issue publication is blocked in this local environment because GitHub CLI and `GITHUB_TOKEN` were not available. This Markdown file is the publishable PRD artifact and is labeled `ready-for-agent`.

---
description: Plan a feature or refactoring — research existing code, break down tasks, propose implementation order
argument-hint: "<what-to-plan>"
---

I need a detailed implementation plan for: $@

Before writing the plan, please:

1. **Research** — read the relevant source files, tests, and existing patterns in this project
2. **Break down** — split into atomic, independently verifiable tasks
3. **Order** — respect dependencies, keep each task self-contained
4. **Verify** — for each task, specify exactly how to confirm it works (test command, expected output, etc.)

Output the plan as a Markdown checklist. Each task should include:
- Files to create/modify
- Concrete action description
- Verification step
- Estimated complexity (S/M/L)

Do not start implementing until I approve the plan.
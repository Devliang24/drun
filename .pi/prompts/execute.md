---
description: Execute a plan task-by-task with atomic git commits and verification at each step
argument-hint: "<plan-file-or-task>"
---

Execute the plan in $@ following these rules:

1. **Read first** — understand the current state before making changes
2. **One task at a time** — complete and verify each task before moving to the next
3. **Atomic commits** — each task gets its own conventional commit (feat/fix/refactor/test/chore)
4. **Verify** — run the verification step for each task; stop if it fails
5. **Report** — after each task, summarize what was done and the commit hash

If a task can't be completed, report the blocker and stop. Do not force through broken changes.
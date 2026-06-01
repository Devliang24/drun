---
name: gsd-execute
description: Execute a plan task-by-task with atomic commits. Use when user says "execute the plan", "implement this plan", or after planning is approved.
---

# GSD-Inspired Execution Skill

Use this skill after a plan has been approved in `.planning/phases/PLAN-*.md`.

## Workflow

### Step 1: Load the Plan

Read the plan file. If the user hasn't specified which plan, list available plans:

```bash
ls .planning/phases/PLAN-*.md
```

### Step 2: Execute Tasks in Order

For each task in the plan:

1. **Read relevant files** — understand the current state before changing
2. **Make the change** — use `edit` for precise changes, `write` only for new files
3. **Verify** — run the verification step specified in the plan
4. **Commit** — atomic commit per task:

```bash
git add {changed-files}
git commit -m "{type}({scope}): {description}"
```

Use conventional commits:
- `feat(scope): description` for new features
- `fix(scope): description` for bug fixes
- `refactor(scope): description` for refactoring
- `test(scope): description` for test additions
- `chore(scope): description` for tooling/build

### Step 3: Post-Execution Checks

After all tasks are done:

1. Run the full test suite
2. Check for linting issues
3. Verify no regressions

### Step 4: Update State

If `.planning/STATE.md` exists, update the current position.

### Step 5: Report

Summarize what was done:

```
## Execution Summary

| Task | Status | Commit |
|------|--------|--------|
| Task 1 | ✓ | abc1234 |
| Task 2 | ✓ | def5678 |

Tests: {passed}/{total} passed
```

### Important Rules

- **Never skip verification** — if a verify step fails, fix before continuing
- **One commit per task** — atomic, revertible
- **Stop on failure** — if a task can't be completed, report the blocker, don't force through
- **Ask before destructive changes** — confirm before deleting files, changing schemas, etc.
---
name: gsd-plan
description: Create a detailed implementation plan for a task — research, break down, verify. Use when user says "plan this", "make a plan", or before starting complex work.
---

# GSD-Inspired Planning Skill

Use this skill when the user asks you to plan a feature, refactoring, or complex change before implementing it.

## Workflow

### Step 1: Gather Context

Before planning, read these files if they exist:

- `.planning/PROJECT.md` — project vision and constraints
- `.planning/REQUIREMENTS.md` — scoped requirements
- `.planning/ROADMAP.md` — phase breakdown
- `.planning/STATE.md` — current position and decisions
- `AGENTS.md` — project conventions

If `.planning/` doesn't exist, create it:

```bash
mkdir -p .planning
```

### Step 2: Research

Before writing the plan, investigate:

1. **Existing code** — read relevant source files to understand current state
2. **Tests** — check existing tests for patterns and coverage
3. **Dependencies** — verify no conflicting changes

### Step 3: Write the Plan

Create `.planning/phases/PLAN-{task-slug}.md` with:

```markdown
# Plan: {task-name}

## Goal
One sentence describing what this plan achieves.

## Context
- Relevant files: {paths}
- Related requirements: {REQ-IDs}
- Decisions from STATE.md: {key decisions}

## Tasks

### Task 1: {name}
**Files:** {paths}
**Action:** {what to do, concretely}
**Verify:** {how to confirm it works}

### Task 2: {name}
...

## Verification
- [ ] All tests pass
- [ ] New tests cover the change
- [ ] Code follows project conventions
- [ ] No regressions in related areas
```

### Step 4: Verify the Plan

Check the plan against these dimensions:

1. **Completeness** — does it cover all requirements?
2. **Minimality** — is each task as small as possible?
3. **Order** — are dependencies respected?
4. **Testability** — does each task have a clear verify step?

### Step 5: Get Approval

Present the plan to the user. Do not start implementing until they approve.
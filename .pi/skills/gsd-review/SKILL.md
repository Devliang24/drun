---
name: gsd-review
description: Review code for bugs, security issues, and code quality problems. Use when user says "review this", "code review", or after implementation is done.
---

# GSD-Inspired Code Review Skill

Use this skill to review code changes systematically.

## Workflow

### Step 1: Determine Scope

If the user doesn't specify what to review, check git:

```bash
git diff --name-only HEAD~1
```

Or review staged changes:

```bash
git diff --cached --name-only
```

### Step 2: Review Each File

For each changed file, check:

1. **Bugs**
   - Null/undefined handling
   - Edge cases (empty input, boundary values)
   - Async error handling (try/catch, promise rejections)
   - Race conditions
   - Off-by-one errors

2. **Security**
   - Input validation
   - Path traversal
   - Shell injection
   - Secret/credential exposure
   - SQL injection (if applicable)

3. **Code Quality**
   - Naming clarity
   - Function length (keep small)
   - Duplication
   - Dead code
   - Missing type annotations
   - Error messages (are they helpful?)

4. **Testing**
   - New code has tests
   - Edge cases covered
   - Mocking is appropriate
   - Tests are readable

5. **Performance**
   - Unnecessary allocations
   - N+1 queries
   - Blocking operations in async context
   - Large in-memory operations

### Step 3: Write Review

Format findings as:

```markdown
## Code Review: {scope}

### Findings

| # | Severity | File | Line | Issue | Fix |
|---|----------|------|------|-------|-----|
| 1 | HIGH | x.py | 42 | ... | ... |

### Summary
- HIGH: {count}
- MEDIUM: {count}
- LOW: {count}
- INFO: {count}
```

### Step 4: Fix Critical Issues

For HIGH severity findings, offer to fix them immediately. For MEDIUM and below, flag them but let the user decide.

### Severity Guidelines

- **HIGH**: Security vulnerability, data loss, crash, incorrect behavior
- **MEDIUM**: Performance issue, missing error handling, test gap
- **LOW**: Style inconsistency, minor duplication, unclear naming
- **INFO**: Suggestions, alternative approaches, documentation
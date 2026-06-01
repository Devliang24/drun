---
description: Review recent changes for bugs, security issues, code quality, and test coverage
argument-hint: "[scope — files, commit range, or leave empty for recent changes]"
---

Review the following changes for:

1. **Bugs** — null handling, edge cases, async errors, race conditions, off-by-one
2. **Security** — input validation, injection, path traversal, secret exposure
3. **Code quality** — naming, function length, duplication, dead code, type safety
4. **Testing** — coverage of new code, edge cases, mock correctness
5. **Performance** — unnecessary allocations, N+1 queries, blocking ops

Format findings as a table with Severity (HIGH/MEDIUM/LOW/INFO), File, Line, Issue, and Fix. For HIGH severity, offer to fix immediately.

Scope: $@
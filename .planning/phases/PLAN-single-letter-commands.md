# Plan: All commands use single-letter abbreviations

## Goal
Rename every Drun CLI subcommand to a single-letter abbreviation, matching the current `q` / `r` / `s` style. Breaking change, no long-name compatibility.

## Context
- **Relevant files**: `drun/cli.py` (all `@app.command` declarations, `_DrunRootGroup`)
- **Related tests**: `tests/test_cli_help_width.py` (asserts long command names in help output), plus many other tests that invoke `drun <cmd> ...`
- **Current state**: 10 commands, 2 with hidden short aliases
  - `init`, `run` (alias `r`), `check`, `fix`, `tags`, `q`, `convert`, `convert-openapi`, `export` (sub-app), `server` (alias `s`)
- **Constraints** (from prior user decisions):
  - No silent fallback, no auto-rename
  - All user-visible references must update: CLI, docs, skill, site, tests
  - Strict, explicit, breaking

## Open design questions (need user decision before Task 1)

### Q1. Letter mapping
Current scheme is 10 commands → 10 letters. Proposed mapping:

| Current | Proposed | Reason |
|---------|----------|--------|
| `init` | `i` | obvious |
| `run` | `r` | already aliased |
| `check` | `c` | obvious |
| `fix` | `f` | obvious |
| `tags` | `t` | obvious |
| `q` | `q` | already 1-letter |
| `export` | `e` | obvious |
| `server` | `s` | already aliased |
| `convert` | `o` | "cOnvert" — first letter conflicts with `check` |
| `convert-openapi` | `w` | sWagger / opena**W** (or `k` for opeNapi) |

Conflicts: `c`=check vs `c`=convert (resolved: `o`=convert)
- **Recommendation A**: First unique letter — `i r c f t q e s o w`
- **Recommendation B**: Mnemonic for clarity — `i r c x g e v q n k`

### Q2. Backward compatibility
- (A) Remove all long names; only single letters accepted. Hidden aliases removed.
- (B) Keep long names as hidden aliases. Both forms work.
- (Recommendation A — matches prior "no compatibility" stance for v8.0.0)

### Q3. `convert` vs `convert-openapi`
Both currently first-letter `c`.
- (A) Keep separate commands with distinct letters: `o`=convert, `w`=openapi
- (B) Merge into one auto-detecting command: `c infile` (detect by extension)
- (Recommendation A — preserves distinct functionality)

### Q4. `export` shape
Currently `drun export curl` is the only subcommand. With single letter:
- (A) Flatten: `drun e` is `export curl` directly. No subcommand.
- (B) Keep group: `drun e` (top-level only exports curl, future-proofed for `e jmeter` etc.)
- (Recommendation B — `e` is the export group, currently has only curl)

### Q5. Subcommand for `export`?
- (A) `drun e` alone means curl
- (B) `drun e curl` required
- (Recommendation A — fewer keystrokes, matches the spirit of single-letter)

## Tasks

### Task 1: Mapping decision (BLOCKS all other tasks)
**Action:** User answers Q1–Q5
**Verify:** Final mapping table confirmed and recorded in STATE.md

### Task 2: Add single-letter command resolution
**Files:** `drun/cli.py`
**Action:** Add a `_DrunRootGroup.resolve_command` override that maps single-letter inputs to the registered long-name command. Long names are no longer registered as commands.
**Verify:** `drun r tcases` runs tests; `drun run` errors with "Unknown command".

### Task 3: Update test_cli_help_width.py and all CLI-invoking tests
**Files:** `tests/test_cli_help_width.py`, plus grep for `["check"]`, `["init"]`, etc. across `tests/`
**Action:** Replace all `runner.invoke(cli.app, ["<long>", ...])` with `["<letter>", ...]`. Update help-text assertions.
**Verify:** `pytest tests/test_cli_help_width.py` passes.

### Task 4: Update docs (README, site, skill, CHANGELOG)
**Files:** `README.md`, `README.zh.md`, `site/src/content.ts`, `site/src/App.tsx`, `drun-usage/references/*.md`, `CHANGELOG.md`
**Action:** Replace all `drun <long>` examples with `drun <letter>`. Add CHANGELOG v8.1.0 entry.
**Verify:** `rg "drun (init|run|check|fix|tags|convert|server|export) " README.md README.zh.md site/ drun-usage/` returns only `letter` forms.

### Task 5: Full regression
**Action:** Run `pytest -q` and manual `drun r -help`, `drun c -help`, etc.
**Verify:** All 152+ tests pass, help output looks clean.

## Verification
- [ ] All tests pass
- [ ] Help output shows only single-letter command names
- [ ] No reference to long command names in user-visible docs
- [ ] CHANGELOG entry added
- [ ] No regressions in `run`, `check`, `fix`, `tags` end-to-end behavior

## Risks
1. **`drun q` collision**: `q` is the only existing single-letter command. All other letters must be uniquely chosen.
2. **Help text length**: Single-letter commands look terse in `--help`. May need to update help formatting.
3. **`q`'s special handling**: `_DrunRootGroup.parse_args` has `args[0] == "q"` logic. Will likely need to stay or be reworked.
4. **User muscle memory**: Existing users will break. CHANGELOG must call this out.

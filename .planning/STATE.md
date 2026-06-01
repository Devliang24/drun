# State: Single-letter commands

## Decisions (Q1–Q5)
- **Q1: A** — First-unique letter mapping
  - `i`=init, `r`=run, `c`=check, `f`=fix, `t`=tags, `q`=q, `e`=export, `s`=server
- **Q2: A** — No backward compat. Long names removed.
- **Q3: B** — Merge `convert` and `convert-openapi` into one auto-detecting command `c`.
  - `c INFILE` detects by extension: `.curl`/`.har`/`.json` → convert; `.yaml`/`.yml` → openapi.
- **Q4: B** — Keep `export` as a group; currently only `curl`.
- **Q5: A** — `drun e` directly invokes `export curl`. No subcommand needed.

## Final mapping
| Letter | Command |
|--------|---------|
| `i` | init |
| `r` | run |
| `c` | check / convert (auto-detect) |
| `f` | fix |
| `t` | tags |
| `q` | quick debug |
| `e` | export curl |
| `s` | server |
| `o` | (reserved, was convert) |
| `w` | (reserved, was convert-openapi) |

## Special: `c`
Currently 9 single-letter commands. Q3=B means `c` is overloaded: `drun c PATH` is `check`, but `drun c INFILE.curl` is `convert`. Need a disambiguation rule.
- **Option 1**: `c PATH` is always check. Convert requires a flag: `c -convert INFILE`.
- **Option 2**: `c` is check by default. Convert invoked as `c INFILE` only when INFILE has `.curl/.har/.json/.yaml/.yml` extension AND no flag.
- **Option 3**: `c` is `check`. Convert gets a different letter, e.g. `o` (was cOnvert).

Q3=B + Option 3 is cleanest: `c`=check, `o`=convert, `w`=openapi. Final mapping:
- `i`=init, `r`=run, `c`=check, `f`=fix, `t`=tags, `q`=quick, `e`=export curl, `s`=server
- `o`=convert (curl/har/json)
- `w`=convert-openapi (yaml)

This preserves 1:1 letter→command, no overloading.

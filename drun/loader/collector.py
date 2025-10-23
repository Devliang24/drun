from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Sequence


def _is_valid_name(path: Path) -> bool:
    name = path.name
    if path.suffix.lower() not in {".yaml", ".yml"}:
        return False
    # Accept files under testcases/ or testsuites/ directories
    parts = {p.lower() for p in path.parts}
    if "testcases" in parts or "testsuites" in parts:
        return True
    # Also accept prefix-based naming convention
    if name.startswith("test_") or name.startswith("suite_"):
        return True
    return False


def discover(paths: Sequence[str | Path]) -> List[Path]:
    found: List[Path] = []
    for p in paths:
        pp = Path(p)
        if pp.is_dir():
            for f in sorted(pp.rglob("*.yml")):
                if _is_valid_name(f):
                    found.append(f)
            for f in sorted(pp.rglob("*.yaml")):
                if _is_valid_name(f):
                    found.append(f)
        elif pp.is_file() and _is_valid_name(pp):
            found.append(pp)
    return found


def match_tags(tags: Iterable[str], expr: str | None) -> bool:
    if not expr:
        return True
    expr = expr.strip()
    tagset = {t.lower() for t in tags}
    # very small boolean expression parser supporting 'and', 'or', 'not', parentheses omitted
    # split by space and evaluate left-to-right with 'and' higher precedence than 'or'
    tokens = expr.lower().replace("(", " ").replace(")", " ").split()
    # convert tokens to booleans
    bools: List[bool] = []
    ops: List[str] = []
    for tok in tokens:
        if tok in {"and", "or", "not"}:
            ops.append(tok)
        else:
            bools.append(tok in tagset)
    # apply 'not'
    i = 0
    while i < len(ops):
        if ops[i] == "not":
            # negate next boolean
            if i < len(bools):
                bools[i] = not bools[i]
            ops.pop(i)
        else:
            i += 1
    # apply 'and'
    i = 0
    while i < len(ops):
        if ops[i] == "and":
            if len(bools) >= 2:
                a = bools.pop(0)
                b = bools.pop(0)
                bools.insert(0, a and b)
            ops.pop(i)
        else:
            i += 1
    # apply 'or'
    res = False
    for b in bools:
        res = res or b
    return res

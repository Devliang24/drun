from __future__ import annotations

import re
from typing import Any, Callable, Dict, Tuple


def _len(x: Any) -> int:
    try:
        return len(x)  # type: ignore[arg-type]
    except Exception:
        return 0


def op_eq(a: Any, b: Any) -> bool: return a == b
def op_ne(a: Any, b: Any) -> bool: return a != b
def op_contains(a: Any, b: Any) -> bool: return b in a if a is not None else False
def op_not_contains(a: Any, b: Any) -> bool: return b not in a if a is not None else True
def op_regex(a: Any, b: Any) -> bool: return bool(re.search(str(b), str(a or "")))
def op_lt(a: Any, b: Any) -> bool: return a < b
def op_le(a: Any, b: Any) -> bool: return a <= b
def op_gt(a: Any, b: Any) -> bool: return a > b
def op_ge(a: Any, b: Any) -> bool: return a >= b
def op_len_eq(a: Any, b: Any) -> bool: return _len(a) == int(b)
def op_in(a: Any, b: Any) -> bool: return a in b if b is not None else False
def op_not_in(a: Any, b: Any) -> bool: return a not in b if b is not None else True


OPS: Dict[str, Callable[[Any, Any], bool]] = {
    "eq": op_eq,
    "ne": op_ne,
    "contains": op_contains,
    "not_contains": op_not_contains,
    "regex": op_regex,
    "lt": op_lt,
    "le": op_le,
    "gt": op_gt,
    "ge": op_ge,
    "len_eq": op_len_eq,
    "in": op_in,
    "not_in": op_not_in,
}


def compare(comparator: str, actual: Any, expect: Any) -> Tuple[bool, str | None]:
    fn = OPS.get(comparator)
    if not fn:
        return False, f"Unknown comparator: {comparator}"
    try:
        res = fn(actual, expect)
        return bool(res), None
    except Exception as e:
        return False, f"Comparator error: {e}"


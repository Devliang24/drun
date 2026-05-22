from __future__ import annotations

from typing import Any, List
import re
from pydantic import BaseModel


class Check(BaseModel):
    """Normalized check item: comparator(check, expect)."""

    check: Any
    comparator: str
    expect: Any


def normalize_checks(items: List[Any]) -> List[Check]:
    out: List[Check] = []
    for it in items or []:
        if isinstance(it, Check):
            out.append(it)
            continue
        if isinstance(it, dict):
            if len(it) != 1:
                raise ValueError(f"Check dict must have exactly one comparator key: {it!r}")
            comparator, payload = next(iter(it.items()))
            if not isinstance(payload, (list, tuple)) or len(payload) != 2:
                raise ValueError(f"Check payload must be a list of [check, expect]: {payload!r}")
            check, expect = payload
            # Disallow order-agnostic tricks using JMESPath sort/sort_by in check side.
            if isinstance(check, str):
                s = check.strip()
                if re.search(r"\bsort_by\s*\(|\bsort\s*\(", s):
                    raise ValueError("Order-agnostic comparison is disabled: 'sort'/'sort_by' are not allowed in checks. Use explicit map alignment or multiple contains.")
            out.append(Check(check=check, comparator=str(comparator), expect=expect))
            continue
        raise ValueError(f"Invalid check item: {it!r}")
    return out

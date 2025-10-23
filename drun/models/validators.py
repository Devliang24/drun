from __future__ import annotations

from typing import Any, List
from pydantic import BaseModel


class Validator(BaseModel):
    """Normalized validator item: comparator(check, expect)."""
    check: Any
    comparator: str
    expect: Any


def normalize_validators(items: List[Any]) -> List[Validator]:
    out: List[Validator] = []
    for it in items or []:
        if isinstance(it, Validator):
            out.append(it)
            continue
        if isinstance(it, dict):
            if len(it) != 1:
                raise ValueError(f"Validator dict must have exactly one comparator key: {it!r}")
            comparator, payload = next(iter(it.items()))
            if not isinstance(payload, (list, tuple)) or len(payload) != 2:
                raise ValueError(f"Validator payload must be a list of [check, expect]: {payload!r}")
            check, expect = payload
            out.append(Validator(check=check, comparator=str(comparator), expect=expect))
            continue
        raise ValueError(f"Invalid validator item: {it!r}")
    return out

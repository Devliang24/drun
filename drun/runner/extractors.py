from __future__ import annotations

from typing import Any
import jmespath


def extract_from_body(body: Any, expr: str) -> Any:
    if body is None:
        return None
    try:
        return jmespath.search(expr, body)
    except Exception:
        return None


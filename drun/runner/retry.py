"""Retry executor for HTTP requests.

Extracted from ``drun/runner/step_lifecycle.py`` to keep the retry policy
(self-contained exponential backoff) testable in isolation.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional


def retry_execute(
    *,
    execute_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    request: Dict[str, Any],
    retry: int = 0,
    retry_backoff: float = 0.5,
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Execute *execute_fn(request)* with exponential-backoff retry.

    Returns ``(response_dict | None, error_string | None)``.
    """
    max_attempts = max(retry, 0)
    last_error: Optional[str] = None

    for attempt in range(max_attempts + 1):
        try:
            resp_obj = execute_fn(request)
            return resp_obj, None
        except Exception as e:
            last_error = str(e)
            if attempt >= max_attempts:
                break
            backoff = min(retry_backoff * (2 ** attempt), 2.0)
            time.sleep(backoff)

    return None, last_error
from __future__ import annotations

import shlex
from typing import Any, Dict


def to_curl(method: str, url: str, *, headers: Dict[str, str] | None = None, data: Any | None = None) -> str:
    """Build a curl command string.

    - Uses --data-raw for request body to keep payload untouched.
    - Pretty prints JSON body with indent=2 when data is dict/list for readability.
    """
    parts = ["curl", "-X", method.upper(), shlex.quote(url)]
    # Prepare headers (case-insensitive handling)
    hdrs: Dict[str, str] = dict(headers or {})
    has_ct = any(k.lower() == "content-type" for k in hdrs.keys())
    if data is not None and not has_ct:
        is_json_like = isinstance(data, (dict, list))
        if not is_json_like and isinstance(data, str):
            s = data.strip()
            is_json_like = s.startswith("{") or s.startswith("[")
        if is_json_like:
            hdrs["Content-Type"] = "application/json"
    for k, v in hdrs.items():
        parts += ["-H", shlex.quote(f"{k}: {v}")]
    if data is not None:
        if isinstance(data, (dict, list)):
            import json
            payload = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            payload = str(data)
        # Prefer --data-raw to avoid implicit transformations
        parts += ["--data-raw", shlex.quote(payload)]
    return " ".join(parts)

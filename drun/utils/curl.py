from __future__ import annotations

import shlex
from typing import Any, Dict


def to_curl(method: str, path: str, *, headers: Dict[str, str] | None = None, data: Any | None = None) -> str:
    """Build a curl command string with multi-line formatting.

    - Uses --data-raw for request body to keep payload untouched.
    - Pretty prints JSON body with indent=2 when data is dict/list for readability.
    - Formats output with each parameter on a separate line using backslash continuation.
    """
    lines = ["curl \\"]
    
    # Method and URL
    lines.append(f"  -X {method.upper()} \\")
    lines.append(f"  {shlex.quote(path)} \\")
    
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
    
    # Headers (each on separate line)
    for k, v in hdrs.items():
        lines.append(f"  -H {shlex.quote(f'{k}: {v}')} \\")
    
    # Data (if exists)
    if data is not None:
        if isinstance(data, (dict, list)):
            import json
            payload = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            payload = str(data)
        # Last line without backslash
        lines.append(f"  --data-raw {shlex.quote(payload)}")
    else:
        # Remove trailing backslash from last line
        lines[-1] = lines[-1].rstrip(' \\')
    
    return '\n'.join(lines)

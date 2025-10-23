from __future__ import annotations

from typing import Any, Dict

SENSITIVE_KEYS = {"authorization", "set-cookie", "password", "access_token", "token"}


def mask_headers(headers: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in (headers or {}).items():
        if k.lower() in SENSITIVE_KEYS:
            out[k] = "***"
        else:
            out[k] = v
    return out


def mask_body(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: ("***" if k.lower() in SENSITIVE_KEYS else mask_body(v)) for k, v in data.items()}
    elif isinstance(data, list):
        return [mask_body(v) for v in data]
    else:
        return data


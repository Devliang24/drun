from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple
import re
from urllib.parse import urlparse, parse_qsl

from .base import ImportedCase, ImportedStep


_PM_PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z0-9_.\-]+)\s*\}\}")


def _sanitize_var_name(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_]", "_", str(name or "").strip())
    if not s:
        s = "var"
    if s[0].isdigit():
        s = f"v_{s}"
    return s


def _replace_placeholders(text: str, name_map: Dict[str, str]) -> str:
    if not isinstance(text, str) or not text:
        return text
    def _sub(m: re.Match) -> str:
        orig = m.group(1)
        key = name_map.get(orig, _sanitize_var_name(orig))
        return f"${key}"
    return _PM_PLACEHOLDER_RE.sub(_sub, text)


def _pm_headers(arr: List[Dict[str, Any]] | None) -> Dict[str, str] | None:
    if not arr:
        return None
    out: Dict[str, str] = {}
    for h in arr:
        k = h.get("key")
        v = h.get("value")
        if k and v is not None:
            out[str(k)] = str(v)
    return out or None


def _pm_url_parts(uobj: Any) -> tuple[Optional[str], str, Dict[str, Any] | None]:
    # Return (base_url, path_or_full, params)
    if isinstance(uobj, str):
        # raw string may include placeholders like {{base_url}}
        # Best effort: if it looks like absolute URL, parse; otherwise treat as path
        if _PM_PLACEHOLDER_RE.search(uobj):
            return None, uobj, None
        u = urlparse(uobj)
        base = f"{u.scheme}://{u.netloc}" if (u.scheme and u.netloc) else None
        path = u.path or "/"
        q = dict(parse_qsl(u.query, keep_blank_values=True)) or None
        return base, path, q
    if isinstance(uobj, dict):
        raw = uobj.get("raw")
        if raw:
            return _pm_url_parts(raw)
        protocol = uobj.get("protocol")
        host = uobj.get("host")
        if isinstance(host, list):
            host = ".".join(host)
        base = f"{protocol}://{host}" if protocol and host else None
        path_list = uobj.get("path") or []
        path = "/" + "/".join(str(x) for x in path_list) if path_list else "/"
        params = None
        if uobj.get("query"):
            params = {q.get("key"): q.get("value") for q in uobj["query"] if q.get("key")}
        return base, path, params
    return None, "/", None


def _parse_postman_env(env_text: Optional[str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Return (original_name -> value, original_name -> sanitized_name)."""
    if not env_text:
        return {}, {}
    try:
        obj = json.loads(env_text)
    except Exception:
        return {}, {}
    raw: Dict[str, str] = {}
    items = obj.get("values") or obj.get("variables") or []
    if isinstance(items, list):
        for it in items:
            if not isinstance(it, dict):
                continue
            k = it.get("key") or it.get("name")
            v = it.get("value")
            if k and v is not None and (it.get("enabled", True) is True):
                raw[str(k)] = str(v)
    name_map = {k: _sanitize_var_name(k) for k in raw.keys()}
    return raw, name_map


def _replace_in_value(val: Any, name_map: Dict[str, str]) -> Any:
    if isinstance(val, str):
        return _replace_placeholders(val, name_map)
    if isinstance(val, list):
        return [_replace_in_value(v, name_map) for v in val]
    if isinstance(val, dict):
        return {k: _replace_in_value(v, name_map) for k, v in val.items()}
    return val


def _map_postman_auth(auth_obj: Any, name_map: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str] | None]:
    """Return (headers_update, auth_dict)."""
    if not isinstance(auth_obj, dict):
        return {}, None
    typ = (auth_obj.get("type") or "").lower()
    if not typ:
        return {}, None
    if typ == "bearer":
        token = None
        arr = auth_obj.get("bearer") or []
        if isinstance(arr, list):
            for it in arr:
                if isinstance(it, dict) and (it.get("key") == "token" or it.get("type") == "string"):
                    token = it.get("value")
                    break
        if isinstance(token, str):
            token = _replace_placeholders(token, name_map)
        return {}, {"type": "bearer", "token": token or ""}
    if typ == "basic":
        us = pw = ""
        arr = auth_obj.get("basic") or []
        if isinstance(arr, list):
            for it in arr:
                if isinstance(it, dict):
                    if it.get("key") == "username":
                        us = _replace_placeholders(str(it.get("value") or ""), name_map)
                    if it.get("key") == "password":
                        pw = _replace_placeholders(str(it.get("value") or ""), name_map)
        return {}, {"type": "basic", "username": us, "password": pw}
    if typ == "apikey":
        arr = auth_obj.get("apikey") or []
        hdrs: Dict[str, str] = {}
        if isinstance(arr, list):
            k = v = pos = None
            for it in arr:
                if isinstance(it, dict):
                    if it.get("key") == "key":
                        k = it.get("value")
                    if it.get("key") == "value":
                        v = it.get("value")
                    if it.get("key") == "in":
                        pos = it.get("value")
            if (pos or "header").lower() == "header" and k and v is not None:
                hdrs[str(k)] = _replace_placeholders(str(v), name_map)
        return hdrs, None
    return {}, None


def parse_postman(
    text: str,
    *,
    case_name: Optional[str] = None,
    base_url: Optional[str] = None,
    env_text: Optional[str] = None,
) -> ImportedCase:
    data = json.loads(text)
    name = case_name or (data.get("info", {}).get("name") if isinstance(data, dict) else None) or "Imported Postman"
    steps: List[ImportedStep] = []
    base_guess: Optional[str] = None

    env_raw, name_map = _parse_postman_env(env_text)
    variables: Dict[str, Any] = { _sanitize_var_name(k): v for k, v in env_raw.items() }

    def visit(items: List[Dict[str, Any]]):
        nonlocal base_guess
        for it in items or []:
            if "item" in it and isinstance(it["item"], list):
                visit(it["item"])  # folder
                continue
            req = it.get("request") or {}
            method = (req.get("method") or "GET").upper()
            url_obj = req.get("url")
            b, path, params = _pm_url_parts(url_obj)
            if not base_guess and b:
                base_guess = b
            # Replace placeholders in path and params if they are strings
            if isinstance(path, str):
                path = _replace_placeholders(path, name_map)
            if isinstance(params, dict):
                params = {k: _replace_placeholders(str(v), name_map) for k, v in params.items()}

            headers = _pm_headers(req.get("header")) or {}
            headers = {k: _replace_placeholders(v, name_map) for k, v in headers.items()}

            add_headers: Dict[str, str] = {}
            auth_dict: Dict[str, str] | None = None
            if req.get("auth"):
                add_headers, auth_dict = _map_postman_auth(req.get("auth"), name_map)
                headers.update(add_headers)

            body = None
            data_raw = None
            body_obj = req.get("body") or {}
            if body_obj.get("mode") == "raw":
                data_raw = body_obj.get("raw")
                if isinstance(data_raw, str):
                    # try replace placeholders then parse JSON
                    replaced = _replace_placeholders(data_raw, name_map)
                    try:
                        body = json.loads(replaced)
                        data_raw = None
                    except Exception:
                        data_raw = replaced

            step_name = it.get("name") or f"{method} {path}"
            steps.append(
                ImportedStep(name=step_name, method=method, url=path, params=params, headers=headers or None, body=body, data=data_raw, auth=auth_dict)
            )

    visit(data.get("item") or [])

    # Base URL from env if not provided or guessed
    final_base = base_url or base_guess
    for k in ("base_url", "BASE_URL", "baseUrl"):
        if not final_base and k in env_raw:
            final_base = env_raw[k]
            break

    return ImportedCase(name=name, base_url=final_base, steps=steps, variables=variables or None)

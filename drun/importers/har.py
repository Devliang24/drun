from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
import re
from urllib.parse import urlparse, parse_qsl

from .base import ImportedCase, ImportedStep


def parse_har(
    text: str,
    *,
    case_name: Optional[str] = None,
    base_url: Optional[str] = None,
    exclude_static: bool = False,
    only_2xx: bool = False,
    exclude_pattern: Optional[str] = None,
) -> ImportedCase:
    data = json.loads(text)
    log = data.get("log") or {}
    entries = log.get("entries") or []
    steps: List[ImportedStep] = []
    base_guess: Optional[str] = None
    pat = re.compile(exclude_pattern) if exclude_pattern else None

    def _is_static(mime: str, url: str) -> bool:
        m = (mime or "").lower()
        if any(x in url.lower() for x in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".css", ".js", ".ico", ".woff", ".woff2", ".ttf")):
            return True
        return m.startswith("image/") or m in {"text/css", "application/javascript", "application/x-javascript", "font/woff", "font/woff2", "application/font-woff2"}

    for ent in entries:
        req = ent.get("request") or {}
        resp = ent.get("response") or {}
        method = (req.get("method") or "GET").upper()
        url = req.get("url") or "/"
        u = urlparse(url)
        if u.scheme and u.netloc and not base_guess:
            base_guess = f"{u.scheme}://{u.netloc}"
        path = u.path or "/"
        params = dict(parse_qsl(u.query, keep_blank_values=True)) or None
        headers = {h.get("name"): h.get("value") for h in (req.get("headers") or []) if h.get("name")}
        # filters
        if only_2xx:
            status = int(resp.get("status") or 0)
            if status < 200 or status >= 300:
                continue
        mime = (resp.get("content", {}) or {}).get("mimeType") or ""
        if exclude_static and _is_static(mime, url):
            continue
        if pat and (pat.search(url) or (isinstance(mime, str) and pat.search(mime))):
            continue
        body = None
        data_raw = None
        postData = req.get("postData") or {}
        if postData:
            mime = (postData.get("mimeType") or "").split(";")[0]
            text = postData.get("text")
            if text:
                if mime == "application/json":
                    try:
                        body = json.loads(text)
                    except Exception:
                        data_raw = text
                else:
                    data_raw = text

        name = f"{method} {path}"
        steps.append(ImportedStep(name=name, method=method, url=path, params=params, headers=headers or None, body=body, data=data_raw))

    return ImportedCase(name=case_name or "Imported HAR", base_url=base_url or base_guess, steps=steps)

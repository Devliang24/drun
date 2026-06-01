from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
import yaml

from .base import ImportedCase, ImportedStep, resolve_schema_ref, sample_from_schema


def _load_spec(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        return yaml.safe_load(text)


def parse_openapi(
    text: str,
    *,
    case_name: Optional[str] = None,
    base_url: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> ImportedCase:
    data = _load_spec(text)
    name = case_name or (data.get("info", {}).get("title") if isinstance(data, dict) else None) or "Imported OpenAPI"
    steps: List[ImportedStep] = []
    base_guess: Optional[str] = None
    components = data.get("components") if isinstance(data, dict) else {}

    # servers -> base_url
    servers = data.get("servers") or []
    if isinstance(servers, list) and servers:
        url = servers[0].get("url") if isinstance(servers[0], dict) else None
        if isinstance(url, str):
            base_guess = url

    allowed_tags = {t.strip() for t in (tags or []) if t and t.strip()}

    paths = data.get("paths") or {}
    for path, item in (paths or {}).items():
        if not isinstance(item, dict):
            continue
        for method, op in item.items():
            m = str(method).upper()
            if m not in {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}:
                continue
            if allowed_tags:
                op_tags = set(op.get("tags") or []) if isinstance(op, dict) else set()
                if not (op_tags & allowed_tags):
                    continue
            step_name = op.get("summary") or op.get("operationId") or f"{m} {path}"
            headers = {"Accept": "application/json"}
            body = None
            # Try to build a sample JSON body if requestBody has example
            rb = op.get("requestBody") if isinstance(op, dict) else None
            if isinstance(rb, dict):
                content = rb.get("content") or {}
                appjson = content.get("application/json") or {}
                ex = appjson.get("example") or (appjson.get("examples", {}) or {}).get("default", {}).get("value")
                if ex is not None:
                    body = ex
                else:
                    schema_obj = appjson.get("schema")
                    if schema_obj:
                        body = sample_from_schema(schema_obj, data)
            steps.append(ImportedStep(name=step_name, method=m, path=path, headers=headers, body=body))

    fallback_base = base_url or base_guess or "http://localhost:8000"
    return ImportedCase(name=name, base_url=fallback_base, steps=steps)

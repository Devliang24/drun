from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
import yaml

from .base import ImportedCase, ImportedStep


def _resolve_ref(ref: str, root: Dict[str, Any]) -> Dict[str, Any] | None:
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return None
    parts = ref[2:].split("/")
    node: Any = root
    for part in parts:
        if not isinstance(node, dict):
            return None
        node = node.get(part)
        if node is None:
            return None
    if isinstance(node, dict):
        return node
    return None


def _sample_from_schema(schema: Dict[str, Any] | None, root: Dict[str, Any], depth: int = 0) -> Any:
    if not schema or depth > 5:
        return None
    if "example" in schema:
        return schema["example"]
    if "$ref" in schema:
        resolved = _resolve_ref(schema.get("$ref"), root)
        if resolved is not None:
            return _sample_from_schema(resolved, root, depth + 1)
    schema_type = schema.get("type")
    if schema_type == "object":
        props = schema.get("properties") or {}
        required = schema.get("required") or []
        result: Dict[str, Any] = {}
        for key, subschema in props.items():
            val = _sample_from_schema(subschema, root, depth + 1)
            if val is None and key in required:
                val = "string"
            if val is not None:
                result[key] = val
        return result or {}
    if schema_type == "array":
        item_schema = schema.get("items") or {}
        sample_item = _sample_from_schema(item_schema, root, depth + 1)
        return [sample_item] if sample_item is not None else []
    if schema_type == "integer":
        return schema.get("default", 0)
    if schema_type == "number":
        return schema.get("default", 0)
    if schema_type == "boolean":
        return schema.get("default", True)
    # string or fallback
    return schema.get("default") or schema.get("pattern") or "string"


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
                        body = _sample_from_schema(schema_obj, data)
            steps.append(ImportedStep(name=step_name, method=m, path=path, headers=headers, body=body))

    fallback_base = base_url or base_guess or "http://localhost:8000"
    return ImportedCase(name=name, base_url=fallback_base, steps=steps)

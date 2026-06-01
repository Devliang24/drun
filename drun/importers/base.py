from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ImportedStep:
    name: str
    method: str
    path: str  # absolute or path
    params: Dict[str, Any] | None = None
    headers: Dict[str, str] | None = None
    body: Any | None = None
    data: Any | None = None
    files: Any | None = None
    auth: Dict[str, str] | None = None  # {type: basic|bearer, ...}


@dataclass
class ImportedCase:
    name: str
    base_url: Optional[str] = None
    steps: List[ImportedStep] = field(default_factory=list)
    variables: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Shared schema utilities — used by OpenAPI / JSON Schema importers
# ---------------------------------------------------------------------------


def resolve_schema_ref(ref: str, root: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Resolve a ``$ref`` JSON pointer (``#/components/schemas/Foo``) within *root*."""
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
    return node if isinstance(node, dict) else None


def sample_from_schema(
    schema: Optional[Dict[str, Any]],
    root: Dict[str, Any],
    *,
    depth: int = 0,
) -> Any:
    """Generate a sample JSON value from an OpenAPI / JSON Schema object."""
    if not schema or depth > 5:
        return None
    if "example" in schema:
        return schema["example"]
    if "$ref" in schema:
        resolved = resolve_schema_ref(schema["$ref"], root)
        if resolved is not None:
            return sample_from_schema(resolved, root, depth=depth + 1)
    schema_type = schema.get("type")
    if schema_type == "object":
        props = schema.get("properties") or {}
        required = schema.get("required") or []
        result: Dict[str, Any] = {}
        for key, subschema in props.items():
            val = sample_from_schema(subschema, root, depth=depth + 1)
            if val is None and key in required:
                val = "string"
            if val is not None:
                result[key] = val
        return result or {}
    if schema_type == "array":
        item_schema = schema.get("items") or {}
        sample_item = sample_from_schema(item_schema, root, depth=depth + 1)
        return [sample_item] if sample_item is not None else []
    if schema_type == "integer":
        return schema.get("default", 0)
    if schema_type == "number":
        return schema.get("default", 0)
    if schema_type == "boolean":
        return schema.get("default", True)
    # string or fallback
    return schema.get("default") or schema.get("pattern") or "string"

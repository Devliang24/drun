from __future__ import annotations

import json
import re
from typing import Any, Dict, List


def run_setup_hooks(
    *,
    names: List[str],
    funcs: Dict[str, Any] | None,
    req: Dict[str, Any],
    variables: Dict[str, Any],
    envmap: Dict[str, Any] | None,
    meta: Dict[str, Any] | None,
    templater: Any,
    log: Any,
    fmt_aligned: Any,
) -> Dict[str, Any]:
    updated: Dict[str, Any] = {}
    fdict = funcs or {}
    env_ctx = envmap or {}
    meta_data = {k: v for k, v in (meta or {}).items() if v is not None}
    hook_ctx: Dict[str, Any] = {
        "request": req,
        "variables": variables,
        "env": env_ctx,
        "step_name": meta_data.get("step_name"),
        "case_name": meta_data.get("case_name"),
        "step_request": meta_data.get("step_request") or req,
        "step_variables": meta_data.get("step_variables") or variables,
        "session_variables": meta_data.get("session_variables") or variables,
        "session_env": meta_data.get("session_env") or env_ctx,
    }
    hook_ctx.update(meta_data)
    for entry in names or []:
        if not isinstance(entry, str):
            raise ValueError(f"Invalid setup hook entry type {type(entry).__name__}; expected string like '${{func(...)}}'")
        text = entry.strip()
        if not text:
            raise ValueError("Invalid empty setup hook entry")
        if not (text.startswith("${") and text.endswith("}")):
            raise ValueError(f"Setup hook must use expression syntax '${{func(...)}}': {entry}")
        m = re.match(r"^\$\{\s*([A-Za-z_][A-Za-z0-9_]*)", text)
        fn_label = f"{m.group(1)}()" if m else text
        if log:
            log.info(f"[HOOK] setup expr -> {fn_label}")
        ret = templater.eval_expr(text, variables, fdict, envmap, extra_ctx=hook_ctx)
        if log:
            if isinstance(ret, (dict, list)):
                formatted = json.dumps(ret, ensure_ascii=False, indent=2)
                log.info(fmt_aligned("HOOK", f"{fn_label} returned", formatted))
            else:
                log.info(f"[HOOK] {fn_label} returned: {ret!r}")
        if isinstance(ret, dict):
            updated.update(ret)
    return updated


def run_teardown_hooks(
    *,
    names: List[str],
    funcs: Dict[str, Any] | None,
    resp: Dict[str, Any],
    variables: Dict[str, Any],
    envmap: Dict[str, Any] | None,
    meta: Dict[str, Any] | None,
    templater: Any,
    log: Any,
    fmt_aligned: Any,
) -> Dict[str, Any]:
    updated: Dict[str, Any] = {}
    fdict = funcs or {}
    env_ctx = envmap or {}
    meta_data = {k: v for k, v in (meta or {}).items() if v is not None}
    hook_ctx: Dict[str, Any] = {
        "response": resp,
        "variables": variables,
        "env": env_ctx,
        "step_name": meta_data.get("step_name"),
        "case_name": meta_data.get("case_name"),
        "step_response": meta_data.get("step_response") or resp,
        "step_variables": meta_data.get("step_variables") or variables,
        "session_variables": meta_data.get("session_variables") or variables,
        "session_env": meta_data.get("session_env") or env_ctx,
    }
    hook_ctx.update(meta_data)
    for entry in names or []:
        if not isinstance(entry, str):
            raise ValueError(f"Invalid teardown hook entry type {type(entry).__name__}; expected string like '${{func(...)}}'")
        text = entry.strip()
        if not text:
            raise ValueError("Invalid empty teardown hook entry")
        if not (text.startswith("${") and text.endswith("}")):
            raise ValueError(f"Teardown hook must use expression syntax '${{func(...)}}': {entry}")
        m = re.match(r"^\$\{\s*([A-Za-z_][A-Za-z0-9_]*)", text)
        fn_label = f"{m.group(1)}()" if m else text
        if log:
            log.info(f"[HOOK] teardown expr -> {fn_label}")
        ret = templater.eval_expr(text, variables, fdict, envmap, extra_ctx=hook_ctx)
        if log:
            if isinstance(ret, (dict, list)):
                formatted = json.dumps(ret, ensure_ascii=False, indent=2)
                log.info(fmt_aligned("HOOK", f"{fn_label} returned", formatted))
            else:
                log.info(f"[HOOK] {fn_label} returned: {ret!r}")
        if isinstance(ret, dict):
            updated.update(ret)
    return updated

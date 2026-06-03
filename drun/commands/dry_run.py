"""Dry-run plan preview for `drun r -dry-run`.

Renders a side-effect-free preview of test execution plan:
which cases match, how parameters expand, what steps will run.
No HTTP requests, no hooks, no report/output artifacts.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from drun.models.case import Case
from drun.models.step import Step
from drun.templating.engine import TemplateEngine


def _json_truncate(obj: Any, max_chars: int = 200) -> str:
    """JSON-dump an object, truncate if too long."""
    try:
        text = json.dumps(obj, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        text = str(obj)
    if len(text) <= max_chars:
        return text
    keys_hint = ""
    if isinstance(obj, dict):
        keys_hint = f", {len(obj)} keys"
    elif isinstance(obj, list):
        keys_hint = f", {len(obj)} items"
    truncated = text[:max_chars].rstrip()
    return f"{truncated}\n... (truncated{keys_hint}, {len(text)} chars)"


def _format_params(params: Dict[str, Any]) -> str:
    """Format parameter dict as 'key=value, key=value'."""
    if not params:
        return "(none)"
    return ", ".join(f"{k}={v!r}" for k, v in params.items())


def _safe_render(value: Any, variables: Dict[str, Any], envmap: Dict[str, Any] | None = None) -> str:
    """Static-only render: resolve config.variables / CLI vars / params / ENV.

    Does NOT execute user hooks, built-in random/uuid functions, or
    runtime-extracted variables. Unresolved tokens are left as-is.
    """
    if not isinstance(value, str):
        return str(value)

    if "${" not in value and "$" not in value:
        return value

    # Build a minimal context with only ENV and static variables,
    # deliberately excluding BUILTINS and user-defined hook functions.
    engine = TemplateEngine()

    # ENV-like lookup (mimics ENV function without side effects)
    import os as _os

    def _env_lookup(name: str, default: Any = None) -> Any:
        if envmap is not None and name in envmap:
            return envmap[name]
        return _os.environ.get(name, default)

    ctx = {**variables, "ENV": _env_lookup}

    try:
        result = engine.render_value(value, ctx, strict=False)
    except Exception:
        return value

    return str(result) if not isinstance(result, str) else result


def _preview_step(step: Step, global_vars: Dict[str, Any], env_store: Dict[str, Any]) -> str:
    """Render a single step as a human-readable line."""
    indent = "    "
    lines: List[str] = []

    # Merge step-local variables over global
    step_vars: Dict[str, Any] = {**global_vars}
    if step.variables:
        step_vars.update(step.variables)

    # --- Request step ---
    if step.request is not None:
        method = (step.request.method or "GET").upper()
        path_raw = step.request.path or "/"
        path_rendered = _safe_render(path_raw, step_vars, env_store)

        # Build the step header
        repeat_suffix = ""
        if step.repeat and step.repeat != 1:
            repeat_suffix = f" repeat={step.repeat}"
        lines.append(f"{indent}request  {method} {path_rendered}{repeat_suffix}")

        # Headers
        if step.request.headers:
            header_lines: List[str] = []
            for hk, hv in step.request.headers.items():
                rendered = _safe_render(hv, step_vars, env_store)
                header_lines.append(f"{hk}: {rendered}")
            if header_lines:
                lines.append(f"{indent}  headers: {', '.join(header_lines)}")

        # Body (truncated)
        body = getattr(step.request, "body", None)
        if body is not None:
            body_rendered = _safe_render(body, step_vars, env_store)
            body_text = _json_truncate(body, max_chars=200)
            lines.append(f"{indent}  body: {body_text}")

        # Checks
        if step.checks:
            check_parts: List[str] = []
            for chk in step.checks:
                check_parts.append(f"{chk.comparator}({chk.check}, {chk.expect!r})")
            lines.append(f"{indent}  checks: {', '.join(check_parts)}")

        # Extracts
        if step.extract:
            extract_parts: List[str] = []
            for var_name, expr in step.extract.items():
                extract_parts.append(f"{var_name} <= {expr}")
            lines.append(f"{indent}  extracts: {', '.join(extract_parts)}")

        # Unresolved tokens
        unresolved = _collect_unresolved(
            path_raw, step.request.headers, body, step_vars, env_store
        )
        if unresolved:
            lines.append(f"{indent}  <dynamic: {', '.join(sorted(unresolved))}>")

        # Skip marker
        if step.skip:
            skip_val = _safe_render(step.skip, step_vars, env_store) if isinstance(step.skip, str) else str(step.skip)
            lines.append(f"{indent}  skip: {skip_val}")

    # --- Invoke step ---
    elif step.invoke is not None:
        invoke_target = step.invoke
        selectors: List[str] = []
        if step.invoke_case_name:
            selectors.append(f"case={step.invoke_case_name}")
        if step.invoke_case_names:
            selectors.append(f"cases={','.join(step.invoke_case_names)}")
        selector_str = f" ({', '.join(selectors)})" if selectors else ""

        repeat_suffix = ""
        if step.repeat and step.repeat != 1:
            repeat_suffix = f" repeat={step.repeat}"

        lines.append(f"{indent}invoke   {invoke_target}{selector_str}{repeat_suffix}")

    # --- Sleep step ---
    elif step.sleep is not None:
        sleep_val = step.sleep
        sleep_rendered = _safe_render(str(sleep_val), step_vars, env_store)
        lines.append(f"{indent}sleep    {sleep_rendered}ms")

    return "\n".join(lines)


def _collect_unresolved(
    path_raw: str,
    headers: Dict[str, str] | None,
    body: Any,
    variables: Dict[str, Any],
    envmap: Dict[str, Any] | None,
) -> set[str]:
    """Collect template tokens that remain unresolved after static render."""
    import re as _re

    unresolved: set[str] = set()
    engine = TemplateEngine()

    # Build context with only static + ENV
    import os as _os

    def _env_lookup(name: str, default: Any = None) -> Any:
        if envmap is not None and name in envmap:
            return envmap[name]
        return _os.environ.get(name, default)

    ctx = {**variables, "ENV": _env_lookup}

    texts_to_check: List[str] = [path_raw]

    if headers:
        for hv in headers.values():
            texts_to_check.append(str(hv))

    if isinstance(body, str):
        texts_to_check.append(body)
    elif isinstance(body, dict):
        for v in body.values():
            if isinstance(v, str):
                texts_to_check.append(v)

    for text in texts_to_check:
        if not isinstance(text, str):
            continue
        tokens = _re.findall(r"\$\{([^{}]+)\}", text)
        for token in tokens:
            # Try to render; if fails, mark as unresolved
            try:
                engine.render_value(f"${{{token}}}", ctx, strict=False)
            except Exception:
                unresolved.add(token)

    return unresolved


def build_dry_run_plan_text(
    *,
    target: str,
    env_label: str,
    env_file_label: str,
    base_url: str | None,
    files_count: int,
    items: list[tuple[Case, Dict[str, str]]],
    parameterized_items: list[tuple[Case, Dict[str, str], List[Dict[str, Any]]]],
    tag_filter: str | None,
    case_selector: list[str] | None,
    global_vars: Dict[str, Any],
    env_store: Dict[str, Any],
    dry_run_limit: int,
    reveal_secrets: bool,
) -> str:
    """Build the dry-run plan text output."""
    lines: List[str] = []

    # Banner
    lines.append("")
    lines.append("=" * 60)
    lines.append("  DRY RUN")
    lines.append("  No HTTP requests will be sent.")
    lines.append("  Hooks, notifications, reports, snippets, and persist-env are disabled.")
    lines.append("=" * 60)
    lines.append("")

    # Plan header
    lines.append("[PLAN]")
    lines.append(f"Target: {target}")
    lines.append(f"Environment: {env_label}")
    lines.append(f"Env file: {env_file_label}")
    lines.append(f"Base URL: {base_url or '(not set / unresolved)'}")
    lines.append(f"Files: {files_count}")
    lines.append(f"Cases: {len(items)}")

    case_instance_count = sum(len(ps) for _, _, ps in parameterized_items)
    lines.append(f"Case instances: {case_instance_count}")
    lines.append(f"Tag filter: {tag_filter or '(none)'}")
    cs_display = ", ".join(case_selector) if case_selector else "(none)"
    lines.append(f"Case selector: {cs_display}")
    lines.append("")

    # Per-case detail
    for idx, (case, meta, param_sets) in enumerate(parameterized_items, start=1):
        case_name = case.config.name or "Unnamed"
        source_file = meta.get("file", "unknown")
        tags = ", ".join(case.config.tags) if case.config.tags else "(none)"

        lines.append(f"[CASE #{idx}]")
        lines.append(f"Name: {case_name}")
        lines.append(f"Source: {source_file}")
        lines.append(f"Tags: {tags}")
        lines.append(f"Instances: {len(param_sets)}")
        lines.append("")

        display_count = min(len(param_sets), dry_run_limit)
        for i, param_set in enumerate(param_sets[:display_count]):
            lines.append(f"  Instance #{i + 1}")
            lines.append(f"  Params: {_format_params(param_set)}")
            lines.append("")

            # Blend param values into step variables for rendering
            step_vars = {**global_vars, **param_set}
            if case.config.variables:
                step_vars.update(case.config.variables)

            # Steps
            lines.append("  Steps:")
            for si, step in enumerate(case.steps, start=1):
                step_text = _preview_step(step, step_vars, env_store)
                lines.append(f"    {si}. {step_text.strip()}")
            lines.append("")

        if len(param_sets) > dry_run_limit:
            remaining = len(param_sets) - dry_run_limit
            lines.append(
                f"  ... and {remaining} more instance(s). "
                f"Use -dry-run-limit {len(param_sets)} to show all."
            )
            lines.append("")

    # Footer summary
    lines.append("[SUMMARY]")
    lines.append(f"Files: {files_count}")
    lines.append(f"Cases: {len(items)}")
    lines.append(f"Case instances: {case_instance_count}")
    lines.append(f"HTTP requests sent: 0")
    lines.append("")

    return "\n".join(lines)

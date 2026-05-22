from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Dict, List, Tuple

import yaml
from pydantic import ValidationError

from drun.models.case import Case, Suite
from drun.models.config import Config
from drun.models.step import Step
from drun.templating.compat import (
    clean_escaped_template_string,
    escape_template_expressions_in_yaml,
    strip_escaped_template_quotes,
)
from drun.models.checks import normalize_checks
from drun.engine.request_files import RequestFilesError, validate_request_files_shape
from drun.utils.errors import Diagnostic, DiagnosticError, LoadError


EXAMPLE_REQUEST_PATH = """request:
  method: GET
  path: /api/users"""

EXAMPLE_CONFIG_PARAMETERS = """config:
  name: User cases
  parameters:
    - user_id: [1, 2, 3]"""

EXAMPLE_BODY_CHECK = """check:
  - eq: [$.data.id, 1]"""

EXAMPLE_MULTIPART = """request:
  method: POST
  path: /upload
  data:
    biz: profile
  files:
    avatar: ./data/avatar.png"""

EXAMPLE_CASEFLOW = """caseflow:
  - name: Login
    invoke: test_login"""

EXAMPLE_REPEAT = """steps:
  - name: Poll status
    repeat: 3
    request:
      method: GET
      path: /status"""

EXAMPLE_SLEEP = """steps:
  - name: Wait async job
    sleep: 2000"""

EXAMPLE_HOOK = """setup_hooks:
  - ${prepare_data()}"""


def _source_line(raw_text: str | None, line: int | None) -> str | None:
    if raw_text is None or line is None or line < 1:
        return None
    lines = raw_text.splitlines()
    if line > len(lines):
        return None
    return lines[line - 1].rstrip()


def _diagnostic(
    code: str,
    message: str,
    *,
    file: Path | None = None,
    line: int | None = None,
    yaml_path: str | None = None,
    hint: str | None = None,
    example: str | None = None,
    raw_text: str | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        message=message,
        file=str(file) if file is not None else None,
        line=line,
        path=yaml_path,
        hint=hint,
        example=example,
        source_line=_source_line(raw_text, line),
    )


def _raise_diagnostic(diagnostic: Diagnostic) -> None:
    raise DiagnosticError(diagnostic=diagnostic)


def _find_top_level_key_location(raw_text: str | None, key: str) -> int | None:
    if not raw_text:
        return None
    pattern = re.compile(rf"^{re.escape(key)}\s*:")
    for idx, line in enumerate(raw_text.splitlines(), start=1):
        if pattern.match(line):
            return idx
    return None


def _is_suite(doc: Dict[str, Any]) -> bool:
    return "cases" in doc


def _is_caseflow(doc: Dict[str, Any]) -> bool:
    """检测是否为 caseflow 格式的测试套件"""
    return isinstance(doc, dict) and isinstance(doc.get("caseflow"), list)


def strip_escape_quotes(value: str) -> str:
    """Backward-compatible wrapper for template quote stripping."""
    return strip_escaped_template_quotes(value)


def format_variables_multiline(variables: Dict[str, Any], prefix: str, max_line_length: int = 120) -> str:
    """
    Format variables into vertical list display.

    This function creates a clean vertical list where each variable is on its own
    line with consistent 2-space indentation, making it easy to read and scan.

    Args:
        variables: Dictionary of variable name-value pairs
        prefix: The prefix string (e.g., "[CONFIG] variables: ")
        max_line_length: Maximum line length before wrapping (default: 120)
        Note: This parameter is kept for backward compatibility but not used in vertical format

    Returns:
        Multi-line formatted string with each variable on its own line
    """
    if not variables:
        return prefix.rstrip() if prefix.endswith(": ") else prefix

    # Format all variable assignments with escape quotes removed
    var_assignments = [f"{k}: {clean_escaped_template_string(str(v))}" for k, v in variables.items()]

    # Return vertical list format with proper indentation
    # Remove trailing colon/space from prefix if present, then add single colon
    clean_prefix = prefix.rstrip()
    if not clean_prefix.endswith(":"):
        clean_prefix += ":"

    lines = [clean_prefix]
    # Calculate indentation to align with the colon in the prefix
    colon_pos = clean_prefix.find(":")
    if colon_pos != -1:
        # Align variables with the colon position
        indentation = " " * (colon_pos + 1)  # +1 to align after the colon
    else:
        # Fallback to 2-space indentation if no colon found
        indentation = "  "

    for var_assignment in var_assignments:
        lines.append(indentation + var_assignment)

    return "\n".join(lines)



def _normalize_case_dict(d: Dict[str, Any], path: Path | None = None, raw_text: str | None = None) -> Dict[str, Any]:
    dd = dict(d)
    has_top_level_parameters = "parameters" in dd
    # Allow case-level hooks declared inside config as aliases, e.g.:
    # config:
    #   setup_hooks: ["${func()}"]
    #   teardown_hooks: ["${func()}"]
    promoted_from_config: set[str] = set()
    parameters_from_config = False
    if "config" in dd and isinstance(dd["config"], dict):
        if "parameters" in dd["config"]:
            parameters_from_config = True
            dd["parameters"] = dd["config"].pop("parameters")
        for hk_field in ("setup_hooks", "teardown_hooks"):
            if hk_field in dd["config"]:
                items = dd["config"].get(hk_field)
                if items is None:
                    items = []
                if not isinstance(items, list):
                    raise LoadError(f"Invalid config.{hk_field} entry type {type(items).__name__}; expected list of '${{func(...)}}'")
                # check expressions and promote to case-level
                for item in items:
                    if not isinstance(item, str):
                        raise LoadError(f"Invalid {hk_field} entry type {type(item).__name__}; expected string like '${{func(...)}}'")
                    text = item.strip()
                    if not text:
                        raise LoadError(f"Invalid empty {hk_field} entry")
                    if not (text.startswith("${") and text.endswith("}")):
                        raise LoadError(f"Invalid {hk_field} entry '{item}': must use expression syntax '${{func(...)}}'")
                dd[hk_field] = list(items)
                promoted_from_config.add(hk_field)
                # remove from config to avoid model validation issues
                dd["config"].pop(hk_field, None)
        if parameters_from_config and has_top_level_parameters:
            raise LoadError(
                "Invalid duplicate 'parameters': define parameters under 'config.parameters' only."
            )
    if "parameters" in dd and not parameters_from_config:
        raise LoadError(
            "Invalid top-level 'parameters'. Move case parameters under 'config.parameters'."
        )
    if "steps" in dd and isinstance(dd["steps"], list):
        new_steps: List[Dict[str, Any]] = []
        for idx, s in enumerate(dd["steps"]):
            ss = dict(s)
            for legacy_field in ("loop", "foreach"):
                if legacy_field in ss:
                    step_label = str(ss.get("name") or f"steps[{idx + 1}]")
                    raise LoadError(
                        f"Invalid step field '{legacy_field}' in step '{step_label}': "
                        "please migrate to 'repeat'."
                    )
            # Disallow legacy request.json field (no compatibility)
            if isinstance(ss.get("request"), dict) and "json" in ss["request"]:
                step_label = str(ss.get("name") or f"steps[{idx + 1}]")
                # Try to locate the exact line of 'request.json' for better UX
                line_hint = None
                if path is not None and raw_text is not None:
                    loc = _find_request_subfield_location(raw_text, idx, "json")
                    if loc is not None:
                        line_no, line_text = loc
                        line_hint = f"{path}:{line_no}: '{line_text.strip()}'"
                hint = (
                    f"Invalid request field 'json' in {path if path else '<file>'}: step '{step_label}'. "
                    "Use 'body' instead (YAML path: request.json)."
                )
                if line_hint:
                    hint += f"\nHint → {line_hint}"
                raise LoadError(hint)
            if isinstance(ss.get("request"), dict):
                request_obj = ss["request"]
                step_label = str(ss.get("name") or f"steps[{idx + 1}]")
                if request_obj.get("body") is not None and request_obj.get("files") is not None:
                    raise LoadError(
                        f"Invalid request in step '{step_label}': request.body cannot be used with request.files. "
                        "Use request.data for multipart form fields."
                    )
                if request_obj.get("files") is not None:
                    try:
                        validate_request_files_shape(request_obj.get("files"), source="request.files")
                    except RequestFilesError as exc:
                        raise LoadError(f"Invalid request.files in step '{step_label}': {exc}") from exc
            if "check" in ss:
                ss["check"] = [v.model_dump() for v in normalize_checks(ss["check"])]
                # enforce $-only for body checks
                for v in ss["check"]:
                    chk = v.get("check")
                    if isinstance(chk, str) and chk.startswith("body."):
                        raise LoadError(f"Invalid check '{chk}': use '$' syntax e.g. '$.path.to.field'")
            # enforce $-only for extract
            if "extract" in ss and isinstance(ss["extract"], dict):
                for k, ex in ss["extract"].items():
                    if isinstance(ex, str) and ex.startswith("body."):
                        raise LoadError(f"Invalid extract '{ex}' for '{k}': use '$' syntax e.g. '$.path.to.field'")
            # hooks field: enforce "${...}" expression form
            for hk_field in ("setup_hooks", "teardown_hooks"):
                if hk_field in ss and isinstance(ss[hk_field], list):
                    for item in ss[hk_field]:
                        if not isinstance(item, str):
                            raise LoadError(f"Invalid {hk_field} entry type {type(item).__name__}; expected string like \"${{func(...)}}\"")
                        text = item.strip()
                        if not text:
                            raise LoadError(f"Invalid empty {hk_field} entry")
                        if not (text.startswith("${") and text.endswith("}")):
                            raise LoadError(f"Invalid {hk_field} entry '{item}': must use expression syntax \"${{func(...)}}\"")
            new_steps.append(ss)
        dd["steps"] = new_steps
    # Disallow old-style case-level hooks at top-level; allow if just promoted from config
    for hk_field in ("setup_hooks", "teardown_hooks"):
        if hk_field in dd and hk_field not in promoted_from_config:
            raise LoadError(
                f"Invalid top-level '{hk_field}': case-level hooks must be declared under 'config.{hk_field}'."
            )
    return dd


def _parse_yaml_document(path: Path) -> tuple[str, str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
        # Pre-process YAML to escape template expressions that may cause parsing issues
        # When template expressions like ${func(...)} appear in arrays/lists, they may confuse YAML parser
        # We temporarily wrap them in quotes to ensure safe parsing
        processed_raw = escape_template_expressions_in_yaml(raw)
        obj = yaml.safe_load(processed_raw) or {}
    except Exception as e:
        line = None
        mark = getattr(e, "problem_mark", None)
        if mark is not None and getattr(mark, "line", None) is not None:
            line = int(mark.line) + 1
        _raise_diagnostic(
            _diagnostic(
                "DRUN-YAML-001",
                "Failed to parse YAML",
                file=path,
                line=line,
                hint="Fix the YAML syntax before running this file.",
                raw_text=raw if "raw" in locals() else None,
            )
        )
    return raw, processed_raw, obj


def load_yaml_file(path: Path) -> Tuple[List[Case], Dict[str, Any]]:
    raw, processed_raw, obj = _parse_yaml_document(path)
    diagnostics = _collect_common_diagnostics(obj, path, raw)
    if diagnostics:
        _raise_diagnostic(diagnostics[0])

    return _build_cases_from_obj(obj, path, raw)


def collect_yaml_diagnostics(path: Path) -> List[Diagnostic]:
    """Collect authoring diagnostics for a YAML file without stopping at one file."""
    try:
        raw, _processed_raw, obj = _parse_yaml_document(path)
    except LoadError as exc:
        return [exc.diagnostic] if exc.diagnostic else [
            _diagnostic(
                "DRUN-YAML-999",
                str(exc) or "Failed to load YAML",
                file=path,
            )
        ]

    diagnostics = _collect_common_diagnostics(obj, path, raw)
    if diagnostics:
        return diagnostics

    try:
        _build_cases_from_obj(obj, path, raw)
    except LoadError as exc:
        return [exc.diagnostic] if exc.diagnostic else [
            _diagnostic(
                "DRUN-YAML-999",
                str(exc) or "Failed to load YAML",
                file=path,
            )
        ]
    return []


def _build_cases_from_obj(obj: Any, path: Path, processed_raw: str) -> Tuple[List[Case], Dict[str, Any]]:
    if not isinstance(obj, dict):
        _raise_diagnostic(
            _diagnostic(
                "DRUN-YAML-002",
                "YAML root must be a mapping",
                file=path,
                hint="Start the file with `config:` and `steps:` or `caseflow:`.",
                example="config:\n  name: Demo\nsteps: []",
                raw_text=processed_raw,
            )
        )

    cases: List[Case] = []
    # Caseflow format: { config: {name, tags}, caseflow: [ {name, invoke, variables?}, ... ] }
    if _is_caseflow(obj):
        # 解析 config（只取 name 和 tags，不支持 base_url/parameters）
        raw_cfg = obj.get("config") or {}
        suite_cfg = Config(
            name=raw_cfg.get("name", "Unnamed Caseflow"),
            tags=raw_cfg.get("tags", []),
        )
        
        # 将 caseflow 项转换为 invoke steps
        steps: List[Step] = []
        caseflow_items = obj.get("caseflow") or []
        if not isinstance(caseflow_items, list):
            raise LoadError("Invalid caseflow: 'caseflow' must be a list")
        
        for idx, item in enumerate(caseflow_items):
            if not isinstance(item, dict):
                raise LoadError(f"Invalid caseflow item at index {idx}: expected dict")

            for legacy_field in ("loop", "foreach"):
                if legacy_field in item:
                    raise LoadError(
                        f"Invalid caseflow item at index {idx}: field '{legacy_field}' is deprecated. "
                        "Please use 'repeat'."
                    )

            invoke_path = item.get("invoke")
            if not invoke_path:
                raise LoadError(f"Caseflow item at index {idx}: missing 'invoke'")
            
            step_dict = {
                "name": item.get("name", f"Step {idx + 1}"),
                "invoke": invoke_path,
                "variables": item.get("variables", {}),
                "invoke_case_name": item.get("invoke_case_name"),
                "invoke_case_names": item.get("invoke_case_names", []),
                "repeat": item.get("repeat", 1),
            }
            steps.append(Step.model_validate_obj(step_dict))
        
        # 构建虚拟 Case
        virtual_case = Case(
            config=suite_cfg,
            steps=steps,
        )
        cases.append(virtual_case)

    elif _is_suite(obj):
        # Legacy inline suite with 'cases:' is no longer supported
        raise LoadError("Legacy inline suite ('cases:') is not supported. Please use caseflow format.")
    else:
        # single case file: normalize checks
        obj = _normalize_case_dict(obj, path=path, raw_text=processed_raw)
        try:
            case = Case.model_validate(obj)
        except ValidationError as exc:
            raise DiagnosticError(
                diagnostic=_diagnostic_from_case_validation_error(exc, obj, path, processed_raw)
            ) from exc
        cases.append(case)

    meta = {"file": str(path)}
    return cases, meta


def _collect_common_diagnostics(obj: Any, path: Path, raw_text: str) -> List[Diagnostic]:
    diagnostics: List[Diagnostic] = []

    def add(diag: Diagnostic) -> None:
        diagnostics.append(diag)

    if not isinstance(obj, dict):
        add(
            _diagnostic(
                "DRUN-YAML-002",
                "YAML root must be a mapping",
                file=path,
                hint="Start the file with `config:` and `steps:` or `caseflow:`.",
                example="config:\n  name: Demo\nsteps: []",
                raw_text=raw_text,
            )
        )
        return diagnostics

    if "cases" in obj:
        add(
            _diagnostic(
                "DRUN-YAML-009",
                "Legacy inline suite `cases:` is not supported",
                file=path,
                line=_find_top_level_key_location(raw_text, "cases"),
                yaml_path="cases",
                hint="Use `caseflow` format instead.",
                example=EXAMPLE_CASEFLOW,
                raw_text=raw_text,
            )
        )

    if "caseflow" in obj:
        caseflow_items = obj.get("caseflow")
        if not isinstance(caseflow_items, list):
            add(
                _diagnostic(
                    "DRUN-YAML-010",
                    "Invalid caseflow: `caseflow` must be a list",
                    file=path,
                    line=_find_top_level_key_location(raw_text, "caseflow"),
                    yaml_path="caseflow",
                    hint="Declare each invoked case as one list item.",
                    example=EXAMPLE_CASEFLOW,
                    raw_text=raw_text,
                )
            )
            return diagnostics

        for idx, item in enumerate(caseflow_items):
            item_line = _find_caseflow_item_location(raw_text, idx)
            if not isinstance(item, dict):
                add(
                    _diagnostic(
                        "DRUN-YAML-010",
                        f"Invalid caseflow item at index {idx}: expected mapping",
                        file=path,
                        line=item_line[0] if item_line else None,
                        yaml_path=f"caseflow[{idx}]",
                        hint="Each `caseflow` item must include at least `name` and `invoke`.",
                        example=EXAMPLE_CASEFLOW,
                        raw_text=raw_text,
                    )
                )
                continue

            for legacy_field in ("loop", "foreach"):
                if legacy_field in item:
                    loc = _find_caseflow_item_location(raw_text, idx, legacy_field)
                    add(
                        _diagnostic(
                            "DRUN-YAML-009",
                            f"Legacy field `{legacy_field}` is not supported",
                            file=path,
                            line=loc[0] if loc else None,
                            yaml_path=f"caseflow[{idx}].{legacy_field}",
                            hint="Please use 'repeat'.",
                            example=EXAMPLE_REPEAT,
                            raw_text=raw_text,
                        )
                    )
            if not item.get("invoke"):
                loc = _find_caseflow_item_location(raw_text, idx, "invoke")
                add(
                    _diagnostic(
                        "DRUN-YAML-010",
                        f"Caseflow item at index {idx} is missing `invoke`",
                        file=path,
                        line=loc[0] if loc else None,
                        yaml_path=f"caseflow[{idx}].invoke",
                        hint="Add the target testcase name or path to `invoke`.",
                        example=EXAMPLE_CASEFLOW,
                        raw_text=raw_text,
                    )
                )
        return diagnostics

    has_top_level_parameters = "parameters" in obj
    cfg = obj.get("config") if isinstance(obj.get("config"), dict) else {}
    if has_top_level_parameters:
        add(
            _diagnostic(
                "DRUN-YAML-006",
                "Invalid parameter location",
                file=path,
                line=_find_top_level_key_location(raw_text, "parameters"),
                yaml_path="parameters",
                hint="Move `parameters` under `config.parameters`.",
                example=EXAMPLE_CONFIG_PARAMETERS,
                raw_text=raw_text,
            )
        )
    if has_top_level_parameters and isinstance(cfg, dict) and "parameters" in cfg:
        add(
            _diagnostic(
                "DRUN-YAML-006",
                "Duplicate parameter declaration",
                file=path,
                line=_find_top_level_key_location(raw_text, "parameters"),
                yaml_path="parameters",
                hint="Define parameters only under `config.parameters`.",
                example=EXAMPLE_CONFIG_PARAMETERS,
                raw_text=raw_text,
            )
        )

    if isinstance(cfg, dict):
        for hk_field in ("setup_hooks", "teardown_hooks"):
            _collect_hook_diagnostics(
                cfg.get(hk_field),
                path=path,
                raw_text=raw_text,
                yaml_path=f"config.{hk_field}",
                field_name=hk_field,
                diagnostics=diagnostics,
            )

    for hk_field in ("setup_hooks", "teardown_hooks"):
        if hk_field in obj:
            add(
                _diagnostic(
                    "DRUN-YAML-013",
                    f"Invalid top-level `{hk_field}`",
                    file=path,
                    line=_find_top_level_key_location(raw_text, hk_field),
                    yaml_path=hk_field,
                    hint=f"Move case-level hooks under `config.{hk_field}`.",
                    example="config:\n  " + EXAMPLE_HOOK,
                    raw_text=raw_text,
                )
            )

    steps = obj.get("steps")
    if isinstance(steps, list):
        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                add(
                    _diagnostic(
                        "DRUN-YAML-002",
                        f"Invalid step at index {idx}: expected mapping",
                        file=path,
                        yaml_path=f"steps[{idx}]",
                        hint="Each step must be a YAML mapping with `name` and one executable target.",
                        example="steps:\n  - name: Ping\n    request:\n      method: GET\n      path: /ping",
                        raw_text=raw_text,
                    )
                )
                continue
            _collect_step_diagnostics(step, idx, path, raw_text, diagnostics)

    return diagnostics


def _collect_step_diagnostics(
    step: Dict[str, Any],
    idx: int,
    path: Path,
    raw_text: str,
    diagnostics: List[Diagnostic],
) -> None:
    def add(diag: Diagnostic) -> None:
        diagnostics.append(diag)

    step_label = str(step.get("name") or f"steps[{idx + 1}]")

    for legacy_field in ("loop", "foreach"):
        if legacy_field in step:
            loc = _find_step_child_location(raw_text, idx, legacy_field)
            add(
                _diagnostic(
                    "DRUN-YAML-009",
                    f"Legacy field `{legacy_field}` is not supported",
                    file=path,
                    line=loc[0] if loc else None,
                    yaml_path=f"steps[{idx}].{legacy_field}",
                    hint="please migrate to 'repeat'.",
                    example=EXAMPLE_REPEAT,
                    raw_text=raw_text,
                )
            )

    active_targets = [
        field
        for field in ("request", "invoke", "sleep")
        if field in step and step.get(field) is not None
    ]
    if len(active_targets) > 1:
        loc = _find_step_child_location(raw_text, idx, active_targets[1]) or _find_step_child_location(raw_text, idx, active_targets[0])
        add(
            _diagnostic(
                "DRUN-YAML-011",
                "Step cannot combine `request`, `invoke`, and `sleep`",
                file=path,
                line=loc[0] if loc else None,
                yaml_path=f"steps[{idx}]",
                hint="Use exactly one executable target per step.",
                example=EXAMPLE_SLEEP,
                raw_text=raw_text,
            )
        )
    elif not active_targets:
        add(
            _diagnostic(
                "DRUN-YAML-011",
                "Step must define one of `request`, `invoke`, or `sleep`",
                file=path,
                line=(_find_step_child_location(raw_text, idx, "name") or (None, ""))[0],
                yaml_path=f"steps[{idx}]",
                hint="Add exactly one executable target to the step.",
                example=EXAMPLE_REQUEST_PATH,
                raw_text=raw_text,
            )
        )

    req = step.get("request")
    if isinstance(req, dict):
        if "url" in req:
            loc = _find_request_subfield_location(raw_text, idx, "url")
            add(
                _diagnostic(
                    "DRUN-YAML-003",
                    "Invalid request field: request.url",
                    file=path,
                    line=loc[0] if loc else None,
                    yaml_path=f"steps[{idx}].request.url",
                    hint="Use `request.path` instead of `request.url`.",
                    example=EXAMPLE_REQUEST_PATH,
                    raw_text=raw_text,
                )
            )
        if "json" in req:
            loc = _find_request_subfield_location(raw_text, idx, "json")
            add(
                _diagnostic(
                    "DRUN-YAML-004",
                    "request.json is not supported",
                    file=path,
                    line=loc[0] if loc else None,
                    yaml_path=f"steps[{idx}].request.json",
                    hint="Use `request.body` for JSON or raw request payloads.",
                    example="request:\n  method: POST\n  path: /users\n  body:\n    name: Alice",
                    raw_text=raw_text,
                )
            )
        if "validate" in req:
            loc = _find_request_subfield_location(raw_text, idx, "validate")
            add(
                _diagnostic(
                    "DRUN-YAML-012",
                    "validate has been renamed to check",
                    file=path,
                    line=loc[0] if loc else None,
                    yaml_path=f"steps[{idx}].request.validate",
                    hint="Use `check` at the step level instead of `request.validate`.",
                    example=EXAMPLE_BODY_CHECK,
                    raw_text=raw_text,
                )
            )
        for nested_field in ("extract", "check", "setup_hooks", "teardown_hooks"):
            if nested_field in req:
                loc = _find_request_subfield_location(raw_text, idx, nested_field)
                add(
                    _diagnostic(
                        "DRUN-YAML-005",
                        f"Invalid YAML indentation: `{nested_field}` is nested under `request`",
                        file=path,
                        line=loc[0] if loc else None,
                        yaml_path=f"steps[{idx}].request.{nested_field}",
                        hint=f"Move `{nested_field}` out to align with `request`.",
                        example="steps:\n  - name: Example\n    request:\n      method: GET\n      path: /api/users\n    check:\n      - eq: [status_code, 200]",
                        raw_text=raw_text,
                    )
                )
        if req.get("body") is not None and req.get("files") is not None:
            loc = _find_request_subfield_location(raw_text, idx, "files")
            add(
                _diagnostic(
                    "DRUN-YAML-008",
                    "request.body cannot be used with request.files",
                    file=path,
                    line=loc[0] if loc else None,
                    yaml_path=f"steps[{idx}].request.files",
                    hint="Use `request.data` for multipart form fields.",
                    example=EXAMPLE_MULTIPART,
                    raw_text=raw_text,
                )
            )
        if req.get("files") is not None:
            try:
                validate_request_files_shape(req.get("files"), source="request.files")
            except RequestFilesError as exc:
                loc = _find_request_subfield_location(raw_text, idx, "files")
                add(
                    _diagnostic(
                        "DRUN-YAML-008",
                        "Invalid request.files declaration",
                        file=path,
                        line=loc[0] if loc else None,
                        yaml_path=f"steps[{idx}].request.files",
                        hint=str(exc),
                        example=EXAMPLE_MULTIPART,
                        raw_text=raw_text,
                    )
                )

    if "validate" in step:
        loc = _find_step_child_location(raw_text, idx, "validate")
        add(
            _diagnostic(
                "DRUN-YAML-012",
                "validate has been renamed to check",
                file=path,
                line=loc[0] if loc else None,
                yaml_path=f"steps[{idx}].validate",
                hint="Use `check` instead of `validate`.",
                example=EXAMPLE_BODY_CHECK,
                raw_text=raw_text,
            )
        )

    if "check" in step:
        try:
            normalized = normalize_checks(step["check"])
        except Exception as exc:
            loc = _find_step_child_location(raw_text, idx, "check")
            add(
                _diagnostic(
                    "DRUN-YAML-002",
                    "Invalid check declaration",
                    file=path,
                    line=loc[0] if loc else None,
                    yaml_path=f"steps[{idx}].check",
                    hint=str(exc),
                    example=EXAMPLE_BODY_CHECK,
                    raw_text=raw_text,
                )
            )
            normalized = []
        for check in normalized:
            if isinstance(check.check, str) and check.check.startswith("body."):
                loc = _find_step_child_location(raw_text, idx, "check")
                add(
                    _diagnostic(
                        "DRUN-YAML-007",
                        f"Invalid check syntax: {check.check}",
                        file=path,
                        line=loc[0] if loc else None,
                        yaml_path=f"steps[{idx}].check",
                        hint="Use `$` JSONPath-like syntax for response body checks, for example `$.data.id`.",
                        example=EXAMPLE_BODY_CHECK,
                        raw_text=raw_text,
                    )
                )

    if isinstance(step.get("extract"), dict):
        for name, expr in step["extract"].items():
            if isinstance(expr, str) and expr.startswith("body."):
                loc = _find_step_child_location(raw_text, idx, "extract")
                add(
                    _diagnostic(
                        "DRUN-YAML-007",
                        f"Invalid extract syntax: {expr}",
                        file=path,
                        line=loc[0] if loc else None,
                        yaml_path=f"steps[{idx}].extract.{name}",
                        hint="Use `$` JSONPath-like syntax for response body extraction, for example `$.data.token`.",
                        example="extract:\n  token: $.data.token",
                        raw_text=raw_text,
                    )
                )

    for hk_field in ("setup_hooks", "teardown_hooks"):
        if hk_field in step:
            _collect_hook_diagnostics(
                step.get(hk_field),
                path=path,
                raw_text=raw_text,
                yaml_path=f"steps[{idx}].{hk_field}",
                field_name=hk_field,
                diagnostics=diagnostics,
            )

    if "repeat" in step:
        repeat_value = step.get("repeat")
        loc = _find_step_child_location(raw_text, idx, "repeat")
        if isinstance(repeat_value, bool):
            add(
                _diagnostic(
                    "DRUN-YAML-015",
                    f"Invalid repeat value in step `{step_label}`",
                    file=path,
                    line=loc[0] if loc else None,
                    yaml_path=f"steps[{idx}].repeat",
                    hint="`repeat` must be an integer or expression string, not boolean.",
                    example=EXAMPLE_REPEAT,
                    raw_text=raw_text,
                )
            )
        elif isinstance(repeat_value, int) and repeat_value < 0:
            add(
                _diagnostic(
                    "DRUN-YAML-015",
                    f"Invalid repeat value in step `{step_label}`",
                    file=path,
                    line=loc[0] if loc else None,
                    yaml_path=f"steps[{idx}].repeat",
                    hint="`repeat` must be >= 0.",
                    example=EXAMPLE_REPEAT,
                    raw_text=raw_text,
                )
            )
        elif isinstance(repeat_value, str) and not repeat_value.strip():
            add(
                _diagnostic(
                    "DRUN-YAML-015",
                    f"Invalid repeat value in step `{step_label}`",
                    file=path,
                    line=loc[0] if loc else None,
                    yaml_path=f"steps[{idx}].repeat",
                    hint="`repeat` must be a non-empty integer or expression string.",
                    example=EXAMPLE_REPEAT,
                    raw_text=raw_text,
                )
            )

    if "sleep" in step and step.get("sleep") is not None:
        sleep_value = step.get("sleep")
        loc = _find_step_child_location(raw_text, idx, "sleep")
        if isinstance(sleep_value, bool):
            add(
                _diagnostic(
                    "DRUN-YAML-015",
                    f"Invalid sleep value in step `{step_label}`",
                    file=path,
                    line=loc[0] if loc else None,
                    yaml_path=f"steps[{idx}].sleep",
                    hint="`sleep` must be a number or expression string, not boolean.",
                    example=EXAMPLE_SLEEP,
                    raw_text=raw_text,
                )
            )
        elif isinstance(sleep_value, (int, float)) and float(sleep_value) < 0:
            add(
                _diagnostic(
                    "DRUN-YAML-015",
                    f"Invalid sleep value in step `{step_label}`",
                    file=path,
                    line=loc[0] if loc else None,
                    yaml_path=f"steps[{idx}].sleep",
                    hint="`sleep` must be >= 0.",
                    example=EXAMPLE_SLEEP,
                    raw_text=raw_text,
                )
            )
        elif isinstance(sleep_value, str) and not sleep_value.strip():
            add(
                _diagnostic(
                    "DRUN-YAML-015",
                    f"Invalid sleep value in step `{step_label}`",
                    file=path,
                    line=loc[0] if loc else None,
                    yaml_path=f"steps[{idx}].sleep",
                    hint="`sleep` must be a non-empty number or expression string.",
                    example=EXAMPLE_SLEEP,
                    raw_text=raw_text,
                )
            )
        incompatible = [
            field
            for field in ("response", "extract", "export", "check", "retry")
            if step.get(field)
        ]
        if incompatible:
            add(
                _diagnostic(
                    "DRUN-YAML-011",
                    f"Step with `sleep` cannot use `{incompatible[0]}`",
                    file=path,
                    line=loc[0] if loc else None,
                    yaml_path=f"steps[{idx}]",
                    hint="Move checks, extraction, export, response saving, or retry to a request step.",
                    example=EXAMPLE_SLEEP,
                    raw_text=raw_text,
                )
            )


def _collect_hook_diagnostics(
    items: Any,
    *,
    path: Path,
    raw_text: str,
    yaml_path: str,
    field_name: str,
    diagnostics: List[Diagnostic],
) -> None:
    if items is None:
        return
    line = _find_top_level_key_location(raw_text, field_name)
    if not isinstance(items, list):
        diagnostics.append(
            _diagnostic(
                "DRUN-YAML-013",
                f"Invalid `{yaml_path}` declaration",
                file=path,
                line=line,
                yaml_path=yaml_path,
                hint=f"`{yaml_path}` must be a list of expression strings like `${{func(...)}}`.",
                example=EXAMPLE_HOOK,
                raw_text=raw_text,
            )
        )
        return
    for item in items:
        if not isinstance(item, str) or not item.strip() or not (item.strip().startswith("${") and item.strip().endswith("}")):
            diagnostics.append(
                _diagnostic(
                    "DRUN-YAML-013",
                    f"Invalid `{yaml_path}` entry",
                    file=path,
                    line=line,
                    yaml_path=yaml_path,
                    hint=f"Hook entries must use expression syntax `${{func(...)}}`.",
                    example=EXAMPLE_HOOK,
                    raw_text=raw_text,
                )
            )
            return


def _diagnostic_from_case_validation_error(
    exc: ValidationError, obj: Dict[str, Any], path: Path, raw_text: str
) -> Diagnostic:
    message = str(exc)
    for err in exc.errors():
        loc = err.get("loc") or ()
        err_type = err.get("type")
        msg = str(err.get("msg") or "")

        if (
            err_type == "extra_forbidden"
            and len(loc) >= 4
            and loc[0] == "steps"
            and isinstance(loc[1], int)
            and loc[2] == "request"
        ):
            field = str(loc[3])
            line_info = _find_request_subfield_location(raw_text, loc[1], field)
            return _diagnostic(
                "DRUN-YAML-003",
                f"Invalid request field: request.{field}",
                file=path,
                line=line_info[0] if line_info else None,
                yaml_path=f"steps[{loc[1]}].request.{field}",
                hint="Use only supported request fields such as `method`, `path`, `headers`, `params`, `body`, `data`, `files`, and `auth`.",
                example=EXAMPLE_REQUEST_PATH,
                raw_text=raw_text,
            )

        if loc and loc[0] == "steps" and isinstance(loc[1] if len(loc) > 1 else None, int):
            step_index = loc[1]
            step_path = f"steps[{step_index}]"
            line_info = _find_step_child_location(raw_text, step_index, "name")
            if "request', 'invoke', and 'sleep'" in msg or "one of 'request', 'invoke', or 'sleep'" in msg:
                return _diagnostic(
                    "DRUN-YAML-011",
                    msg.replace("Value error, ", ""),
                    file=path,
                    line=line_info[0] if line_info else None,
                    yaml_path=step_path,
                    hint="Use exactly one executable target per step.",
                    example=EXAMPLE_REQUEST_PATH,
                    raw_text=raw_text,
                )
            if "sleep" in msg or "repeat" in msg:
                return _diagnostic(
                    "DRUN-YAML-015",
                    msg.replace("Value error, ", ""),
                    file=path,
                    line=line_info[0] if line_info else None,
                    yaml_path=step_path,
                    hint="Check `repeat` and `sleep` values and keep them as numbers or expression strings.",
                    example=EXAMPLE_SLEEP,
                    raw_text=raw_text,
                )

    return _diagnostic(
        "DRUN-YAML-002",
        "Invalid YAML test case schema",
        file=path,
        hint=message,
        raw_text=raw_text,
    )


def _format_case_validation_error(exc: ValidationError, obj: Dict[str, Any], path: Path, raw_text: str) -> str:
    """Provide user-friendly messages for common authoring mistakes."""

    def _step_name(idx: int) -> str:
        steps = obj.get("steps") if isinstance(obj.get("steps"), list) else []
        if isinstance(steps, list) and 0 <= idx < len(steps):
            step = steps[idx] or {}
            name = step.get("name") if isinstance(step, dict) else None
            if name:
                return str(name)
        return f"steps[{idx + 1}]"

    for err in exc.errors():
        loc = err.get("loc") or ()
        err_type = err.get("type")

        # Friendly message for url vs path confusion
        if (
            err_type == "extra_forbidden"
            and len(loc) >= 4
            and loc[0] == "steps"
            and isinstance(loc[1], int)
            and loc[2] == "request"
            and loc[3] == "url"
        ):
            step_label = _step_name(loc[1])
            return (
                f"Invalid request field 'url' in {path}: step '{step_label}'.\n"
                f"Use 'path' instead of 'url' for the request endpoint.\n\n"
                "Example:\n"
                "  - name: Example Step\n"
                "    request:\n"
                "      method: GET\n"
                "      path: /api/endpoint  # Use 'path', not 'url'"
            )

        # Friendly message when fields (extract/check/...) are indented under request
        if (
            err_type == "extra_forbidden"
            and len(loc) >= 4
            and loc[0] == "steps"
            and isinstance(loc[1], int)
            and loc[2] == "request"
        ):
            field = loc[3]
            if field in {"extract", "check", "setup_hooks", "teardown_hooks"}:
                step_label = _step_name(loc[1])
                line_info = _find_step_field_location(raw_text, loc[1], field)
                if line_info:
                    line_no, actual_indent, expected_indent, line_text = line_info
                    indent_hint = (
                        f"line {line_no}: '{line_text.strip()}' uses {actual_indent} leading spaces; "
                        f"expected {expected_indent}."
                    )
                    return (
                        f"Invalid YAML indentation in {path}: step '{step_label}' has '{field}' nested under 'request'. "
                        f"Move '{field}' out to align with 'request' (indent {expected_indent} spaces).\n"
                        f"Hint → {indent_hint}\n"
                        "Example:\n"
                        "  - name: Example\n"
                        "    request:\n"
                        "      ...\n"
                        "    extract: { token: $.data.token }\n"
                        "    check: [ { eq: [status_code, 200] } ]"
                    )
                return (
                    f"Invalid YAML indentation in {path}: step '{step_label}' has '{field}' nested under 'request'. "
                    "Check indentation — 'extract'/'check' blocks belong alongside 'request', not inside it."
                )

    # Fallback to default detail when we cannot produce a custom hint
    return f"Failed to load {path}: {exc}"


def _find_step_field_location(raw_text: str, step_index: int, field: str) -> tuple[int, int, int, str] | None:
    """Locate the line/indentation for a field inside a step for better diagnostics."""

    lines = raw_text.splitlines()
    step_pattern = re.compile(r"^\s*-\s+name\s*:")
    current_step = -1
    step_indent = None
    step_start = None

    for idx, line in enumerate(lines):
        if step_pattern.match(line):
            current_step += 1
            if current_step == step_index:
                step_indent = len(line) - len(line.lstrip(" "))
                step_start = idx
                break

    if step_start is None or step_indent is None:
        return None

    expected_indent = step_indent + 2
    field_prefix = f"{field}:"

    for idx in range(step_start + 1, len(lines)):
        line = lines[idx]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if step_pattern.match(line) and indent <= step_indent:
            break
        if not stripped:
            continue
        if stripped.startswith(field_prefix):
            if indent > expected_indent:
                return idx + 1, indent, expected_indent, line.rstrip()
            return None

    return None


def _find_request_subfield_location(raw_text: str, step_index: int, subfield: str) -> tuple[int, str] | None:
    """Best-effort locate the line where a given request subfield (e.g., 'json') appears.

    We detect the step by matching '- name:' lines, then find the 'request:' block
    and finally the target subfield under it.
    Returns (line_no_1_based, line_text) or None if not found.
    """
    lines = raw_text.splitlines()
    step_pattern = re.compile(r"^\s*-\s+name\s*:")
    current_step = -1
    step_indent = None
    step_start = None

    for idx, line in enumerate(lines):
        if step_pattern.match(line):
            current_step += 1
            if current_step == step_index:
                step_indent = len(line) - len(line.lstrip(" "))
                step_start = idx
                break

    if step_start is None or step_indent is None:
        return None

    expected_step_child_indent = step_indent + 2
    request_indent = None
    # Find 'request:' within this step
    for idx in range(step_start + 1, len(lines)):
        line = lines[idx]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if step_pattern.match(line) and indent <= step_indent:
            # next step begins
            break
        if not stripped:
            continue
        if stripped.startswith("request:") and indent == expected_step_child_indent:
            request_indent = indent
            request_start = idx
            break

    if request_indent is None:
        return None

    # Now search within request block for the subfield
    expected_sub_indent = request_indent + 2
    sub_prefix = f"{subfield}:"
    for idx in range(request_start + 1, len(lines)):
        line = lines[idx]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if not stripped:
            continue
        # out of request block when indentation returns to step-level child
        if indent <= request_indent and not stripped.startswith("#"):
            break
        if stripped.startswith(sub_prefix) and indent == expected_sub_indent:
            return idx + 1, line.rstrip()

    return None


def _find_step_child_location(raw_text: str, step_index: int, field: str) -> tuple[int, str] | None:
    lines = raw_text.splitlines()
    step_pattern = re.compile(r"^\s*-\s+name\s*:")
    current_step = -1
    step_indent = None
    step_start = None

    for idx, line in enumerate(lines):
        if step_pattern.match(line):
            current_step += 1
            if current_step == step_index:
                step_indent = len(line) - len(line.lstrip(" "))
                step_start = idx
                break

    if step_start is None or step_indent is None:
        return None

    expected_indent = step_indent + 2
    field_prefix = f"{field}:"
    for idx in range(step_start + 1, len(lines)):
        line = lines[idx]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if step_pattern.match(line) and indent <= step_indent:
            break
        if not stripped:
            continue
        if stripped.startswith(field_prefix) and indent == expected_indent:
            return idx + 1, line.rstrip()
    return None


def _find_caseflow_item_location(raw_text: str, item_index: int, field: str | None = None) -> tuple[int, str] | None:
    lines = raw_text.splitlines()
    caseflow_start = None
    base_indent = 0
    for idx, line in enumerate(lines):
        if re.match(r"^\s*caseflow\s*:", line):
            caseflow_start = idx
            base_indent = len(line) - len(line.lstrip(" "))
            break
    if caseflow_start is None:
        return None

    item_starts: list[int] = []
    for idx in range(caseflow_start + 1, len(lines)):
        line = lines[idx]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if stripped and indent <= base_indent and not stripped.startswith("-"):
            break
        if stripped.startswith("-") and indent == base_indent + 2:
            item_starts.append(idx)

    if item_index >= len(item_starts):
        return None
    item_start = item_starts[item_index]
    if field is None:
        return item_start + 1, lines[item_start].rstrip()

    field_prefix = f"{field}:"
    for idx in range(item_start, len(lines)):
        line = lines[idx]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if idx > item_start and stripped.startswith("-") and indent == base_indent + 2:
            break
        if stripped.startswith(field_prefix):
            return idx + 1, line.rstrip()
    return item_start + 1, lines[item_start].rstrip()


def expand_parameters(parameters: Any, *, source_path: str | Path | None = None) -> List[Dict[str, Any]]:
    from drun.loader.parameters import expand_parameters as _expand_parameters

    return _expand_parameters(parameters, source_path=source_path)

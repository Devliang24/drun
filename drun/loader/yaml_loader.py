from __future__ import annotations

import csv
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Tuple

import yaml
from pydantic import ValidationError

from drun.models.case import Case, Suite
from drun.models.config import Config
from drun.models.step import Step
from drun.models.validators import normalize_validators
from drun.utils.errors import LoadError


def _is_suite(doc: Dict[str, Any]) -> bool:
    return "cases" in doc


def _is_testsuite_reference(doc: Dict[str, Any]) -> bool:
    return isinstance(doc, dict) and isinstance(doc.get("testcases"), list)


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
                # validate expressions and promote to case-level
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
            if "validate" in ss:
                ss["validate"] = [v.model_dump() for v in normalize_validators(ss["validate"])]
                # enforce $-only for body checks
                for v in ss["validate"]:
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


def load_yaml_file(path: Path) -> Tuple[List[Case], Dict[str, Any]]:
    try:
        raw = path.read_text(encoding="utf-8")
        obj = yaml.safe_load(raw) or {}
    except Exception as e:
        raise LoadError(f"Failed to parse YAML: {path}: {e}")

    cases: List[Case] = []
    # New-style reference testsuite: { config: {}, testcases: [ {testcase: path, name?, variables?, parameters?, tags?}, ... ] }
    if _is_testsuite_reference(obj):
        promoted_from_config: set[str] = set()
        suite_setup_hooks: List[str] = []
        suite_teardown_hooks: List[str] = []
        if isinstance(obj.get("config"), dict):
            for hk_field in ("setup_hooks", "teardown_hooks"):
                if hk_field in obj["config"]:
                    items = obj["config"].get(hk_field)
                    if items is None:
                        items = []
                    if not isinstance(items, list):
                        raise LoadError(
                            f"Invalid config.{hk_field} entry type {type(items).__name__}; expected list of '${{func(...)}}'"
                        )
                    for item in items:
                        if not isinstance(item, str):
                            raise LoadError(
                                f"Invalid suite {hk_field} entry type {type(item).__name__}; expected string like '${{func(...)}}'"
                            )
                        text = item.strip()
                        if not text:
                            raise LoadError(f"Invalid empty suite {hk_field} entry")
                        if not (text.startswith("${") and text.endswith("}")):
                            raise LoadError(
                                f"Invalid suite {hk_field} entry '{item}': must use expression syntax '${{func(...)}}'"
                            )
                    if hk_field == "setup_hooks":
                        suite_setup_hooks = list(items)
                    else:
                        suite_teardown_hooks = list(items)
                    promoted_from_config.add(hk_field)
                    obj["config"].pop(hk_field, None)
        for hk_field in ("setup_hooks", "teardown_hooks"):
            if hk_field in obj and hk_field not in promoted_from_config:
                raise LoadError(
                    f"Invalid top-level '{hk_field}': suite-level hooks must be declared under 'config.{hk_field}'."
                )

        suite_cfg = Config.model_validate(obj.get("config") or {})
        # iterate referenced testcases
        items = obj.get("testcases") or []
        if not isinstance(items, list):
            raise LoadError("Invalid testsuite: 'testcases' must be a list")

        for idx, it in enumerate(items):
            # item can be a string path or a dict
            if isinstance(it, str):
                tc_path = it
                item_name = None
                item_vars: Dict[str, Any] = {}
                item_params: Any = None
                item_tags: List[str] = []
            elif isinstance(it, dict):
                tc_path = it.get("testcase") or it.get("path") or it.get("file")
                if not tc_path:
                    raise LoadError(f"Invalid testsuite item at index {idx}: missing 'testcase' path")
                item_name = it.get("name")
                item_vars = dict(it.get("variables") or {})
                item_params = it.get("parameters")
                item_tags = list(it.get("tags") or [])
            else:
                raise LoadError(f"Invalid testsuite item type at index {idx}: {type(it).__name__}")

            # resolve referenced path relative to testsuite file
            ref = Path(tc_path)
            if not ref.is_absolute():
                candidate = (path.parent / ref).resolve()
                if candidate.exists():
                    ref = candidate
                else:
                    ref = (Path.cwd() / ref).resolve()
            if not ref.exists():
                raise LoadError(f"Referenced testcase not found: {tc_path}")

            loaded_cases, _meta = load_yaml_file(ref)
            if len(loaded_cases) != 1:
                raise LoadError(
                    f"Referenced testcase '{tc_path}' resolved to {len(loaded_cases)} cases; expected exactly 1."
                )
            base_case = loaded_cases[0]
            merged = base_case.model_copy(deep=True)
            # inherit/merge from suite config
            if not merged.config.base_url:
                merged.config.base_url = suite_cfg.base_url
            merged.config.variables = {
                **(suite_cfg.variables or {}),
                **(merged.config.variables or {}),
                **(item_vars or {}),
            }
            merged.config.headers = {**(suite_cfg.headers or {}), **(merged.config.headers or {})}
            merged.config.tags = list({*(suite_cfg.tags or []), *merged.config.tags, *item_tags})
            # item-level name override
            if item_name:
                merged.config.name = item_name
            # item-level parameters override (simple override to avoid ambiguous compositions)
            if item_params is not None:
                merged.parameters = item_params
            # inherit suite hooks
            merged.suite_setup_hooks = list(suite_setup_hooks or [])
            merged.suite_teardown_hooks = list(suite_teardown_hooks or [])
            cases.append(merged)

    elif _is_suite(obj):
        # Legacy inline suite with 'cases:' is no longer supported
        raise LoadError("Legacy inline suite ('cases:') is not supported. Please use reference testsuite with 'testcases:'.")
    else:
        # single case file: normalize validators
        obj = _normalize_case_dict(obj, path=path, raw_text=raw)
        try:
            case = Case.model_validate(obj)
        except ValidationError as exc:
            raise LoadError(_format_case_validation_error(exc, obj, path, raw)) from exc
        cases.append(case)

    meta = {"file": str(path)}
    return cases, meta


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

        # Friendly message when fields (extract/validate/...) are indented under request
        if (
            err_type == "extra_forbidden"
            and len(loc) >= 4
            and loc[0] == "steps"
            and isinstance(loc[1], int)
            and loc[2] == "request"
        ):
            field = loc[3]
            if field in {"extract", "validate", "setup_hooks", "teardown_hooks", "sql_validate"}:
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
                        "    validate: [ { eq: [status_code, 200] } ]"
                    )
                return (
                    f"Invalid YAML indentation in {path}: step '{step_label}' has '{field}' nested under 'request'. "
                    "Check indentation — 'extract'/'validate' blocks belong alongside 'request', not inside it."
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


def _resolve_csv_path(path_value: str, source_path: Path | None) -> Path:
    candidate = Path(path_value).expanduser()
    if candidate.is_absolute():
        return candidate
    base = Path(source_path).resolve().parent if source_path else Path.cwd()
    return (base / candidate).resolve()


def _normalize_csv_columns(columns: Any) -> List[str]:
    if columns is None:
        return []
    if not isinstance(columns, list) or not columns:
        raise LoadError("CSV parameters 'columns' must be a non-empty list of column names.")
    names: List[str] = []
    for idx, col in enumerate(columns):
        if not isinstance(col, str):
            raise LoadError(f"CSV parameters column at index {idx} must be a string; got {type(col).__name__}.")
        name = col.strip()
        if not name:
            raise LoadError(f"CSV parameters column at index {idx} cannot be empty or whitespace.")
        if name in names:
            raise LoadError(f"CSV parameters column '{name}' is duplicated; column names must be unique.")
        names.append(name)
    return names


def _load_csv_parameters(spec: Any, source_path: Path | None) -> List[Dict[str, Any]]:
    if isinstance(spec, str):
        cfg: Dict[str, Any] = {"path": spec}
    elif isinstance(spec, dict):
        cfg = dict(spec)
    else:
        raise LoadError(
            f"Invalid CSV parameters declaration: expected string or mapping, got {type(spec).__name__}."
        )

    raw_path = cfg.get("path") or cfg.get("file")
    if not raw_path or not isinstance(raw_path, str):
        raise LoadError("CSV parameters require a string 'path'.")

    delimiter = cfg.get("delimiter", ",")
    if not isinstance(delimiter, str) or not delimiter:
        raise LoadError("CSV parameters 'delimiter' must be a non-empty string.")
    if len(delimiter) > 1:
        raise LoadError("CSV parameters 'delimiter' must be a single character.")

    encoding = cfg.get("encoding", "utf-8")
    if not isinstance(encoding, str) or not encoding:
        raise LoadError("CSV parameters 'encoding' must be a valid encoding name.")

    header_flag = cfg.get("header")
    if header_flag is not None and not isinstance(header_flag, bool):
        raise LoadError("CSV parameters 'header' must be a boolean if provided.")

    columns = _normalize_csv_columns(cfg.get("columns"))
    header = header_flag if header_flag is not None else True

    strip_values = cfg.get("strip", False)
    if strip_values not in (True, False):
        raise LoadError("CSV parameters 'strip' must be boolean when provided.")

    csv_path = _resolve_csv_path(raw_path, source_path)
    if not csv_path.exists():
        raise LoadError(f"CSV parameters file not found: '{raw_path}' (resolved to '{csv_path}')")

    rows: List[Dict[str, Any]] = []
    try:
        with csv_path.open(newline="", encoding=encoding) as fp:
            reader = csv.reader(fp, delimiter=delimiter)
            if header:
                try:
                    header_row = next(reader)
                except StopIteration as exc:
                    raise LoadError(f"CSV parameters file '{csv_path}' is empty.") from exc
                header_values = [str(h).strip() for h in header_row]
                if columns:
                    if len(columns) != len(header_values):
                        raise LoadError(
                            f"CSV parameters file '{csv_path}' header has {len(header_values)} columns but 'columns' override defines {len(columns)}."
                        )
                    fieldnames = columns
                else:
                    if any(not name for name in header_values):
                        raise LoadError(
                            f"CSV parameters file '{csv_path}' has empty column names in header row."
                        )
                    seen: set[str] = set()
                    for name in header_values:
                        if name in seen:
                            raise LoadError(
                                f"CSV parameters file '{csv_path}' header contains duplicate column '{name}'."
                            )
                        seen.add(name)
                    fieldnames = header_values
                start_line = 2
            else:
                if not columns:
                    raise LoadError(
                        f"CSV parameters for '{csv_path}' require 'columns' when 'header' is false."
                    )
                fieldnames = columns
                start_line = 1

            expected_len = len(fieldnames)
            for line_no, raw_row in enumerate(reader, start=start_line):
                if not raw_row or all(not str(cell).strip() for cell in raw_row):
                    continue
                if len(raw_row) != expected_len:
                    raise LoadError(
                        f"CSV parameters file '{csv_path}' line {line_no}: expected {expected_len} columns, got {len(raw_row)}."
                    )
                row_dict = {
                    fieldnames[idx]: (raw_row[idx].strip() if strip_values else raw_row[idx])
                    for idx in range(expected_len)
                }
                rows.append(row_dict)
    except UnicodeDecodeError as exc:
        raise LoadError(
            f"Failed to decode CSV parameters file '{csv_path}' with encoding '{encoding}'."
        ) from exc
    except OSError as exc:
        raise LoadError(f"Failed to read CSV parameters file '{csv_path}': {exc}") from exc

    if not rows:
        raise LoadError(f"CSV parameters file '{csv_path}' produced no data rows.")

    return rows


def _expand_zipped_block(key: str, rows: Any) -> List[Dict[str, Any]]:
    if not isinstance(rows, list):
        raise LoadError(f"Zipped parameters for '{key}' must be provided as a list.")
    names = [n.strip() for n in str(key).split("-") if n.strip()]
    if not names:
        raise LoadError(f"Zipped parameter key '{key}' must contain at least one variable name.")

    unit: List[Dict[str, Any]] = []
    for row in rows:
        if len(names) == 1:
            if isinstance(row, (list, tuple)):
                if len(row) != 1:
                    raise LoadError(
                        f"Zipped parameters for '{key}' expect single values; got {row!r}."
                    )
                values = [row[0]]
            else:
                values = [row]
        else:
            if not isinstance(row, (list, tuple)):
                raise LoadError(
                    f"Zipped parameters for '{key}' expect list/tuple rows matching {names}; got {row!r}."
                )
            if len(row) != len(names):
                raise LoadError(
                    f"Row {row!r} does not match variables {names} for zipped group '{key}'."
                )
            values = list(row)
        unit.append({name: value for name, value in zip(names, values)})
    return unit


def expand_parameters(parameters: Any, *, source_path: str | Path | None = None) -> List[Dict[str, Any]]:
    """Expand parameterization to a list of param dicts (zipped + CSV)."""
    if not parameters:
        return [{}]

    if isinstance(parameters, list):
        combos: List[Dict[str, Any]] = [{}]

        def product_append(base: List[Dict[str, Any]], unit: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            out: List[Dict[str, Any]] = []
            for b in base:
                for u in unit:
                    out.append({**b, **u})
            return out

        for idx, item in enumerate(parameters):
            if not isinstance(item, dict) or len(item) != 1:
                raise LoadError(
                    f"Invalid parameters at index {idx}: expected single-key dict like '- a-b: [...]' or '- csv: ...'."
                )
            key, value = next(iter(item.items()))
            if key == "csv" and not isinstance(value, list):
                unit = _load_csv_parameters(value, Path(source_path) if source_path else None)
            else:
                unit = _expand_zipped_block(str(key), value)
            combos = product_append(combos, unit)

        return combos

    raise LoadError(
        "Parameters must be declared as a list of single-key dictionaries under config.parameters."
    )

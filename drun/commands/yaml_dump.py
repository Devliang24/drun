"""YAML dump and formatting utilities shared by CLI commands.

Provides custom YAML dumper, case dict normalisation, step spacer formatting,
and helpers for writing imported test cases to files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import typer
import yaml

from drun.models.case import Case
from drun.models.checks import Check
from drun.models.config import Config
from drun.models.request import StepRequest
from drun.models.step import Step
from drun.utils.naming import derive_case_name


# ── Custom YAML Dumper ────────────────────────────────────────────────────────

class _FlowSeq(list):
    """Sequence rendered in flow-style YAML (e.g., [a, b])."""


class _YamlDumper(yaml.SafeDumper):
    """Custom dumper ensuring sequence indentation matches project style."""

    def increase_indent(self, flow: bool = False, indentless: bool = False):
        return super().increase_indent(flow, False)


def _flow_seq_representer(dumper: yaml.Dumper, value: _FlowSeq):
    return dumper.represent_sequence("tag:yaml.org,2002:seq", value, flow_style=True)


_YamlDumper.add_representer(_FlowSeq, _flow_seq_representer)


# ── Case-to-dict helpers ──────────────────────────────────────────────────────

def to_yaml_case_dict(case: Case) -> Dict[str, object]:
    # Dump with aliases and prune fields loader forbids at top-level.
    d = case.model_dump(by_alias=True, exclude_none=True)
    for k in (
        "setup_hooks",
        "teardown_hooks",
        "suite_setup_hooks",
        "suite_teardown_hooks",
    ):
        if k in d and not d.get(k):
            d.pop(k, None)
    # Drop empty config blocks (variables/headers/tags) to keep YAML clean.
    cfg = d.get("config")
    if isinstance(cfg, dict):
        for field in ("variables", "headers", "tags"):
            if not cfg.get(field):
                cfg.pop(field, None)

    steps = d.get("steps") or []
    cleaned_steps: List[Dict[str, object]] = []
    for step in steps:
        if not isinstance(step, dict):
            cleaned_steps.append(step)
            continue
        # Normalize checks to shorthand form expected by loader: {'eq': [status_code, 200]}
        raw_checks = step.get("check", []) or []
        step_checks: List[Dict[str, _FlowSeq]] = []
        for item in raw_checks:
            if not isinstance(item, dict):
                continue
            comparator = item.get("comparator")
            check = item.get("check")
            expect = item.get("expect")
            if comparator and check is not None:
                step_checks.append({str(comparator): _FlowSeq([check, expect])})
        if "check" in step:
            step.pop("check", None)

        for field in ("variables", "extract", "setup_hooks", "teardown_hooks"):
            if field in step and not step.get(field):
                step.pop(field, None)

        req = step.get("request") or {}
        # Normalize legacy alias: 'json' -> 'body'
        if isinstance(req, dict) and ("json" in req) and ("body" not in req):
            req["body"] = req.pop("json")
        headers = req.get("headers") or {}
        headers_lc = (
            {str(k).lower(): v for k, v in headers.items()}
            if isinstance(headers, dict)
            else {}
        )
        accept = str(headers_lc.get("accept", "")) if headers_lc else ""
        content_type = str(headers_lc.get("content-type", "")) if headers_lc else ""
        body_obj = req.get("body")
        method = str(req.get("method") or "").upper()

        expect_json = False
        if "json" in accept.lower() or "json" in content_type.lower():
            expect_json = True
        elif isinstance(body_obj, (dict, list)):
            expect_json = True

        ensure_body = expect_json or method in {"POST", "PUT", "PATCH"}

        # Add default checks when applicable.
        def _ensure_check(
            comp: str, check_value: str | object, expect_value: object
        ) -> None:
            for item in step_checks:
                if comp in item:
                    seq = item[comp]
                    if seq and str(seq[0]) == str(check_value):
                        return
            step_checks.append({comp: _FlowSeq([check_value, expect_value])})

        if expect_json:
            _ensure_check("contains", "headers.Content-Type", "application/json")

        if ensure_body:
            _ensure_check("ne", "$", None)

        reorder_keys = (
            "method",
            "path",
            "url",
            "headers",
            "params",
            "body",
            "data",
            "files",
            "auth",
            "timeout",
            "verify",
            "allow_redirects",
        )
        if isinstance(req, dict):
            reordered: Dict[str, object] = {}
            for key in reorder_keys:
                if key in req:
                    reordered[key] = req[key]
            for key, value in req.items():
                if key not in reordered:
                    reordered[key] = value
            step["request"] = reordered

        # Remove unnecessary default fields from request
        req = step.get("request", {})
        if "stream" in req and req["stream"] is False:
            req.pop("stream", None)
        if "stream_timeout" in req and req.get("stream_timeout") is None:
            req.pop("stream_timeout", None)

        if step_checks:
            step["check"] = step_checks

        # Remove default retry values
        if "retry" in step and step["retry"] is None:
            step.pop("retry", None)

        cleaned_steps.append(step)
    d["steps"] = cleaned_steps
    return d


# ── Formatting helpers ────────────────────────────────────────────────────────

def add_step_spacers(text: str) -> str:
    lines = text.splitlines()
    out: List[str] = []
    prev_step = False
    for line in lines:
        if line.startswith("steps:") and out and out[-1] != "":
            out.append("")
        if line.startswith("  - name:"):
            if prev_step and out and out[-1] != "":
                out.append("")
            prev_step = True
        elif line.strip() and not line.startswith("  "):
            prev_step = False
        out.append(line)
    if text.endswith("\n"):
        return "\n".join(out) + "\n"
    return "\n".join(out)


def dump_case_dict(obj: Dict[str, object]) -> str:
    raw = yaml.dump(obj, Dumper=_YamlDumper, allow_unicode=True, sort_keys=False)
    return add_step_spacers(raw)


# ── Import helper factories ───────────────────────────────────────────────────

def make_step_from_imported(imported_step: Any) -> Step:
    req = StepRequest(
        method=imported_step.method,
        path=imported_step.path,
        params=imported_step.params,
        headers=imported_step.headers,
        body=imported_step.body,
        data=imported_step.data,
        files=imported_step.files,
        auth=imported_step.auth,
    )
    return Step(
        name=imported_step.name,
        request=req,
        checks=[Check(check="status_code", comparator="eq", expect=200)],
    )


def build_cases_from_import(
    icase: Any, *, split_output: bool
) -> List[Tuple[Case, int]]:
    cases: List[Tuple[Case, int]] = []
    if split_output:
        for idx, imported_step in enumerate(icase.steps, start=1):
            step_obj = make_step_from_imported(imported_step)
            case_title = derive_case_name(icase.name, imported_step.name, idx)
            case = Case(
                config=Config(
                    name=case_title,
                    base_url=icase.base_url,
                    variables=getattr(icase, "variables", None) or {},
                ),
                steps=[step_obj],
            )
            cases.append((case, idx))
    else:
        steps = [make_step_from_imported(s) for s in icase.steps]
        case = Case(
            config=Config(
                name=icase.name,
                base_url=icase.base_url,
                variables=getattr(icase, "variables", None) or {},
            ),
            steps=steps,
        )
        cases.append((case, 1))
    return cases


def resolve_output_paths(
    count: int,
    *,
    outfile: Optional[str],
    source_path: Optional[str],
    default_prefix: str = "imported_step",
) -> List[Path]:
    if outfile:
        base = Path(outfile)
        suffix = base.suffix or ".yaml"
        stem = base.stem or "imported_case"
        parent = base.parent if str(base.parent) != "" else Path.cwd()
        if count == 1:
            return [base]
        return [parent / f"{stem}_{i}{suffix}" for i in range(1, count + 1)]
    if source_path:
        src = Path(source_path)
        stem = src.stem or "imported_case"
        parent = src.parent or Path.cwd()
        return [parent / f"{stem}_step{i}.yaml" for i in range(1, count + 1)]
    return [Path(f"{default_prefix}_{i}.yaml") for i in range(1, count + 1)]


def write_caseflow(
    paths: List[Path],
    names: List[str],
    *,
    suite_path: str,
    suite_name: Optional[str] = None,
) -> None:
    """生成 caseflow 格式的测试套件文件"""
    obj = {
        "config": {
            "name": suite_name or "Imported Caseflow",
        },
        "caseflow": [{"name": nm, "invoke": p.stem} for nm, p in zip(names, paths)],
    }
    from pathlib import Path as _Path

    out = yaml.dump(obj, Dumper=_YamlDumper, sort_keys=False, allow_unicode=True)
    _p = _Path(suite_path)
    _p.parent.mkdir(parents=True, exist_ok=True)
    _p.write_text(out, encoding="utf-8")
    typer.echo(f"[CONVERT] Wrote caseflow to {suite_path}")


def write_imported_cases(
    cases_with_index: List[Tuple[Case, int]],
    *,
    outfile: Optional[str],
    into: Optional[str],
    split_output: bool,
    source_path: Optional[str],
) -> None:
    rendered: List[Tuple[Dict[str, object], int, Case]] = [
        (to_yaml_case_dict(case_obj), idx, case_obj)
        for case_obj, idx in cases_with_index
    ]
    if into:
        out_dict, _, _case_obj = rendered[0]
        text = dump_case_dict(out_dict)
        p = Path(into)
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
            typer.echo(f"[CONVERT] Created new case file: {into}")
            return
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        message: str
        if "config" in data and "steps" in data:
            steps_existing = data.get("steps") or []
            steps_existing.extend(out_dict.get("steps") or [])
            data["steps"] = steps_existing
            message = f"[CONVERT] Appended {len(out_dict.get('steps', []))} steps into case: {into}"
        elif "cases" in data:
            cases_list = data.get("cases") or []
            cases_list.append(out_dict)
            data["cases"] = cases_list
            message = f"[CONVERT] Added case into suite: {into}"
        else:
            data = out_dict
            message = f"[CONVERT] Replaced file with generated case: {into}"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(dump_case_dict(data), encoding="utf-8")
        typer.echo(message)
        return

    if split_output:
        paths = resolve_output_paths(
            len(rendered), outfile=outfile, source_path=source_path
        )
        for (out_dict, _, case_obj), path in zip(rendered, paths):
            text = dump_case_dict(out_dict)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            typer.echo(f"[CONVERT] Wrote YAML for '{case_obj.config.name}' to {path}")
        return

    out_dict, _, _case_obj = rendered[0]
    text = dump_case_dict(out_dict)
    if outfile:
        path = Path(outfile)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        typer.echo(f"[CONVERT] Wrote YAML to {outfile}")
    else:
        typer.echo(text)

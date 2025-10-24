from __future__ import annotations

import json
import sys
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import typer
from importlib import metadata as _im
import yaml

from drun.loader.collector import discover, match_tags
from drun.loader.yaml_loader import expand_parameters, load_yaml_file
from drun.loader.hooks import get_functions_for
from drun.loader.env import load_environment
from drun.models.case import Case
from drun.models.config import Config
from drun.models.request import StepRequest
from drun.models.step import Step
from drun.models.validators import Validator
from drun.models.report import RunReport
from drun.reporter.json_reporter import write_json
from drun.runner.runner import Runner
from drun.templating.engine import TemplateEngine
from drun.utils.logging import setup_logging, get_logger
import time


from drun.utils.errors import LoadError


def _resolve_env_file_alias(value: str) -> tuple[str, bool, List[str]]:
    """Resolve shorthand env aliases (e.g., 'dev') to actual file paths."""

    clean = (value or "").strip()
    tried: List[str] = []
    if not clean:
        return clean, False, tried

    direct_path = Path(clean)
    tried.append(str(direct_path))
    if direct_path.exists():
        return str(direct_path), False, tried

    # Only consider alias expansion when there are no path separators or suffixes
    sep_chars = {"/", "\\", os.sep}
    has_separator = any(ch in clean for ch in sep_chars if ch)
    if has_separator or direct_path.suffix:
        return str(direct_path), False, tried

    templates = [
        ".env.{name}",
        ".env/{name}",
        ".env/{name}.env",
        "{name}.env",
        "env/{name}.env",
        "env/{name}",
        "environments/{name}.env",
        "environments/{name}",
    ]
    yaml_templates = [
        ".env.{name}.yaml",
        ".env.{name}.yml",
        "{name}.yaml",
        "{name}.yml",
        "env/{name}.yaml",
        "env/{name}.yml",
        "environments/{name}.yaml",
        "environments/{name}.yml",
    ]

    for template in templates + yaml_templates:
        candidate = Path(template.format(name=clean))
        tried.append(str(candidate))
        if candidate.exists():
            return str(candidate), True, tried

    return str(direct_path), False, tried
class _FlowSeq(list):
    """Sequence rendered in flow-style YAML (e.g., [a, b])."""


class _YamlDumper(yaml.SafeDumper):
    """Custom dumper ensuring sequence indentation matches project style."""

    def increase_indent(self, flow: bool = False, indentless: bool = False):
        return super().increase_indent(flow, False)


def _flow_seq_representer(dumper: yaml.Dumper, value: _FlowSeq):
    return dumper.represent_sequence("tag:yaml.org,2002:seq", value, flow_style=True)


_YamlDumper.add_representer(_FlowSeq, _flow_seq_representer)


def _get_drun_version() -> str:
    """Best-effort version detection for help banner.

    Priority:
    1) Installed package metadata (importlib.metadata)
    2) pyproject.toml under a project root (if available when running from source)
    3) drun.__version__ attribute
    4) "unknown"
    """
    # 1) package metadata (installed/installed in editable)
    try:
        return _im.version("drun")
    except Exception:
        pass

    # 2) pyproject.toml (running from source without installed metadata)
    try:
        here = Path(__file__).resolve()
        for parent in [here.parent, *here.parents]:
            pp = parent / "pyproject.toml"
            if pp.exists():
                text = pp.read_text(encoding="utf-8", errors="ignore")
                in_project = False
                for line in text.splitlines():
                    s = line.strip()
                    if s.startswith("[") and s.endswith("]"):
                        in_project = (s == "[project]")
                    elif in_project and s.startswith("version") and "=" in s:
                        # naive TOML parse: version = "x.y.z"
                        try:
                            _, rhs = s.split("=", 1)
                            v = rhs.strip().strip('"').strip("'")
                            if v:
                                return v
                        except Exception:
                            pass
                break
    except Exception:
        pass

    # 3) module attribute
    try:
        from drun import __version__ as _v  # type: ignore
        if _v:
            return str(_v)
    except Exception:
        pass

    # 4) fallback
    return "unknown"


_APP_HELP = f"drun v{_get_drun_version()} · Zero-code HTTP API test framework"


def _version_callback(value: bool):
    """Display version and exit."""
    if value:
        typer.echo(f"drun version {_get_drun_version()}")
        raise typer.Exit()


app = typer.Typer(add_completion=False, help=_APP_HELP, rich_markup_mode=None)
export_app = typer.Typer()
app.add_typer(export_app, name="export")


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=_version_callback,
        is_eager=True,
    )
):
    """drun - Zero-code HTTP API test framework"""
    pass

# Importers / exporters (lazy optional imports inside functions where needed)


def _emit_tag_list(tags: set[str], case_count: int) -> None:
    """Pretty-print collected tag information."""
    if not tags:
        typer.echo(f"No tags defined in {case_count} cases.")
        return
    typer.echo(f"Cases scanned: {case_count}")
    typer.echo("Tags:")
    for tag in sorted(tags):
        typer.echo(f"  - {tag}")


def parse_kv(items: List[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for it in items:
        if "=" not in it:
            continue
        k, v = it.split("=", 1)
        out[k] = v
    return out


def load_env_file(path: Optional[str]) -> Dict[str, str]:
    # Kept for backward compat; now handled in load_environment
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    # fallback simple parser
    data: Dict[str, str] = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    return data


def _to_yaml_case_dict(case: Case) -> Dict[str, object]:
    # Dump with aliases and prune fields loader forbids at top-level.
    d = case.model_dump(by_alias=True, exclude_none=True)
    for k in ("setup_hooks", "teardown_hooks", "suite_setup_hooks", "suite_teardown_hooks"):
        if k in d and not d.get(k):
            d.pop(k, None)
    # Drop empty config blocks (variables/headers/tags) to keep YAML clean.
    cfg = d.get("config")
    if isinstance(cfg, dict):
        for field in ("variables", "headers", "tags"):
            if not cfg.get(field):
                cfg.pop(field, None)

    steps = d.get("steps") or []
    from drun.models.step import Step as _Step

    default_retry = _Step.model_fields.get("retry").default if "retry" in _Step.model_fields else None
    default_backoff = _Step.model_fields.get("retry_backoff").default if "retry_backoff" in _Step.model_fields else None
    cleaned_steps: List[Dict[str, object]] = []
    for step in steps:
        if not isinstance(step, dict):
            cleaned_steps.append(step)
            continue
        # Normalize validators to shorthand form expected by loader: {'eq': [status_code, 200]}
        raw_validators = step.get("validate", []) or []
        step_validators: List[Dict[str, _FlowSeq]] = []
        for item in raw_validators:
            if not isinstance(item, dict):
                continue
            comparator = item.get("comparator")
            check = item.get("check")
            expect = item.get("expect")
            if comparator and check is not None:
                step_validators.append({str(comparator): _FlowSeq([check, expect])})
        if "validate" in step:
            step.pop("validate", None)

        for field in ("variables", "extract", "setup_hooks", "teardown_hooks", "sql_validate"):
            if field in step and not step.get(field):
                step.pop(field, None)

        req = step.get("request") or {}
        # Normalize legacy alias: 'json' -> 'body'
        if isinstance(req, dict) and ("json" in req) and ("body" not in req):
            req["body"] = req.pop("json")
        headers = req.get("headers") or {}
        headers_lc = {str(k).lower(): v for k, v in headers.items()} if isinstance(headers, dict) else {}
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

        # Add default validators when applicable.
        def _ensure_validator(comp: str, check_value: str | object, expect_value: object) -> None:
            for item in step_validators:
                if comp in item:
                    seq = item[comp]
                    if seq and str(seq[0]) == str(check_value):
                        return
            step_validators.append({comp: _FlowSeq([check_value, expect_value])})

        if expect_json:
            _ensure_validator("contains", "headers.Content-Type", "application/json")

        if ensure_body:
            _ensure_validator("ne", "$", None)

        reorder_keys = ("method", "url", "headers", "params", "body", "data", "files", "auth", "timeout", "verify", "allow_redirects")
        if isinstance(req, dict):
            reordered: Dict[str, object] = {}
            for key in reorder_keys:
                if key in req:
                    reordered[key] = req[key]
            for key, value in req.items():
                if key not in reordered:
                    reordered[key] = value
            step["request"] = reordered

        if step_validators:
            step["validate"] = step_validators

        if "retry" in step and (step["retry"] is None or step["retry"] == default_retry):
            step.pop("retry", None)
        if "retry_backoff" in step and (step["retry_backoff"] is None or step["retry_backoff"] == default_backoff):
            step.pop("retry_backoff", None)

        cleaned_steps.append(step)
    d["steps"] = cleaned_steps
    return d


def _add_step_spacers(text: str) -> str:
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


def _dump_case_dict(obj: Dict[str, object]) -> str:
    raw = yaml.dump(obj, Dumper=_YamlDumper, allow_unicode=True, sort_keys=False)
    return _add_step_spacers(raw)


def _derive_case_name(base: Optional[str], step_name: Optional[str], idx: int) -> str:
    label = (step_name or "").strip() or f"Step {idx}"
    base = (base or "Imported Case").strip() or "Imported Case"
    combined = f"{base} - {label}"
    return combined.strip()


def _sanitize_var_name(name: str) -> str:
    import re as _re
    s = _re.sub(r"[^A-Za-z0-9_]", "_", str(name or "").strip())
    if not s:
        s = "var"
    if s[0].isdigit():
        s = f"v_{s}"
    return s


def _apply_convert_filters(case: Case, *, redact_headers: list[str] | None = None, placeholders: bool = False) -> Case:
    """Mutate case in-place to redact sensitive headers or lift values into variables as placeholders.

    - redact_headers: list of header names (case-insensitive) to mask as '***'.
    - placeholders: when True, convert sensitive headers into variables and reference via $var in headers.
    """
    redact_lc = {h.lower() for h in (redact_headers or [])}
    default_sensitive = {"authorization", "cookie", "x-api-key", "x-api-token", "api-key", "apikey"}
    # if placeholders requested but no explicit headers, use default set
    if placeholders and not redact_lc:
        redact_lc = set(default_sensitive)

    vars_map = dict(case.config.variables or {})

    for st in case.steps:
        req = st.request
        # headers
        hdrs = dict(req.headers or {})
        new_hdrs: dict[str, str] = {}
        for k, v in hdrs.items():
            kl = str(k).lower()
            if kl in redact_lc and isinstance(v, str):
                if placeholders:
                    # Special handling for Authorization: Bearer <token>
                    if kl == "authorization" and v.lower().startswith("bearer "):
                        token_val = v.split(" ", 1)[1]
                        var_name = "token"
                        # avoid overwrite existing values with different content
                        if vars_map.get(var_name) not in (None, token_val):
                            # ensure unique
                            i = 2
                            while f"token{i}" in vars_map:
                                i += 1
                            var_name = f"token{i}"
                        vars_map[var_name] = token_val
                        new_hdrs[k] = f"Bearer ${var_name}"
                    else:
                        var_name = _sanitize_var_name(kl)
                        vars_map[var_name] = v
                        new_hdrs[k] = f"${var_name}"
                else:
                    new_hdrs[k] = "***"
            else:
                new_hdrs[k] = v
        if new_hdrs:
            req.headers = new_hdrs
        # auth
        if placeholders and req.auth and isinstance(req.auth, dict):
            if req.auth.get("type") == "bearer":
                tok = req.auth.get("token")
                if isinstance(tok, str) and not tok.strip().startswith("$"):
                    var_name = "token"
                    if vars_map.get(var_name) not in (None, tok):
                        i = 2
                        while f"token{i}" in vars_map:
                            i += 1
                        var_name = f"token{i}"
                    vars_map[var_name] = tok
                    req.auth["token"] = f"${var_name}"
            elif req.auth.get("type") == "basic":
                u = req.auth.get("username")
                p = req.auth.get("password")
                if isinstance(u, str) and not u.startswith("$"):
                    un = "username"
                    vars_map[un] = u
                    req.auth["username"] = f"${un}"
                if isinstance(p, str) and not p.startswith("$"):
                    pn = "password"
                    vars_map[pn] = p
                    req.auth["password"] = f"${pn}"

    case.config.variables = vars_map or {}
    return case


def _make_step_from_imported(imported_step: Any) -> Step:
    req = StepRequest(
        method=imported_step.method,
        url=imported_step.url,
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
        validators=[Validator(check="status_code", comparator="eq", expect=200)],
    )


def _build_cases_from_import(icase: Any, *, split_output: bool) -> List[Tuple[Case, int]]:
    cases: List[Tuple[Case, int]] = []
    if split_output:
        for idx, imported_step in enumerate(icase.steps, start=1):
            step_obj = _make_step_from_imported(imported_step)
            case_title = _derive_case_name(icase.name, imported_step.name, idx)
            case = Case(config=Config(name=case_title, base_url=icase.base_url, variables=getattr(icase, 'variables', None) or {}), steps=[step_obj])
            cases.append((case, idx))
    else:
        steps = [_make_step_from_imported(s) for s in icase.steps]
        case = Case(config=Config(name=icase.name, base_url=icase.base_url, variables=getattr(icase, 'variables', None) or {}), steps=steps)
        cases.append((case, 1))
    return cases


def _resolve_output_paths(
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


def _write_testsuite_reference(paths: List[Path], names: List[str], *, suite_path: str, suite_name: Optional[str] = None) -> None:
    obj = {
        "config": {
            "name": suite_name or "Imported Testsuite",
        },
        "testcases": [
            {"name": nm, "testcase": str(p)} for nm, p in zip(names, paths)
        ],
    }
    from pathlib import Path as _Path
    from typing import Any as _Any
    out = yaml.dump(obj, Dumper=_YamlDumper, sort_keys=False, allow_unicode=True)
    _p = _Path(suite_path)
    _p.parent.mkdir(parents=True, exist_ok=True)
    _p.write_text(out, encoding="utf-8")
    typer.echo(f"[CONVERT] Wrote testsuite to {suite_path}")


def _write_imported_cases(
    cases_with_index: List[Tuple[Case, int]],
    *,
    outfile: Optional[str],
    into: Optional[str],
    split_output: bool,
    source_path: Optional[str],
) -> None:
    rendered: List[Tuple[Dict[str, object], int, Case]] = [
        (_to_yaml_case_dict(case_obj), idx, case_obj) for case_obj, idx in cases_with_index
    ]
    if into:
        out_dict, _, _case_obj = rendered[0]
        text = _dump_case_dict(out_dict)
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
        p.write_text(_dump_case_dict(data), encoding="utf-8")
        typer.echo(message)
        return

    if split_output:
        paths = _resolve_output_paths(len(rendered), outfile=outfile, source_path=source_path)
        for (out_dict, _, case_obj), path in zip(rendered, paths):
            text = _dump_case_dict(out_dict)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            typer.echo(f"[CONVERT] Wrote YAML for '{case_obj.config.name}' to {path}")
        return

    out_dict, _, _case_obj = rendered[0]
    text = _dump_case_dict(out_dict)
    if outfile:
        path = Path(outfile)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        typer.echo(f"[CONVERT] Wrote YAML to {outfile}")
    else:
        typer.echo(text)


# Unified convert entrypoint (auto-detect by suffix)
@app.command("convert")
def convert_auto(
    infile: str = typer.Argument(..., help="Source file (.curl/.har/.json) to convert"),
    outfile: Optional[str] = typer.Option(None, "--outfile", help="Write output to file"),
    into: Optional[str] = typer.Option(None, "--into", help="Append into existing YAML"),
    case_name: Optional[str] = typer.Option(None, "--case-name", help="Override generated case name"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Override base_url in generated case"),
    split_output: bool = typer.Option(
        False,
        "--split-output/--single-output",
        help="Generate one YAML file per request when supported",
    ),
    # Pass-through options for specific converters (available at top-level for convenience)
    redact: Optional[str] = typer.Option(
        None,
        "--redact",
        help="Comma-separated header names to mask or placeholder, e.g., Authorization,Cookie",
    ),
    placeholders: bool = typer.Option(
        False,
        "--placeholders/--no-placeholders",
        help="Replace sensitive headers with $vars and store values in config.variables",
    ),
) -> None:
    # Enforce: options must be after INFILE (no legacy compatibility)
    try:
        argv = list(sys.argv)
        i_convert = argv.index("convert")
    except ValueError:
        i_convert = -1
    if i_convert >= 0:
        tail = argv[i_convert + 1 :]
        # locate infile token in raw argv
        cand_suffix = (".curl", ".har", ".json")
        pos = None
        for i, tok in enumerate(tail):
            if tok == "-" or tok.lower().endswith(cand_suffix):
                pos = i
                break
        if pos is not None and any(t.startswith("-") for t in tail[:pos]):
            typer.echo("[CONVERT] Options must follow INFILE. Example:\n  drun convert file.curl --outfile out.yaml")
            raise typer.Exit(code=2)
    # Enforce: no bare conversion without any options
    any_option = any([
        outfile is not None,
        into is not None,
        case_name is not None,
        base_url is not None,
        split_output,
        (redact is not None),
        placeholders,
    ])
    if not any_option:
        typer.echo("[CONVERT] No options provided. Bare conversion is not supported. Place options after INFILE, e.g.:\n  drun convert my.curl --outfile testcases/from_curl.yaml")
        raise typer.Exit(code=2)

    if infile == "-":
        # stdin: treat as curl text
        convert_curl(
            infile=infile,
            outfile=outfile,
            into=into,
            case_name=case_name,
            base_url=base_url,
            split_output=split_output,
            redact=redact,
            placeholders=placeholders,
        )
        return
    suffix = Path(infile).suffix.lower()
    if suffix == ".curl":
        convert_curl(
            infile=infile,
            outfile=outfile,
            into=into,
            case_name=case_name,
            base_url=base_url,
            split_output=split_output,
            redact=redact,
            placeholders=placeholders,
        )
    elif suffix == ".har":
        convert_har(
            infile=infile,
            outfile=outfile,
            into=into,
            case_name=case_name,
            base_url=base_url,
            split_output=split_output,
            redact=redact,
            placeholders=placeholders,
        )
    elif suffix == ".json":
        # Try Postman by default; if 'openapi' field detected, prefer OpenAPI
        data = {}
        try:
            data = json.loads(Path(infile).read_text(encoding="utf-8"))
        except Exception:
            pass
        if isinstance(data, dict) and data.get("openapi"):
            convert_openapi(
                spec=infile,
                outfile=outfile,
                case_name=case_name,
                base_url=base_url,
                split_output=split_output,
                redact=redact,
                placeholders=placeholders,
            )
        else:
            convert_postman(
                collection=infile,
                outfile=outfile,
                into=into,
                case_name=case_name,
                base_url=base_url,
                split_output=split_output,
                redact=redact,
                placeholders=placeholders,
            )
    else:
        typer.echo("[CONVERT] Unrecognized file format. Supported suffixes: .curl, .har, .json")
        raise typer.Exit(code=2)


# Helper for curl conversion
def convert_curl(
    infile: str = typer.Argument(..., help="Path to file with curl commands or '-' for stdin"),
    redact: Optional[str] = typer.Option(None, "--redact", help="Comma-separated header names to mask or placeholder, e.g., Authorization,Cookie"),
    placeholders: bool = typer.Option(False, "--placeholders/--no-placeholders", help="Replace sensitive headers with $vars and store values in config.variables"),
    outfile: Optional[str] = typer.Option(None, "--outfile", help="Write to new YAML file (default stdout)"),
    into: Optional[str] = typer.Option(None, "--into", help="Append into existing YAML (case or suite)"),
    case_name: Optional[str] = typer.Option(None, "--case-name", help="Case name; default 'Imported Case'"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Override base_url in generated case"),
    split_output: bool = typer.Option(
        False,
        "--split-output/--single-output",
        help="Generate one YAML file per curl command when the source has multiple commands",
    ),
) -> None:
    from drun.importers.curl import parse_curl_text

    # Read input
    if infile == "-":
        text = typer.get_text_stream("stdin").read()
    else:
        # Enforce .curl suffix for curl files
        pth = Path(infile)
        if pth.suffix.lower() != ".curl":
            typer.echo(f"[CONVERT] Refusing to read '{infile}': curl file must have '.curl' suffix.")
            raise typer.Exit(code=2)
        text = pth.read_text(encoding="utf-8")

    icase = parse_curl_text(text, case_name=case_name, base_url=base_url)

    if not icase.steps:
        typer.echo("[CONVERT] No curl commands detected in input.")
        return

    if split_output and into:
        typer.echo("[CONVERT] --split-output cannot be combined with --into; provide --outfile or rely on inferred names.")
        raise typer.Exit(code=2)

    cases = _build_cases_from_import(icase, split_output=split_output)
    redact_list = [x.strip() for x in (redact or '').split(',') if x.strip()]
    cases = [(_apply_convert_filters(case, redact_headers=redact_list, placeholders=placeholders), idx) for case, idx in cases]
    source_path = None if infile == "-" else infile
    _write_imported_cases(
        cases,
        outfile=outfile,
        into=into,
        split_output=split_output,
        source_path=source_path,
    )


def convert_postman(
    collection: str = typer.Argument(..., help="Postman collection v2 JSON file"),
    outfile: Optional[str] = typer.Option(None, "--outfile"),
    into: Optional[str] = typer.Option(None, "--into"),
    case_name: Optional[str] = typer.Option(None, "--case-name"),
    base_url: Optional[str] = typer.Option(None, "--base-url"),
    postman_env: Optional[str] = typer.Option(None, "--postman-env", help="Postman environment JSON to import variables"),
    redact: Optional[str] = typer.Option(None, "--redact", help="Comma-separated header names to mask or placeholder, e.g., Authorization,Cookie"),
    placeholders: bool = typer.Option(False, "--placeholders/--no-placeholders", help="Replace sensitive headers with $vars and store values in config.variables"),
    suite_out: Optional[str] = typer.Option(None, "--suite-out", help="Write a reference testsuite YAML that includes generated case files (requires --split-output or --outfile)"),
    split_output: bool = typer.Option(
        False,
        "--split-output/--single-output",
        help="Generate one YAML file per request when the collection has multiple items",
    ),
) -> None:
    from drun.importers.postman import parse_postman

    text = Path(collection).read_text(encoding="utf-8")
    env_text = None
    if postman_env:
        env_text = Path(postman_env).read_text(encoding="utf-8")
    icase = parse_postman(text, case_name=case_name, base_url=base_url, env_text=env_text)

    if not icase.steps:
        typer.echo("[CONVERT] No requests detected in Postman collection.")
        return
    if split_output and into:
        typer.echo("[CONVERT] --split-output cannot be combined with --into; provide --outfile or rely on inferred names.")
        raise typer.Exit(code=2)

    cases = _build_cases_from_import(icase, split_output=split_output)
    redact_list = [x.strip() for x in (redact or '').split(',') if x.strip()]
    cases = [(_apply_convert_filters(case, redact_headers=redact_list, placeholders=placeholders), idx) for case, idx in cases]
    _write_imported_cases(
        cases,
        outfile=outfile,
        into=into,
        split_output=split_output,
        source_path=collection,
    )
    # Optional suite generation
    if suite_out:
        if into:
            typer.echo("[CONVERT] --suite-out cannot be combined with --into")
            raise typer.Exit(code=2)
        # compute case paths/names similar to writer
        names = [c.config.name or f"Case {i}" for (c, i) in cases]
        if split_output:
            paths = _resolve_output_paths(len(cases), outfile=outfile, source_path=collection)
        else:
            if outfile:
                paths = [Path(outfile)]
            else:
                typer.echo("[CONVERT] --suite-out requires --split-output or --outfile to materialize case files")
                raise typer.Exit(code=2)
        _write_testsuite_reference(paths, names, suite_path=suite_out, suite_name=case_name or icase.name)


def convert_har(
    infile: str = typer.Argument(..., help="HAR file to convert"),
    outfile: Optional[str] = typer.Option(None, "--outfile"),
    into: Optional[str] = typer.Option(None, "--into"),
    case_name: Optional[str] = typer.Option(None, "--case-name"),
    base_url: Optional[str] = typer.Option(None, "--base-url"),
    redact: Optional[str] = typer.Option(None, "--redact", help="Comma-separated header names to mask or placeholder, e.g., Authorization,Cookie"),
    placeholders: bool = typer.Option(False, "--placeholders/--no-placeholders", help="Replace sensitive headers with $vars and store values in config.variables"),
    exclude_static: bool = typer.Option(True, "--exclude-static/--keep-static", help="Filter out images/css/js/font entries"),
    only_2xx: bool = typer.Option(False, "--only-2xx/--all-status", help="Keep only responses with 2xx status code"),
    exclude_pattern: Optional[str] = typer.Option(None, "--exclude-pattern", help="Regex to exclude entries by URL or mimeType"),
    split_output: bool = typer.Option(
        False,
        "--split-output/--single-output",
        help="Generate one YAML file per HAR entry when the source has multiple requests",
    ),
) -> None:
    from drun.importers.har import parse_har

    text = Path(infile).read_text(encoding="utf-8")
    icase = parse_har(
        text,
        case_name=case_name,
        base_url=base_url,
        exclude_static=exclude_static,
        only_2xx=only_2xx,
        exclude_pattern=exclude_pattern,
    )
    if not icase.steps:
        typer.echo("[CONVERT] No HTTP entries detected in HAR file.")
        return
    if split_output and into:
        typer.echo("[CONVERT] --split-output cannot be combined with --into; provide --outfile or rely on inferred names.")
        raise typer.Exit(code=2)

    cases = _build_cases_from_import(icase, split_output=split_output)
    redact_list = [x.strip() for x in (redact or '').split(',') if x.strip()]
    cases = [(_apply_convert_filters(case, redact_headers=redact_list, placeholders=placeholders), idx) for case, idx in cases]
    _write_imported_cases(
        cases,
        outfile=outfile,
        into=into,
        split_output=split_output,
        source_path=infile,
    )
@export_app.command("curl")
def export_curl(
    path: str = typer.Argument(..., help="Case/Suite YAML file or directory to export"),
    case_name: Optional[str] = typer.Option(None, "--case-name", help="Only export a specific case name"),
    steps: Optional[str] = typer.Option(None, "--steps", help="Step indexes, e.g., '1,3-5' (1-based)"),
    multiline: bool = typer.Option(True, "--multiline/--one-line", help="Format curl on multiple lines with continuations"),
    shell: str = typer.Option("sh", "--shell", help="Line continuation style: sh|ps"),
    redact: Optional[str] = typer.Option(None, "--redact", help="Comma-separated header names to mask, e.g., Authorization,Cookie"),
    with_comments: bool = typer.Option(False, "--with-comments/--no-comments", help="Prepend '# Case/Step' comments to each curl"),
    outfile: Optional[str] = typer.Option(None, "--outfile", help="Write output to file (must end with .curl when provided)"),
) -> None:
    from drun.exporters.curl import step_to_curl, step_placeholders
    out_lines: List[str] = []

    env_name = os.environ.get("DRUN_ENV")
    env_store = load_environment(env_name, ".env")

    files: List[str] = []
    p = Path(path)
    if p.is_dir():
        from drun.loader.collector import discover
        files = discover([path])
    else:
        files = [path]

    def parse_steps_spec(spec: Optional[str], maxn: int) -> List[int]:
        if not spec:
            return list(range(maxn))
        out: List[int] = []
        for part in spec.split(','):
            part = part.strip()
            if not part:
                continue
            if '-' in part:
                a, b = part.split('-', 1)
                try:
                    ia = max(1, int(a))
                    ib = min(maxn, int(b))
                except Exception:
                    continue
                out.extend(list(range(ia-1, ib)))
            else:
                try:
                    i = int(part)
                    if 1 <= i <= maxn:
                        out.append(i-1)
                except Exception:
                    pass
        # dedupe preserve order
        seen=set(); res=[]
        for i in out:
            if i not in seen:
                res.append(i); seen.add(i)
        return res

    redact_list = [x.strip() for x in (redact or '').split(',') if x.strip()]

    if outfile and not outfile.lower().endswith('.curl'):
        typer.echo(f"[EXPORT] Outfile must end with '.curl': {outfile}")
        raise typer.Exit(code=2)

    from pathlib import Path as _Path
    for f in files:
        cases, _meta = load_yaml_file(_Path(f))
        if case_name:
            cases = [c for c in cases if (c.config.name or "") == case_name]
        for c in cases:
            if not c.config.base_url:
                base_from_env = env_store.get("BASE_URL") or env_store.get("base_url")
                if base_from_env:
                    c.config.base_url = str(base_from_env)
            idxs = parse_steps_spec(steps, len(c.steps))
            for j, idx in enumerate(idxs, start=1):
                if with_comments:
                    cname = c.config.name or 'Unnamed'
                    sname = c.steps[idx].name or f"Step {idx+1}"
                    out_lines.append(f"# Case: {cname} | Step {idx+1}: {sname}")
                    # Add placeholder annotations such as $token or ${...}
                    vars_set, exprs_set = step_placeholders(c, idx)
                    if vars_set:
                        out_lines.append("# Vars: " + " ".join(sorted(vars_set)))
                    if exprs_set:
                        out_lines.append("# Exprs: " + " ".join(sorted(exprs_set)))
                out_lines.append(step_to_curl(c, idx, multiline=multiline, shell=shell, redact=redact_list, envmap=env_store))

    output = "\n\n".join(out_lines)
    if outfile:
        Path(outfile).write_text(output, encoding="utf-8")
        typer.echo(f"[EXPORT] Wrote {len(out_lines)} curl commands to {outfile}")
    else:
        typer.echo(output)
@app.command("tags")
def list_tags(
    path: str = typer.Argument("testcases", help="File or directory to scan for YAML test cases"),
) -> None:
    """List all unique tags used by the discovered test cases."""
    files = discover([path])
    if not files:
        from pathlib import Path as _Path
        typer.echo(f"No YAML test files found at: {path}")
        pth = _Path(path)
        # Friendly hints and likely fixes
        hints: list[str] = []
        # Suggest missing extension correction
        if not pth.exists():
            # if user omitted extension, suggest .yaml/.yml
            if not pth.suffix:
                for ext in (".yaml", ".yml"):
                    cand = pth.with_suffix(ext)
                    if cand.exists():
                        hints.append(f"Did you mean: drun run {cand}")
                        break
        else:
            if pth.is_file():
                if pth.suffix.lower() not in {".yaml", ".yml"}:
                    hints.append("Only .yaml/.yml files are recognized.")
                    for ext in (".yaml", ".yml"):
                        cand = pth.with_suffix(ext)
                        if cand.exists():
                            hints.append(f"Try: drun run {cand}")
                            break
            elif pth.is_dir():
                hints.append("Provide a YAML file or a directory containing YAML tests under testcases/ or testsuites/.")
        # Always provide examples
        hints.append("Examples:")
        hints.append("  drun run testcases")
        hints.append("  drun run testcases/test_hello.yaml")
        hints.append("  drun run testsuites/testsuite_smoke.yaml")
        for h in hints:
            typer.echo(h)
        raise typer.Exit(code=2)

    collected: Dict[str, set[tuple[str, str]]] = {}
    case_count = 0
    diagnostics: List[str] = []

    for f in files:
        try:
            cases, _meta = load_yaml_file(f)
        except Exception as exc:  # pragma: no cover - defensive
            diagnostics.append(f"[WARN] Failed to parse {f}: {exc}")
            continue
        if not cases:
            diagnostics.append(f"[INFO] No cases found in {f}")
            continue
        diagnostics.append(f"[OK] {f} -> {len(cases)} cases")
        for c in cases:
            case_count += 1
            tags = c.config.tags or []
            case_name = c.config.name or "Unnamed"
            entry = (case_name, str(f))
            if not tags:
                collected.setdefault("<no-tag>", set()).add(entry)
            for tag in tags:
                collected.setdefault(tag, set()).add(entry)

    for line in diagnostics:
        typer.echo(line)
    # Detailed tag summary
    typer.echo("\nTag Summary:")
    for tag, cases_for_tag in sorted(collected.items(), key=lambda item: item[0]):
        typer.echo(f"- {tag}: {len(cases_for_tag)} cases")
        for case_name, case_path in sorted(cases_for_tag):
            typer.echo(f"    • {case_name} -> {case_path}")


@app.command()
def run(
    path: str = typer.Argument(..., help="File or directory to run"),
    k: Optional[str] = typer.Option(None, "-k", help="Tag filter expression (and/or/not)"),
    vars: List[str] = typer.Option([], "--vars", help="Variable overrides k=v (repeatable)"),
    failfast: bool = typer.Option(False, "--failfast", help="Stop on first failure"),
    report: Optional[str] = typer.Option(None, "--report", help="Write JSON report to file"),
    html: Optional[str] = typer.Option(None, "--html", help="Write HTML report to file (default reports/report-<timestamp>.html)"),
    allure_results: Optional[str] = typer.Option(None, "--allure-results", help="Write Allure results to directory (for allure generate)"),
    log_level: str = typer.Option("INFO", "--log-level", help="Logging level"),
    env_file: Optional[str] = typer.Option(None, "--env-file", help=".env file path (default .env)"),
    log_file: Optional[str] = typer.Option(None, "--log-file", help="Write console logs to file (default logs/run-<ts>.log)"),
    httpx_logs: bool = typer.Option(False, "--httpx-logs/--no-httpx-logs", help="Show httpx internal request logs", show_default=False),
    reveal_secrets: bool = typer.Option(True, "--reveal-secrets/--mask-secrets", help="Show sensitive fields (password, tokens) in plaintext logs and reports", show_default=True),
    response_headers: bool = typer.Option(
        False,
        "--response-headers/--no-response-headers",
        help="Log HTTP response headers (default off)",
        show_default=False,
    ),
    notify: Optional[str] = typer.Option(None, "--notify", help="Notify channels, comma-separated: feishu,email,dingtalk"),
    notify_only: Optional[str] = typer.Option(
        None,
        "--notify-only",
        help="Notify policy: failed|always (defaults to $DRUN_NOTIFY_ONLY or 'failed')",
        show_default=False,
    ),
    notify_attach_html: bool = typer.Option(False, "--notify-attach-html/--no-notify-attach-html", help="Attach HTML report in email (if email enabled)", show_default=False),
):
    # default log file path
    ts = time.strftime("%Y%m%d-%H%M%S")
    default_log = log_file or f"logs/run-{ts}.log"
    setup_logging(log_level, log_file=default_log)
    log = get_logger("drun.cli")
    # unify httpx logs: default suppress, unless enabled
    import logging as _logging
    _httpx_logger = _logging.getLogger("httpx")
    _httpx_logger.setLevel(_logging.INFO if httpx_logs else _logging.WARNING)

    # Default env file (.env) when not provided
    env_file_explicit = env_file is not None
    env_file_input = env_file or ".env"
    if env_file_explicit:
        resolved_env_file, alias_used, tried_candidates = _resolve_env_file_alias(env_file_input)
        env_file = resolved_env_file
        if alias_used:
            log.info(f"[ENV] Using env alias '{env_file_input}' -> '{env_file}'")
        if not Path(env_file).exists():
            tried_text = ", ".join(tried_candidates) if tried_candidates else env_file_input
            raise typer.BadParameter(
                f"Env file '{env_file_input}' not found. Tried: {tried_text}",
                param='--env-file',
            )
    else:
        env_file = env_file_input
        log.info(f"[ENV] Using default env file: {env_file}")

    # Global variables from env file and CLI overrides
    # Unified env loading: --env <name> YAML + --env-file (kv or yaml) + OS ENV
    env_name: Optional[str] = os.environ.get("DRUN_ENV")  # optional default via env var
    env_store = load_environment(env_name, env_file)
    # Sync env_store to os.environ for notification and other integrations
    for env_key, env_val in env_store.items():
        if env_key and isinstance(env_val, str) and env_key.upper() == env_key:  # Only uppercase keys (skip lowercase duplicates)
            os.environ.setdefault(env_key, env_val)
    # Preflight: warn when default env file is missing and no BASE_URL provided anywhere
    from pathlib import Path as _Path
    _env_exists = _Path(env_file).exists() if env_file else False
    _base_any = os.environ.get("BASE_URL") or os.environ.get("base_url") or None
    if not _base_any:
        _base_any = env_store.get("BASE_URL") or env_store.get("base_url")
    if (not _env_exists) and (not env_file_explicit) and (not _base_any):
        log.warning(
            "[ENV] Default .env not found and BASE_URL is missing. Relative URLs may fail. "
            "Create a .env or pass --env-file/--vars. Example .env:\n"
            "BASE_URL=http://localhost:8000\nUSER_USERNAME=test_user\nUSER_PASSWORD=test_pass\nSHIPPING_ADDRESS=Test Address"
        )
    cli_vars = parse_kv(vars)
    # Only CLI --vars go into templating variables directly
    global_vars: Dict[str, str] = {}
    for k2, v2 in cli_vars.items():
        global_vars[k2] = v2
        global_vars[k2.lower()] = v2

    # Always honor user-provided tag filter `-k`.
    # Previously we neutralized `-k` when it matched an env key, which caused
    # confusing behavior (e.g., `-k auth` ignored if ENV has AUTH/auth).
    # That heuristic is removed to ensure explicit filters are respected.
    # Discover files
    typer.echo(f"Filter expression: {k!r}")
    files = discover([path])
    if not files:
        from pathlib import Path as _Path
        typer.echo(f"No YAML test files found at: {path}")
        pth = _Path(path)
        hints: list[str] = []
        if not pth.exists():
            hints.append("Path does not exist. Create it or use an existing directory/file.")
            if not pth.suffix:
                for ext in (".yaml", ".yml"):
                    cand = pth.with_suffix(ext)
                    if cand.exists():
                        hints.append(f"Did you mean: drun run {cand}")
                        break
        else:
            if pth.is_file():
                if pth.suffix.lower() not in {".yaml", ".yml"}:
                    hints.append("Only .yaml/.yml files are recognized.")
                    for ext in (".yaml", ".yml"):
                        cand = pth.with_suffix(ext)
                        if cand.exists():
                            hints.append(f"Try: drun run {cand}")
                            break
            elif pth.is_dir():
                hints.append("Provide a YAML file or a directory containing YAML tests under testcases/ or testsuites/.")
        hints.append("Examples:")
        hints.append("  drun run testcases")
        hints.append("  drun run testcases/test_hello.yaml")
        hints.append("  drun run testsuites/testsuite_smoke.yaml")
        for h in hints:
            typer.echo(h)
        raise typer.Exit(code=2)

    # Load cases
    items: List[tuple[Case, Dict[str, str]]] = []
    debug_info: List[str] = []
    for f in files:
        try:
            loaded, meta = load_yaml_file(f)
        except LoadError as exc:
            log.error(str(exc))
            raise typer.Exit(code=2)
        debug_info.append(f"file={f} cases={len(loaded)}")
        # tag filter on case level
        for c in loaded:
            tags = c.config.tags or []
            m = match_tags(tags, k)
            debug_info.append(f"  case={c.config.name!r} tags={tags} match={m}")
            if m:
                items.append((c, meta))

    if not items:
        typer.echo("No cases matched tag expression.")
        # extra diagnostics
        for line in debug_info:
            typer.echo(line)
        raise typer.Exit(code=2)

    # Execute
    runner = Runner(
        log=log,
        failfast=failfast,
        log_debug=(log_level.upper() == "DEBUG"),
        reveal_secrets=reveal_secrets,
        log_response_headers=response_headers,
    )
    templater = TemplateEngine()
    instance_results = []
    log.info(f"[RUN] Discovered files: {len(files)} | Matched cases: {len(items)} | Failfast={failfast}")
    # Sanity check: ensure cases with relative step URLs have a base_url from any source
    def _need_base_url(case: Case) -> bool:
        try:
            for st in case.steps:
                u = (st.request.url or "").strip()
                # if not absolute (no scheme), we treat it as relative and require base_url
                if not (u.startswith("http://") or u.startswith("https://")):
                    return True
            return False
        except Exception:
            return False

    for c, meta in items:
        funcs = get_functions_for(Path(meta.get("file", path)).resolve())
        param_sets = expand_parameters(c.parameters, source_path=meta.get("file"))
        for ps in param_sets:
            # Promote BASE_URL to base_url if not set
            if (not c.config.base_url) and (base := global_vars.get("BASE_URL") or global_vars.get("base_url") or env_store.get("BASE_URL") or env_store.get("base_url")):
                c.config.base_url = base
            # Render base_url if it contains template syntax
            if c.config.base_url and ("{{" in c.config.base_url or "${" in c.config.base_url):
                c.config.base_url = templater.render_value(c.config.base_url, global_vars, funcs, envmap=env_store)
            # If case has relative URLs but still no base_url after all sources, print a clear guidance and exit
            if _need_base_url(c) and not (c.config.base_url and str(c.config.base_url).strip()):
                msg_lines = [
                    "[ERROR] base_url is required for cases using relative URLs.",
                    f"        Case: {c.config.name or 'Unnamed'} | Source: {meta.get('file', path)}",
                    "        Provide base_url in one of the following ways:",
                    f"          - Create an env file: {env_file} (recommended)",
                    "              BASE_URL=http://localhost:8000",
                    "              USER_USERNAME=test_user",
                    "              USER_PASSWORD=test_pass",
                    "              SHIPPING_ADDRESS=Test Address",
                    "          - Or pass CLI vars: --vars base_url=http://localhost:8000",
                    "          - Or export env:   export BASE_URL=http://localhost:8000",
                    "        Tip: use --env-file <path> to specify a different env file.",
                ]
                for line in msg_lines:
                    typer.echo(line)
                raise typer.Exit(code=2)
            log.info(f"[CASE] Start: {c.config.name or 'Unnamed'} | params={ps}")
            res = runner.run_case(c, global_vars=global_vars, params=ps, funcs=funcs, envmap=env_store, source=meta.get("file"))
            log.info(f"[CASE] Result: {res.name} | status={res.status} | duration={res.duration_ms:.1f}ms")
            instance_results.append(res)
            if failfast and res.status == "failed":
                break

    report_obj: RunReport = runner.build_report(instance_results)
    # Print summary (standardized log format)
    s = report_obj.summary
    log.info(
        "[CASE] Total: %s Passed: %s Failed: %s Skipped: %s Duration: %.1fms",
        s["total"], s.get("passed", 0), s.get("failed", 0), s.get("skipped", 0), s.get("duration_ms", 0.0)
    )
    if "steps_total" in s:
        log.info(
            "[STEP] Total: %s Passed: %s Failed: %s Skipped: %s",
            s.get("steps_total", 0),
            s.get("steps_passed", 0),
            s.get("steps_failed", 0),
            s.get("steps_skipped", 0),
        )

    html_target = html or f"reports/report-{ts}.html"

    if report:
        write_json(report_obj, report)
        log.info("[CASE] JSON report written to %s", report)
    from drun.reporter.html_reporter import write_html
    write_html(report_obj, html_target)
    log.info("[CASE] HTML report written to %s", html_target)

    if allure_results:
        try:
            from drun.reporter.allure_reporter import write_allure_results
            write_allure_results(report_obj, allure_results)
            log.info("[CASE] Allure results written to %s", allure_results)
        except Exception as e:
            log = get_logger("drun.cli")
            log.error(f"Failed to write Allure results: {e}")

    # Notifications (best-effort)
    try:
        from drun.notifier import (
            NotifyContext,
            FeishuNotifier,
            EmailNotifier,
            DingTalkNotifier,
            build_summary_text,
        )

        channels_spec = notify if notify is not None else os.environ.get("DRUN_NOTIFY", "")
        channels = [c.strip().lower() for c in channels_spec.split(",") if c.strip()]
        if not channels:
            auto_channels: List[str] = []
            if os.environ.get("FEISHU_WEBHOOK"):
                auto_channels.append("feishu")
            if os.environ.get("DINGTALK_WEBHOOK"):
                auto_channels.append("dingtalk")
            if os.environ.get("SMTP_HOST") or os.environ.get("MAIL_TO"):
                auto_channels.append("email")
            if auto_channels:
                log.info("[NOTIFY] Auto-enabling channels from environment: %s", ", ".join(auto_channels))
            channels = auto_channels
        # deduplicate while preserving order
        seen = set()
        channels = [c for c in channels if not (c in seen or seen.add(c))]
        policy = (notify_only or os.environ.get("DRUN_NOTIFY_ONLY", "failed")).strip().lower()
        topn = int(os.environ.get("NOTIFY_TOPN", "5") or "5")

        log.info("[NOTIFY] channels=%s policy=%s", channels, policy)

        should_send = (
            (policy == "always") or (policy == "failed" and (s.get("failed", 0) or 0) > 0)
        )
        log.info("[NOTIFY] should_send=%s (failed_count=%s)", should_send, s.get("failed", 0))

        if channels and should_send:
            log.info("[NOTIFY] Preparing to send notifications to: %s", ", ".join(channels))
            ctx = NotifyContext(html_path=html_target, log_path=default_log, notify_only=policy, topn=topn)
            notifiers = []

            if "feishu" in channels:
                fw = os.environ.get("FEISHU_WEBHOOK", "").strip()
                if fw:
                    fs = os.environ.get("FEISHU_SECRET")
                    fm = os.environ.get("FEISHU_MENTION")
                    style = os.environ.get("FEISHU_STYLE", "text").lower().strip()
                    notifiers.append(FeishuNotifier(webhook=fw, secret=fs, mentions=fm, style=style))
                    log.info("[NOTIFY] Feishu notifier created (style=%s)", style)
                else:
                    log.warning("[NOTIFY] Feishu channel requested but FEISHU_WEBHOOK not configured")

            if "email" in channels:
                host = os.environ.get("SMTP_HOST", "").strip()
                if host:
                    notifiers.append(
                        EmailNotifier(
                            smtp_host=host,
                            smtp_port=int(os.environ.get("SMTP_PORT", "465") or 465),
                            smtp_user=os.environ.get("SMTP_USER"),
                            smtp_pass=os.environ.get("SMTP_PASS"),
                            mail_from=os.environ.get("MAIL_FROM"),
                            mail_to=os.environ.get("MAIL_TO"),
                            use_ssl=(os.environ.get("SMTP_SSL", "true").lower() != "false"),
                            attach_html=bool(notify_attach_html or (os.environ.get("NOTIFY_ATTACH_HTML", "").lower() in {"1","true","yes"})),
                            html_body=(os.environ.get("NOTIFY_HTML_BODY", "true").lower() != "false"),
                        )
                    )

            if "dingtalk" in channels:
                dw = os.environ.get("DINGTALK_WEBHOOK", "").strip()
                if dw:
                    ds = os.environ.get("DINGTALK_SECRET")
                    mobiles = os.environ.get("DINGTALK_AT_MOBILES", "").strip()
                    at_mobiles = [m.strip() for m in mobiles.split(",") if m.strip()]
                    at_all = os.environ.get("DINGTALK_AT_ALL", "").lower() in {"1", "true", "yes"}
                    style = os.environ.get("DINGTALK_STYLE", "text").lower().strip()
                    notifiers.append(
                        DingTalkNotifier(webhook=dw, secret=ds, at_mobiles=at_mobiles, at_all=at_all, style=style)
                    )

            log.info("[NOTIFY] Sending notifications via %d notifier(s)", len(notifiers))
            for n in notifiers:
                try:
                    notifier_name = n.__class__.__name__
                    log.info("[NOTIFY] Sending via %s...", notifier_name)
                    n.send(report_obj, ctx)
                    log.info("[NOTIFY] %s notification sent successfully", notifier_name)
                except Exception as e:
                    log.error("[NOTIFY] Failed to send via %s: %s", n.__class__.__name__, str(e))
    except Exception as e:
        # never break main flow for notifications
        log.error("[NOTIFY] Notification module error: %s", str(e))

    log.info("[CASE] Logs written to %s", default_log)
    if s.get("failed", 0) > 0:
        raise typer.Exit(code=1)


@app.command("check")
def check(
    path: str = typer.Argument(..., help="File or directory to validate"),
):
    """Validate YAML tests for syntax and style without executing.

    Enforces:
    - Extract uses only `$` syntax
    - Check uses `$` for body, and `status_code`/`headers.*` for metadata
    - Hooks function-name style has required prefixes
    """
    files = discover([path])
    if not files:
        typer.echo("No YAML test files found.")
        raise typer.Exit(code=2)
    # spacing check helper
    def _check_steps_spacing(filepath: Path) -> tuple[bool, str | None]:
        try:
            text = Path(filepath).read_text(encoding="utf-8")
        except Exception as e:
            return False, f"read error: {e}"
        lines = text.splitlines()
        import re as _re
        i = 0
        while i < len(lines):
            m = _re.match(r"^(\s*)steps:\s*$", lines[i])
            if not m:
                i += 1
                continue
            base = len(m.group(1))
            step_indent = base + 2
            seen_first = False
            j = i + 1
            while j < len(lines):
                ln = lines[j]
                # end steps block
                if ln.strip() and (len(ln) - len(ln.lstrip(" ")) <= base) and not ln.lstrip().startswith("-"):
                    break
                if ln.startswith(" " * step_indent + "-"):
                    if seen_first:
                        prev = lines[j - 1] if j - 1 >= 0 else ""
                        if prev.strip() != "":
                            return False, f"steps spacing error near line {j+1}: add a blank line between step items"
                    else:
                        seen_first = True
                j += 1
            i = j
        return True, None

    ok = 0
    for f in files:
        try:
            load_yaml_file(f)
            spacing_ok, spacing_msg = _check_steps_spacing(Path(f))
            if not spacing_ok:
                typer.echo(f"FAIL: {f} -> {spacing_msg}")
                raise typer.Exit(code=2)
            ok += 1
            typer.echo(f"OK: {f}")
        except Exception as e:
            typer.echo(f"FAIL: {f} -> {e}")
            raise typer.Exit(code=2)
    typer.echo(f"Validated {ok} file(s).")


@app.command("fix")
def fix(
    paths: List[str] = typer.Argument(..., help="File(s) or directories to auto-fix YAML (move hooks to config.* / spacing)", metavar="PATH..."),
    only_spacing: bool = typer.Option(False, "--only-spacing", help="Only fix steps spacing (do not move hooks)"),
    only_hooks: bool = typer.Option(False, "--only-hooks", help="Only move hooks into config.* (do not change spacing)"),
):
    """Auto-fix YAML files for style and structure.

    - Move suite/case-level hooks under `config.setup_hooks/config.teardown_hooks`.
    - Ensure a single blank line between adjacent steps items under `steps:`.
    """
    files = discover(paths)
    if not files:
        typer.echo("No YAML test files found.")
        raise typer.Exit(code=2)

    def _merge_hooks(dst_cfg: dict, src_obj: dict, level: str) -> bool:
        changed = False
        for hk in ("setup_hooks", "teardown_hooks"):
            if hk in src_obj and isinstance(src_obj.get(hk), list):
                items = [it for it in src_obj.get(hk) or []]
                if items:
                    # merge with existing config hooks (config first, then moved)
                    existing = list(dst_cfg.get(hk) or [])
                    dst_cfg[hk] = existing + items
                    changed = True
                src_obj.pop(hk, None)
        return changed

    import yaml as _yaml
    import re as _re
    def _fix_steps_spacing(filepath: Path) -> bool:
        try:
            text = Path(filepath).read_text(encoding="utf-8")
        except Exception:
            return False
        lines = text.splitlines()
        changed = False
        i = 0
        while i < len(lines):
            m = _re.match(r"^(\s*)steps:\s*$", lines[i])
            if not m:
                i += 1
                continue
            base = len(m.group(1))
            step_indent = base + 2
            seen_first = False
            j = i + 1
            while j < len(lines):
                ln = lines[j]
                if ln.strip() and (len(ln) - len(ln.lstrip(" ")) <= base) and not ln.lstrip().startswith("-"):
                    break
                if ln.startswith(" " * step_indent + "-"):
                    if seen_first:
                        prev = lines[j - 1] if j - 1 >= 0 else ""
                        if prev.strip() != "":
                            lines.insert(j, "")
                            changed = True
                            j += 1
                    else:
                        seen_first = True
                j += 1
            i = j
        if changed:
            Path(filepath).write_text("\n".join(lines) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
        return changed
    changed_files = []
    for f in files:
        raw = Path(f).read_text(encoding="utf-8")
        try:
            obj = _yaml.safe_load(raw) or {}
        except Exception:
            # skip invalid YAML
            continue
        if not isinstance(obj, dict):
            continue
        modified = False
        if not only_spacing:
            # Suite vs Case: move hooks
            if "cases" in obj and isinstance(obj["cases"], list):
                cfg = obj.get("config") or {}
                if not isinstance(cfg, dict):
                    cfg = {}
                if _merge_hooks(cfg, obj, level="suite"):
                    obj["config"] = cfg
                    modified = True
                new_cases = []
                for c in obj["cases"]:
                    if not isinstance(c, dict):
                        new_cases.append(c)
                        continue
                    c_cfg = c.get("config") or {}
                    if not isinstance(c_cfg, dict):
                        c_cfg = {}
                    if _merge_hooks(c_cfg, c, level="case"):
                        c["config"] = c_cfg
                        modified = True
                    new_cases.append(c)
                obj["cases"] = new_cases
            elif "steps" in obj and isinstance(obj["steps"], list):
                cfg = obj.get("config") or {}
                if not isinstance(cfg, dict):
                    cfg = {}
                if _merge_hooks(cfg, obj, level="case"):
                    obj["config"] = cfg
                    modified = True
            else:
                # not a recognized test file; still attempt spacing fix later
                pass

        if modified and not only_spacing:
            Path(f).write_text(_yaml.dump(obj, Dumper=_YamlDumper, sort_keys=False, allow_unicode=True), encoding="utf-8")
            changed_files.append(str(f))
        # steps spacing fix unless only_hooks
        if not only_hooks and _fix_steps_spacing(Path(f)) and str(f) not in changed_files:
            changed_files.append(str(f))

    if changed_files:
        typer.echo("Fixed files:")
        for p in changed_files:
            typer.echo(f"- {p}")
    else:
        typer.echo("No changes needed.")

@app.command("init")
def init_project(
    name: Optional[str] = typer.Argument(None, help="项目名称（默认为当前目录）"),
    force: bool = typer.Option(False, "--force", help="强制覆盖已存在的文件"),
) -> None:
    """初始化 Drun 测试项目脚手架

    生成完整的项目目录结构，包含：
    - testcases/: 测试用例示例
    - testsuites/: 测试套件示例
    - converts/: 格式转换源文件目录
    - reports/: 报告输出目录
    - logs/: 日志输出目录
    - .env: 环境配置
    - drun_hooks.py: Hooks 函数
    - README.md: 快速上手文档

    示例:
        drun init                    # 在当前目录初始化
        drun init my-api-test        # 创建新项目目录
        drun init --force            # 强制覆盖已存在文件
    """
    from drun import scaffolds

    # 确定目标目录
    if name:
        target_dir = Path(name)
        if target_dir.exists() and not target_dir.is_dir():
            typer.echo(f"[ERROR] '{name}' exists but is not a directory.")
            raise typer.Exit(code=2)
    else:
        target_dir = Path.cwd()

    # 检查是否已存在关键文件
    key_files = ["testcases", ".env", "drun_hooks.py", ".gitignore", "README.md"]
    existing_files = [f for f in key_files if (target_dir / f).exists()]

    if existing_files and not force:
        typer.echo(f"[WARNING] Directory already contains Drun project files: {', '.join(existing_files)}")
        typer.echo("Use --force to overwrite existing files. Existing files will be kept otherwise.")
        if not typer.confirm("Continue without overwriting existing files?", default=False):
            raise typer.Exit(code=0)

    # 开始创建项目
    if name:
        typer.echo(f"\nCreating Drun project: {target_dir}/\n")
    else:
        typer.echo(f"\nInitializing Drun project in current directory\n")

    # 创建目录结构
    dirs_to_create = {
        "testcases": "测试用例目录",
        "testsuites": "测试套件目录",
        "data": "数据文件目录",
        "converts": "格式转换源文件目录",
        "reports": "报告输出目录",
        "logs": "日志输出目录",
    }

    for dir_name, desc in dirs_to_create.items():
        dir_path = target_dir / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)

    # 创建 converts/ 子目录
    convert_subdirs = ["curl", "postman", "har", "openapi"]
    for subdir in convert_subdirs:
        (target_dir / "converts" / subdir).mkdir(parents=True, exist_ok=True)

    # 在 reports 和 logs 目录放置 .gitkeep
    for empty_dir in ["reports", "logs"]:
        gitkeep_path = target_dir / empty_dir / ".gitkeep"
        gitkeep_path.write_text(scaffolds.GITKEEP_CONTENT, encoding="utf-8")

    # 写入文件
    skipped_files: List[str] = []
    overwritten_files: List[str] = []

    def _write_template(rel_path: str, content: str) -> None:
        file_path = target_dir / rel_path
        existed_before = file_path.exists()
        if existed_before and not force:
            skipped_files.append(rel_path)
            typer.echo(f"[SKIP] {rel_path} 已存在，使用 --force 可覆盖。")
            return
        file_path.write_text(content, encoding="utf-8")
        if existed_before and force:
            overwritten_files.append(rel_path)

    # testcases/test_demo.yaml
    _write_template("testcases/test_demo.yaml", scaffolds.DEMO_TESTCASE)

    # testcases/test_api_health.yaml
    _write_template("testcases/test_api_health.yaml", scaffolds.HEALTH_TESTCASE)

    # data/users.csv
    _write_template("data/users.csv", scaffolds.CSV_USERS_SAMPLE)

    # testcases/test_import_users.yaml
    _write_template("testcases/test_import_users.yaml", scaffolds.CSV_DATA_TESTCASE)

    # testsuites/testsuite_smoke.yaml
    _write_template("testsuites/testsuite_smoke.yaml", scaffolds.DEMO_TESTSUITE)

    # testsuites/testsuite_csv.yaml
    _write_template("testsuites/testsuite_csv.yaml", scaffolds.CSV_DATA_TESTSUITE)

    # converts/README.md
    _write_template("converts/README.md", scaffolds.CONVERTS_README)

    # converts/curl/sample.curl
    _write_template("converts/curl/sample.curl", scaffolds.SAMPLE_CURL)

    # converts/postman/sample_collection.json
    _write_template("converts/postman/sample_collection.json", scaffolds.SAMPLE_POSTMAN_COLLECTION)

    # converts/postman/sample_environment.json
    _write_template("converts/postman/sample_environment.json", scaffolds.SAMPLE_POSTMAN_ENVIRONMENT)

    # converts/har/sample_recording.har
    _write_template("converts/har/sample_recording.har", scaffolds.SAMPLE_HAR)

    # converts/openapi/sample_openapi.json
    _write_template("converts/openapi/sample_openapi.json", scaffolds.SAMPLE_OPENAPI)

    # .env
    _write_template(".env", scaffolds.ENV_TEMPLATE)

    # drun_hooks.py
    _write_template("drun_hooks.py", scaffolds.HOOKS_TEMPLATE)

    # .gitignore
    _write_template(".gitignore", scaffolds.GITIGNORE_TEMPLATE)

    # README.md
    _write_template("README.md", scaffolds.README_TEMPLATE)

    # 输出创建的文件列表（tree 风格）
    project_name = name if name else "."

    tree_entries = [
        ("├── ", "testcases/", ""),
        ("│   ├── ", "test_demo.yaml", "完整认证流程示例"),
        ("│   ├── ", "test_api_health.yaml", "健康检查示例"),
        ("│   └── ", "test_import_users.yaml", "CSV 参数化示例"),
        ("├── ", "testsuites/", ""),
        ("│   ├── ", "testsuite_smoke.yaml", "冒烟测试套件"),
        ("│   └── ", "testsuite_csv.yaml", "CSV 示例套件"),
        ("├── ", "data/", ""),
        ("│   └── ", "users.csv", "CSV 参数数据示例"),
        ("├── ", "converts/", ""),
        ("│   ├── ", "README.md", "格式转换完整指南"),
        ("│   ├── ", "curl/", ""),
        ("│   │   └── ", "sample.curl", "cURL 命令示例"),
        ("│   ├── ", "postman/", ""),
        ("│   │   ├── ", "sample_collection.json", "Postman Collection"),
        ("│   │   └── ", "sample_environment.json", "Postman 环境变量"),
        ("│   ├── ", "har/", ""),
        ("│   │   └── ", "sample_recording.har", "HAR 录屏示例"),
        ("│   └── ", "openapi/", ""),
        ("│       └── ", "sample_openapi.json", "OpenAPI 规范"),
        ("├── ", "reports/", "测试报告输出目录"),
        ("├── ", "logs/", "运行日志输出目录"),
        ("├── ", ".env", "环境变量配置"),
        ("├── ", "drun_hooks.py", "自定义 Hooks 函数"),
        ("├── ", ".gitignore", "Git 忽略规则"),
        ("└── ", "README.md", "项目文档"),
    ]

    pad = max(len(prefix + entry) for prefix, entry, desc in tree_entries if desc) + 8

    typer.echo(f"{project_name}")
    for prefix, entry, desc in tree_entries:
        full = f"{prefix}{entry}"
        if desc:
            typer.echo(f"{full.ljust(pad)}{desc}")
        else:
            typer.echo(full)
    typer.echo("")
    typer.echo("9 directories, 16 files")

    if skipped_files:
        typer.echo("")
        typer.echo("保留已有文件（未覆盖）:")
        for rel_path in skipped_files:
            typer.echo(f"  - {rel_path}")

    if overwritten_files:
        typer.echo("")
        typer.echo("已覆盖文件 (--force):")
        for rel_path in overwritten_files:
            typer.echo(f"  - {rel_path}")

    typer.echo("")
    typer.echo("✅ 项目初始化完成！")
    typer.echo("")
    typer.echo("快速开始:")
    if name:
        typer.echo(f"  cd {name}")
    typer.echo("  drun run testcases/test_api_health.yaml")
    typer.echo("  drun run testcases/test_import_users.yaml  # CSV 数据驱动示例")
    typer.echo("")
    typer.echo("格式转换 (查看 converts/README.md 获取详细说明):")
    typer.echo("  - cURL 转用例:")
    typer.echo("    drun convert converts/curl/sample.curl --outfile testcases/new_test.yaml")
    typer.echo("  - Postman 转用例:")
    typer.echo("    drun convert converts/postman/sample_collection.json --split-output --suite-out testsuites/new_suite.yaml")
    typer.echo("  - HAR 转用例:")
    typer.echo("    drun convert converts/har/sample_recording.har --exclude-static --only-2xx --outfile testcases/from_har.yaml")
    typer.echo("  - OpenAPI 转用例:")
    typer.echo("    drun convert-openapi converts/openapi/sample_openapi.json --split-output --outfile testcases/from_openapi.yaml")
    typer.echo("")
    typer.echo("文档: https://github.com/Devliang24/drun")


@app.command("convert-openapi")
def convert_openapi(
    spec: str = typer.Argument(..., help="OpenAPI 3.x spec file (.json or .yaml)"),
    outfile: Optional[str] = typer.Option(None, "--outfile"),
    case_name: Optional[str] = typer.Option(None, "--case-name"),
    base_url: Optional[str] = typer.Option(None, "--base-url"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated tags to include (case-sensitive)"),
    split_output: bool = typer.Option(False, "--split-output/--single-output", help="One YAML per operation"),
    redact: Optional[str] = typer.Option(None, "--redact", help="Comma-separated header names to mask or placeholder, e.g., Authorization,Cookie"),
    placeholders: bool = typer.Option(False, "--placeholders/--no-placeholders", help="Replace sensitive headers with $vars and store values in config.variables"),
) -> None:
    from drun.importers.openapi import parse_openapi
    text = Path(spec).read_text(encoding="utf-8")
    tag_list = [t.strip() for t in (tags or '').split(',') if t.strip()]
    icase = parse_openapi(text, case_name=case_name, base_url=base_url, tags=tag_list or None)
    if not icase.steps:
        typer.echo("[CONVERT] No operations detected in OpenAPI spec.")
        return
    cases = _build_cases_from_import(icase, split_output=split_output)
    redact_list = [x.strip() for x in (redact or '').split(',') if x.strip()]
    cases = [(_apply_convert_filters(case, redact_headers=redact_list, placeholders=placeholders), idx) for case, idx in cases]
    _write_imported_cases(
        cases,
        outfile=outfile,
        into=None,
        split_output=split_output,
        source_path=spec,
    )


if __name__ == "__main__":
    app()

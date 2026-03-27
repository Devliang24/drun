from __future__ import annotations

import json
import os
import re
import sys
from importlib import metadata as _im
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import typer
import yaml

from drun.commands.check import run_check
from drun.commands.fix import run_fix
from drun.commands.run import run_cases
from drun.commands.tags import run_tags
from drun.extensions import get_importer, resolve_exporter
from drun.loader.collector import discover
from drun.loader.yaml_loader import load_yaml_file
from drun.loader.env import load_environment
from drun.models.case import Case
from drun.models.config import Config
from drun.models.request import StepRequest
from drun.models.step import Step
from drun.models.validators import Validator
from drun.runner.runner import Runner

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
    1) drun.__version__ attribute
    2) pyproject.toml under a project root (if available when running from source)
    3) Installed package metadata (importlib.metadata)
    4) "unknown"
    """
    # 1) module attribute
    try:
        from drun import __version__ as _v  # type: ignore
        if _v:
            return str(_v)
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

    # 3) package metadata (installed/installed in editable)
    try:
        return _im.version("drun")
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
export_app = typer.Typer(help="导出测试用例到其他格式")
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

        for field in ("variables", "extract", "setup_hooks", "teardown_hooks"):
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


def _write_caseflow(paths: List[Path], names: List[str], *, suite_path: str, suite_name: Optional[str] = None) -> None:
    """生成 caseflow 格式的测试套件文件"""
    obj = {
        "config": {
            "name": suite_name or "Imported Caseflow",
        },
        "caseflow": [
            {"name": nm, "invoke": p.stem} for nm, p in zip(names, paths)
        ],
    }
    from pathlib import Path as _Path
    out = yaml.dump(obj, Dumper=_YamlDumper, sort_keys=False, allow_unicode=True)
    _p = _Path(suite_path)
    _p.parent.mkdir(parents=True, exist_ok=True)
    _p.write_text(out, encoding="utf-8")
    typer.echo(f"[CONVERT] Wrote caseflow to {suite_path}")


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


def _require_importer(format_name: str):
    importer = get_importer(format_name)
    if importer is None:
        typer.echo(f"[CONVERT] No importer registered for format: {format_name}")
        raise typer.Exit(code=2)
    return importer


def _require_exporter(format_name: str):
    exporter = resolve_exporter(format_name)
    if exporter is None:
        typer.echo(f"[EXPORT] No exporter registered for format: {format_name}")
        raise typer.Exit(code=2)
    return exporter


# Unified convert entrypoint (auto-detect by suffix)
@app.command("convert")
def convert_auto(
    infile: str = typer.Argument(..., help="待转换的源文件 (.curl/.har/.json)"),
    outfile: Optional[str] = typer.Option(None, "--outfile", help="输出到指定文件"),
    into: Optional[str] = typer.Option(None, "--into", help="追加到已存在的 YAML 文件"),
    case_name: Optional[str] = typer.Option(None, "--case-name", help="覆盖生成的用例名称"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="覆盖生成用例的 base_url"),
    postman_env: Optional[str] = typer.Option(None, "--postman-env", help="Postman 环境 JSON 文件，用于导入变量"),
    suite_out: Optional[str] = typer.Option(None, "--suite-out", help="生成引用测试套件 YAML（需配合 --split-output 或 --outfile）"),
    split_output: bool = typer.Option(
        False,
        "--split-output/--single-output",
        help="每个请求生成独立的 YAML 文件",
    ),
    # Pass-through options for specific converters (available at top-level for convenience)
    redact: Optional[str] = typer.Option(
        None,
        "--redact",
        help="逗号分隔的需要脱敏的请求头名称，如 Authorization,Cookie",
    ),
    placeholders: bool = typer.Option(
        False,
        "--placeholders/--no-placeholders",
        help="将敏感请求头替换为 $变量 并保存到 config.variables",
    ),
) -> None:
    """转换格式（支持 .curl/.har/.json）到 YAML 测试用例"""
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
        postman_env is not None,
        suite_out is not None,
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
            exclude_static=True,
            only_2xx=False,
            exclude_pattern=None,
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
                tags=None,
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
                postman_env=postman_env,
                suite_out=suite_out,
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
    parse_curl_text = _require_importer("curl")

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
    parse_postman = _require_importer("postman")

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
        _write_caseflow(paths, names, suite_path=suite_out, suite_name=case_name or icase.name)


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
    parse_har = _require_importer("har")

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
    path: str = typer.Argument(..., help="要导出的用例/套件 YAML 文件或目录"),
    case_name: Optional[str] = typer.Option(None, "--case-name", help="仅导出指定名称的用例"),
    steps: Optional[str] = typer.Option(None, "--steps", help="步骤索引，如 '1,3-5'（从 1 开始）"),
    multiline: bool = typer.Option(True, "--multiline/--one-line", help="多行格式化 curl 命令（带续行符）"),
    shell: str = typer.Option("sh", "--shell", help="续行符风格：sh|ps"),
    redact: Optional[str] = typer.Option(None, "--redact", help="逗号分隔的需要脱敏的请求头名称，如 Authorization,Cookie"),
    with_comments: bool = typer.Option(False, "--with-comments/--no-comments", help="为每个 curl 命令添加 '# Case/Step' 注释"),
    outfile: Optional[str] = typer.Option(None, "--outfile", help="输出到文件（必须以 .curl 结尾）"),
) -> None:
    """导出测试用例为 curl 命令"""
    exporter = _require_exporter("curl")
    step_to_curl = exporter.render_step
    step_placeholders = exporter.describe_placeholders
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
                    if step_placeholders:
                        vars_set, exprs_set = step_placeholders(c, idx)
                        if vars_set:
                            out_lines.append("# Vars: " + " ".join(sorted(vars_set)))
                        if exprs_set:
                            out_lines.append("# Exprs: " + " ".join(sorted(exprs_set)))
                out_lines.append(step_to_curl(c, idx, multiline=multiline, shell=shell, redact=redact_list, envmap=env_store))

    output = "\n\n".join(out_lines)
    if outfile:
        out_path = Path(outfile)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        typer.echo(f"[EXPORT] Wrote {len(out_lines)} curl commands to {outfile}")
    else:
        typer.echo(output)
@app.command("tags")
def list_tags(
    path: str = typer.Argument("testcases", help="要扫描的文件或目录"),
) -> None:
    """列出所有测试用例使用的标签"""
    run_tags(path)



def _run_impl(
    path: str,
    k: Optional[str],
    vars: List[str],
    failfast: bool,
    report: Optional[str],
    html: Optional[str],
    allure_results: Optional[str],
    log_level: str,
    env: Optional[str],
    env_file: Optional[str],
    persist_env: Optional[str],
    log_file: Optional[str],
    httpx_logs: bool,
    reveal_secrets: bool,
    response_headers: bool,
    notify: Optional[str],
    notify_only: Optional[str],
    notify_attach_html: bool,
    no_snippet: bool,
    snippet_output: Optional[str],
    snippet_lang: str,
):
    return run_cases(
        path=path,
        k=k,
        vars=vars,
        failfast=failfast,
        report=report,
        html=html,
        allure_results=allure_results,
        log_level=log_level,
        env=env,
        env_file=env_file,
        persist_env=persist_env,
        log_file=log_file,
        httpx_logs=httpx_logs,
        reveal_secrets=reveal_secrets,
        response_headers=response_headers,
        notify=notify,
        notify_only=notify_only,
        notify_attach_html=notify_attach_html,
        no_snippet=no_snippet,
        snippet_output=snippet_output,
        snippet_lang=snippet_lang,
    )


def _quick_parse_headers(items: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for it in items or []:
        if ":" not in it:
            raise ValueError(f"Invalid header (expected 'Key: Value'): {it}")
        k, v = it.split(":", 1)
        key = k.strip()
        val = v.strip()
        if not key:
            raise ValueError(f"Invalid header (empty key): {it}")
        headers[key] = val
    return headers


def _quick_parse_params(items: list[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for it in items or []:
        if "=" not in it:
            raise ValueError(f"Invalid param (expected k=v): {it}")
        k, v = it.split("=", 1)
        key = k.strip()
        val = v.strip()
        if not key:
            raise ValueError(f"Invalid param (empty key): {it}")
        pairs.append((key, val))
    return pairs


def _quick_parse_expect(text: str) -> Any:
    s = (text or "").strip()
    if s.lower() in {"null", "none"}:
        return None
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False

    # number
    if re.fullmatch(r"[-+]?\d+", s or ""):
        try:
            return int(s)
        except Exception:
            pass
    if re.fullmatch(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", s or ""):
        try:
            return float(s)
        except Exception:
            pass

    # JSON object/array
    if s and s[0] in {"{", "["}:
        try:
            return json.loads(s)
        except Exception:
            pass

    return s


def _quick_parse_validate_expr(expr: str) -> tuple[str, str, Any]:
    raw = (expr or "").strip()
    if not raw:
        raise ValueError("Empty validate expression")

    comparator: str | None = None
    rest = raw

    # Support: comparator:CHECK<op>EXPECT (e.g., len_ge:$.data=1)
    if ":" in raw:
        prefix, tail = raw.split(":", 1)
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", prefix.strip()):
            comparator = prefix.strip()
            rest = tail.strip()

    ops = ["!=", ">=", "<=", "==", ">", "<", "="]
    pos: int | None = None
    op_found: str | None = None
    for op in ops:
        i = rest.find(op)
        if i < 0:
            continue
        if pos is None or i < pos or (i == pos and op_found and len(op) > len(op_found)):
            pos = i
            op_found = op

    if pos is None or op_found is None:
        raise ValueError("Validate expression must contain one of: !=, >=, <=, ==, >, <, =")

    check = rest[:pos].strip()
    expect_str = rest[pos + len(op_found) :].strip()
    if not check:
        raise ValueError("Validate check is empty")

    if comparator is None:
        comparator = {
            "=": "eq",
            "==": "eq",
            "!=": "ne",
            ">": "gt",
            ">=": "ge",
            "<": "lt",
            "<=": "le",
        }[op_found]

    expect = _quick_parse_expect(expect_str)
    return comparator, check, expect


def _quick_format_body(body: Any) -> str:
    if body is None:
        return ""
    if isinstance(body, (dict, list)):
        try:
            return json.dumps(body, ensure_ascii=False, indent=2)
        except Exception:
            return str(body)
    return str(body)


def _quick_truncate(text: str, max_chars: int) -> tuple[str, bool]:
    if max_chars <= 0:
        return "", bool(text)
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


@app.command("quick")
@app.command("q", hidden=True)
def quick(
    url: str = typer.Argument(..., help="请求 URL（必须以 http:// 或 https:// 开头）"),
    method: str = typer.Option("GET", "-X", "--method", help="HTTP 方法"),
    header: List[str] = typer.Option([], "-H", "--header", help="请求头（可多次），格式: 'Key: Value'"),
    param: List[str] = typer.Option([], "-p", "--param", help="Query 参数（可多次），格式: k=v"),
    data: Optional[str] = typer.Option(None, "-d", "--data", help="请求体字符串（自动尝试按 JSON 解析）"),
    data_file: Optional[str] = typer.Option(None, "--data-file", help="从文件读取请求体（推荐 Windows）"),
    validate: List[str] = typer.Option([], "--validate", help="断言表达式（可多次）"),
    extract: List[str] = typer.Option([], "--extract", help="提取变量（可多次），格式: name=$expr"),
    max_body: int = typer.Option(2048, "--max-body", help="终端输出 body 最大字符数"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="保存完整响应体到文件"),
    save_yaml: Optional[str] = typer.Option(None, "--save-yaml", help="转存为 YAML 用例（建议配合 --mask-secrets）"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="输出请求/响应头等详细信息"),
    reveal_secrets: bool = typer.Option(
        True,
        "--reveal-secrets/--mask-secrets",
        help="在输出/转存中显示敏感字段明文（Authorization/token/password）",
        show_default=True,
    ),
) -> None:
    """快速调试：直接执行 HTTP 请求（httpie 风格），无需 YAML 和环境文件。

    默认输出：Status + Body（截断）。
    退出码：0=通过，1=断言失败，2=参数或请求错误。
    """

    from http import HTTPStatus
    from urllib.parse import urlsplit, urlunsplit, parse_qsl

    from drun.engine.http import HTTPClient
    from drun.runner.assertions import compare, OPS
    from drun.utils.mask import mask_body, mask_headers

    raw_url = (url or "").strip()
    if not (raw_url.lower().startswith("http://") or raw_url.lower().startswith("https://")):
        typer.echo("[ERROR] url must start with http:// or https://")
        raise typer.Exit(code=2)

    if data is not None and data_file is not None:
        typer.echo("[ERROR] --data and --data-file cannot be used together")
        raise typer.Exit(code=2)

    # Parse URL + params
    try:
        u = urlsplit(raw_url)
    except Exception as e:
        typer.echo(f"[ERROR] Invalid url: {e}")
        raise typer.Exit(code=2)

    base_url = urlunsplit((u.scheme, u.netloc, u.path, "", ""))
    url_query = parse_qsl(u.query, keep_blank_values=True)

    try:
        headers = _quick_parse_headers(header)
        extra_params = _quick_parse_params(param)
    except ValueError as e:
        typer.echo(f"[ERROR] {e}")
        raise typer.Exit(code=2)

    all_params = list(url_query) + list(extra_params)
    params_obj: Any = all_params if all_params else None

    # Pre-validate validate/extract flags BEFORE sending request (no network)
    parsed_validations: list[tuple[str, str, Any]] = []
    for rule in validate or []:
        try:
            comp, check, expect = _quick_parse_validate_expr(rule)
        except ValueError as e:
            typer.echo(f"[ERROR] Invalid --validate '{rule}': {e}")
            raise typer.Exit(code=2)

        if comp not in OPS:
            typer.echo(f"[ERROR] Invalid --validate '{rule}': unknown comparator '{comp}'")
            raise typer.Exit(code=2)

        if not (check == "status_code" or check.startswith("headers.") or check.strip().startswith("$")):
            typer.echo(
                f"[ERROR] Unsupported validate check: {check!r} (use status_code, headers.<name>, or $expr)"
            )
            raise typer.Exit(code=2)

        if check.startswith("headers.") and not check.split(".", 1)[1].strip():
            typer.echo("[ERROR] Invalid validate check: headers.<name> is required")
            raise typer.Exit(code=2)

        parsed_validations.append((comp, check, expect))

    parsed_extracts: list[tuple[str, str]] = []
    for item in extract or []:
        if "=" not in item:
            typer.echo(f"[ERROR] Invalid --extract '{item}' (expected name=$expr)")
            raise typer.Exit(code=2)
        name, expr = item.split("=", 1)
        name = name.strip()
        expr = expr.strip()
        if not name or not expr:
            typer.echo(f"[ERROR] Invalid --extract '{item}' (expected name=$expr)")
            raise typer.Exit(code=2)
        if not expr.startswith("$"):
            typer.echo(f"[ERROR] Unsupported extract expr: {expr!r} (must start with '$')")
            raise typer.Exit(code=2)
        parsed_extracts.append((name, expr))

    # Read request body
    body_raw: Optional[str] = None
    if data_file:
        try:
            body_raw = Path(data_file).read_text(encoding="utf-8")
        except Exception as e:
            typer.echo(f"[ERROR] Failed to read --data-file '{data_file}': {e}")
            raise typer.Exit(code=2)
    elif data is not None:
        body_raw = data

    # Decide JSON vs raw data
    json_body: Any = None
    data_body: Any = None
    content_type = None
    for hk, hv in headers.items():
        if hk.lower() == "content-type":
            content_type = str(hv)
            break

    if body_raw is not None:
        stripped = body_raw.lstrip()
        should_try_json = bool(content_type and "json" in content_type.lower()) or stripped.startswith(("{", "["))
        if should_try_json:
            try:
                json_body = json.loads(body_raw)
            except Exception:
                json_body = None
        if json_body is None:
            data_body = body_raw

    # Build request dict for HTTPClient
    req: Dict[str, Any] = {
        "method": (method or "GET").upper(),
        "path": base_url,
    }
    if params_obj is not None:
        req["params"] = params_obj
    if headers:
        req["headers"] = headers
    if json_body is not None:
        req["body"] = json_body
    if data_body is not None:
        req["data"] = data_body

    # Execute
    client = HTTPClient()
    try:
        resp_obj = client.request(req)
    except Exception as e:
        typer.echo(f"[ERROR] Request failed: {e}")
        raise typer.Exit(code=2)
    finally:
        try:
            client.close()
        except Exception:
            pass

    # Masking (output/save)
    out_headers_req: dict[str, Any] = dict(headers)
    out_headers_resp: dict[str, Any] = dict(resp_obj.get("headers") or {})
    out_body: Any = resp_obj.get("body")
    if not reveal_secrets:
        out_headers_req = mask_headers(out_headers_req)
        out_headers_resp = mask_headers(out_headers_resp)
        if isinstance(out_body, (dict, list)):
            out_body = mask_body(out_body)

    # Print (default: status + truncated body)
    method_actual = str(resp_obj.get("method") or req.get("method") or "GET").upper()
    url_actual = str(resp_obj.get("url") or raw_url)
    typer.echo(f"{method_actual} {url_actual}")

    code = int(resp_obj.get("status_code") or 0)
    phrase = ""
    try:
        phrase = HTTPStatus(code).phrase
    except Exception:
        phrase = ""
    elapsed_ms = resp_obj.get("elapsed_ms")

    status_tail = f"{code} {phrase}".strip() if code else "<unknown>"
    if isinstance(elapsed_ms, (int, float)):
        typer.echo(f"Status: {status_tail} ({elapsed_ms:.1f}ms)")
    else:
        typer.echo(f"Status: {status_tail}")

    if verbose:
        if out_headers_req:
            typer.echo("Request headers:")
            typer.echo(_quick_format_body(out_headers_req))
        if json_body is not None:
            typer.echo("Request body:")
            preview, truncated = _quick_truncate(_quick_format_body(json_body if reveal_secrets else mask_body(json_body)), max_body)
            typer.echo(preview)
            if truncated:
                typer.echo("... (truncated)")
        elif data_body is not None:
            typer.echo("Request data:")
            preview, truncated = _quick_truncate(str(data_body), max_body)
            typer.echo(preview)
            if truncated:
                typer.echo("... (truncated)")
        if out_headers_resp:
            typer.echo("Response headers:")
            typer.echo(_quick_format_body(out_headers_resp))

    typer.echo("Body:")
    body_text = _quick_format_body(out_body)
    preview, truncated = _quick_truncate(body_text, max_body)
    typer.echo(preview if preview else "<empty>")
    if truncated:
        typer.echo("... (truncated, use -o/--output to save full body)")

    # Save full body to file
    if output:
        try:
            out_path = Path(output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(out_body, (dict, list)):
                out_path.write_text(json.dumps(out_body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            else:
                out_path.write_text(("" if out_body is None else str(out_body)) + "\n", encoding="utf-8")
        except Exception as e:
            typer.echo(f"[ERROR] Failed to write output file '{output}': {e}")
            raise typer.Exit(code=2)

    # Validate / extract (reuse runner internals for '$' semantics)
    runner = Runner(log=None)

    any_failed = False

    for comp, check, expect in parsed_validations:
        actual = runner._resolve_check(check, resp_obj)
        passed, err = compare(comp, actual, expect)
        if err is not None:
            typer.echo(f"[ERROR] Validate error: {err}")
            raise typer.Exit(code=2)

        if passed:
            typer.echo(f"Validate: {check} {comp} {expect!r} -> PASS")
        else:
            any_failed = True
            typer.echo(f"Validate: {check} {comp} {expect!r} -> FAIL (actual={actual!r})")

    extracted: dict[str, Any] = {}
    for name, expr in parsed_extracts:
        val = runner._eval_extract(expr, resp_obj)
        extracted[name] = val

    if extracted:
        typer.echo("Extracted:")
        for k, v in extracted.items():
            typer.echo(f"  {k} = {v!r}")

    # Save YAML testcase
    if save_yaml:
        try:
            out_path = Path(save_yaml)
            out_path.parent.mkdir(parents=True, exist_ok=True)

            base = f"{u.scheme}://{u.netloc}".rstrip("/")
            path_only = u.path or "/"
            if not path_only.startswith("/"):
                path_only = "/" + path_only

            params_dict: dict[str, Any] | None = None
            if all_params:
                params_dict = {}
                for k, v in all_params:
                    params_dict[k] = v

            yaml_headers: dict[str, Any] | None = dict(headers) if headers else None
            yaml_body: Any = json_body
            yaml_data: Any = data_body
            if not reveal_secrets:
                if yaml_headers is not None:
                    yaml_headers = mask_headers(yaml_headers)
                if isinstance(yaml_body, (dict, list)):
                    yaml_body = mask_body(yaml_body)

            yaml_validations: list[dict[str, _FlowSeq]] = []
            for comp, check, expect in parsed_validations:
                yaml_validations.append({str(comp): _FlowSeq([check, expect])})
            # If user didn't provide validations, use current status_code as a sane default
            if not yaml_validations and code:
                yaml_validations.append({"eq": _FlowSeq(["status_code", code])})

            yaml_extract: dict[str, str] | None = None
            if parsed_extracts:
                yaml_extract = {name: expr for name, expr in parsed_extracts}

            step_req: dict[str, Any] = {
                "method": (method or "GET").upper(),
                "path": path_only,
            }
            if params_dict is not None:
                step_req["params"] = params_dict
            if yaml_headers:
                step_req["headers"] = yaml_headers
            if yaml_body is not None:
                step_req["body"] = yaml_body
            if yaml_data is not None and yaml_body is None:
                step_req["data"] = yaml_data

            step_obj: dict[str, Any] = {
                "name": f"{(method or 'GET').upper()} {path_only}",
                "request": step_req,
            }
            if yaml_extract:
                step_obj["extract"] = yaml_extract
            if yaml_validations:
                step_obj["validate"] = yaml_validations

            case_obj: dict[str, Any] = {
                "config": {
                    "name": f"Quick: {(method or 'GET').upper()} {path_only}",
                    "base_url": base,
                },
                "steps": [step_obj],
            }

            out_path.write_text(_dump_case_dict(case_obj), encoding="utf-8")
        except Exception as e:
            typer.echo(f"[ERROR] Failed to write YAML '{save_yaml}': {e}")
            raise typer.Exit(code=2)

    if any_failed:
        raise typer.Exit(code=1)


@app.command("run")
@app.command("r", hidden=True)
def r(
    path: str = typer.Argument(..., help="要运行的文件或目录"),
    k: Optional[str] = typer.Option(None, "-k", help="标签过滤表达式（支持 and/or/not）"),
    vars: List[str] = typer.Option([], "--vars", help="变量覆盖 k=v（可重复）"),
    failfast: bool = typer.Option(False, "--failfast", help="遇到第一个失败时停止"),
    report: Optional[str] = typer.Option(None, "--report", help="输出 JSON 报告到文件"),
    html: Optional[str] = typer.Option(None, "--html", help="输出 HTML 报告到文件（脚手架项目默认 reports/report-<timestamp>.html；临时单文件运行默认不生成）"),
    allure_results: Optional[str] = typer.Option(None, "--allure-results", help="输出 Allure 结果到目录（用于 allure generate）"),
    log_level: str = typer.Option("INFO", "--log-level", help="日志级别"),
    env: Optional[str] = typer.Option(None, "--env", help="环境名称（如: dev, uat, prod），优先加载 .env.<name> 并合并命名环境配置"),
    env_file: Optional[str] = typer.Option(None, "--env-file", help="显式指定环境文件路径（支持任意文件名；优先级高于 --env 与默认 .env）"),
    persist_env: Optional[str] = typer.Option(None, "--persist-env", help="指定提取变量的持久化文件（默认：.env.<env> 文件）"),
    log_file: Optional[str] = typer.Option(None, "--log-file", help="输出控制台日志到文件（脚手架项目默认 logs/run-<ts>.log；临时单文件运行默认在当前目录生成一个日志文件）"),
    httpx_logs: bool = typer.Option(False, "--httpx-logs/--no-httpx-logs", help="显示 httpx 内部请求日志", show_default=False),
    reveal_secrets: bool = typer.Option(True, "--reveal-secrets/--mask-secrets", help="在日志和报告中显示敏感字段明文（password、tokens）", show_default=True),
    response_headers: bool = typer.Option(
        False,
        "--response-headers/--no-response-headers",
        help="记录 HTTP 响应头（默认关闭）",
        show_default=False,
    ),
    notify: Optional[str] = typer.Option(None, "--notify", help="通知渠道，逗号分隔：feishu,email,dingtalk"),
    notify_only: Optional[str] = typer.Option(
        None,
        "--notify-only",
        help="通知策略：failed|always（默认 $DRUN_NOTIFY_ONLY 或 'failed'）",
        show_default=False,
    ),
    notify_attach_html: bool = typer.Option(False, "--notify-attach-html/--no-notify-attach-html", help="在邮件中附加 HTML 报告（如果启用邮件）", show_default=False),
    no_snippet: bool = typer.Option(False, "--no-snippet", help="禁用代码片段生成（脚手架项目默认会自动生成到 snippets/；临时单文件运行默认关闭）"),
    snippet_output: Optional[str] = typer.Option(None, "--snippet-output", help="自定义代码片段输出目录（显式指定时始终按该目录生成）"),
    snippet_lang: str = typer.Option("all", "--snippet-lang", help="生成的语言: all|curl|python（默认 all）"),
):
    """Run test cases or suites."""
    return _run_impl(
        path, k, vars, failfast, report, html, allure_results,
        log_level, env, env_file, persist_env, log_file, httpx_logs,
        reveal_secrets, response_headers, notify, notify_only,
        notify_attach_html, no_snippet, snippet_output, snippet_lang,
    )


@app.command("check")
def check(
    path: str = typer.Argument(..., help="要验证的文件或目录"),
):
    """验证 YAML 测试文件的语法和风格（不执行）

    检查规则：
    - Extract 仅使用 `$` 语法
    - Check 对 body 使用 `$`，对元数据使用 `status_code`/`headers.*`
    - request.files 结构需符合上传规范
    - Hooks 函数名格式需符合前缀要求
    """
    run_check(path)


@app.command("fix")
def fix(
    paths: List[str] = typer.Argument(..., help="要修复的文件或目录（移动 hooks 到 config.* / 步骤间距）", metavar="PATH..."),
    only_spacing: bool = typer.Option(False, "--only-spacing", help="仅修复步骤间距（不移动 hooks）"),
    only_hooks: bool = typer.Option(False, "--only-hooks", help="仅移动 hooks 到 config.*（不修改间距）"),
):
    """自动修复 YAML 文件的格式和结构

    - 将 suite/case 级别的 hooks 移动到 `config.setup_hooks/config.teardown_hooks` 下
    - 确保 `steps:` 下相邻步骤之间有一个空行
    """
    run_fix(paths=paths, only_spacing=only_spacing, only_hooks=only_hooks)

@app.command("init")
def init_project(
    name: Optional[str] = typer.Argument(None, help="Project name (default: current directory)"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing files"),
    ci: bool = typer.Option(False, "--ci", help="Generate CI workflow (GitHub Actions)"),
) -> None:
    """Initialize Drun test project scaffold.

    Examples:
        drun init                    # Initialize in current directory
        drun init my-api-test        # Create new project directory
        drun init --force            # Overwrite existing files
        drun init --ci               # Include GitHub Actions workflow
    """
    from drun import scaffolds
    
    # Display version
    typer.echo(f"Drun v{_get_drun_version()}")

    # 确定目标目录
    if name:
        target_dir = Path(name)
        if target_dir.exists() and not target_dir.is_dir():
            typer.echo(f"[ERROR] '{name}' exists but is not a directory.")
            raise typer.Exit(code=2)
    else:
        target_dir = Path.cwd()

    # 检查是否已存在关键文件
    key_files = ["testcases", ".env", "drun_hooks.py", ".gitignore"]
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

    # Create directory structure
    dirs_to_create = {
        "testcases": "Test cases",
        "testsuites": "Test suites",
        "data": "Test data",
        "converts": "Format conversion",
        "reports": "Reports output",
        "logs": "Logs output",
        "snippets": "Code snippets",
    }

    for dir_name, desc in dirs_to_create.items():
        dir_path = target_dir / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)

    # CI workflow directory (optional)
    if ci:
        (target_dir / ".github/workflows").mkdir(parents=True, exist_ok=True)

    # 在 reports、logs 和 snippets 目录放置 .gitkeep
    for empty_dir in ["reports", "logs", "snippets"]:
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
            typer.echo(f"[SKIP] {rel_path} exists, use --force to overwrite")
            return
        file_path.write_text(content, encoding="utf-8")
        if existed_before and force:
            overwritten_files.append(rel_path)

    # Test cases
    _write_template("testcases/test_demo.yaml", scaffolds.DEMO_TESTCASE)
    _write_template("testcases/test_api_health.yaml", scaffolds.HEALTH_TESTCASE)
    _write_template("testcases/test_import_users.yaml", scaffolds.CSV_DATA_TESTCASE)

    # Test data
    _write_template("data/users.csv", scaffolds.CSV_USERS_SAMPLE)

    # Test suites
    _write_template("testsuites/testsuite_smoke.yaml", scaffolds.DEMO_TESTSUITE)

    # Format conversion sample
    _write_template("converts/sample.curl", scaffolds.SAMPLE_CURL)

    # Config files
    _write_template(".env", scaffolds.ENV_TEMPLATE)
    _write_template("drun_hooks.py", scaffolds.HOOKS_TEMPLATE)
    _write_template(".gitignore", scaffolds.GITIGNORE_TEMPLATE)

    # CI workflow (optional)
    if ci:
        _write_template(".github/workflows/test.yml", scaffolds.GITHUB_WORKFLOW_TEMPLATE)

    # Output file tree
    project_name = name if name else "."

    tree_entries = [
        ("├── ", "testcases/", ""),
        ("│   ├── ", "test_demo.yaml", "HTTP demo"),
        ("│   ├── ", "test_api_health.yaml", "Health check"),
        ("│   └── ", "test_import_users.yaml", "CSV data-driven"),
        ("├── ", "testsuites/", ""),
        ("│   └── ", "testsuite_smoke.yaml", "Smoke test suite"),
        ("├── ", "data/", ""),
        ("│   └── ", "users.csv", "Sample CSV data"),
        ("├── ", "converts/", ""),
        ("│   └── ", "sample.curl", "cURL sample"),
        ("├── ", "reports/", "Reports output"),
        ("├── ", "logs/", "Logs output"),
        ("├── ", "snippets/", "Code snippets"),
    ]

    if ci:
        tree_entries.extend([
            ("├── ", ".github/workflows/", ""),
            ("│   └── ", "test.yml", "CI workflow"),
        ])

    tree_entries.extend([
        ("├── ", ".env", "Environment config"),
        ("├── ", "drun_hooks.py", "Custom hooks"),
        ("└── ", ".gitignore", "Git ignore"),
    ])

    pad = max(len(prefix + entry) for prefix, entry, desc in tree_entries if desc) + 4

    typer.echo(f"{project_name}")
    for prefix, entry, desc in tree_entries:
        full = f"{prefix}{entry}"
        if desc:
            typer.echo(f"{full.ljust(pad)}{desc}")
        else:
            typer.echo(full)
    typer.echo("")

    dir_count = 8 if ci else 7
    file_count = 10 if ci else 9
    typer.echo(f"{dir_count} directories, {file_count} files")

    if skipped_files:
        typer.echo("")
        typer.echo("Skipped (already exists):")
        for rel_path in skipped_files:
            typer.echo(f"  - {rel_path}")

    if overwritten_files:
        typer.echo("")
        typer.echo("Overwritten (--force):")
        for rel_path in overwritten_files:
            typer.echo(f"  - {rel_path}")

    typer.echo("")
    typer.echo("Project initialized!")
    typer.echo("")
    typer.echo("Quick start:")
    if name:
        typer.echo(f"  cd {name}")
    typer.echo("  drun run testcases --env dev")
    typer.echo("  drun run testsuite_smoke --env dev")
    typer.echo("")
    typer.echo("Docs: https://github.com/Devliang24/drun")


@app.command("convert-openapi")
def convert_openapi(
    spec: str = typer.Argument(..., help="OpenAPI 3.x 规范文件（.json 或 .yaml）"),
    outfile: Optional[str] = typer.Option(None, "--outfile", help="输出文件路径"),
    case_name: Optional[str] = typer.Option(None, "--case-name", help="用例名称"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="基础 URL"),
    tags: Optional[str] = typer.Option(None, "--tags", help="逗号分隔的标签列表（区分大小写）"),
    split_output: bool = typer.Option(False, "--split-output/--single-output", help="每个操作生成一个 YAML 文件"),
    redact: Optional[str] = typer.Option(None, "--redact", help="逗号分隔的需要脱敏的请求头名称，如 Authorization,Cookie"),
    placeholders: bool = typer.Option(False, "--placeholders/--no-placeholders", help="将敏感请求头替换为 $变量 并保存到 config.variables"),
) -> None:
    """转换 OpenAPI 规范到 YAML 测试用例"""
    parse_openapi = _require_importer("openapi")
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


@app.command("server")
@app.command("s", hidden=True)
def serve_reports(
    port: int = typer.Option(8080, "--port", help="监听端口"),
    host: str = typer.Option("0.0.0.0", "--host", help="监听地址 (0.0.0.0 允许外部访问)"),
    reports_dir: str = typer.Option("reports", "--reports-dir", help="报告目录路径"),
    reload: bool = typer.Option(False, "--reload/--no-reload", help="开发模式（热重载）"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="自动打开浏览器"),
):
    """启动 Web Server 查看测试报告"""
    try:
        import uvicorn
        import webbrowser
        import threading
    except ImportError:
        typer.echo("[ERROR] FastAPI and uvicorn are required for the serve command.")
        typer.echo("Install them with: pip install fastapi uvicorn")
        raise typer.Exit(code=1)
    
    # Convert to absolute path and ensure directory exists
    reports_path = Path(reports_dir).resolve()
    if not reports_path.exists():
        typer.echo(f"[WARN] Reports directory not found: {reports_dir}")
        typer.echo(f"[INFO] Creating directory: {reports_dir}")
        reports_path.mkdir(parents=True, exist_ok=True)
    
    # Pass absolute path to server via environment variable
    os.environ["DRUN_REPORTS_DIR"] = str(reports_path)
    
    url = f"http://{host}:{port}"
    typer.echo(f"[SERVER] Starting Drun Report Server")
    typer.echo(f"[SERVER] Web UI: {url}")
    typer.echo(f"[SERVER] API docs: {url}/docs")
    typer.echo(f"[SERVER] Reports directory: {reports_path}")
    typer.echo(f"[SERVER] Listening on: {host}:{port}")
    if host == "0.0.0.0":
        typer.echo(f"[SERVER] ⚠️  Server is accessible from public network")
    typer.echo(f"[SERVER] Press Ctrl+C to stop")
    
    if open_browser and not reload and host in ["127.0.0.1", "localhost"]:
        # Open browser after a short delay (only for local access)
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    
    try:
        uvicorn.run(
            "drun.server.app:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except KeyboardInterrupt:
        typer.echo("\n[SERVER] Stopped")


if __name__ == "__main__":
    app()

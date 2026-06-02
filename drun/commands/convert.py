"""Convert helpers — shared logic for `drun convert` and `drun convert-openapi`.

These functions were moved from ``drun/cli.py`` to keep the CLI entry-point
file focused on routing.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer

from drun.commands.yaml_dump import (
    build_cases_from_import,
    resolve_output_paths,
    write_caseflow,
    write_imported_cases,
)
from drun.extensions import require_exporter, require_importer
from drun.loader.collector import InvalidTestPathError, discover
from drun.loader.env import load_environment
from drun.loader.yaml_loader import load_yaml_file
from drun.models.case import Case
from drun.utils.naming import sanitize_var_name


def apply_convert_filters(
    case: Case,
    *,
    redact_headers: Optional[List[str]] = None,
    placeholders: bool = False,
) -> Case:
    """Mutate case in-place to redact sensitive headers or lift values into variables as placeholders.

    - redact_headers: list of header names (case-insensitive) to mask as '***'.
    - placeholders: when True, convert sensitive headers into variables and reference via $var in headers.
    """
    redact_lc = {h.lower() for h in (redact_headers or [])}
    default_sensitive = {
        "authorization",
        "cookie",
        "x-api-key",
        "x-api-token",
        "api-key",
        "apikey",
    }
    if placeholders and not redact_lc:
        redact_lc = set(default_sensitive)

    vars_map = dict(case.config.variables or {})

    for st in case.steps:
        req = st.request
        hdrs = dict(req.headers or {})
        new_hdrs: dict[str, str] = {}
        for k, v in hdrs.items():
            kl = str(k).lower()
            if kl in redact_lc and isinstance(v, str):
                if placeholders:
                    if kl == "authorization" and v.lower().startswith("bearer "):
                        token_val = v.split(" ", 1)[1]
                        var_name = "token"
                        if vars_map.get(var_name) not in (None, token_val):
                            i = 2
                            while f"token{i}" in vars_map:
                                i += 1
                            var_name = f"token{i}"
                        vars_map[var_name] = token_val
                        new_hdrs[k] = f"Bearer ${var_name}"
                    else:
                        var_name = sanitize_var_name(kl)
                        vars_map[var_name] = v
                        new_hdrs[k] = f"${var_name}"
                else:
                    new_hdrs[k] = "***"
            else:
                new_hdrs[k] = v
        if new_hdrs:
            req.headers = new_hdrs
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


# ── Convert helpers (called from cli.py convert_auto dispatch) ──

def convert_curl(
    infile: str,
    redact: Optional[str] = None,
    placeholders: bool = False,
    outfile: Optional[str] = None,
    into: Optional[str] = None,
    case_name: Optional[str] = None,
    base_url: Optional[str] = None,
    split_output: bool = False,
) -> None:
    parse_curl_text = require_importer("curl")

    # Read input
    if infile == "-":
        text = typer.get_text_stream("stdin").read()
    else:
        # Enforce .curl suffix for curl files
        pth = Path(infile)
        if pth.suffix.lower() != ".curl":
            typer.echo(
                f"[CONVERT] Refusing to read '{infile}': curl file must have '.curl' suffix."
            )
            raise typer.Exit(code=2)
        text = pth.read_text(encoding="utf-8")

    icase = parse_curl_text(text, case_name=case_name, base_url=base_url)

    if not icase.steps:
        typer.echo("[CONVERT] No curl commands detected in input.")
        return

    if split_output and into:
        typer.echo(
            "[CONVERT] -output-mode split cannot be combined with -into; provide -outfile or rely on inferred names."
        )
        raise typer.Exit(code=2)

    cases = build_cases_from_import(icase, split_output=split_output)
    redact_list = [x.strip() for x in (redact or "").split(",") if x.strip()]
    cases = [
        (
            apply_convert_filters(
                case, redact_headers=redact_list, placeholders=placeholders
            ),
            idx,
        )
        for case, idx in cases
    ]
    source_path = None if infile == "-" else infile
    write_imported_cases(
        cases,
        outfile=outfile,
        into=into,
        split_output=split_output,
        source_path=source_path,
    )


def convert_postman(
    collection: str,
    outfile: Optional[str] = None,
    into: Optional[str] = None,
    case_name: Optional[str] = None,
    base_url: Optional[str] = None,
    postman_env: Optional[str] = None,
    redact: Optional[str] = None,
    placeholders: bool = False,
    suite_out: Optional[str] = None,
    split_output: bool = False,
) -> None:
    parse_postman = require_importer("postman")

    text = Path(collection).read_text(encoding="utf-8")
    env_text = None
    if postman_env:
        env_text = Path(postman_env).read_text(encoding="utf-8")
    icase = parse_postman(
        text, case_name=case_name, base_url=base_url, env_text=env_text
    )

    if not icase.steps:
        typer.echo("[CONVERT] No requests detected in Postman collection.")
        return
    if split_output and into:
        typer.echo(
            "[CONVERT] -output-mode split cannot be combined with -into; provide -outfile or rely on inferred names."
        )
        raise typer.Exit(code=2)

    cases = build_cases_from_import(icase, split_output=split_output)
    redact_list = [x.strip() for x in (redact or "").split(",") if x.strip()]
    cases = [
        (
            apply_convert_filters(
                case, redact_headers=redact_list, placeholders=placeholders
            ),
            idx,
        )
        for case, idx in cases
    ]
    write_imported_cases(
        cases,
        outfile=outfile,
        into=into,
        split_output=split_output,
        source_path=collection,
    )
    # Optional suite generation
    if suite_out:
        if into:
            typer.echo("[CONVERT] -suite-out cannot be combined with -into")
            raise typer.Exit(code=2)
        # compute case paths/names similar to writer
        names = [c.config.name or f"Case {i}" for (c, i) in cases]
        if split_output:
            paths = resolve_output_paths(
                len(cases), outfile=outfile, source_path=collection
            )
        else:
            if outfile:
                paths = [Path(outfile)]
            else:
                typer.echo(
                    "[CONVERT] -suite-out requires -output-mode split or -outfile to materialize case files"
                )
                raise typer.Exit(code=2)
        write_caseflow(
            paths, names, suite_path=suite_out, suite_name=case_name or icase.name
        )


def convert_har(
    infile: str,
    outfile: Optional[str] = None,
    into: Optional[str] = None,
    case_name: Optional[str] = None,
    base_url: Optional[str] = None,
    redact: Optional[str] = None,
    placeholders: bool = False,
    exclude_static: bool = True,
    only_2xx: bool = False,
    exclude_pattern: Optional[str] = None,
    split_output: bool = False,
) -> None:
    parse_har = require_importer("har")

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
        typer.echo(
            "[CONVERT] -output-mode split cannot be combined with -into; provide -outfile or rely on inferred names."
        )
        raise typer.Exit(code=2)

    cases = build_cases_from_import(icase, split_output=split_output)
    redact_list = [x.strip() for x in (redact or "").split(",") if x.strip()]
    cases = [
        (
            apply_convert_filters(
                case, redact_headers=redact_list, placeholders=placeholders
            ),
            idx,
        )
        for case, idx in cases
    ]
    write_imported_cases(
        cases,
        outfile=outfile,
        into=into,
        split_output=split_output,
        source_path=infile,
    )


def export_curl(
    path: str,
    case_name: Optional[str] = None,
    steps: Optional[str] = None,
    layout: str = "multiline",
    shell: str = "sh",
    redact: Optional[str] = None,
    comments: str = "off",
    outfile: Optional[str] = None,
) -> None:
    """导出测试用例为 curl 命令（无 typer 装饰器，由 cli.py 转发调用）"""
    resolved_layout = (layout or "multiline").strip().lower()
    if resolved_layout not in {"multiline", "oneline"}:
        typer.echo("[EXPORT] Invalid -layout value. Use 'multiline' or 'oneline'.")
        raise typer.Exit(code=2)
    multiline = resolved_layout == "multiline"

    resolved_comments = (comments or "off").strip().lower()
    if resolved_comments not in {"on", "off"}:
        typer.echo("[EXPORT] Invalid -comments value. Use 'on' or 'off'.")
        raise typer.Exit(code=2)
    with_comments = resolved_comments == "on"

    exporter = require_exporter("curl")
    step_to_curl = exporter.render_step
    step_placeholders = exporter.describe_placeholders
    out_lines: List[str] = []

    env_name = os.environ.get("DRUN_ENV")
    env_store = load_environment(env_name, ".env")

    files: List[str] = []
    p = Path(path)
    if p.is_dir():
        try:
            files = discover([path])
        except InvalidTestPathError as exc:
            typer.echo(str(exc))
            raise typer.Exit(code=2)
    else:
        files = [path]

    def parse_steps_spec(spec: Optional[str], maxn: int) -> List[int]:
        if not spec:
            return list(range(maxn))
        out: List[int] = []
        for part in spec.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                a, b = part.split("-", 1)
                try:
                    ia = max(1, int(a))
                    ib = min(maxn, int(b))
                except Exception:
                    continue
                out.extend(list(range(ia - 1, ib)))
            else:
                try:
                    i = int(part)
                    if 1 <= i <= maxn:
                        out.append(i - 1)
                except Exception:
                    pass
        # dedupe preserve order
        seen = set()
        res = []
        for i in out:
            if i not in seen:
                res.append(i)
                seen.add(i)
        return res

    redact_list = [x.strip() for x in (redact or "").split(",") if x.strip()]

    if outfile and not outfile.lower().endswith(".curl"):
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
                    cname = c.config.name or "Unnamed"
                    sname = c.steps[idx].name or f"Step {idx + 1}"
                    out_lines.append(f"# Case: {cname} | Step {idx + 1}: {sname}")
                    # Add placeholder annotations such as $token or ${...}
                    if step_placeholders:
                        vars_set, exprs_set = step_placeholders(c, idx)
                        if vars_set:
                            out_lines.append("# Vars: " + " ".join(sorted(vars_set)))
                        if exprs_set:
                            out_lines.append("# Exprs: " + " ".join(sorted(exprs_set)))
                out_lines.append(
                    step_to_curl(
                        c,
                        idx,
                        multiline=multiline,
                        shell=shell,
                        redact=redact_list,
                        envmap=env_store,
                    )
                )

    output = "\n\n".join(out_lines)
    if outfile:
        out_path = Path(outfile)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        typer.echo(f"[EXPORT] Wrote {len(out_lines)} curl commands to {outfile}")
    else:
        typer.echo(output)
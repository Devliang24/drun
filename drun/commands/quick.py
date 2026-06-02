"""Quick HTTP request command (httpie-style), no YAML files needed."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import typer

from drun.commands.yaml_dump import _FlowSeq, dump_case_dict as _dump_case_dict

# ── Quick command helpers ──

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


def _quick_parse_check_expr(expr: str) -> tuple[str, str, Any]:
    raw = (expr or "").strip()
    if not raw:
        raise ValueError("Empty check expression")

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
        if (
            pos is None
            or i < pos
            or (i == pos and op_found and len(op) > len(op_found))
        ):
            pos = i
            op_found = op

    if pos is None or op_found is None:
        raise ValueError(
            "Check expression must contain one of: !=, >=, <=, ==, >, <, ="
        )

    check = rest[:pos].strip()
    expect_str = rest[pos + len(op_found) :].strip()
    if not check:
        raise ValueError("Check target is empty")

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


def quick(
    url: str = typer.Argument(..., help="请求 URL（必须以 http:// 或 https:// 开头）"),
    method: str = typer.Option("GET", "-X", help="HTTP 方法"),
    header: List[str] = typer.Option([], "-H", help="请求头（可多次），格式: 'Key: Value'"),
    param: List[str] = typer.Option([], "-p", help="Query 参数（可多次），格式: k=v"),
    data: Optional[str] = typer.Option(
        None,
        "-d",
        help="请求体内容；使用 @file 从文件读取（如 -d @body.json）",
    ),
    check: List[str] = typer.Option([], "-check", help="检查表达式（可多次）"),
    extract: List[str] = typer.Option(
        [], "-extract", help="提取变量（可多次），格式: name=$expr"
    ),
    max_body: int = typer.Option(2048, "-max-body", help="终端输出 body 最大字符数"),
    output: Optional[str] = typer.Option(None, "-o", help="保存完整响应体到文件"),
    save_yaml: Optional[str] = typer.Option(
        None, "-save-yaml", help="转存为 YAML 用例（建议配合 -secrets mask）"
    ),
    verbose: bool = typer.Option(False, "-v", help="输出请求/响应头等详细信息"),
    secrets: str = typer.Option(
        "plain",
        "-secrets",
        help="敏感信息模式 plain|mask。例: -secrets mask",
        metavar="",
    ),
) -> None:
    """快速调试：直接执行 HTTP 请求（httpie 风格），无需 YAML 和环境文件。

    默认输出：Status + Body（截断）。
    退出码：0=通过，1=检查失败，2=参数或请求错误。
    """
    # Lazy imports — keep at call time so mocks in tests can intercept
    from http import HTTPStatus
    from urllib.parse import parse_qsl, urlsplit, urlunsplit

    from drun.engine.http import HTTPClient
    from drun.runner.checks import OPS, compare
    from drun.runner.runner import Runner
    from drun.utils.mask import mask_body, mask_headers

    secrets_mode = (secrets or "plain").strip().lower()
    if secrets_mode not in {"plain", "mask"}:
        typer.echo("[ERROR] Invalid -secrets value. Use 'plain' or 'mask'.")
        raise typer.Exit(code=2)
    resolved_reveal_secrets = secrets_mode == "plain"

    raw_url = (url or "").strip()
    if not (
        raw_url.lower().startswith("http://") or raw_url.lower().startswith("https://")
    ):
        typer.echo("[ERROR] url must start with http:// or https://")
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

    # Pre-check check/extract flags BEFORE sending request (no network)
    parsed_checks: list[tuple[str, str, Any]] = []
    for rule in check or []:
        try:
            comp, check_target, expect = _quick_parse_check_expr(rule)
        except ValueError as e:
            typer.echo(f"[ERROR] Invalid -check '{rule}': {e}")
            raise typer.Exit(code=2)

        if comp not in OPS:
            typer.echo(
                f"[ERROR] Invalid -check '{rule}': unknown comparator '{comp}'"
            )
            raise typer.Exit(code=2)

        if not (
            check_target == "status_code"
            or check_target.startswith("headers.")
            or check_target.strip().startswith("$")
        ):
            typer.echo(
                f"[ERROR] Unsupported check target: {check_target!r} (use status_code, headers.<name>, or $expr)"
            )
            raise typer.Exit(code=2)

        if check_target.startswith("headers.") and not check_target.split(".", 1)[1].strip():
            typer.echo("[ERROR] Invalid check target: headers.<name> is required")
            raise typer.Exit(code=2)

        parsed_checks.append((comp, check_target, expect))

    parsed_extracts: list[tuple[str, str]] = []
    for item in extract or []:
        if "=" not in item:
            typer.echo(f"[ERROR] Invalid -extract '{item}' (expected name=$expr)")
            raise typer.Exit(code=2)
        name, expr = item.split("=", 1)
        name = name.strip()
        expr = expr.strip()
        if not name or not expr:
            typer.echo(f"[ERROR] Invalid -extract '{item}' (expected name=$expr)")
            raise typer.Exit(code=2)
        if not expr.startswith("$"):
            typer.echo(
                f"[ERROR] Unsupported extract expr: {expr!r} (must start with '$')"
            )
            raise typer.Exit(code=2)
        parsed_extracts.append((name, expr))

    # Read request body
    body_raw: Optional[str] = None
    if data is not None and data.startswith("@"):
        data_file = data[1:].strip()
        if not data_file:
            typer.echo("[ERROR] Invalid -d value: '@' must be followed by file path")
            raise typer.Exit(code=2)
        try:
            body_raw = Path(data_file).read_text(encoding="utf-8")
        except Exception as e:
            typer.echo(f"[ERROR] Failed to read body file '{data_file}': {e}")
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
        should_try_json = bool(
            content_type and "json" in content_type.lower()
        ) or stripped.startswith(("{", "["))
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
    if not resolved_reveal_secrets:
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
            preview, truncated = _quick_truncate(
                _quick_format_body(
                    json_body
                    if resolved_reveal_secrets
                    else mask_body(json_body)
                ),
                max_body,
            )
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
        typer.echo("... (truncated, use -o/-output to save full body)")

    # Save full body to file
    if output:
        try:
            out_path = Path(output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(out_body, (dict, list)):
                out_path.write_text(
                    json.dumps(out_body, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            else:
                out_path.write_text(
                    ("" if out_body is None else str(out_body)) + "\n", encoding="utf-8"
                )
        except Exception as e:
            typer.echo(f"[ERROR] Failed to write output file '{output}': {e}")
            raise typer.Exit(code=2)

    # Check / extract (reuse runner internals for '$' semantics)
    runner = Runner(log=None)

    any_failed = False

    for comp, check_target, expect in parsed_checks:
        actual = runner._resolve_check(check_target, resp_obj)
        passed, err = compare(comp, actual, expect)
        if err is not None:
            typer.echo(f"[ERROR] Check error: {err}")
            raise typer.Exit(code=2)

        if passed:
            typer.echo(f"Check: {check_target} {comp} {expect!r} -> PASS")
        else:
            any_failed = True
            typer.echo(
                f"Check: {check_target} {comp} {expect!r} -> FAIL (actual={actual!r})"
            )

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
            if not resolved_reveal_secrets:
                if yaml_headers is not None:
                    yaml_headers = mask_headers(yaml_headers)
                if isinstance(yaml_body, (dict, list)):
                    yaml_body = mask_body(yaml_body)

            yaml_checks: list[dict[str, _FlowSeq]] = []
            for comp, check_target, expect in parsed_checks:
                yaml_checks.append({str(comp): _FlowSeq([check_target, expect])})
            # If user didn't provide checks, use current status_code as a sane default.
            if not yaml_checks and code:
                yaml_checks.append({"eq": _FlowSeq(["status_code", code])})

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
            if yaml_checks:
                step_obj["check"] = yaml_checks

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

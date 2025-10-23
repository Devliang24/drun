from __future__ import annotations

import json
from typing import List, Dict, Optional, Iterable, Tuple, Set, Any, Mapping
import re
from urllib.parse import urljoin, urlencode

from drun.models.case import Case
from drun.templating.engine import TemplateEngine


_TEMPLATER = TemplateEngine()


def _render_with_env(text: str, case: Case, envmap: Optional[Mapping[str, Any]]) -> str:
    if not isinstance(text, str):
        return text
    if "${" not in text and "{{" not in text:
        return text
    try:
        rendered = _TEMPLATER.render_value(text, case.config.variables or {}, envmap=envmap)
    except Exception:
        return text
    if rendered is None:
        return ""
    return str(rendered)


def _full_url(case: Case, url: str, envmap: Optional[Mapping[str, Any]] = None) -> str:
    u = (url or "").strip()
    if "${" in u or "{{" in u:
        resolved = _render_with_env(u, case, envmap)
        if resolved:
            u = resolved.strip()
    if u.startswith("http://") or u.startswith("https://"):
        return u
    base = (case.config.base_url or "").strip()
    if base:
        if "${" in base or "{{" in base:
            resolved_base = _render_with_env(base, case, envmap)
            if resolved_base:
                base = resolved_base.strip()
        if base:
            return urljoin(base if base.endswith('/') else base + '/', u.lstrip('/'))
    return u


def _quote(token: str) -> str:
    if token == "\\":
        return token
    if any(ch in token for ch in [' ', '"', "'", '\n', '\t']):
        q = token.replace("'", "'\\''")
        return f"'{q}'"
    return token


def _build_parts(
    case: Case,
    idx: int,
    *,
    redact: Optional[Iterable[str]] = None,
    envmap: Optional[Mapping[str, Any]] = None,
) -> List[str]:
    step = case.steps[idx]
    req = step.request
    parts: List[str] = ["curl"]
    method = (req.method or "GET").upper()
    body_present = req.body is not None or req.data is not None or req.files is not None
    add_method_flag = True
    if method == "GET":
        add_method_flag = False
    elif method == "POST" and body_present:
        add_method_flag = False
    if add_method_flag:
        parts += ["-X", method]
    # headers
    redact_set = set(h.lower() for h in (redact or []))
    for k, v in (req.headers or {}).items():
        vv = v
        if k.lower() in redact_set:
            vv = "***"
        parts += ["-H", f"{k}: {vv}"]
    # params -> query
    url = _full_url(case, req.url or "/", envmap=envmap)
    if req.params:
        qs = urlencode(req.params, doseq=True)
        sep = '&' if ('?' in url) else '?'
        url = f"{url}{sep}{qs}"

    # body / data
    if req.body is not None:
        try:
            s = json.dumps(req.body, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            s = str(req.body)
        parts += ["--data-raw", s]
    elif req.data is not None:
        parts += ["--data-raw", str(req.data)]

    parts.append(url)
    return parts


def step_to_curl(
    case: Case,
    idx: int,
    *,
    multiline: bool = False,
    shell: str = "sh",
    redact: Optional[Iterable[str]] = None,
    envmap: Optional[Mapping[str, Any]] = None,
) -> str:
    parts = _build_parts(case, idx, redact=redact, envmap=envmap)
    if not multiline:
        return " ".join(_quote(p) for p in parts)
    # multiline formatting (curl '<url>' \n  -H '...' \)
    cont = "\\" if shell in ("sh", "bash", "zsh") else ("`" if shell in ("ps", "powershell") else "\\")
    tokens = parts[:]
    url = tokens.pop() if tokens else ""
    if tokens and tokens[0] == "curl":
        tokens.pop(0)

    def _quote_force(token: str) -> str:
        if token == "":
            return "''"
        q = token.replace("'", "'\\''")
        return f"'{q}'"

    def _group_tokens(seq: List[str]) -> List[str]:
        grouped: List[str] = []
        i = 0
        while i < len(seq):
            tok = seq[i]
            if tok.startswith("-") and (i + 1) < len(seq) and not seq[i + 1].startswith("-"):
                grouped.append(f"{tok} {_quote(seq[i + 1])}")
                i += 2
            else:
                grouped.append(_quote(tok))
                i += 1
        return grouped

    lines: List[str] = []
    first_line = f"curl {_quote_force(url)}" if url else "curl"
    lines.append(first_line)
    for segment in _group_tokens(tokens):
        lines.append(f"  {segment}")

    for i in range(len(lines) - 1):
        lines[i] = f"{lines[i]} {cont}"
    return "\n".join(lines)


def case_to_curls(
    case: Case,
    *,
    steps: Optional[Iterable[int]] = None,
    multiline: bool = False,
    shell: str = "sh",
    redact: Optional[Iterable[str]] = None,
    envmap: Optional[Mapping[str, Any]] = None,
) -> List[str]:
    idxs = list(steps) if steps is not None else range(len(case.steps))
    return [step_to_curl(case, i, multiline=multiline, shell=shell, redact=redact, envmap=envmap) for i in idxs]


_VAR_RE = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*")
_EXPR_RE = re.compile(r"\$\{[^}]+\}")


def _collect_from_value(val: Any, vars_set: Set[str], exprs_set: Set[str]) -> None:
    if val is None:
        return
    if isinstance(val, str):
        for m in _VAR_RE.findall(val):
            vars_set.add(m)
        for m in _EXPR_RE.findall(val):
            exprs_set.add(m)
        return
    if isinstance(val, dict):
        for v in val.values():
            _collect_from_value(v, vars_set, exprs_set)
        return
    if isinstance(val, (list, tuple)):
        for v in val:
            _collect_from_value(v, vars_set, exprs_set)
        return


def step_placeholders(case: Case, idx: int) -> Tuple[Set[str], Set[str]]:
    """Return ($var placeholders, ${...} expressions) found in URL/params/headers/body/data."""
    req = case.steps[idx].request
    vars_set: Set[str] = set()
    exprs_set: Set[str] = set()
    _collect_from_value(req.url or "", vars_set, exprs_set)
    _collect_from_value(req.params or {}, vars_set, exprs_set)
    _collect_from_value(req.headers or {}, vars_set, exprs_set)
    _collect_from_value(req.body, vars_set, exprs_set)
    _collect_from_value(req.data, vars_set, exprs_set)
    return vars_set, exprs_set

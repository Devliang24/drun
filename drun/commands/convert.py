"""Convert helpers — shared logic for `drun convert` and `drun convert-openapi`.

These functions were moved from ``drun/cli.py`` to keep the CLI entry-point
file focused on routing.
"""

from __future__ import annotations

from typing import List, Optional

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
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from drun.engine.http import HTTPClient
from drun.models.case import Case
from drun.models.report import AssertionResult, CaseInstanceResult, RunReport, StepResult
from drun.models.step import Step
from drun.templating.context import VarContext
from drun.templating.engine import TemplateEngine
from drun.runner.extractors import extract_from_body
from drun.runner.assertions import compare
from drun.utils.curl import to_curl
from drun.utils.mask import mask_body, mask_headers
from drun.db.sql_validate import run_sql_validate


class Runner:
    def __init__(
        self,
        *,
        log,
        failfast: bool = False,
        log_debug: bool = False,
        reveal_secrets: bool = True,
        log_response_headers: bool = True,
    ) -> None:
        self.log = log
        self.failfast = failfast
        self.log_debug = log_debug
        self.reveal = reveal_secrets
        self.log_response_headers = log_response_headers
        self.templater = TemplateEngine()

    def _render(self, data: Any, variables: Dict[str, Any], functions: Dict[str, Any] | None = None, envmap: Dict[str, Any] | None = None) -> Any:
        return self.templater.render_value(data, variables, functions, envmap)

    def _build_client(self, case: Case) -> HTTPClient:
        cfg = case.config
        return HTTPClient(base_url=cfg.base_url, timeout=cfg.timeout, verify=cfg.verify, headers=cfg.headers)

    def _request_dict(self, step: Step) -> Dict[str, Any]:
        # Use field names (not aliases) so "body" stays as expected downstream.
        # Otherwise the StepRequest alias "json" leaks into runtime and the
        # payload is dropped, triggering 422 responses on JSON APIs.
        return step.request.model_dump(exclude_none=True)

    def _fmt_json(self, obj: Any) -> str:
        try:
            return json.dumps(obj, ensure_ascii=False, indent=2)
        except Exception:
            return str(obj)

    @staticmethod
    def _format_log_value(value: Any, *, prefix_len: int = 0) -> str:
        if isinstance(value, (dict, list)):
            try:
                text = json.dumps(value, ensure_ascii=False, indent=2)
                pad = "\n" + " " * max(prefix_len, 0)
                return text.replace("\n", pad)
            except Exception:
                pass
        return repr(value)

    def _fmt_aligned(self, section: str, label: str, text: str) -> str:
        """Format a label + multiline text with consistent alignment.

        JSON behavior (text starting with '{' or '['):
        - Keep the original JSON indentation from json.dumps (indent=2) so keys are
          indented relative to the opening brace as expected.
        - Simply pad every subsequent line with spaces equal to header length so the
          entire JSON block is shifted as a group; the closing brace aligns under the
          opening brace naturally.
        """
        section_label = {
            "REQ": "REQUEST",
            "RESP": "RESPONSE",
        }.get(section, section)
        header = f"[{section_label}] {label}: "
        lines = (text or "").splitlines() or [""]
        if len(lines) == 1:
            return header + lines[0]
        first = lines[0].lstrip()
        tail_lines = lines[1:]

        # Detect JSON-style block
        is_json = first.startswith("{") or first.startswith("[")
        # Closing brace should align exactly with opening '{' -> pad only
        pad = " " * len(header)

        if is_json:
            # Preserve original JSON indentation; just shift as a block
            adjusted = [pad + ln if ln else "" for ln in tail_lines]
            return header + first + "\n" + "\n".join(adjusted)
        else:
            adjusted = [pad + ln if ln else "" for ln in tail_lines]
            return header + first + "\n" + "\n".join(adjusted)

    def _resolve_check(self, check: str, resp: Dict[str, Any]) -> Any:
        # $-style check support
        if isinstance(check, str) and check.strip().startswith("$"):
            return self._eval_extract(check, resp)
        if check == "status_code":
            return resp.get("status_code")
        if check.startswith("headers."):
            key = check.split(".", 1)[1]
            headers = resp.get("headers") or {}
            # HTTP headers are case-insensitive, do case-insensitive lookup
            key_lower = key.lower()
            for h_key, h_val in headers.items():
                if h_key.lower() == key_lower:
                    return h_val
            return None
        # unsupported check format (body.* no longer supported)
        return None

    def _eval_extract(self, expr: Any, resp: Dict[str, Any]) -> Any:
        # Only support string expressions starting with $
        if not isinstance(expr, str):
            return None
        e = expr.strip()
        if not e.startswith("$"):
            return None
        if e in ("$", "$body"):
            return resp.get("body")
        if e == "$headers":
            return resp.get("headers")
        if e == "$status_code":
            return resp.get("status_code")
        if e == "$elapsed_ms":
            return resp.get("elapsed_ms")
        if e == "$url":
            return resp.get("url")
        if e == "$method":
            return resp.get("method")
        if e.startswith("$headers."):
            key = e.split(".", 1)[1]
            headers = resp.get("headers") or {}
            key_lower = key.lower()
            for h_key, h_val in headers.items():
                if h_key.lower() == key_lower:
                    return h_val
            return None
        # JSON body via JSONPath-like: $.a.b or $[0].id -> jmespath a.b / [0].id
        body = resp.get("body")
        if e.startswith("$."):
            jexpr = e[2:]
            return extract_from_body(body, jexpr)
        if e.startswith("$["):
            jexpr = e[1:]  # e.g. $[0].id -> [0].id
            return extract_from_body(body, jexpr)
        # Fallback: remove leading $ and try
        return extract_from_body(body, e.lstrip("$"))

    def _run_setup_hooks(
        self,
        names: List[str],
        *,
        funcs: Dict[str, Any] | None,
        req: Dict[str, Any],
        variables: Dict[str, Any],
        envmap: Dict[str, Any] | None,
        meta: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        updated: Dict[str, Any] = {}
        fdict = funcs or {}
        env_ctx = envmap or {}
        meta_data = {k: v for k, v in (meta or {}).items() if v is not None}
        hook_ctx: Dict[str, Any] = {
            "request": req,
            "variables": variables,
            "env": env_ctx,
            "step_name": meta_data.get("step_name"),
            "case_name": meta_data.get("case_name"),
            "step_request": meta_data.get("step_request") or req,
            "step_variables": meta_data.get("step_variables") or variables,
            "session_variables": meta_data.get("session_variables") or variables,
            "session_env": meta_data.get("session_env") or env_ctx,
        }
        hook_ctx.update(meta_data)
        for entry in names or []:
            if not isinstance(entry, str):
                raise ValueError(f"Invalid setup hook entry type {type(entry).__name__}; expected string like '${{func(...)}}'")
            text = entry.strip()
            if not text:
                raise ValueError("Invalid empty setup hook entry")
            if not (text.startswith("${") and text.endswith("}")):
                raise ValueError(f"Setup hook must use expression syntax '${{func(...)}}': {entry}")
            import re as _re
            m = _re.match(r"^\$\{\s*([A-Za-z_][A-Za-z0-9_]*)", text)
            fn_label = f"{m.group(1)}()" if m else text
            if self.log:
                self.log.info(f"[HOOK] setup expr -> {fn_label}")
            ret = self.templater.eval_expr(text, variables, fdict, envmap, extra_ctx=hook_ctx)
            if isinstance(ret, dict):
                updated.update(ret)
        return updated

    def _run_teardown_hooks(
        self,
        names: List[str],
        *,
        funcs: Dict[str, Any] | None,
        resp: Dict[str, Any],
        variables: Dict[str, Any],
        envmap: Dict[str, Any] | None,
        meta: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        updated: Dict[str, Any] = {}
        fdict = funcs or {}
        env_ctx = envmap or {}
        meta_data = {k: v for k, v in (meta or {}).items() if v is not None}
        hook_ctx: Dict[str, Any] = {
            "response": resp,
            "variables": variables,
            "env": env_ctx,
            "step_name": meta_data.get("step_name"),
            "case_name": meta_data.get("case_name"),
            "step_response": meta_data.get("step_response") or resp,
            "step_variables": meta_data.get("step_variables") or variables,
            "session_variables": meta_data.get("session_variables") or variables,
            "session_env": meta_data.get("session_env") or env_ctx,
        }
        hook_ctx.update(meta_data)
        for entry in names or []:
            if not isinstance(entry, str):
                raise ValueError(f"Invalid teardown hook entry type {type(entry).__name__}; expected string like '${{func(...)}}'")
            text = entry.strip()
            if not text:
                raise ValueError("Invalid empty teardown hook entry")
            if not (text.startswith("${") and text.endswith("}")):
                raise ValueError(f"Teardown hook must use expression syntax '${{func(...)}}': {entry}")
            import re as _re
            m = _re.match(r"^\$\{\s*([A-Za-z_][A-Za-z0-9_]*)", text)
            fn_label = f"{m.group(1)}()" if m else text
            if self.log:
                self.log.info(f"[HOOK] teardown expr -> {fn_label}")
            ret = self.templater.eval_expr(text, variables, fdict, envmap, extra_ctx=hook_ctx)
            if isinstance(ret, dict):
                updated.update(ret)
        return updated

    def run_case(self, case: Case, global_vars: Dict[str, Any], params: Dict[str, Any], *, funcs: Dict[str, Any] | None = None, envmap: Dict[str, Any] | None = None, source: str | None = None) -> CaseInstanceResult:
        name = case.config.name or "Unnamed Case"
        t0 = time.perf_counter()
        steps_results: List[StepResult] = []
        status = "passed"
        last_resp_obj: Dict[str, Any] | None = None

        # Evaluate case-level variables once to fix values across steps
        base_vars_raw: Dict[str, Any] = {**(case.config.variables or {}), **(params or {})}
        rendered_base = self._render(base_vars_raw, {}, funcs, envmap)
        if not isinstance(rendered_base, dict):
            rendered_base = base_vars_raw
        ctx = VarContext(rendered_base)
        client = self._build_client(case)

        try:
            # Suite + Case setup hooks
            try:
                # suite-level
                if getattr(case, "suite_setup_hooks", None):
                    base_vars = ctx.get_merged(global_vars)
                    new_vars_suite = self._run_setup_hooks(
                        case.suite_setup_hooks,
                        funcs=funcs,
                        req={},
                        variables=base_vars,
                        envmap=envmap,
                        meta={
                            "case_name": case.config.name or name,
                            "step_variables": base_vars,
                            "session_variables": base_vars,
                            "session_env": envmap or {},
                        },
                    )
                    for k, v in (new_vars_suite or {}).items():
                        ctx.set_base(k, v)
                        if self.log:
                            self.log.info(f"[HOOK] suite set var: {k} = {v!r}")
                # case-level
                if getattr(case, "setup_hooks", None):
                    base_vars = ctx.get_merged(global_vars)
                    new_vars_case = self._run_setup_hooks(
                        case.setup_hooks,
                        funcs=funcs,
                        req={},
                        variables=base_vars,
                        envmap=envmap,
                        meta={
                            "case_name": case.config.name or name,
                            "step_variables": base_vars,
                            "session_variables": base_vars,
                            "session_env": envmap or {},
                        },
                    )
                    for k, v in (new_vars_case or {}).items():
                        ctx.set_base(k, v)
                        if self.log:
                            self.log.info(f"[HOOK] case set var: {k} = {v!r}")
            except Exception as e:
                status = "failed"
                steps_results.append(StepResult(name="case setup hooks", status="failed", error=f"{e}"))
                raise

            for step in case.steps:
                # skip handling
                if step.skip:
                    if self.log:
                        self.log.info(f"[STEP] Skip: {step.name} | reason={step.skip}")
                    steps_results.append(StepResult(name=step.name, status="skipped"))
                    continue

                # variables: case -> step -> CLI/global overrides
                ctx.push(step.variables)
                variables = ctx.get_merged(global_vars)
                # render step-level variables so expressions like ${token} inside values are resolved
                rendered_locals = self._render(step.variables, variables, funcs, envmap)
                ctx.pop()
                ctx.push(rendered_locals if isinstance(rendered_locals, dict) else (step.variables or {}))
                variables = ctx.get_merged(global_vars)

                # Render step name to support variable interpolation (e.g., $model_name in parametrized tests)
                rendered_step_name = self._render(step.name, variables, funcs, envmap)
                if not isinstance(rendered_step_name, str):
                    rendered_step_name = str(step.name)

                # render request
                req_dict = self._request_dict(step)
                req_rendered = self._render(req_dict, variables, funcs, envmap)
                step_locals_for_hook = rendered_locals if isinstance(rendered_locals, dict) else (step.variables or {})
                session_vars_for_hook = variables
                setup_meta = {
                    "step_name": step.name,
                    "case_name": case.config.name or name,
                    "step_request": req_rendered,
                    "step_variables": step_locals_for_hook,
                    "session_variables": session_vars_for_hook,
                    "session_env": envmap or {},
                }
                # run setup hooks (mutation allowed)
                try:
                    new_vars = self._run_setup_hooks(
                        step.setup_hooks,
                        funcs=funcs,
                        req=req_rendered,
                        variables=variables,
                        envmap=envmap,
                        meta=setup_meta,
                    )
                    for k, v in (new_vars or {}).items():
                        ctx.set_base(k, v)
                        if self.log:
                            self.log.info(f"[HOOK] set var: {k} = {v!r}")
                    variables = ctx.get_merged(global_vars)
                except Exception as e:
                    status = "failed"
                    if self.log:
                        self.log.error(f"[HOOK] setup error: {e}")
                    steps_results.append(StepResult(name=rendered_step_name, status="failed", error=f"setup hook error: {e}"))
                    if self.failfast:
                        break
                    ctx.pop()
                    continue
                # sanitize headers to avoid illegal values (e.g., Bearer <empty>)
                if isinstance(req_rendered.get("headers"), dict):
                    headers = dict(req_rendered["headers"])  # type: ignore[index]
                    for hk, hv in list(headers.items()):
                        if hv is None:
                            headers.pop(hk, None)
                        elif isinstance(hv, str) and (hv.strip() == "" or hv.strip().lower() in {"bearer", "bearer none"}):
                            headers.pop(hk, None)
                    req_rendered["headers"] = headers
                # Auto-inject Authorization if token is available and no header set
                if (not (isinstance(req_rendered.get("headers"), dict) and any(k.lower()=="authorization" for k in req_rendered["headers"]))):
                    tok = variables.get("token") if isinstance(variables, dict) else None
                    if isinstance(tok, str) and tok.strip():
                        hdrs = dict(req_rendered.get("headers") or {})
                        hdrs["Authorization"] = f"Bearer {tok}"
                        req_rendered["headers"] = hdrs

                if self.log:
                    self.log.info(f"[STEP] Start: {rendered_step_name}")
                    # brief request line
                    self.log.info(f"[REQUEST] {req_rendered.get('method','GET')} {req_rendered.get('url')}")
                    if req_rendered.get("params") is not None:
                        self.log.info(self._fmt_aligned("REQ", "params", self._fmt_json(req_rendered.get("params"))))
                    if req_rendered.get("headers"):
                        hdrs_out = req_rendered.get("headers")
                        if not self.reveal:
                            hdrs_out = mask_headers(hdrs_out)
                        self.log.info(self._fmt_aligned("REQ", "headers", self._fmt_json(hdrs_out)))
                    if req_rendered.get("body") is not None:
                        body = req_rendered.get("body")
                        if isinstance(body, (dict, list)) and not self.reveal:
                            body = mask_body(body)
                        self.log.info(self._fmt_aligned("REQ", "body", self._fmt_json(body)))
                    if req_rendered.get("data") is not None:
                        data = req_rendered.get("data")
                        if isinstance(data, (dict, list)) and not self.reveal:
                            data = mask_body(data)
                        self.log.info(self._fmt_aligned("REQ", "data", self._fmt_json(data)))

                # send with retry
                last_error: Optional[str] = None
                attempt = 0
                resp_obj: Optional[Dict[str, Any]] = None
                while attempt <= max(step.retry, 0):
                    try:
                        resp_obj = client.request(req_rendered)
                        last_error = None
                        break
                    except Exception as e:
                        last_error = str(e)
                        if attempt >= step.retry:
                            break
                        backoff = min(step.retry_backoff * (2 ** attempt), 2.0)
                        time.sleep(backoff)
                        attempt += 1

                if last_error:
                    status = "failed"
                    if self.log:
                        self.log.error(f"[STEP] Request error: {last_error}")

                    # Build request summary (method/url/params/headers/body/data)
                    req_summary = {
                        k: v
                        for k, v in (req_rendered or {}).items()
                        if k in ("method", "url", "params", "headers", "body", "data")
                    }
                    # Build cURL even on error for better diagnostics
                    url_rendered = (req_rendered or {}).get("url")
                    curl_headers = (req_rendered or {}).get("headers") or {}
                    if not self.reveal and isinstance(curl_headers, dict):
                        curl_headers = mask_headers(curl_headers)
                    curl_data = (req_rendered or {}).get("body")
                    if curl_data is None:
                        curl_data = (req_rendered or {}).get("data")
                    if not self.reveal and isinstance(curl_data, (dict, list)):
                        curl_data = mask_body(curl_data)
                    curl_cmd = to_curl(
                        (req_rendered or {}).get("method", "GET"),
                        url_rendered,
                        headers=curl_headers if isinstance(curl_headers, dict) else {},
                        data=curl_data,
                    )

                    steps_results.append(
                        StepResult(
                            name=rendered_step_name,
                            status="failed",
                            request=req_summary,
                            response={"error": f"Request error: {last_error}"},
                            curl=curl_cmd,
                            error=f"Request error: {last_error}",
                            duration_ms=0.0,
                        )
                    )
                    if self.failfast:
                        break
                    ctx.pop()
                    continue

                assert resp_obj is not None
                last_resp_obj = resp_obj
                if self.log:
                    hdrs = resp_obj.get("headers") or {}
                    if not self.reveal:
                        hdrs = mask_headers(hdrs)
                    self.log.info(f"[RESPONSE] status={resp_obj.get('status_code')} elapsed={resp_obj.get('elapsed_ms'):.1f}ms")
                    if self.log_response_headers:
                        self.log.info(self._fmt_aligned("RESP", "headers", self._fmt_json(hdrs)))
                    body_preview = resp_obj.get("body")
                    if isinstance(body_preview, (dict, list)):
                        out_body = body_preview
                        if not self.reveal:
                            out_body = mask_body(out_body)
                        self.log.info(self._fmt_aligned("RESP", "body", self._fmt_json(out_body)))
                    elif body_preview is not None:
                        text = str(body_preview)
                        if len(text) > 2000:
                            text = text[:2000] + "..."
                        self.log.info(self._fmt_aligned("RESP", "text", text))

                # assertions
                assertions: List[AssertionResult] = []
                step_failed = False
                for v in step.validators:
                    rendered_check = self._render(v.check, variables, funcs, envmap)
                    check_str = rendered_check if isinstance(rendered_check, str) else str(v.check)
                    expect_rendered = self._render(v.expect, variables, funcs, envmap)
                    actual = self._resolve_check(check_str, resp_obj)
                    passed, err = compare(v.comparator, actual, expect_rendered)
                    msg = err
                    if not passed and msg is None:
                        addon = ""
                        if isinstance(check_str, str) and check_str.startswith("body."):
                            addon = " | unsupported 'body.' syntax; use '$' (e.g., $.path.to.field)"
                        msg = f"Assertion failed: {check_str} {v.comparator} {expect_rendered!r} (actual={actual!r}){addon}"
                    assertions.append(
                        AssertionResult(
                            check=str(check_str),
                            comparator=v.comparator,
                            expect=expect_rendered,
                            actual=actual,
                            passed=bool(passed),
                            message=msg,
                        )
                    )
                    if not passed:
                        step_failed = True
                        if self.log:
                            expect_fmt = self._format_log_value(expect_rendered)
                            prefix = f"[VALIDATION] {check_str} {v.comparator} {expect_fmt} => actual="
                            indent_len = len(prefix.split("\n")[-1])
                            actual_fmt = self._format_log_value(actual, prefix_len=indent_len)
                            self.log.error(prefix + actual_fmt + f" | FAIL | {msg}")
                    else:
                        if self.log:
                            expect_fmt = self._format_log_value(expect_rendered)
                            prefix = f"[VALIDATION] {check_str} {v.comparator} {expect_fmt} => actual="
                            indent_len = len(prefix.split("\n")[-1])
                            actual_fmt = self._format_log_value(actual, prefix_len=indent_len)
                            self.log.info(prefix + actual_fmt + " | PASS")

                if step.sql_validate:
                    sql_updates_total: Dict[str, Any] = {}
                    temp_vars = dict(variables)
                    for idx, sql_cfg in enumerate(step.sql_validate):
                        try:
                            rendered_cfg = self._render(sql_cfg.model_dump(), temp_vars, funcs, envmap)
                        except Exception as e:
                            step_failed = True
                            err_msg = f"SQL validate render error: {e}"
                            assertions.append(
                                AssertionResult(
                                    check=f"sql.config[{idx}]",
                                    comparator="render",
                                    expect=None,
                                    actual=None,
                                    passed=False,
                                    message=err_msg,
                                )
                            )
                            if self.log:
                                self.log.error(f"[SQL] render error: {e}")
                            continue
                        try:
                            sql_results, sql_updates = run_sql_validate(
                                [rendered_cfg],
                                response=resp_obj,
                                variables=temp_vars,
                                env=envmap or {},
                                render=None,
                                logger=self.log,
                            )
                        except Exception as e:
                            step_failed = True
                            err_msg = f"SQL validate error: {e}"
                            assertions.append(
                                AssertionResult(
                                    check=f"sql.exec[{idx}]",
                                    comparator="execute",
                                    expect=None,
                                    actual=None,
                                    passed=False,
                                    message=err_msg,
                                )
                            )
                            if self.log:
                                self.log.error(f"[SQL] execution error: {e}")
                            continue
                        for res in sql_results:
                            assertions.append(res)
                            if not res.passed:
                                step_failed = True
                        sql_updates_total.update(sql_updates)
                        temp_vars.update(sql_updates)
                    if sql_updates_total:
                        for k, v in sql_updates_total.items():
                            ctx.set_base(k, v)
                            if self.log:
                                self.log.info(f"[SQL] set var: {k} = {v!r}")
                        variables = ctx.get_merged(global_vars)

                # extracts ($-only syntax)
                extracts: Dict[str, Any] = {}
                for var, expr in (step.extract or {}).items():
                    val = self._eval_extract(expr, resp_obj)
                    extracts[var] = val
                    ctx.set_base(var, val)
                    if self.log:
                        self.log.info(f"[EXTRACT] {var} = {val!r} from {expr}")

                # teardown hooks
                try:
                    teardown_meta = {
                        "step_name": step.name,
                        "case_name": case.config.name or name,
                        "step_response": resp_obj,
                        "step_request": req_rendered,
                        "step_variables": variables,
                        "session_variables": ctx.get_merged(global_vars),
                        "session_env": envmap or {},
                    }
                    new_vars_td = self._run_teardown_hooks(
                        step.teardown_hooks,
                        funcs=funcs,
                        resp=resp_obj,
                        variables=variables,
                        envmap=envmap,
                        meta=teardown_meta,
                    )
                    for k, v in (new_vars_td or {}).items():
                        ctx.set_base(k, v)
                        if self.log:
                            self.log.info(f"[HOOK] set var: {k} = {v!r}")
                    variables = ctx.get_merged(global_vars)
                except Exception as e:
                    step_failed = True
                    if self.log:
                        self.log.error(f"[HOOK] teardown error: {e}")

                # build result
                body_masked = resp_obj.get("body")
                if not self.reveal:
                    body_masked = mask_body(body_masked)
                # Build curl command for the step (always available in report)
                url_rendered = resp_obj.get("url") or req_rendered.get("url")
                curl_headers = req_rendered.get("headers") or {}
                if not self.reveal and isinstance(curl_headers, dict):
                    curl_headers = mask_headers(curl_headers)
                curl_data = req_rendered.get("body") if req_rendered.get("body") is not None else req_rendered.get("data")
                if not self.reveal and isinstance(curl_data, (dict, list)):
                    curl_data = mask_body(curl_data)
                curl = to_curl(
                    req_rendered.get("method", "GET"),
                    url_rendered,
                    headers=curl_headers if isinstance(curl_headers, dict) else {},
                    data=curl_data,
                )
                if self.log_debug:
                    self.log.debug("cURL: %s", curl)

                sr = StepResult(
                    name=rendered_step_name,
                    status="failed" if step_failed else "passed",
                    request={
                        k: v for k, v in req_rendered.items() if k in ("method", "url", "params", "headers", "body", "data")
                    },
                    response={
                        "status_code": resp_obj.get("status_code"),
                        "body": body_masked if isinstance(body_masked, (dict, list)) else (str(body_masked)[:2048] if body_masked else None),
                    },
                    curl=curl,
                    asserts=assertions,
                    extracts=extracts,
                    duration_ms=resp_obj.get("elapsed_ms") or 0.0,
                )
                steps_results.append(sr)
                if step_failed:
                    status = "failed"
                    if self.log:
                        self.log.error(f"[STEP] Result: {rendered_step_name} | FAILED")
                    if self.failfast:
                        ctx.pop()
                        break
                else:
                    if self.log:
                        self.log.info(f"[STEP] Result: {rendered_step_name} | PASSED")
                ctx.pop()

        finally:
            # Suite + Case teardown hooks (best-effort)
            try:
                if getattr(case, "teardown_hooks", None):
                    session_vars = ctx.get_merged(global_vars)
                    _ = self._run_teardown_hooks(
                        case.teardown_hooks,
                        funcs=funcs,
                        resp=last_resp_obj or {},
                        variables=session_vars,
                        envmap=envmap,
                        meta={
                            "case_name": case.config.name or name,
                            "step_response": last_resp_obj or {},
                            "step_variables": session_vars,
                            "session_variables": session_vars,
                            "session_env": envmap or {},
                        },
                    )
                if getattr(case, "suite_teardown_hooks", None):
                    session_vars = ctx.get_merged(global_vars)
                    _ = self._run_teardown_hooks(
                        case.suite_teardown_hooks,
                        funcs=funcs,
                        resp=last_resp_obj or {},
                        variables=session_vars,
                        envmap=envmap,
                        meta={
                            "case_name": case.config.name or name,
                            "step_response": last_resp_obj or {},
                            "step_variables": session_vars,
                            "session_variables": session_vars,
                            "session_env": envmap or {},
                        },
                    )
            except Exception as e:
                steps_results.append(StepResult(name="case teardown hooks", status="failed", error=f"{e}"))
            client.close()

        total_ms = (time.perf_counter() - t0) * 1000.0

        # Final validation: ensure if any step failed, the case is marked as failed
        if any(sr.status == "failed" for sr in steps_results):
            status = "failed"

        return CaseInstanceResult(name=name, parameters=params or {}, steps=steps_results, status=status, duration_ms=total_ms, source=source)

    def build_report(self, results: List[CaseInstanceResult]) -> RunReport:
        total = len(results)
        failed = sum(1 for r in results if r.status == "failed")
        skipped = sum(1 for r in results if r.status == "skipped")
        passed = total - failed - skipped
        duration = sum(r.duration_ms for r in results)

        step_total = 0
        step_failed = 0
        step_skipped = 0
        for case in results:
            for step in case.steps or []:
                step_total += 1
                if step.status == "failed":
                    step_failed += 1
                elif step.status == "skipped":
                    step_skipped += 1

        step_passed = step_total - step_failed - step_skipped

        summary = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration_ms": duration,
        }
        if step_total:
            summary.update(
                {
                    "steps_total": step_total,
                    "steps_passed": step_passed,
                    "steps_failed": step_failed,
                    "steps_skipped": step_skipped,
                }
            )

        return RunReport(
            summary=summary,
            cases=results,
        )

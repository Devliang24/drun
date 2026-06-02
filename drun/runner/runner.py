from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path
from typing import Any, Dict, List

from drun.engine.http import HTTPClient
from drun.models.case import Case
from drun.models.report import CaseInstanceResult, RunReport, StepResult
from drun.models.step import Step
from drun.templating.compat import clean_escaped_template_string
from drun.templating.context import VarContext
from drun.templating.engine import TemplateEngine
from drun.runner.extractors import extract_from_body
from drun.runner.hooks import run_setup_hooks, run_teardown_hooks
from drun.runner.invoke import execute_invoke_step
from drun.runner.step_lifecycle import StepLifecycle, StepLifecycleContext


class Runner:
    def __init__(
        self,
        *,
        log,
        failfast: bool = False,
        log_debug: bool = False,
        reveal_secrets: bool = True,
        log_response_headers: bool = True,
        persist_env_file: str = ".env",
    ) -> None:
        self.log = log
        self.failfast = failfast
        self.log_debug = log_debug
        self.reveal = reveal_secrets
        self.log_response_headers = log_response_headers
        self.persist_env_file = persist_env_file
        self.templater = TemplateEngine()

    def _render(
        self,
        data: Any,
        variables: Dict[str, Any],
        functions: Dict[str, Any] | None = None,
        envmap: Dict[str, Any] | None = None,
        strict: bool = False,
    ) -> Any:
        return self.templater.render_value(data, variables, functions, envmap, strict=strict)

    def _collect_render_diffs(self, original: Any, rendered: Any, path: str = "") -> List[tuple]:
        """Collect before/after differences for variable substitution."""
        diffs = []
        if isinstance(original, str):
            # Check if original contains variable references
            if '$' in original and original != str(rendered):
                diffs.append((original, rendered))
        elif isinstance(original, dict) and isinstance(rendered, dict):
            for key in original:
                if key in rendered:
                    diffs.extend(self._collect_render_diffs(original[key], rendered[key], f"{path}.{key}"))
        elif isinstance(original, list) and isinstance(rendered, list):
            for i, (o, r) in enumerate(zip(original, rendered)):
                diffs.extend(self._collect_render_diffs(o, r, f"{path}[{i}]"))
        return diffs

    def _log_render_diffs(self, req_dict: Dict[str, Any], req_rendered: Dict[str, Any]) -> None:
        """Log variable substitution before/after values."""
        if not self.log:
            return
        diffs = self._collect_render_diffs(req_dict, req_rendered)
        for orig, rendered in diffs:
            rendered_str = str(rendered) if not isinstance(rendered, str) else rendered
            self.log.info(f"[RENDER] {orig} → {rendered_str}")

        # Check for unresolved variables
        if isinstance(req_dict, dict):
            for key, val in req_dict.items():
                if isinstance(val, str) and "${" in val:
                    rendered_val = req_rendered.get(key, val) if isinstance(req_rendered, dict) else val
                    val_str = str(val)
                    rendered_str = str(rendered_val)
                    if val_str == rendered_str and "${" in rendered_str:
                        # Variable was not resolved
                        self.log.warning(f"[WARN] Unresolved variable in '{key}': {val_str}")

    def _build_client(self, case: Case) -> HTTPClient:
        cfg = case.config
        # For caseflow (invoke-only cases), base_url may be None
        # Use a placeholder URL since the client won't be used for invoke steps
        base_url = cfg.base_url or "http://placeholder.local"
        return HTTPClient(
            base_url=base_url,
            timeout=cfg.timeout,
            verify=cfg.verify,
            headers=cfg.headers,
        )

    def _request_dict(self, step: Step) -> Dict[str, Any]:
        # Use field names (not aliases) so "body" stays as expected downstream.
        # Otherwise the StepRequest alias "json" leaks into runtime and the
        # payload is dropped, triggering 422 responses on JSON APIs.
        return step.request.model_dump(exclude_none=True)

    def _fmt_json(self, obj: Any) -> str:
        try:
            # Process object to strip escape quotes from string values
            processed_obj = self._strip_escape_quotes_from_obj(obj)
            return json.dumps(processed_obj, ensure_ascii=False, indent=2)
        except Exception:
            return str(obj)

    def _strip_escape_quotes_from_obj(self, obj: Any) -> Any:
        """Recursively strip escape quotes from string values in an object.

        This processes JSON-like structures (dict, list, and strings) to remove
        escape quotes that were added during YAML parsing, making the output
        cleaner and more readable.
        """
        if isinstance(obj, str):
            return clean_escaped_template_string(obj)
        elif isinstance(obj, dict):
            return {k: self._strip_escape_quotes_from_obj(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._strip_escape_quotes_from_obj(item) for item in obj]
        else:
            return obj

    def _format_log_value(self, value: Any, *, prefix_len: int = 0) -> str:
        if isinstance(value, (dict, list)):
            try:
                # Process object to strip escape quotes from string values
                processed_obj = self._strip_escape_quotes_from_obj(value)
                text = json.dumps(processed_obj, ensure_ascii=False, indent=2)
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

    def _save_response_body(
        self,
        *,
        target: str,
        resp: Dict[str, Any],
        variables: Dict[str, Any],
        funcs: Dict[str, Any] | None,
        envmap: Dict[str, Any] | None,
    ) -> str:
        rendered_target = self._render(target, variables, funcs, envmap)
        if not isinstance(rendered_target, str) or not rendered_target.strip():
            raise ValueError("response.save_body_to must resolve to a non-empty path string")

        raw_bytes = resp.get("raw_bytes")
        if raw_bytes is None:
            raise ValueError("response.save_body_to requires a response body")
        if isinstance(raw_bytes, memoryview):
            raw_bytes = raw_bytes.tobytes()
        elif isinstance(raw_bytes, bytearray):
            raw_bytes = bytes(raw_bytes)
        if not isinstance(raw_bytes, bytes):
            raise ValueError("response.save_body_to requires raw response bytes")

        out_path = Path(rendered_target).expanduser()
        if not out_path.is_absolute():
            out_path = Path.cwd() / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(raw_bytes)
        return str(out_path.resolve())

    def _resolve_check(self, check: str, resp: Dict[str, Any]) -> Any:
        # $-style check support
        if isinstance(check, str) and check.strip().startswith("$"):
            return self._eval_extract(check, resp)
        if check == "status_code":
            return resp.get("status_code")
        if check == "content_type":
            return resp.get("content_type")
        if check == "body_size":
            return resp.get("body_size")
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

    def _convert_jmespath_expression(self, expr: str) -> str:
        """
        Convert JSONPath-like expression to JMESPath with proper quoting.

        Handles field names with special characters by adding quotes.
        Examples:
            "headers.X-Demo-User" -> "headers.\"X-Demo-User\""
            "json.user-name" -> "json.\"user-name\""
            "data.normal_field" -> "data.normal_field"
        """
        # Split expression by dots, but preserve array access like [0]
        parts = []
        i = 0
        n = len(expr)

        while i < n:
            if i + 1 < n and expr[i] == '[':
                # Found array access, find the closing bracket
                j = expr.find(']', i)
                if j == -1:
                    # No closing bracket, treat as regular character
                    if i == 0:
                        parts.append(expr[i:])
                        break
                    else:
                        parts.append(expr[i])
                        i += 1
                        continue

                # Extract array access part
                array_part = expr[i:j+1]
                parts.append(array_part)
                i = j + 1

                # Skip dot after array access if present
                if i < n and expr[i] == '.':
                    i += 1
            else:
                # Regular field access, find next dot or array access
                j = i
                while j < n and expr[j] != '.' and expr[j] != '[':
                    j += 1

                field_name = expr[i:j]
                # Check if field name needs quoting (contains special chars)
                if re.search(r'[^a-zA-Z0-9_]', field_name):
                    field_name = f'"{field_name}"'
                parts.append(field_name)

                if j < n and expr[j] == '.':
                    i = j + 1
                else:
                    i = j

        # Join parts with dots for field access (array parts already include brackets)
        result = []
        for i, part in enumerate(parts):
            if '[' in part and ']' in part:
                # Array access, don't add dot before it
                if i > 0:
                    result[-1] = result[-1] + part
                else:
                    result.append(part)
            else:
                # Regular field access
                if i == 0:
                    result.append(part)
                else:
                    result.append('.' + part)

        return ''.join(result)

    def _eval_extract(self, expr: Any, resp: Dict[str, Any]) -> Any:
        # Only support string expressions starting with $
        if not isinstance(expr, str):
            return None
        e = expr.strip()
        if not e.startswith("$"):
            return None
        # Backwards compatibility: treat "$.path.length" as len($.path)
        # instead of object field access.
        if e.endswith(".length") and len(e) > len("$.length"):
            base_expr = e[:-len(".length")]
            base_val = self._eval_extract(base_expr, resp)
            try:
                return len(base_val)  # type: ignore[arg-type]
            except Exception:
                return None
        # Disallow order-agnostic JMESPath functions (sort/sort_by)
        body_expr = e[1:].strip()
        try:
            import re as _re
            if _re.search(r"\bsort_by\s*\(|\bsort\s*\(", body_expr):
                raise ValueError("JMESPath 'sort'/'sort_by' functions are disabled. Use explicit alignment.")
        except Exception:
            # best-effort; fall through
            pass
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
        if e == "$content_type":
            return resp.get("content_type")
        if e == "$body_size":
            return resp.get("body_size")
        if e == "$raw_bytes":
            return resp.get("raw_bytes")
        if e == "$body_bytes_b64":
            return resp.get("body_bytes_b64")
        if e.startswith("$headers."):
            key = e.split(".", 1)[1]
            headers = resp.get("headers") or {}
            key_lower = key.lower()
            for h_key, h_val in headers.items():
                if h_key.lower() == key_lower:
                    return h_val
            return None
        
        # Streaming-specific fields
        if e.startswith("$stream_events"):
            # Support $.stream_events[0].data or $stream_events[0].data
            if e == "$stream_events":
                return resp.get("stream_events")
            # Use JMESPath for nested access: $.stream_events[0].data -> stream_events[0].data
            jexpr = e[2:] if e.startswith("$.") else e[1:]
            return extract_from_body(resp, jexpr)
        if e.startswith("$stream_summary"):
            # Support $.stream_summary.event_count or $stream_summary.first_chunk_ms
            if e == "$stream_summary":
                return resp.get("stream_summary")
            jexpr = e[2:] if e.startswith("$.") else e[1:]
            return extract_from_body(resp, jexpr)
        if e == "$stream_raw_chunks":
            return resp.get("stream_raw_chunks")
        
        # JSON body via JSONPath-like: $.a.b or $[0].id -> jmespath a.b / [0].id
        body = resp.get("body")
        if e.startswith("$."):
            jexpr = self._convert_jmespath_expression(e[2:])
            # For streaming responses, try extracting from full response first
            if resp.get("is_stream"):
                result = extract_from_body(resp, jexpr)
                if result is not None:
                    return result
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
        return run_setup_hooks(
            names=names,
            funcs=funcs,
            req=req,
            variables=variables,
            envmap=envmap,
            meta=meta,
            templater=self.templater,
            log=self.log,
            fmt_aligned=self._fmt_aligned,
        )

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
        return run_teardown_hooks(
            names=names,
            funcs=funcs,
            resp=resp,
            variables=variables,
            envmap=envmap,
            meta=meta,
            templater=self.templater,
            log=self.log,
            fmt_aligned=self._fmt_aligned,
        )

    def _run_invoke_step(
        self,
        step: Step,
        step_idx: int,
        rendered_step_name: str,
        variables: Dict[str, Any],
        global_vars: Dict[str, Any],
        funcs: Dict[str, Any] | None,
        envmap: Dict[str, Any] | None,
        ctx: VarContext,
        params: Dict[str, Any] | None,
        invoke_result_prefix: str | None = None,
        repeat_index: int | None = None,
        repeat_no: int | None = None,
        repeat_total: int | None = None,
        source: str | None = None,
    ) -> List[StepResult]:
        return execute_invoke_step(
            runner=self,
            step=step,
            step_idx=step_idx,
            rendered_step_name=rendered_step_name,
            variables=variables,
            global_vars=global_vars,
            funcs=funcs,
            envmap=envmap,
            ctx=ctx,
            params=params,
            invoke_result_prefix=invoke_result_prefix,
            repeat_index=repeat_index,
            repeat_no=repeat_no,
            repeat_total=repeat_total,
            source=source,
        )

    def _format_repeat_step_name(self, step_name: str, repeat_index: int, repeat_total: int) -> str:
        if repeat_total <= 1:
            return step_name
        return f"{step_name} [repeat={repeat_index + 1}/{repeat_total}]"

    def _build_repeat_variables(self, variables: Dict[str, Any], repeat_index: int) -> Dict[str, Any]:
        return {
            **variables,
            "repeat_index": repeat_index,
            "repeat_no": repeat_index + 1,
        }

    def _coerce_skip_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"", "false", "0", "no", "off", "none", "null"}:
                return False
            if lowered in {"true", "1", "yes", "on"}:
                return True
            return True
        return bool(value)

    def _resolve_skip_decision(
        self,
        step: Step,
        variables: Dict[str, Any],
        funcs: Dict[str, Any] | None,
        envmap: Dict[str, Any] | None,
    ) -> tuple[bool, str | None]:
        raw_skip = step.skip
        if raw_skip is None:
            return False, None
        if isinstance(raw_skip, bool):
            return raw_skip, "true" if raw_skip else None
        if isinstance(raw_skip, str):
            skip_text = raw_skip.strip()
            if not skip_text:
                return False, None
            if skip_text.startswith("${") and skip_text.endswith("}"):
                literal_expr = skip_text[2:-1].strip().lower()
                if literal_expr in {"false", "none", "null"}:
                    return False, None
                if literal_expr == "true":
                    return True, f"{skip_text} => True"
                try:
                    rendered_skip = self._render(skip_text, variables, funcs, envmap, strict=True)
                except Exception as exc:
                    raise ValueError(
                        f"Invalid skip expression for step '{step.name}': {exc}"
                    ) from exc
                should_skip = self._coerce_skip_bool(rendered_skip)
                if not should_skip:
                    return False, None
                return True, f"{skip_text} => {rendered_skip!r}"
            return True, skip_text
        should_skip = bool(raw_skip)
        return should_skip, str(raw_skip) if should_skip else None

    def _resolve_repeat_count(
        self,
        step: Step,
        variables: Dict[str, Any],
        funcs: Dict[str, Any] | None,
        envmap: Dict[str, Any] | None,
    ) -> int:
        raw_repeat = step.repeat if step.repeat is not None else 1
        rendered_repeat: Any = raw_repeat
        if isinstance(raw_repeat, str):
            try:
                rendered_repeat = self._render(raw_repeat, variables, funcs, envmap, strict=True)
            except Exception as exc:
                raise ValueError(
                    f"Invalid repeat expression for step '{step.name}': {exc}"
                ) from exc

        if isinstance(rendered_repeat, bool):
            raise ValueError(f"Step '{step.name}' repeat must be an integer, got boolean.")

        if isinstance(rendered_repeat, int):
            repeat_count = rendered_repeat
        elif isinstance(rendered_repeat, str):
            stripped = rendered_repeat.strip()
            if re.fullmatch(r"-?\d+", stripped):
                repeat_count = int(stripped)
            else:
                raise ValueError(
                    f"Step '{step.name}' repeat must resolve to an integer, got '{rendered_repeat}'."
                )
        else:
            raise ValueError(
                f"Step '{step.name}' repeat must resolve to an integer, got {type(rendered_repeat).__name__}."
            )

        if repeat_count < 0:
            raise ValueError(f"Step '{step.name}' repeat must be >= 0.")
        return repeat_count

    def _resolve_sleep_milliseconds(
        self,
        step: Step,
        variables: Dict[str, Any],
        funcs: Dict[str, Any] | None,
        envmap: Dict[str, Any] | None,
    ) -> float:
        raw_sleep = step.sleep
        if raw_sleep is None:
            raise ValueError(f"Step '{step.name}' does not define 'sleep'.")

        rendered_sleep: Any = raw_sleep
        if isinstance(raw_sleep, str):
            try:
                rendered_sleep = self._render(raw_sleep, variables, funcs, envmap, strict=True)
            except Exception as exc:
                raise ValueError(
                    f"Invalid sleep expression for step '{step.name}': {exc}"
                ) from exc

        if isinstance(rendered_sleep, bool):
            raise ValueError(f"Step '{step.name}' sleep must be a number, got boolean.")

        try:
            sleep_ms = float(rendered_sleep)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Step '{step.name}' sleep must resolve to a number, got {rendered_sleep!r}."
            ) from exc

        if not math.isfinite(sleep_ms):
            raise ValueError(f"Step '{step.name}' sleep must be a finite number.")
        if sleep_ms < 0:
            raise ValueError(f"Step '{step.name}' sleep must be >= 0.")
        return sleep_ms

    def _prepare_context(
        self,
        case: Case,
        global_vars: Dict[str, Any],
        params: Dict[str, Any],
        funcs: Dict[str, Any] | None,
        envmap: Dict[str, Any] | None,
    ) -> tuple[VarContext, HTTPClient]:
        """Build merged variable context and HTTP client for a case run."""
        base_vars_raw: Dict[str, Any] = {**(case.config.variables or {}), **(params or {})}
        rendered_base = {**global_vars}
        for key, value in base_vars_raw.items():
            if key not in global_vars:
                rendered_base[key] = self._render(value, rendered_base, funcs, envmap)
        ctx = VarContext(rendered_base)
        client = self._build_client(case)
        return ctx, client

    def _execute_setup_hooks(
        self,
        case: Case,
        ctx: VarContext,
        global_vars: Dict[str, Any],
        funcs: Dict[str, Any] | None,
        envmap: Dict[str, Any] | None,
        name: str,
    ) -> List[StepResult]:
        """Run suite- and case-level setup hooks, updating ctx in-place."""
        results: List[StepResult] = []
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
            results.append(StepResult(name="case setup hooks", status="failed", error=f"{e}"))
            raise
        return results

    def _execute_teardown_hooks(
        self,
        case: Case,
        ctx: VarContext,
        global_vars: Dict[str, Any],
        funcs: Dict[str, Any] | None,
        envmap: Dict[str, Any] | None,
        last_resp_obj: Dict[str, Any] | None,
        name: str,
    ) -> List[StepResult]:
        """Run suite- and case-level teardown hooks (best-effort)."""
        results: List[StepResult] = []
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
            results.append(StepResult(name="case teardown hooks", status="failed", error=f"{e}"))
        return results

    def run_case(self, case: Case, global_vars: Dict[str, Any], params: Dict[str, Any], *, funcs: Dict[str, Any] | None = None, envmap: Dict[str, Any] | None = None, source: str | None = None) -> CaseInstanceResult:
        name = case.config.name or "Unnamed Case"
        t0 = time.perf_counter()
        steps_results: List[StepResult] = []
        status = "passed"
        last_resp_obj: Dict[str, Any] | None = None

        ctx, client = self._prepare_context(case, global_vars, params, funcs, envmap)
        step_lifecycle = StepLifecycle(self)

        try:
            steps_results.extend(self._execute_setup_hooks(case, ctx, global_vars, funcs, envmap, name))

            for step_idx, step in enumerate(case.steps, 1):
                base_variables = ctx.get_merged(global_vars)
                rendered_locals = self._render(step.variables, base_variables, funcs, envmap)
                ctx.push(rendered_locals if isinstance(rendered_locals, dict) else (step.variables or {}))
                variables = ctx.get_merged(global_vars)

                if step.sleep is not None or step.request is not None or step.invoke is not None:
                    lifecycle_result = step_lifecycle.execute(
                        StepLifecycleContext(
                            step=step,
                            step_idx=step_idx,
                            case_name=case.config.name or name,
                            ctx=ctx,
                            global_vars=global_vars,
                            rendered_locals=rendered_locals if isinstance(rendered_locals, dict) else (step.variables or {}),
                            funcs=funcs,
                            envmap=envmap,
                            client=client,
                            params=params,
                            source=source,
                        )
                    )
                    lifecycle_results = lifecycle_result.results
                    steps_results.extend(lifecycle_results)
                    if lifecycle_result.last_response is not None:
                        last_resp_obj = lifecycle_result.last_response
                    if any(result.status == "failed" for result in lifecycle_results):
                        status = "failed"
                        if self.failfast:
                            ctx.pop()
                            break
                    ctx.pop()
                    continue

                ctx.pop()

        finally:
            steps_results.extend(
                self._execute_teardown_hooks(case, ctx, global_vars, funcs, envmap, last_resp_obj, name)
            )
            client.close()

        total_ms = (time.perf_counter() - t0) * 1000.0

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
        step_duration = 0.0
        for case in results:
            for step in case.steps or []:
                step_total += 1
                step_duration += step.duration_ms or 0.0
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
                    "steps_duration_ms": step_duration,
                }
            )

        return RunReport(
            summary=summary,
            cases=results,
        )

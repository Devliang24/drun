from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from drun.engine.http import HTTPClient
from drun.loader.yaml_loader import format_variables_multiline
from drun.models.case import Case
from drun.models.report import CaseInstanceResult, RunReport, StepResult, to_report_safe
from drun.models.step import Step
from drun.templating.compat import clean_escaped_template_string
from drun.templating.context import VarContext
from drun.templating.engine import TemplateEngine
from drun.runner.extractors import extract_from_body
from drun.runner.asserting import evaluate_validators
from drun.runner.hooks import run_setup_hooks, run_teardown_hooks
from drun.runner.invoke import execute_invoke_step
from drun.utils.curl import to_curl
from drun.utils.mask import mask_body, mask_headers


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

    def run_case(self, case: Case, global_vars: Dict[str, Any], params: Dict[str, Any], *, funcs: Dict[str, Any] | None = None, envmap: Dict[str, Any] | None = None, source: str | None = None) -> CaseInstanceResult:
        name = case.config.name or "Unnamed Case"
        t0 = time.perf_counter()
        steps_results: List[StepResult] = []
        status = "passed"
        last_resp_obj: Dict[str, Any] | None = None

        # Evaluate case-level variables once to fix values across steps
        # global_vars (from invoke) take precedence over case.config.variables
        base_vars_raw: Dict[str, Any] = {**(case.config.variables or {}), **(params or {})}
        # Resolve sequentially so variables can reference earlier ones
        # Use global_vars as initial context so invoke-passed variables are available
        rendered_base = {**global_vars}
        for key, value in base_vars_raw.items():
            # Only render if not already set by global_vars (invoke takes precedence)
            if key not in global_vars:
                rendered_base[key] = self._render(value, rendered_base, funcs, envmap)
            # else: keep the value from global_vars
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

            for step_idx, step in enumerate(case.steps, 1):
                base_variables = ctx.get_merged(global_vars)
                rendered_locals = self._render(step.variables, base_variables, funcs, envmap)
                ctx.push(rendered_locals if isinstance(rendered_locals, dict) else (step.variables or {}))
                variables = ctx.get_merged(global_vars)

                rendered_base_step_name = self._render(step.name, variables, funcs, envmap)
                if not isinstance(rendered_base_step_name, str):
                    rendered_base_step_name = str(step.name)

                try:
                    repeat_total = self._resolve_repeat_count(step, variables, funcs, envmap)
                except Exception as e:
                    status = "failed"
                    error_msg = f"repeat error: {e}"
                    if self.log:
                        self.log.error(f"[STEP] Step {step_idx} Repeat error: {e}")
                    steps_results.append(
                        StepResult(
                            name=rendered_base_step_name,
                            origin_step_name=rendered_base_step_name,
                            status="failed",
                            error=error_msg,
                        )
                    )
                    ctx.pop()
                    if self.failfast:
                        break
                    continue

                if repeat_total == 0:
                    skipped_name = f"{rendered_base_step_name} [repeat=0]"
                    if self.log:
                        self.log.info(f"[STEP] Step {step_idx} Skip: {skipped_name} | reason=repeat=0")
                    steps_results.append(
                        StepResult(
                            name=skipped_name,
                            origin_step_name=rendered_base_step_name,
                            status="skipped",
                            repeat_total=0,
                        )
                    )
                    ctx.pop()
                    continue

                stop_current_step = False

                if step.invoke:
                    for repeat_index in range(repeat_total):
                        iteration_base_vars = ctx.get_merged(global_vars)
                        iteration_vars = self._build_repeat_variables(iteration_base_vars, repeat_index)

                        iteration_step_name = self._render(step.name, iteration_vars, funcs, envmap)
                        if not isinstance(iteration_step_name, str):
                            iteration_step_name = str(step.name)
                        rendered_step_name = self._format_repeat_step_name(
                            iteration_step_name, repeat_index, repeat_total
                        )

                        try:
                            should_skip, skip_reason = self._resolve_skip_decision(
                                step, iteration_vars, funcs, envmap
                            )
                        except Exception as e:
                            status = "failed"
                            if self.log:
                                self.log.error(f"[STEP] Step {step_idx} Skip error: {e}")
                            steps_results.append(
                                StepResult(
                                    name=rendered_step_name,
                                    origin_step_name=iteration_step_name,
                                    repeat_index=repeat_index,
                                    repeat_no=repeat_index + 1,
                                    repeat_total=repeat_total,
                                    status="failed",
                                    error=f"skip error: {e}",
                                )
                            )
                            if self.failfast:
                                stop_current_step = True
                                break
                            continue

                        if should_skip:
                            skip_reason_text = skip_reason or "skip=true"
                            if self.log:
                                self.log.info(
                                    f"[STEP] Step {step_idx} Skip: {rendered_step_name} | reason={skip_reason_text}"
                                )
                            steps_results.append(
                                StepResult(
                                    name=rendered_step_name,
                                    origin_step_name=iteration_step_name,
                                    repeat_index=repeat_index,
                                    repeat_no=repeat_index + 1,
                                    repeat_total=repeat_total,
                                    status="skipped",
                                    error=skip_reason_text,
                                )
                            )
                            continue

                        invoke_results = self._run_invoke_step(
                            step=step,
                            step_idx=step_idx,
                            rendered_step_name=rendered_step_name,
                            variables=iteration_vars,
                            global_vars=global_vars,
                            funcs=funcs,
                            envmap=envmap,
                            ctx=ctx,
                            params=params,
                            invoke_result_prefix=rendered_step_name if repeat_total > 1 else None,
                            repeat_index=repeat_index,
                            repeat_no=repeat_index + 1,
                            repeat_total=repeat_total,
                        )
                        steps_results.extend(invoke_results)
                        if any(r.status == "failed" for r in invoke_results):
                            status = "failed"
                            if self.failfast:
                                stop_current_step = True
                                break

                    ctx.pop()
                    if stop_current_step:
                        break
                    continue

                if step.sleep is not None:
                    step_locals_for_hook = rendered_locals if isinstance(rendered_locals, dict) else (step.variables or {})

                    for repeat_index in range(repeat_total):
                        iteration_base_vars = ctx.get_merged(global_vars)
                        variables = self._build_repeat_variables(iteration_base_vars, repeat_index)

                        iteration_step_name = self._render(step.name, variables, funcs, envmap)
                        if not isinstance(iteration_step_name, str):
                            iteration_step_name = str(step.name)
                        rendered_step_name = self._format_repeat_step_name(
                            iteration_step_name, repeat_index, repeat_total
                        )

                        try:
                            should_skip, skip_reason = self._resolve_skip_decision(
                                step, variables, funcs, envmap
                            )
                        except Exception as e:
                            status = "failed"
                            if self.log:
                                self.log.error(f"[STEP] Step {step_idx} Skip error: {e}")
                            steps_results.append(
                                StepResult(
                                    name=rendered_step_name,
                                    origin_step_name=iteration_step_name,
                                    repeat_index=repeat_index,
                                    repeat_no=repeat_index + 1,
                                    repeat_total=repeat_total,
                                    status="failed",
                                    error=f"skip error: {e}",
                                )
                            )
                            if self.failfast:
                                stop_current_step = True
                                break
                            continue

                        if should_skip:
                            skip_reason_text = skip_reason or "skip=true"
                            if self.log:
                                self.log.info(
                                    f"[STEP] Step {step_idx} Skip: {rendered_step_name} | reason={skip_reason_text}"
                                )
                            steps_results.append(
                                StepResult(
                                    name=rendered_step_name,
                                    origin_step_name=iteration_step_name,
                                    repeat_index=repeat_index,
                                    repeat_no=repeat_index + 1,
                                    repeat_total=repeat_total,
                                    status="skipped",
                                    error=skip_reason_text,
                                )
                            )
                            continue

                        try:
                            sleep_ms = self._resolve_sleep_milliseconds(
                                step, variables, funcs, envmap
                            )
                        except Exception as e:
                            status = "failed"
                            if self.log:
                                self.log.error(f"[STEP] Step {step_idx} Sleep error: {e}")
                            steps_results.append(
                                StepResult(
                                    name=rendered_step_name,
                                    origin_step_name=iteration_step_name,
                                    repeat_index=repeat_index,
                                    repeat_no=repeat_index + 1,
                                    repeat_total=repeat_total,
                                    status="failed",
                                    error=f"sleep error: {e}",
                                )
                            )
                            if self.failfast:
                                stop_current_step = True
                                break
                            continue

                        sleep_request = {"sleep": sleep_ms}
                        setup_meta = {
                            "step_name": step.name,
                            "case_name": case.config.name or name,
                            "step_request": sleep_request,
                            "step_variables": step_locals_for_hook,
                            "session_variables": variables,
                            "session_env": envmap or {},
                            "step_sleep": sleep_ms,
                            "step_sleep_ms": sleep_ms,
                        }
                        try:
                            new_vars = self._run_setup_hooks(
                                step.setup_hooks,
                                funcs=funcs,
                                req=sleep_request,
                                variables=variables,
                                envmap=envmap,
                                meta=setup_meta,
                            )
                            for k, v in (new_vars or {}).items():
                                ctx.set_base(k, v)
                                if self.log:
                                    self.log.info(f"[HOOK] set var: {k} = {v!r}")
                            variables = self._build_repeat_variables(ctx.get_merged(global_vars), repeat_index)
                        except Exception as e:
                            status = "failed"
                            if self.log:
                                self.log.error(f"[HOOK] setup error: {e}")
                            steps_results.append(
                                StepResult(
                                    name=rendered_step_name,
                                    origin_step_name=iteration_step_name,
                                    repeat_index=repeat_index,
                                    repeat_no=repeat_index + 1,
                                    repeat_total=repeat_total,
                                    status="failed",
                                    error=f"setup hook error: {e}",
                                )
                            )
                            if self.failfast:
                                stop_current_step = True
                                break
                            continue

                        if self.log:
                            self.log.info(f"[STEP] Step {step_idx} Start: {rendered_step_name}")
                            step_vars = step.variables or {}
                            if step_vars:
                                vars_str = format_variables_multiline(step_vars, "[STEP] variables: ")
                                self.log.info(vars_str)
                            self.log.info(f"[SLEEP] {sleep_ms:g}ms")

                        sleep_started = time.perf_counter()
                        try:
                            time.sleep(sleep_ms / 1000.0)
                            elapsed_ms = (time.perf_counter() - sleep_started) * 1000.0
                        except Exception as e:
                            status = "failed"
                            if self.log:
                                self.log.error(f"[STEP] Sleep execution error: {e}")
                            steps_results.append(
                                StepResult(
                                    name=rendered_step_name,
                                    origin_step_name=iteration_step_name,
                                    repeat_index=repeat_index,
                                    repeat_no=repeat_index + 1,
                                    repeat_total=repeat_total,
                                    status="failed",
                                    request={"sleep": sleep_ms},
                                    error=f"sleep error: {e}",
                                )
                            )
                            if self.failfast:
                                stop_current_step = True
                                break
                            continue

                        resp_obj = {
                            "sleep_ms": sleep_ms,
                            "elapsed_ms": elapsed_ms,
                        }
                        last_resp_obj = resp_obj
                        step_failed = False
                        teardown_error: Optional[str] = None

                        try:
                            teardown_meta = {
                                "step_name": step.name,
                                "case_name": case.config.name or name,
                                "step_response": resp_obj,
                                "step_request": sleep_request,
                                "step_variables": variables,
                                "session_variables": ctx.get_merged(global_vars),
                                "session_env": envmap or {},
                                "step_sleep": sleep_ms,
                                "step_sleep_ms": sleep_ms,
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
                            variables = self._build_repeat_variables(ctx.get_merged(global_vars), repeat_index)
                        except Exception as e:
                            step_failed = True
                            teardown_error = f"teardown hook error: {e}"
                            if self.log:
                                self.log.error(f"[HOOK] teardown error: {e}")

                        steps_results.append(
                            StepResult(
                                name=rendered_step_name,
                                origin_step_name=iteration_step_name,
                                repeat_index=repeat_index,
                                repeat_no=repeat_index + 1,
                                repeat_total=repeat_total,
                                status="failed" if step_failed else "passed",
                                request={"sleep": sleep_ms},
                                response={
                                    "sleep_ms": sleep_ms,
                                    "elapsed_ms": elapsed_ms,
                                },
                                duration_ms=elapsed_ms,
                                error=teardown_error,
                            )
                        )

                        if step_failed:
                            status = "failed"
                            if self.log:
                                self.log.error(f"[STEP] Step {step_idx} Completed: {rendered_step_name} | FAILED")
                        else:
                            if self.log:
                                self.log.info(
                                    f"[STEP] Step {step_idx} Completed: {rendered_step_name} | PASSED"
                                )

                        if step_failed and self.failfast:
                            stop_current_step = True
                            break

                    ctx.pop()
                    if stop_current_step:
                        break
                    continue

                req_dict = self._request_dict(step)
                step_locals_for_hook = rendered_locals if isinstance(rendered_locals, dict) else (step.variables or {})

                for repeat_index in range(repeat_total):
                    iteration_base_vars = ctx.get_merged(global_vars)
                    variables = self._build_repeat_variables(iteration_base_vars, repeat_index)

                    iteration_step_name = self._render(step.name, variables, funcs, envmap)
                    if not isinstance(iteration_step_name, str):
                        iteration_step_name = str(step.name)
                    rendered_step_name = self._format_repeat_step_name(
                        iteration_step_name, repeat_index, repeat_total
                    )

                    try:
                        should_skip, skip_reason = self._resolve_skip_decision(
                            step, variables, funcs, envmap
                        )
                    except Exception as e:
                        status = "failed"
                        if self.log:
                            self.log.error(f"[STEP] Step {step_idx} Skip error: {e}")
                        steps_results.append(
                            StepResult(
                                name=rendered_step_name,
                                origin_step_name=iteration_step_name,
                                repeat_index=repeat_index,
                                repeat_no=repeat_index + 1,
                                repeat_total=repeat_total,
                                status="failed",
                                error=f"skip error: {e}",
                            )
                        )
                        if self.failfast:
                            stop_current_step = True
                            break
                        continue

                    if should_skip:
                        skip_reason_text = skip_reason or "skip=true"
                        if self.log:
                            self.log.info(
                                f"[STEP] Step {step_idx} Skip: {rendered_step_name} | reason={skip_reason_text}"
                            )
                        steps_results.append(
                            StepResult(
                                name=rendered_step_name,
                                origin_step_name=iteration_step_name,
                                repeat_index=repeat_index,
                                repeat_no=repeat_index + 1,
                                repeat_total=repeat_total,
                                status="skipped",
                                error=skip_reason_text,
                            )
                        )
                        continue

                    req_rendered = self._render(req_dict, variables, funcs, envmap, strict=True)
                    session_vars_for_hook = variables
                    setup_meta = {
                        "step_name": step.name,
                        "case_name": case.config.name or name,
                        "step_request": req_rendered,
                        "step_variables": step_locals_for_hook,
                        "session_variables": session_vars_for_hook,
                        "session_env": envmap or {},
                    }
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
                        variables = self._build_repeat_variables(ctx.get_merged(global_vars), repeat_index)
                    except Exception as e:
                        status = "failed"
                        if self.log:
                            self.log.error(f"[HOOK] setup error: {e}")
                        steps_results.append(
                            StepResult(
                                name=rendered_step_name,
                                origin_step_name=iteration_step_name,
                                repeat_index=repeat_index,
                                repeat_no=repeat_index + 1,
                                repeat_total=repeat_total,
                                status="failed",
                                error=f"setup hook error: {e}",
                            )
                        )
                        if self.failfast:
                            stop_current_step = True
                            break
                        continue

                    if isinstance(req_rendered.get("headers"), dict):
                        headers = dict(req_rendered["headers"])  # type: ignore[index]
                        for hk, hv in list(headers.items()):
                            if hv is None:
                                headers.pop(hk, None)
                            elif isinstance(hv, str) and (hv.strip() == "" or hv.strip().lower() in {"bearer", "bearer none"}):
                                headers.pop(hk, None)
                        req_rendered["headers"] = headers
                    if not (isinstance(req_rendered.get("headers"), dict) and any(k.lower() == "authorization" for k in req_rendered["headers"])):
                        tok = variables.get("token") if isinstance(variables, dict) else None
                        if isinstance(tok, str) and tok.strip():
                            hdrs = dict(req_rendered.get("headers") or {})
                            hdrs["Authorization"] = f"Bearer {tok}"
                            req_rendered["headers"] = hdrs

                    if self.log:
                        self.log.info(f"[STEP] Step {step_idx} Start: {rendered_step_name}")
                        self._log_render_diffs(req_dict, req_rendered)
                        step_vars = step.variables or {}
                        if step_vars:
                            vars_str = format_variables_multiline(step_vars, "[STEP] variables: ")
                            self.log.info(vars_str)
                        self.log.info(f"[REQUEST] {req_rendered.get('method','GET')} {req_rendered.get('path')}")
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
                        if req_rendered.get("files") is not None:
                            self.log.info(self._fmt_aligned("REQ", "files", self._fmt_json(req_rendered.get("files"))))

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

                        req_summary = {
                            k: to_report_safe(v)
                            for k, v in (req_rendered or {}).items()
                            if k in ("method", "path", "params", "headers", "body", "data", "files")
                        }
                        url_rendered = (req_rendered or {}).get("path")
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
                                origin_step_name=iteration_step_name,
                                repeat_index=repeat_index,
                                repeat_no=repeat_index + 1,
                                repeat_total=repeat_total,
                                status="failed",
                                request=req_summary,
                                response={"error": f"Request error: {last_error}"},
                                curl=curl_cmd,
                                error=f"Request error: {last_error}",
                                duration_ms=0.0,
                            )
                        )
                        if self.failfast:
                            stop_current_step = True
                            break
                        continue

                    assert resp_obj is not None
                    last_resp_obj = resp_obj

                    if self.log:
                        hdrs = resp_obj.get("headers") or {}
                        if not self.reveal:
                            hdrs = mask_headers(hdrs)

                        is_stream = resp_obj.get("is_stream", False)
                        if is_stream:
                            stream_summary = resp_obj.get("stream_summary", {})
                            event_count = stream_summary.get("event_count", 0)
                            first_chunk_ms = stream_summary.get("first_chunk_ms", 0)
                            self.log.info(f"[RESPONSE] status={resp_obj.get('status_code')} elapsed={resp_obj.get('elapsed_ms'):.1f}ms (streaming: {event_count} events, first chunk: {first_chunk_ms:.1f}ms)")
                        else:
                            self.log.info(f"[RESPONSE] status={resp_obj.get('status_code')} elapsed={resp_obj.get('elapsed_ms'):.1f}ms")

                        if self.log_response_headers:
                            self.log.info(self._fmt_aligned("RESP", "headers", self._fmt_json(hdrs)))

                        if is_stream:
                            stream_events = resp_obj.get("stream_events", [])
                            progressive_content = resp_obj.get("progressive_content", [])

                            if stream_events:
                                self.log.info(f"[STREAM] {len(stream_events)} events received")

                                if progressive_content:
                                    chunk_num = 0
                                    for event in stream_events:
                                        event_data = event.get("data")
                                        if event_data and isinstance(event_data, dict):
                                            choices = event_data.get("choices", [])
                                            if choices and len(choices) > 0:
                                                delta = choices[0].get("delta", {})
                                                if delta.get("content"):
                                                    chunk_num += 1
                                                    self.log.info(self._fmt_aligned("STREAM", f"Chunk {chunk_num}", self._fmt_json(event)))

                                    if progressive_content:
                                        final_chunk = progressive_content[-1]
                                        final_content = final_chunk.get("content", "")
                                        final_time = final_chunk.get("timestamp_ms", 0)
                                        self.log.info(f"[STREAM] 完成 ({final_time:.0f}ms)，最终内容：")
                                        self.log.info(final_content)
                                else:
                                    if len(stream_events) > 0:
                                        first_event = stream_events[0]
                                        self.log.info(self._fmt_aligned("STREAM", "event[0]", self._fmt_json(first_event)))
                                    if len(stream_events) > 1:
                                        last_event = stream_events[-1]
                                        self.log.info(self._fmt_aligned("STREAM", f"event[{len(stream_events)-1}]", self._fmt_json(last_event)))
                        else:
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
                            elif resp_obj.get("body_size") is not None:
                                content_type = resp_obj.get("content_type") or "application/octet-stream"
                                self.log.info(
                                    "[RESPONSE] binary body=%s bytes content-type=%s",
                                    resp_obj.get("body_size"),
                                    content_type,
                                )

                    extracts: Dict[str, Any] = {}
                    for var, expr in (step.extract or {}).items():
                        if isinstance(expr, str) and "${" in expr:
                            import re
                            jpath_pattern = r'\$\.[\w\[\]\.]+(?:\[\d+\])*(?:\.[\w\[\]]+)*'
                            jpaths = re.findall(jpath_pattern, expr)
                            temp_vars = dict(variables)
                            temp_expr = expr
                            for idx, jp in enumerate(jpaths):
                                extracted = self._eval_extract(jp, resp_obj)
                                temp_var_name = f"_jpath_{idx}"
                                temp_vars[temp_var_name] = extracted
                                temp_expr = temp_expr.replace(jp, temp_var_name)
                            val = self.templater.render_expression(temp_expr, temp_vars, funcs, envmap)
                        else:
                            val = self._eval_extract(expr, resp_obj)
                        extracts[var] = val
                        ctx.set_base(var, val)
                        if self.log:
                            self.log.info(f"[EXTRACT] {var} = {val!r} from {expr}")

                    if extracts and envmap is not None:
                        from drun.utils.env_writer import to_env_var_name
                        for var_name, value in extracts.items():
                            env_key = to_env_var_name(var_name)
                            envmap[env_key] = value
                            envmap[var_name] = value

                    if extracts:
                        from pathlib import Path
                        from drun.utils.env_writer import (
                            write_env_variable,
                            write_yaml_variable,
                            to_env_var_name
                        )

                        env_path = Path(self.persist_env_file)
                        is_yaml = env_path.suffix.lower() in {'.yaml', '.yml'}

                        for var_name, value in extracts.items():
                            try:
                                env_key = to_env_var_name(var_name)

                                if is_yaml:
                                    write_yaml_variable(str(env_path), var_name, value)
                                else:
                                    write_env_variable(str(env_path), var_name, value)

                                if self.log:
                                    self.log.info(
                                        f"[PERSIST] {var_name} → {env_key} = {value!r} "
                                        f"(已写入 {self.persist_env_file})"
                                    )
                            except Exception as e:
                                if self.log:
                                    self.log.warning(f"[PERSIST] 写入失败 {var_name}: {e}")

                    if step.export:
                        if "csv" in step.export:
                            csv_config = step.export["csv"]
                            rendered_config = self._render(csv_config, variables, funcs, envmap)
                            data_expr = rendered_config.get("data")
                            if not data_expr:
                                raise ValueError("export.csv.data 字段是必填的")

                            array_data = self._eval_extract(data_expr, resp_obj)

                            from pathlib import Path
                            from drun.utils.data_exporter import export_to_csv

                            try:
                                from drun.loader.hooks import find_hooks
                                hooks_file = find_hooks(Path.cwd())
                                base_dir = hooks_file.parent if hooks_file else Path.cwd()

                                row_count = export_to_csv(
                                    data=array_data,
                                    file_path=rendered_config["file"],
                                    columns=rendered_config.get("columns"),
                                    encoding=rendered_config.get("encoding", "utf-8"),
                                    mode=rendered_config.get("mode", "overwrite"),
                                    delimiter=rendered_config.get("delimiter", ","),
                                    base_dir=base_dir,
                                )

                                if self.log:
                                    self.log.info(
                                        f"[EXPORT CSV] {row_count} rows → {rendered_config['file']}"
                                    )
                            except Exception as e:
                                if self.log:
                                    self.log.error(f"[EXPORT CSV] 导出失败: {e}")
                                raise

                    variables = self._build_repeat_variables(ctx.get_merged(global_vars), repeat_index)

                    saved_body_to: Optional[str] = None
                    save_error: Optional[str] = None
                    if step.response and step.response.save_body_to:
                        try:
                            saved_body_to = self._save_response_body(
                                target=step.response.save_body_to,
                                resp=resp_obj,
                                variables=variables,
                                funcs=funcs,
                                envmap=envmap,
                            )
                            resp_obj["saved_body_to"] = saved_body_to
                            if self.log:
                                self.log.info(f"[RESPONSE] body saved to {saved_body_to}")
                        except Exception as e:
                            save_error = f"Save response body failed: {e}"
                            resp_obj["save_error"] = save_error
                            if self.log:
                                self.log.error(f"[RESPONSE] {save_error}")

                    assertions, step_failed = evaluate_validators(
                        runner=self,
                        validators=step.validators,
                        variables=variables,
                        funcs=funcs,
                        envmap=envmap,
                        resp_obj=resp_obj,
                    )
                    if save_error:
                        step_failed = True

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
                        variables = self._build_repeat_variables(ctx.get_merged(global_vars), repeat_index)
                    except Exception as e:
                        step_failed = True
                        if self.log:
                            self.log.error(f"[HOOK] teardown error: {e}")

                    body_masked = resp_obj.get("body")
                    if not self.reveal:
                        body_masked = mask_body(body_masked)

                    response_dict = {
                        "status_code": resp_obj.get("status_code"),
                    }

                    if resp_obj.get("is_stream"):
                        response_dict["is_stream"] = True
                        response_dict["stream_events"] = resp_obj.get("stream_events", [])
                        response_dict["stream_summary"] = resp_obj.get("stream_summary", {})
                        response_dict["stream_raw_chunks"] = resp_obj.get("stream_raw_chunks", [])
                        if not self.reveal:
                            masked_events = []
                            for event in response_dict["stream_events"]:
                                masked_event = event.copy()
                                if isinstance(masked_event.get("data"), (dict, list)):
                                    masked_event["data"] = mask_body(masked_event["data"])
                                masked_events.append(masked_event)
                            response_dict["stream_events"] = masked_events
                    else:
                        if isinstance(body_masked, (dict, list)):
                            response_dict["body"] = body_masked
                        elif body_masked is None:
                            response_dict["body"] = None
                        elif isinstance(body_masked, (str, bytes)):
                            if isinstance(body_masked, bytes):
                                text = body_masked.decode("utf-8", errors="replace")
                            else:
                                text = body_masked
                            response_dict["body"] = text if len(text) <= 2048 else text[:2048] + "..."
                        elif isinstance(body_masked, (bool, int, float)):
                            response_dict["body"] = body_masked
                        else:
                            text = str(body_masked)
                            response_dict["body"] = text if len(text) <= 2048 else text[:2048] + "..."
                        if resp_obj.get("content_type") is not None:
                            response_dict["content_type"] = resp_obj.get("content_type")
                        if resp_obj.get("body_size") is not None:
                            response_dict["body_size"] = resp_obj.get("body_size")
                        if resp_obj.get("body_bytes_b64") is not None:
                            response_dict["body_bytes_b64"] = resp_obj.get("body_bytes_b64")
                        if resp_obj.get("saved_body_to") is not None:
                            response_dict["saved_body_to"] = resp_obj.get("saved_body_to")
                        if resp_obj.get("save_error") is not None:
                            response_dict["save_error"] = resp_obj.get("save_error")

                    url_rendered = resp_obj.get("url") or req_rendered.get("path")
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
                        origin_step_name=iteration_step_name,
                        repeat_index=repeat_index,
                        repeat_no=repeat_index + 1,
                        repeat_total=repeat_total,
                        status="failed" if step_failed else "passed",
                        request={
                            k: to_report_safe(v)
                            for k, v in req_rendered.items()
                            if k in ("method", "path", "url", "params", "headers", "body", "data", "files")
                        },
                        response=response_dict,
                        curl=curl,
                        asserts=assertions,
                        extracts=extracts,
                        duration_ms=resp_obj.get("elapsed_ms") or 0.0,
                        error=save_error,
                    )
                    steps_results.append(sr)
                    if step_failed:
                        status = "failed"
                        if self.log:
                            self.log.error(f"[STEP] Step {step_idx} Completed: {rendered_step_name} | FAILED")
                    else:
                        if self.log:
                            self.log.info(f"[STEP] Step {step_idx} Completed: {rendered_step_name} | PASSED")

                    if step_failed and self.failfast:
                        stop_current_step = True
                        break

                ctx.pop()
                if stop_current_step:
                    break

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

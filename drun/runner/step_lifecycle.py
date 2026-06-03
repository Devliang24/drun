"""Step lifecycle: orchestrates step execution with unified retry.

Each step runs through: skip → setup hooks → retry loop → teardown hooks.
The retry loop covers both HTTP exceptions and check failures.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Dict, List, Optional

from drun.loader.yaml_loader import format_variables_multiline
from drun.models.report import StepResult
from drun.models.retry import get_retry_max, get_retry_every
from drun.models.step import Step
from drun.runner.execution_context import ExecutionContext
from drun.runner.protocols import RunnerProtocol
from drun.runner.request_projection import (
    finalize_request_projection,
    render_request_for_setup,
)
from drun.runner.retry import parse_duration, sleep_every
from drun.runner.step_outcome import StepOutcomeContext, process_step_outcome
from drun.utils.mask import mask_body, mask_headers


@dataclass
class StepLifecycleContext(ExecutionContext):
    step_idx: int
    case_name: str
    rendered_locals: Dict[str, Any]
    client: Any | None = None
    params: Dict[str, Any] | None = None
    source: str | None = None


@dataclass
class StepLifecycleResult:
    results: List[StepResult]
    last_response: Dict[str, Any] | None = None


class StepLifecycle:
    def __init__(self, runner: RunnerProtocol) -> None:
        self.runner = runner

    def execute(self, context: StepLifecycleContext) -> StepLifecycleResult:
        if context.step.sleep is not None:
            return self._execute_sleep_step(context)
        if context.step.request is not None:
            return self._execute_request_step(context)
        if context.step.invoke is not None:
            return self._execute_invoke_step(context)
        raise NotImplementedError(
            "StepLifecycle currently supports sleep, request, and invoke steps only."
        )

    # ── Sleep step (no retry) ─────────────────────────────────────

    def _execute_sleep_step(self, context: StepLifecycleContext) -> StepLifecycleResult:
        step = context.step
        runner = self.runner
        last_response: Dict[str, Any] | None = None

        rendered_step_name = self._render_step_name(
            step,
            context.ctx.get_merged(context.global_vars),
            context,
        )

        # skip decision
        try:
            should_skip, skip_reason = runner._resolve_skip_decision(
                step,
                context.ctx.get_merged(context.global_vars),
                context.funcs,
                context.envmap,
            )
        except Exception as e:
            if runner.log:
                runner.log.error(f"[STEP] Step {context.step_idx} Skip error: {e}")
            return StepLifecycleResult(
                results=[
                    StepResult(
                        name=rendered_step_name,
                        origin_step_name=rendered_step_name,
                        status="failed",
                        error=f"skip error: {e}",
                    )
                ]
            )

        if should_skip:
            skip_reason_text = skip_reason or "skip=true"
            if runner.log:
                runner.log.info(
                    f"[STEP] Step {context.step_idx} Skip: {rendered_step_name} | reason={skip_reason_text}"
                )
            return StepLifecycleResult(
                results=[
                    StepResult(
                        name=rendered_step_name,
                        origin_step_name=rendered_step_name,
                        status="skipped",
                        error=skip_reason_text,
                    )
                ]
            )

        variables = context.ctx.get_merged(context.global_vars)

        try:
            sleep_ms = runner._resolve_sleep_milliseconds(
                step, variables, context.funcs, context.envmap
            )
        except Exception as e:
            if runner.log:
                runner.log.error(f"[STEP] Step {context.step_idx} Sleep error: {e}")
            return StepLifecycleResult(
                results=[
                    StepResult(
                        name=rendered_step_name,
                        origin_step_name=rendered_step_name,
                        status="failed",
                        error=f"sleep error: {e}",
                    )
                ]
            )

        step_locals_for_hook = (
            context.rendered_locals
            if isinstance(context.rendered_locals, dict)
            else (step.variables or {})
        )

        sleep_request = {"sleep": sleep_ms}
        setup_meta = {
            "step_name": step.name,
            "case_name": context.case_name,
            "step_request": sleep_request,
            "step_variables": step_locals_for_hook,
            "session_variables": variables,
            "session_env": context.envmap or {},
            "step_sleep": sleep_ms,
            "step_sleep_ms": sleep_ms,
        }

        # setup hooks
        try:
            new_vars = runner._run_setup_hooks(
                step.setup_hooks,
                funcs=context.funcs,
                req=sleep_request,
                variables=variables,
                envmap=context.envmap,
                meta=setup_meta,
            )
            for k, v in (new_vars or {}).items():
                context.ctx.set_base(k, v)
                if runner.log:
                    runner.log.info(f"[HOOK] set var: {k} = {v!r}")
            variables = context.ctx.get_merged(context.global_vars)
        except Exception as e:
            if runner.log:
                runner.log.error(f"[HOOK] setup error: {e}")
            return StepLifecycleResult(
                results=[
                    StepResult(
                        name=rendered_step_name,
                        origin_step_name=rendered_step_name,
                        status="failed",
                        error=f"setup hook error: {e}",
                    )
                ]
            )

        if runner.log:
            runner.log.info(f"[STEP] Step {context.step_idx} Start: {rendered_step_name}")
            step_vars = step.variables or {}
            if step_vars:
                vars_str = format_variables_multiline(step_vars, "[STEP] variables: ")
                runner.log.info(vars_str)
            runner.log.info(f"[SLEEP] {sleep_ms:g}ms")

        sleep_started = time.perf_counter()
        try:
            time.sleep(sleep_ms / 1000.0)
            elapsed_ms = (time.perf_counter() - sleep_started) * 1000.0
        except Exception as e:
            if runner.log:
                runner.log.error(f"[STEP] Sleep execution error: {e}")
            return StepLifecycleResult(
                results=[
                    StepResult(
                        name=rendered_step_name,
                        origin_step_name=rendered_step_name,
                        status="failed",
                        request={"sleep": sleep_ms},
                        error=f"sleep error: {e}",
                    )
                ]
            )

        resp_obj = {"sleep_ms": sleep_ms, "elapsed_ms": elapsed_ms}
        last_response = resp_obj
        step_failed = False
        teardown_error: Optional[str] = None

        # teardown hooks
        try:
            teardown_meta = {
                "step_name": step.name,
                "case_name": context.case_name,
                "step_response": resp_obj,
                "step_request": sleep_request,
                "step_variables": variables,
                "session_variables": context.ctx.get_merged(context.global_vars),
                "session_env": context.envmap or {},
                "step_sleep": sleep_ms,
                "step_sleep_ms": sleep_ms,
            }
            new_vars_td = runner._run_teardown_hooks(
                step.teardown_hooks,
                funcs=context.funcs,
                resp=resp_obj,
                variables=variables,
                envmap=context.envmap,
                meta=teardown_meta,
            )
            for k, v in (new_vars_td or {}).items():
                context.ctx.set_base(k, v)
                if runner.log:
                    runner.log.info(f"[HOOK] set var: {k} = {v!r}")
        except Exception as e:
            step_failed = True
            teardown_error = f"teardown hook error: {e}"
            if runner.log:
                runner.log.error(f"[HOOK] teardown error: {e}")

        sr = StepResult(
            name=rendered_step_name,
            origin_step_name=rendered_step_name,
            status="failed" if step_failed else "passed",
            request={"sleep": sleep_ms},
            response={"sleep_ms": sleep_ms, "elapsed_ms": elapsed_ms},
            duration_ms=elapsed_ms,
            error=teardown_error,
        )

        if step_failed:
            if runner.log:
                runner.log.error(
                    f"[STEP] Step {context.step_idx} Completed: {rendered_step_name} | FAILED"
                )
        elif runner.log:
            runner.log.info(
                f"[STEP] Step {context.step_idx} Completed: {rendered_step_name} | PASSED"
            )

        return StepLifecycleResult(results=[sr], last_response=last_response)

    # ── Request step (with retry) ──────────────────────────────────

    def _execute_request_step(self, context: StepLifecycleContext) -> StepLifecycleResult:
        step = context.step
        runner = self.runner
        client = context.client
        if client is None:
            raise ValueError("StepLifecycleContext.client is required for request steps.")

        last_response: Dict[str, Any] | None = None

        rendered_base_step_name = self._render_step_name(
            step, context.ctx.get_merged(context.global_vars), context
        )

        retry_max = get_retry_max(step.retry)
        retry_every = get_retry_every(step.retry)

        # --- skip decision (once) ---
        try:
            should_skip, skip_reason = runner._resolve_skip_decision(
                step,
                context.ctx.get_merged(context.global_vars),
                context.funcs,
                context.envmap,
            )
        except Exception as e:
            if runner.log:
                runner.log.error(f"[STEP] Step {context.step_idx} Skip error: {e}")
            return StepLifecycleResult(
                results=[
                    StepResult(
                        name=rendered_base_step_name,
                        origin_step_name=rendered_base_step_name,
                        status="failed",
                        error=f"skip error: {e}",
                    )
                ]
            )

        if should_skip:
            skip_reason_text = skip_reason or "skip=true"
            if runner.log:
                runner.log.info(
                    f"[STEP] Step {context.step_idx} Skip: {rendered_base_step_name} | reason={skip_reason_text}"
                )
            return StepLifecycleResult(
                results=[
                    StepResult(
                        name=rendered_base_step_name,
                        origin_step_name=rendered_base_step_name,
                        status="skipped",
                        error=skip_reason_text,
                    )
                ]
            )

        req_dict = runner._request_dict(step)
        step_locals_for_hook = (
            context.rendered_locals
            if isinstance(context.rendered_locals, dict)
            else (step.variables or {})
        )

        # --- setup hooks (once) ---
        variables = context.ctx.get_merged(context.global_vars)
        req_rendered = render_request_for_setup(
            runner=runner,
            step=step,
            variables=variables,
            funcs=context.funcs,
            envmap=context.envmap,
        )
        setup_meta = {
            "step_name": step.name,
            "case_name": context.case_name,
            "step_request": req_rendered,
            "step_variables": step_locals_for_hook,
            "session_variables": variables,
            "session_env": context.envmap or {},
        }
        try:
            new_vars = runner._run_setup_hooks(
                step.setup_hooks,
                funcs=context.funcs,
                req=req_rendered,
                variables=variables,
                envmap=context.envmap,
                meta=setup_meta,
            )
            for k, v in (new_vars or {}).items():
                context.ctx.set_base(k, v)
                if runner.log:
                    runner.log.info(f"[HOOK] set var: {k} = {v!r}")
        except Exception as e:
            if runner.log:
                runner.log.error(f"[HOOK] setup error: {e}")
            return StepLifecycleResult(
                results=[
                    StepResult(
                        name=rendered_base_step_name,
                        origin_step_name=rendered_base_step_name,
                        status="failed",
                        error=f"setup hook error: {e}",
                    )
                ]
            )

        # --- retry loop ---
        final_sr: StepResult | None = None
        final_variables = variables
        # teardown offset — rebuild ctx vars with base so hooks see latest state
        teardown_variables_final: Dict[str, Any] | None = None

        for attempt in range(1, retry_max + 1):
            # rebuild variables for current attempt (hooks may have updated ctx)
            attempt_vars_raw = context.ctx.get_merged(context.global_vars)
            attempt_vars = runner._build_retry_variables(
                attempt_vars_raw, attempt, retry_max
            )

            # render step name and request
            iteration_step_name = self._render_step_name(step, attempt_vars, context)
            rendered_step_name = runner._format_retry_step_name(
                iteration_step_name, attempt, retry_max
            )

            req_rendered_attempt = render_request_for_setup(
                runner=runner,
                step=step,
                variables=attempt_vars,
                funcs=context.funcs,
                envmap=context.envmap,
            )

            request_projection = finalize_request_projection(
                runner=runner,
                rendered_request=req_rendered_attempt,
                variables=attempt_vars,
            )
            req_rendered_attempt = request_projection.runtime_request

            self._log_request_start(
                context=context,
                rendered_step_name=rendered_step_name,
                req_dict=req_dict,
                req_rendered=req_rendered_attempt,
                step=step,
            )

            # --- HTTP request ---
            try:
                resp_obj = client.request(req_rendered_attempt)
            except Exception as e:
                if runner.log:
                    runner.log.warning(
                        f"[RETRY] Request error attempt {attempt}/{retry_max}: {e}"
                    )
                if attempt >= retry_max:
                    # last attempt exhausted
                    sr = self._build_request_error_result(
                        request_projection=request_projection,
                        rendered_step_name=rendered_step_name,
                        iteration_step_name=iteration_step_name,
                        attempt=attempt,
                        attempt_total=retry_max,
                        error=str(e),
                    )
                    final_sr = sr
                    break
                sleep_every(retry_every, attempt)
                continue

            last_response = resp_obj
            request_projection = finalize_request_projection(
                runner=runner,
                rendered_request=req_rendered_attempt,
                variables=attempt_vars,
                response_url=resp_obj.get("url"),
            )
            req_rendered_attempt = request_projection.runtime_request
            self._log_response(resp_obj)

            # --- process outcome (check / extract / export) ---
            outcome = process_step_outcome(
                runner=runner,
                context=StepOutcomeContext(
                    step=step,
                    resp_obj=resp_obj,
                    variables=attempt_vars,
                    ctx=context.ctx,
                    global_vars=context.global_vars,
                    attempt=attempt,
                    funcs=context.funcs,
                    envmap=context.envmap,
                ),
            )
            final_variables = outcome.variables

            if not outcome.step_failed:
                # passed — build success result
                sr = StepResult(
                    name=rendered_step_name,
                    origin_step_name=iteration_step_name,
                    attempt=attempt,
                    attempt_total=retry_max,
                    status="passed",
                    request=request_projection.report_request,
                    response=outcome.report_response,
                    curl=request_projection.curl,
                    checks=outcome.checks,
                    extracts=outcome.extracts,
                    duration_ms=resp_obj.get("elapsed_ms") or 0.0,
                    error=outcome.error,
                )
                final_sr = sr
                teardown_variables_final = final_variables
                if runner.log:
                    runner.log.info(
                        f"[STEP] Step {context.step_idx} Completed: {rendered_step_name} | PASSED"
                    )
                break

            # check failed — may retry
            if runner.log:
                runner.log.warning(
                    f"[RETRY] Check failed attempt {attempt}/{retry_max}"
                )
            if attempt >= retry_max:
                sr = StepResult(
                    name=rendered_step_name,
                    origin_step_name=iteration_step_name,
                    attempt=attempt,
                    attempt_total=retry_max,
                    status="failed",
                    request=request_projection.report_request,
                    response=outcome.report_response,
                    curl=request_projection.curl,
                    checks=outcome.checks,
                    extracts=outcome.extracts,
                    duration_ms=resp_obj.get("elapsed_ms") or 0.0,
                    error=outcome.error,
                )
                final_sr = sr
                if runner.log:
                    runner.log.error(
                        f"[STEP] Step {context.step_idx} Completed: {rendered_step_name} | FAILED"
                    )
                break
            sleep_every(retry_every, attempt)

        # --- teardown hooks (once) ---
        if final_sr is None:
            # should never happen but safety net
            final_sr = StepResult(
                name=rendered_base_step_name,
                origin_step_name=rendered_base_step_name,
                attempt=retry_max,
                attempt_total=retry_max,
                status="failed",
                error="step did not produce a result",
            )

        td_vars = teardown_variables_final or context.ctx.get_merged(context.global_vars)
        teardown_meta: Dict[str, Any] = {
            "step_name": step.name,
            "case_name": context.case_name,
            "step_response": last_response or {},
            "step_request": final_sr.request or {},
            "step_variables": td_vars,
            "session_variables": context.ctx.get_merged(context.global_vars),
            "session_env": context.envmap or {},
        }
        try:
            new_vars_td = runner._run_teardown_hooks(
                step.teardown_hooks,
                funcs=context.funcs,
                resp=last_response or {},
                variables=td_vars,
                envmap=context.envmap,
                meta=teardown_meta,
            )
            for k, v in (new_vars_td or {}).items():
                context.ctx.set_base(k, v)
                if runner.log:
                    runner.log.info(f"[HOOK] set var: {k} = {v!r}")
        except Exception as e:
            final_sr.status = "failed"
            final_sr.error = f"{final_sr.error}; teardown hook error: {e}" if final_sr.error else f"teardown hook error: {e}"
            if runner.log:
                runner.log.error(f"[HOOK] teardown error: {e}")

        return StepLifecycleResult(results=[final_sr], last_response=last_response)

    # ── Invoke step (with retry) ───────────────────────────────────

    def _execute_invoke_step(self, context: StepLifecycleContext) -> StepLifecycleResult:
        step = context.step
        runner = self.runner

        rendered_base_step_name = self._render_step_name(
            step, context.ctx.get_merged(context.global_vars), context
        )

        retry_max = get_retry_max(step.retry)
        retry_every = get_retry_every(step.retry)

        # --- skip decision (once) ---
        try:
            should_skip, skip_reason = runner._resolve_skip_decision(
                step,
                context.ctx.get_merged(context.global_vars),
                context.funcs,
                context.envmap,
            )
        except Exception as e:
            if runner.log:
                runner.log.error(f"[STEP] Step {context.step_idx} Skip error: {e}")
            return StepLifecycleResult(
                results=[
                    StepResult(
                        name=rendered_base_step_name,
                        origin_step_name=rendered_base_step_name,
                        status="failed",
                        error=f"skip error: {e}",
                    )
                ]
            )

        if should_skip:
            skip_reason_text = skip_reason or "skip=true"
            if runner.log:
                runner.log.info(
                    f"[STEP] Step {context.step_idx} Skip: {rendered_base_step_name} | reason={skip_reason_text}"
                )
            return StepLifecycleResult(
                results=[
                    StepResult(
                        name=rendered_base_step_name,
                        origin_step_name=rendered_base_step_name,
                        status="skipped",
                        error=skip_reason_text,
                    )
                ]
            )

        # --- retry loop ---
        for attempt in range(1, retry_max + 1):
            attempt_vars_raw = context.ctx.get_merged(context.global_vars)
            attempt_vars = runner._build_retry_variables(
                attempt_vars_raw, attempt, retry_max
            )

            iteration_step_name = self._render_step_name(step, attempt_vars, context)
            rendered_step_name = runner._format_retry_step_name(
                iteration_step_name, attempt, retry_max
            )

            if runner.log:
                runner.log.info(f"[STEP] Step {context.step_idx} Start: {rendered_step_name}")

            invoke_results = runner._run_invoke_step(
                step=step,
                step_idx=context.step_idx,
                rendered_step_name=rendered_step_name,
                variables=attempt_vars,
                global_vars=context.global_vars,
                funcs=context.funcs,
                envmap=context.envmap,
                ctx=context.ctx,
                params=context.params,
                source=context.source,
            )

            any_failed = any(r.status == "failed" for r in invoke_results)
            if not any_failed:
                # passed — keep only this attempt's results
                all_invoke_results = invoke_results
                if runner.log:
                    runner.log.info(
                        f"[STEP] Step {context.step_idx} Completed: {rendered_step_name} | PASSED"
                    )
                break
            if attempt >= retry_max:
                all_invoke_results = invoke_results
                if runner.log:
                    runner.log.error(
                        f"[STEP] Step {context.step_idx} Completed: {rendered_step_name} | FAILED"
                    )
                break
            if runner.log:
                runner.log.warning(
                    f"[RETRY] Invoke failed attempt {attempt}/{retry_max}"
                )
            sleep_every(retry_every, attempt)

        return StepLifecycleResult(results=all_invoke_results)

    # ── Helpers ────────────────────────────────────────────────────

    def _log_request_start(
        self,
        *,
        context: StepLifecycleContext,
        rendered_step_name: str,
        req_dict: Dict[str, Any],
        req_rendered: Dict[str, Any],
        step: Step,
    ) -> None:
        runner = self.runner
        if not runner.log:
            return
        runner.log.info(f"[STEP] Step {context.step_idx} Start: {rendered_step_name}")
        runner._log_render_diffs(req_dict, req_rendered)
        step_vars = step.variables or {}
        if step_vars:
            vars_str = format_variables_multiline(step_vars, "[STEP] variables: ")
            runner.log.info(vars_str)
        runner.log.info(
            f"[REQUEST] {req_rendered.get('method','GET')} {req_rendered.get('path')}"
        )
        if req_rendered.get("params") is not None:
            runner.log.info(
                runner._fmt_aligned("REQ", "params", runner._fmt_json(req_rendered.get("params")))
            )
        if req_rendered.get("headers"):
            hdrs_out = req_rendered.get("headers")
            if not runner.reveal:
                hdrs_out = mask_headers(hdrs_out)
            runner.log.info(
                runner._fmt_aligned("REQ", "headers", runner._fmt_json(hdrs_out))
            )
        if req_rendered.get("body") is not None:
            body = req_rendered.get("body")
            if isinstance(body, (dict, list)) and not runner.reveal:
                body = mask_body(body)
            runner.log.info(runner._fmt_aligned("REQ", "body", runner._fmt_json(body)))
        if req_rendered.get("data") is not None:
            data = req_rendered.get("data")
            if isinstance(data, (dict, list)) and not runner.reveal:
                data = mask_body(data)
            runner.log.info(runner._fmt_aligned("REQ", "data", runner._fmt_json(data)))
        if req_rendered.get("files") is not None:
            runner.log.info(
                runner._fmt_aligned("REQ", "files", runner._fmt_json(req_rendered.get("files")))
            )

    def _log_response(self, resp_obj: Dict[str, Any]) -> None:
        runner = self.runner
        if not runner.log:
            return
        hdrs = resp_obj.get("headers") or {}
        if not runner.reveal:
            hdrs = mask_headers(hdrs)

        is_stream = resp_obj.get("is_stream", False)
        if is_stream:
            stream_summary = resp_obj.get("stream_summary", {})
            event_count = stream_summary.get("event_count", 0)
            first_chunk_ms = stream_summary.get("first_chunk_ms", 0)
            runner.log.info(
                f"[RESPONSE] status={resp_obj.get('status_code')} elapsed={resp_obj.get('elapsed_ms'):.1f}ms "
                f"(streaming: {event_count} events, first chunk: {first_chunk_ms:.1f}ms)"
            )
        else:
            runner.log.info(
                f"[RESPONSE] status={resp_obj.get('status_code')} elapsed={resp_obj.get('elapsed_ms'):.1f}ms"
            )

        if runner.log_response_headers:
            runner.log.info(runner._fmt_aligned("RESP", "headers", runner._fmt_json(hdrs)))

        if is_stream:
            stream_events = resp_obj.get("stream_events", [])
            progressive_content = resp_obj.get("progressive_content", [])

            if stream_events:
                runner.log.info(f"[STREAM] {len(stream_events)} events received")

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
                                    runner.log.info(
                                        runner._fmt_aligned(
                                            "STREAM", f"Chunk {chunk_num}", runner._fmt_json(event)
                                        )
                                    )

                    if progressive_content:
                        final_chunk = progressive_content[-1]
                        final_content = final_chunk.get("content", "")
                        final_time = final_chunk.get("timestamp_ms", 0)
                        runner.log.info(f"[STREAM] 完成 ({final_time:.0f}ms)，最终内容：")
                        runner.log.info(final_content)
                else:
                    if len(stream_events) > 0:
                        first_event = stream_events[0]
                        runner.log.info(
                            runner._fmt_aligned(
                                "STREAM", "event[0]", runner._fmt_json(first_event)
                            )
                        )
                    if len(stream_events) > 1:
                        last_event = stream_events[-1]
                        runner.log.info(
                            runner._fmt_aligned(
                                "STREAM",
                                f"event[{len(stream_events)-1}]",
                                runner._fmt_json(last_event),
                            )
                        )
            return

        body_preview = resp_obj.get("body")
        if isinstance(body_preview, (dict, list)):
            out_body = body_preview
            if not runner.reveal:
                out_body = mask_body(out_body)
            runner.log.info(runner._fmt_aligned("RESP", "body", runner._fmt_json(out_body)))
        elif body_preview is not None:
            text = str(body_preview)
            if len(text) > 2000:
                text = text[:2000] + "..."
            runner.log.info(runner._fmt_aligned("RESP", "text", text))
        elif resp_obj.get("body_size") is not None:
            content_type = resp_obj.get("content_type") or "application/octet-stream"
            runner.log.info(
                "[RESPONSE] binary body=%s bytes content-type=%s",
                resp_obj.get("body_size"),
                content_type,
            )

    def _build_request_error_result(
        self,
        *,
        request_projection: Any,
        rendered_step_name: str,
        iteration_step_name: str,
        attempt: int,
        attempt_total: int,
        error: str,
    ) -> StepResult:
        return StepResult(
            name=rendered_step_name,
            origin_step_name=iteration_step_name,
            attempt=attempt,
            attempt_total=attempt_total,
            status="failed",
            request=request_projection.report_request,
            response={"error": f"Request error: {error}"},
            curl=request_projection.curl,
            error=f"Request error: {error}",
            duration_ms=0.0,
        )

    def _render_step_name(
        self,
        step: Step,
        variables: Dict[str, Any],
        context: StepLifecycleContext,
    ) -> str:
        rendered = self.runner._render(
            step.name,
            variables,
            context.funcs,
            context.envmap,
        )
        if not isinstance(rendered, str):
            return str(step.name)
        return rendered

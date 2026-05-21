from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

from drun.loader.yaml_loader import format_variables_multiline
from drun.models.report import StepResult
from drun.models.step import Step
from drun.runner.asserting import evaluate_validators
from drun.runner.request_projection import (
    finalize_request_projection,
    render_request_for_setup,
)
from drun.templating.context import VarContext
from drun.utils.mask import mask_body, mask_headers


@dataclass
class StepLifecycleContext:
    step: Step
    step_idx: int
    case_name: str
    ctx: VarContext
    global_vars: Dict[str, Any]
    rendered_locals: Dict[str, Any]
    funcs: Dict[str, Any] | None = None
    envmap: Dict[str, Any] | None = None
    client: Any | None = None


@dataclass
class StepLifecycleResult:
    results: List[StepResult]
    last_response: Dict[str, Any] | None = None


class StepLifecycle:
    def __init__(self, runner: Any) -> None:
        self.runner = runner

    def execute(self, context: StepLifecycleContext) -> StepLifecycleResult:
        if context.step.sleep is not None:
            return self._execute_sleep_step(context)
        if context.step.request is not None:
            return self._execute_request_step(context)
        raise NotImplementedError("StepLifecycle currently supports sleep and request steps only.")

    def _execute_sleep_step(self, context: StepLifecycleContext) -> StepLifecycleResult:
        step = context.step
        runner = self.runner
        results: List[StepResult] = []
        last_response: Dict[str, Any] | None = None
        stop_current_step = False

        try:
            repeat_total = runner._resolve_repeat_count(
                step,
                context.ctx.get_merged(context.global_vars),
                context.funcs,
                context.envmap,
            )
        except Exception as e:
            rendered_name = self._render_step_name(
                step,
                context.ctx.get_merged(context.global_vars),
                context,
            )
            if runner.log:
                runner.log.error(f"[STEP] Step {context.step_idx} Repeat error: {e}")
            return StepLifecycleResult(
                results=[
                    StepResult(
                        name=rendered_name,
                        origin_step_name=rendered_name,
                        status="failed",
                        error=f"repeat error: {e}",
                    )
                ]
            )

        if repeat_total == 0:
            rendered_name = self._render_step_name(
                step,
                context.ctx.get_merged(context.global_vars),
                context,
            )
            skipped_name = f"{rendered_name} [repeat=0]"
            if runner.log:
                runner.log.info(
                    f"[STEP] Step {context.step_idx} Skip: {skipped_name} | reason=repeat=0"
                )
            return StepLifecycleResult(
                results=[
                    StepResult(
                        name=skipped_name,
                        origin_step_name=rendered_name,
                        status="skipped",
                        repeat_total=0,
                    )
                ]
            )

        step_locals_for_hook = (
            context.rendered_locals
            if isinstance(context.rendered_locals, dict)
            else (step.variables or {})
        )

        for repeat_index in range(repeat_total):
            iteration_base_vars = context.ctx.get_merged(context.global_vars)
            variables = runner._build_repeat_variables(iteration_base_vars, repeat_index)

            iteration_step_name = self._render_step_name(step, variables, context)
            rendered_step_name = runner._format_repeat_step_name(
                iteration_step_name, repeat_index, repeat_total
            )

            try:
                should_skip, skip_reason = runner._resolve_skip_decision(
                    step, variables, context.funcs, context.envmap
                )
            except Exception as e:
                if runner.log:
                    runner.log.error(f"[STEP] Step {context.step_idx} Skip error: {e}")
                results.append(
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
                if runner.failfast:
                    break
                continue

            if should_skip:
                skip_reason_text = skip_reason or "skip=true"
                if runner.log:
                    runner.log.info(
                        f"[STEP] Step {context.step_idx} Skip: {rendered_step_name} | reason={skip_reason_text}"
                    )
                results.append(
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
                sleep_ms = runner._resolve_sleep_milliseconds(
                    step, variables, context.funcs, context.envmap
                )
            except Exception as e:
                if runner.log:
                    runner.log.error(f"[STEP] Step {context.step_idx} Sleep error: {e}")
                results.append(
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
                if runner.failfast:
                    break
                continue

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
                variables = runner._build_repeat_variables(
                    context.ctx.get_merged(context.global_vars),
                    repeat_index,
                )
            except Exception as e:
                if runner.log:
                    runner.log.error(f"[HOOK] setup error: {e}")
                results.append(
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
                if runner.failfast:
                    break
                continue

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
                results.append(
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
                if runner.failfast:
                    break
                continue

            resp_obj = {
                "sleep_ms": sleep_ms,
                "elapsed_ms": elapsed_ms,
            }
            last_response = resp_obj
            step_failed = False
            teardown_error: Optional[str] = None

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

            results.append(
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
                if runner.log:
                    runner.log.error(
                        f"[STEP] Step {context.step_idx} Completed: {rendered_step_name} | FAILED"
                    )
                if runner.failfast:
                    stop_current_step = True
            elif runner.log:
                runner.log.info(
                    f"[STEP] Step {context.step_idx} Completed: {rendered_step_name} | PASSED"
                )

            if stop_current_step:
                break

        return StepLifecycleResult(results=results, last_response=last_response)

    def _execute_request_step(self, context: StepLifecycleContext) -> StepLifecycleResult:
        step = context.step
        runner = self.runner
        client = context.client
        if client is None:
            raise ValueError("StepLifecycleContext.client is required for request steps.")

        results: List[StepResult] = []
        last_response: Dict[str, Any] | None = None

        rendered_base_step_name = self._render_step_name(
            step,
            context.ctx.get_merged(context.global_vars),
            context,
        )

        try:
            repeat_total = runner._resolve_repeat_count(
                step,
                context.ctx.get_merged(context.global_vars),
                context.funcs,
                context.envmap,
            )
        except Exception as e:
            if runner.log:
                runner.log.error(f"[STEP] Step {context.step_idx} Repeat error: {e}")
            return StepLifecycleResult(
                results=[
                    StepResult(
                        name=rendered_base_step_name,
                        origin_step_name=rendered_base_step_name,
                        status="failed",
                        error=f"repeat error: {e}",
                    )
                ]
            )

        if repeat_total == 0:
            skipped_name = f"{rendered_base_step_name} [repeat=0]"
            if runner.log:
                runner.log.info(
                    f"[STEP] Step {context.step_idx} Skip: {skipped_name} | reason=repeat=0"
                )
            return StepLifecycleResult(
                results=[
                    StepResult(
                        name=skipped_name,
                        origin_step_name=rendered_base_step_name,
                        status="skipped",
                        repeat_total=0,
                    )
                ]
            )

        req_dict = runner._request_dict(step)
        step_locals_for_hook = (
            context.rendered_locals
            if isinstance(context.rendered_locals, dict)
            else (step.variables or {})
        )
        stop_current_step = False

        for repeat_index in range(repeat_total):
            iteration_base_vars = context.ctx.get_merged(context.global_vars)
            variables = runner._build_repeat_variables(iteration_base_vars, repeat_index)

            iteration_step_name = self._render_step_name(step, variables, context)
            rendered_step_name = runner._format_repeat_step_name(
                iteration_step_name, repeat_index, repeat_total
            )

            try:
                should_skip, skip_reason = runner._resolve_skip_decision(
                    step, variables, context.funcs, context.envmap
                )
            except Exception as e:
                if runner.log:
                    runner.log.error(f"[STEP] Step {context.step_idx} Skip error: {e}")
                results.append(
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
                if runner.failfast:
                    break
                continue

            if should_skip:
                skip_reason_text = skip_reason or "skip=true"
                if runner.log:
                    runner.log.info(
                        f"[STEP] Step {context.step_idx} Skip: {rendered_step_name} | reason={skip_reason_text}"
                    )
                results.append(
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

            req_rendered = render_request_for_setup(
                runner=runner,
                step=step,
                variables=variables,
                funcs=context.funcs,
                envmap=context.envmap,
            )
            session_vars_for_hook = variables
            setup_meta = {
                "step_name": step.name,
                "case_name": context.case_name,
                "step_request": req_rendered,
                "step_variables": step_locals_for_hook,
                "session_variables": session_vars_for_hook,
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
                variables = runner._build_repeat_variables(
                    context.ctx.get_merged(context.global_vars), repeat_index
                )
            except Exception as e:
                if runner.log:
                    runner.log.error(f"[HOOK] setup error: {e}")
                results.append(
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
                if runner.failfast:
                    stop_current_step = True
                    break
                continue

            request_projection = finalize_request_projection(
                runner=runner,
                rendered_request=req_rendered,
                variables=variables,
            )
            req_rendered = request_projection.runtime_request

            self._log_request_start(
                context=context,
                rendered_step_name=rendered_step_name,
                req_dict=req_dict,
                req_rendered=req_rendered,
                step=step,
            )

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
                if runner.log:
                    runner.log.error(f"[STEP] Request error: {last_error}")
                results.append(
                    self._build_request_error_result(
                        request_projection=request_projection,
                        rendered_step_name=rendered_step_name,
                        iteration_step_name=iteration_step_name,
                        repeat_index=repeat_index,
                        repeat_total=repeat_total,
                        error=last_error,
                    )
                )
                if runner.failfast:
                    stop_current_step = True
                    break
                continue

            assert resp_obj is not None
            last_response = resp_obj
            request_projection = finalize_request_projection(
                runner=runner,
                rendered_request=req_rendered,
                variables=variables,
                response_url=resp_obj.get("url"),
            )
            req_rendered = request_projection.runtime_request
            self._log_response(resp_obj)

            extracts = self._extract_response_values(step, resp_obj, variables, context)
            self._persist_extracts(extracts, context)

            if step.export:
                self._export_step_data(step, resp_obj, variables, context)

            variables = runner._build_repeat_variables(
                context.ctx.get_merged(context.global_vars), repeat_index
            )

            save_error = self._save_response_body_if_needed(
                step=step,
                resp_obj=resp_obj,
                variables=variables,
                context=context,
            )

            assertions, step_failed = evaluate_validators(
                runner=runner,
                validators=step.validators,
                variables=variables,
                funcs=context.funcs,
                envmap=context.envmap,
                resp_obj=resp_obj,
            )
            if save_error:
                step_failed = True

            try:
                teardown_meta = {
                    "step_name": step.name,
                    "case_name": context.case_name,
                    "step_response": resp_obj,
                    "step_request": req_rendered,
                    "step_variables": variables,
                    "session_variables": context.ctx.get_merged(context.global_vars),
                    "session_env": context.envmap or {},
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
                variables = runner._build_repeat_variables(
                    context.ctx.get_merged(context.global_vars), repeat_index
                )
            except Exception as e:
                step_failed = True
                if runner.log:
                    runner.log.error(f"[HOOK] teardown error: {e}")

            sr = StepResult(
                name=rendered_step_name,
                origin_step_name=iteration_step_name,
                repeat_index=repeat_index,
                repeat_no=repeat_index + 1,
                repeat_total=repeat_total,
                status="failed" if step_failed else "passed",
                request=request_projection.report_request,
                response=self._build_response_dict(resp_obj),
                curl=request_projection.curl,
                asserts=assertions,
                extracts=extracts,
                duration_ms=resp_obj.get("elapsed_ms") or 0.0,
                error=save_error,
            )
            results.append(sr)
            if step_failed:
                if runner.log:
                    runner.log.error(
                        f"[STEP] Step {context.step_idx} Completed: {rendered_step_name} | FAILED"
                    )
                if runner.failfast:
                    stop_current_step = True
            elif runner.log:
                runner.log.info(
                    f"[STEP] Step {context.step_idx} Completed: {rendered_step_name} | PASSED"
                )

            if stop_current_step:
                break

        return StepLifecycleResult(results=results, last_response=last_response)

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

    def _extract_response_values(
        self,
        step: Step,
        resp_obj: Dict[str, Any],
        variables: Dict[str, Any],
        context: StepLifecycleContext,
    ) -> Dict[str, Any]:
        runner = self.runner
        extracts: Dict[str, Any] = {}
        for var, expr in (step.extract or {}).items():
            if isinstance(expr, str) and "${" in expr:
                import re

                jpath_pattern = r'\$\.[\w\[\]\.]+(?:\[\d+\])*(?:\.[\w\[\]]+)*'
                jpaths = re.findall(jpath_pattern, expr)
                temp_vars = dict(variables)
                temp_expr = expr
                for idx, jp in enumerate(jpaths):
                    extracted = runner._eval_extract(jp, resp_obj)
                    temp_var_name = f"_jpath_{idx}"
                    temp_vars[temp_var_name] = extracted
                    temp_expr = temp_expr.replace(jp, temp_var_name)
                val = runner.templater.render_expression(
                    temp_expr, temp_vars, context.funcs, context.envmap
                )
            else:
                val = runner._eval_extract(expr, resp_obj)
            extracts[var] = val
            context.ctx.set_base(var, val)
            if runner.log:
                runner.log.info(f"[EXTRACT] {var} = {val!r} from {expr}")
        return extracts

    def _persist_extracts(
        self,
        extracts: Dict[str, Any],
        context: StepLifecycleContext,
    ) -> None:
        if not extracts:
            return

        runner = self.runner
        from drun.utils.env_writer import to_env_var_name

        if context.envmap is not None:
            for var_name, value in extracts.items():
                env_key = to_env_var_name(var_name)
                context.envmap[env_key] = value
                context.envmap[var_name] = value

        from drun.utils.env_writer import write_env_variable, write_yaml_variable

        env_path = Path(runner.persist_env_file)
        is_yaml = env_path.suffix.lower() in {".yaml", ".yml"}

        for var_name, value in extracts.items():
            try:
                env_key = to_env_var_name(var_name)
                if is_yaml:
                    write_yaml_variable(str(env_path), var_name, value)
                else:
                    write_env_variable(str(env_path), var_name, value)
                if runner.log:
                    runner.log.info(
                        f"[PERSIST] {var_name} → {env_key} = {value!r} "
                        f"(已写入 {runner.persist_env_file})"
                    )
            except Exception as e:
                if runner.log:
                    runner.log.warning(f"[PERSIST] 写入失败 {var_name}: {e}")

    def _export_step_data(
        self,
        step: Step,
        resp_obj: Dict[str, Any],
        variables: Dict[str, Any],
        context: StepLifecycleContext,
    ) -> None:
        runner = self.runner
        if not step.export or "csv" not in step.export:
            return

        csv_config = step.export["csv"]
        rendered_config = runner._render(csv_config, variables, context.funcs, context.envmap)
        data_expr = rendered_config.get("data")
        if not data_expr:
            raise ValueError("export.csv.data 字段是必填的")

        array_data = runner._eval_extract(data_expr, resp_obj)

        from drun.loader.hooks import find_hooks
        from drun.utils.data_exporter import export_to_csv

        try:
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

            if runner.log:
                runner.log.info(f"[EXPORT CSV] {row_count} rows → {rendered_config['file']}")
        except Exception as e:
            if runner.log:
                runner.log.error(f"[EXPORT CSV] 导出失败: {e}")
            raise

    def _save_response_body_if_needed(
        self,
        *,
        step: Step,
        resp_obj: Dict[str, Any],
        variables: Dict[str, Any],
        context: StepLifecycleContext,
    ) -> Optional[str]:
        runner = self.runner
        if not (step.response and step.response.save_body_to):
            return None

        try:
            saved_body_to = runner._save_response_body(
                target=step.response.save_body_to,
                resp=resp_obj,
                variables=variables,
                funcs=context.funcs,
                envmap=context.envmap,
            )
            resp_obj["saved_body_to"] = saved_body_to
            if runner.log:
                runner.log.info(f"[RESPONSE] body saved to {saved_body_to}")
            return None
        except Exception as e:
            save_error = f"Save response body failed: {e}"
            resp_obj["save_error"] = save_error
            if runner.log:
                runner.log.error(f"[RESPONSE] {save_error}")
            return save_error

    def _build_response_dict(self, resp_obj: Dict[str, Any]) -> Dict[str, Any]:
        runner = self.runner
        body_masked = resp_obj.get("body")
        if not runner.reveal:
            body_masked = mask_body(body_masked)

        response_dict: Dict[str, Any] = {
            "status_code": resp_obj.get("status_code"),
        }

        if resp_obj.get("is_stream"):
            response_dict["is_stream"] = True
            response_dict["stream_events"] = resp_obj.get("stream_events", [])
            response_dict["stream_summary"] = resp_obj.get("stream_summary", {})
            response_dict["stream_raw_chunks"] = resp_obj.get("stream_raw_chunks", [])
            if not runner.reveal:
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

        return response_dict

    def _build_request_error_result(
        self,
        *,
        request_projection: Any,
        rendered_step_name: str,
        iteration_step_name: str,
        repeat_index: int,
        repeat_total: int,
        error: str,
    ) -> StepResult:
        return StepResult(
            name=rendered_step_name,
            origin_step_name=iteration_step_name,
            repeat_index=repeat_index,
            repeat_no=repeat_index + 1,
            repeat_total=repeat_total,
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

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Dict, List, Optional

from drun.loader.yaml_loader import format_variables_multiline
from drun.models.report import StepResult
from drun.models.step import Step
from drun.templating.context import VarContext


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


class StepLifecycle:
    def __init__(self, runner: Any) -> None:
        self.runner = runner

    def execute(self, context: StepLifecycleContext) -> List[StepResult]:
        if context.step.sleep is not None:
            return self._execute_sleep_step(context)
        raise NotImplementedError("StepLifecycle currently supports sleep steps only.")

    def _execute_sleep_step(self, context: StepLifecycleContext) -> List[StepResult]:
        step = context.step
        runner = self.runner
        results: List[StepResult] = []
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
            return [
                StepResult(
                    name=rendered_name,
                    origin_step_name=rendered_name,
                    status="failed",
                    error=f"repeat error: {e}",
                )
            ]

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
            return [
                StepResult(
                    name=skipped_name,
                    origin_step_name=rendered_name,
                    status="skipped",
                    repeat_total=0,
                )
            ]

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

        return results

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

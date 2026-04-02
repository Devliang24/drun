from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List

from drun.loader.collector import resolve_invoke_path
from drun.loader.yaml_loader import expand_parameters, load_yaml_file
from drun.models.report import StepResult
from drun.models.step import Step


def execute_invoke_step(
    *,
    runner: Any,
    step: Step,
    step_idx: int,
    rendered_step_name: str,
    variables: Dict[str, Any],
    global_vars: Dict[str, Any],
    funcs: Dict[str, Any] | None,
    envmap: Dict[str, Any] | None,
    ctx: Any,
    params: Dict[str, Any] | None,
) -> List[StepResult]:
    t0 = time.perf_counter()
    invoke_path = step.invoke

    if runner.log:
        runner.log.info(f"[STEP] Step {step_idx} Start: {rendered_step_name}")
        runner.log.info(f"[INVOKE] Loading testcase: {invoke_path}")

    resolved_path = resolve_invoke_path(invoke_path, Path.cwd())
    if resolved_path is None:
        error_msg = f"Cannot find testcase for invoke: {invoke_path}"
        if runner.log:
            runner.log.error(f"[INVOKE] {error_msg}")
        return [
            StepResult(
                name=rendered_step_name,
                status="failed",
                error=error_msg,
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        ]

    if runner.log:
        runner.log.info(f"[INVOKE] Resolved to: {resolved_path}")

    try:
        cases, _ = load_yaml_file(resolved_path)
        if not cases:
            error_msg = f"No testcases found in: {resolved_path}"
            if runner.log:
                runner.log.error(f"[INVOKE] {error_msg}")
            return [
                StepResult(
                    name=rendered_step_name,
                    status="failed",
                    error=error_msg,
                    duration_ms=(time.perf_counter() - t0) * 1000,
                )
            ]
    except Exception as e:
        error_msg = f"Failed to load testcase {resolved_path}: {e}"
        if runner.log:
            runner.log.error(f"[INVOKE] {error_msg}")
        return [
            StepResult(
                name=rendered_step_name,
                status="failed",
                error=error_msg,
                duration_ms=(time.perf_counter() - t0) * 1000,
            )
        ]

    requested_case_names: List[str] = []
    if step.invoke_case_name:
        requested_case_names = [step.invoke_case_name]
    elif step.invoke_case_names:
        requested_case_names = list(step.invoke_case_names)

    named_cases = [(case.config.name or "Unnamed Case", case) for case in cases]
    selected_cases = named_cases
    if requested_case_names:
        if runner.log:
            runner.log.info(
                f"[INVOKE] Selecting case names: {', '.join(requested_case_names)}"
            )

        selected_name_set = set(requested_case_names)
        selected_cases = [
            (case_name, case_obj)
            for case_name, case_obj in named_cases
            if case_name in selected_name_set
        ]
        if not selected_cases:
            requested_display = ", ".join(requested_case_names)
            available_names = [name for name, _ in named_cases]
            available_display = ", ".join(available_names) if available_names else "(none)"
            error_msg = (
                f"No matched case names for invoke '{invoke_path}': "
                f"requested=[{requested_display}] available=[{available_display}]"
            )
            if runner.log:
                runner.log.error(f"[INVOKE] {error_msg}")
            return [
                StepResult(
                    name=rendered_step_name,
                    status="failed",
                    error=error_msg,
                    duration_ms=(time.perf_counter() - t0) * 1000,
                )
            ]

        duplicate_requested: List[str] = []
        for requested_name in requested_case_names:
            match_count = sum(
                1 for case_name, _ in named_cases if case_name == requested_name
            )
            if match_count > 1:
                duplicate_requested.append(requested_name)
        if duplicate_requested and runner.log:
            unique_duplicates = ", ".join(dict.fromkeys(duplicate_requested))
            runner.log.warning(
                f"[INVOKE] Duplicate case names matched and all will run: {unique_duplicates}"
            )
        if len(selected_cases) > 1 and runner.log:
            runner.log.info(f"[INVOKE] Multi-case invoke matched: {len(selected_cases)}")
    else:
        selected_cases = [named_cases[0]]

    invoke_vars = {**variables}
    if step.variables:
        rendered_step_vars = runner._render(step.variables, variables, funcs, envmap)
        if isinstance(rendered_step_vars, dict):
            invoke_vars.update(rendered_step_vars)
            if runner.log:
                for k, v in rendered_step_vars.items():
                    runner.log.info(f"[INVOKE] Passing variable: {k} = {v!r}")

    all_step_results: List[StepResult] = []
    final_status = "passed"
    accumulated_vars = {**invoke_vars}
    stop_execution = False
    for selected_case_name, invoked_case in selected_cases:
        invoked_base_url = invoked_case.config.base_url
        if not invoked_base_url:
            fallback_base = (
                invoke_vars.get("base_url")
                or invoke_vars.get("BASE_URL")
                or (envmap or {}).get("base_url")
                or (envmap or {}).get("BASE_URL")
            )
            if fallback_base:
                invoked_case.config.base_url = fallback_base
                invoked_base_url = fallback_base

        if isinstance(invoked_base_url, str) and (
            "${" in invoked_base_url or "{{" in invoked_base_url
        ):
            try:
                invoked_case.config.base_url = runner._render(
                    invoked_base_url, invoke_vars, funcs, envmap
                )
            except Exception as exc:
                if runner.log:
                    runner.log.error(
                        f"[INVOKE] Failed to render base_url '{invoked_base_url}': {exc}"
                    )
                raise

        if runner.log:
            runner.log.info(f"[INVOKE] Executing case: {selected_case_name}")

        param_sets = expand_parameters(invoked_case.parameters, source_path=str(resolved_path))
        if runner.log and len(param_sets) > 1:
            runner.log.info(
                f"[INVOKE] Expanding {len(param_sets)} parameter sets for {selected_case_name}"
            )

        for ps in param_sets:
            merged_vars = {**accumulated_vars, **ps}

            invoke_result = runner.run_case(
                case=invoked_case,
                global_vars=merged_vars,
                params=ps,
                funcs=funcs,
                envmap=envmap,
                source=str(resolved_path),
            )

            for sr in invoke_result.steps:
                if sr.extracts:
                    for k, v in sr.extracts.items():
                        should_update = bool(v) or k not in accumulated_vars
                        if should_update:
                            accumulated_vars[k] = v

            all_step_results.extend(invoke_result.steps)
            if invoke_result.status == "failed":
                final_status = "failed"
                if runner.failfast:
                    stop_execution = True
                    break
        if stop_execution:
            break

    invoked_extracts = {k: v for k, v in accumulated_vars.items() if k not in invoke_vars or accumulated_vars[k] != invoke_vars.get(k)}

    exported_vars: Dict[str, Any] = {}

    if step.export:
        if isinstance(step.export, list):
            for var_name in step.export:
                if var_name in invoked_extracts:
                    exported_vars[var_name] = invoked_extracts[var_name]
                    ctx.set_base(var_name, invoked_extracts[var_name])
                    if runner.log:
                        runner.log.info(f"[INVOKE] Exported: {var_name} = {invoked_extracts[var_name]!r}")
                elif runner.log:
                    runner.log.warning(f"[INVOKE] Export variable not found: {var_name}")
        elif isinstance(step.export, dict):
            for local_name, source_name in step.export.items():
                if source_name in invoked_extracts:
                    exported_vars[local_name] = invoked_extracts[source_name]
                    ctx.set_base(local_name, invoked_extracts[source_name])
                    if runner.log:
                        runner.log.info(f"[INVOKE] Exported: {local_name} = {invoked_extracts[source_name]!r}")
                elif runner.log:
                    runner.log.warning(f"[INVOKE] Export variable not found: {source_name}")
    else:
        for var_name, var_value in invoked_extracts.items():
            exported_vars[var_name] = var_value
            ctx.set_base(var_name, var_value)
            if runner.log:
                runner.log.info(f"[INVOKE] Auto-exported: {var_name} = {var_value!r}")

    if runner.log:
        status_label = "PASSED" if final_status == "passed" else "FAILED"
        runner.log.info(f"[STEP] Step {step_idx} Completed: {rendered_step_name} | {status_label}")

    return all_step_results

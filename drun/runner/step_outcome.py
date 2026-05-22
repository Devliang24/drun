from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from drun.models.report import CheckResult
from drun.models.step import Step
from drun.runner.checking import evaluate_checks
from drun.runner.response_capture import capture_step_response
from drun.templating.context import VarContext


@dataclass
class StepOutcomeContext:
    step: Step
    resp_obj: Dict[str, Any]
    variables: Dict[str, Any]
    ctx: VarContext
    global_vars: Dict[str, Any]
    repeat_index: int
    funcs: Dict[str, Any] | None = None
    envmap: Dict[str, Any] | None = None


@dataclass
class StepOutcome:
    checks: List[CheckResult] = field(default_factory=list)
    extracts: Dict[str, Any] = field(default_factory=dict)
    report_response: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    step_failed: bool = False
    error: Optional[str] = None


def process_step_outcome(*, runner: Any, context: StepOutcomeContext) -> StepOutcome:
    step = context.step
    resp_obj = context.resp_obj

    extracts = _extract_response_values(
        runner=runner,
        step=step,
        resp_obj=resp_obj,
        variables=context.variables,
        context=context,
    )
    _persist_extracts(runner=runner, extracts=extracts, context=context)

    if step.export:
        _export_step_data(
            runner=runner,
            step=step,
            resp_obj=resp_obj,
            variables=context.variables,
            context=context,
        )

    variables = runner._build_repeat_variables(
        context.ctx.get_merged(context.global_vars),
        context.repeat_index,
    )

    save_error = _save_response_body_if_needed(
        runner=runner,
        step=step,
        resp_obj=resp_obj,
        variables=variables,
        context=context,
    )

    checks, step_failed = evaluate_checks(
        runner=runner,
        check_rules=step.checks,
        variables=variables,
        funcs=context.funcs,
        envmap=context.envmap,
        resp_obj=resp_obj,
    )
    if save_error:
        step_failed = True

    response_capture = capture_step_response(runner=runner, resp_obj=resp_obj)
    return StepOutcome(
        checks=checks,
        extracts=extracts,
        report_response=response_capture.report_response,
        variables=variables,
        step_failed=step_failed,
        error=save_error,
    )


def _extract_response_values(
    *,
    runner: Any,
    step: Step,
    resp_obj: Dict[str, Any],
    variables: Dict[str, Any],
    context: StepOutcomeContext,
) -> Dict[str, Any]:
    extracts: Dict[str, Any] = {}
    for var, expr in (step.extract or {}).items():
        if isinstance(expr, str) and "${" in expr:
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
    *,
    runner: Any,
    extracts: Dict[str, Any],
    context: StepOutcomeContext,
) -> None:
    if not extracts:
        return

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
    *,
    runner: Any,
    step: Step,
    resp_obj: Dict[str, Any],
    variables: Dict[str, Any],
    context: StepOutcomeContext,
) -> None:
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
    *,
    runner: Any,
    step: Step,
    resp_obj: Dict[str, Any],
    variables: Dict[str, Any],
    context: StepOutcomeContext,
) -> Optional[str]:
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

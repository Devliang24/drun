from __future__ import annotations

from typing import Any, Dict, List, Tuple

from drun.models.report import AssertionResult
from drun.models.validators import Validator
from drun.runner.assertions import compare


def evaluate_validators(
    *,
    runner: Any,
    validators: List[Validator],
    variables: Dict[str, Any],
    funcs: Dict[str, Any] | None,
    envmap: Dict[str, Any] | None,
    resp_obj: Dict[str, Any],
) -> Tuple[List[AssertionResult], bool]:
    assertions: List[AssertionResult] = []
    step_failed = False
    for v in validators:
        rendered_check = runner._render(v.check, variables, funcs, envmap)
        if not isinstance(rendered_check, str):
            actual = rendered_check
            check_str = str(v.check)
        else:
            check_str = rendered_check
            actual = runner._resolve_check(check_str, resp_obj)
        expect_rendered = runner._render(v.expect, variables, funcs, envmap)
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
            if runner.log:
                expect_fmt = runner._format_log_value(expect_rendered)
                prefix = f"[VALIDATION] {check_str} {v.comparator} {expect_fmt} => actual="
                indent_len = len(prefix.split("\n")[-1])
                actual_fmt = runner._format_log_value(actual, prefix_len=indent_len)
                runner.log.error(prefix + actual_fmt + " | FAIL")
        else:
            if runner.log:
                expect_fmt = runner._format_log_value(expect_rendered)
                prefix = f"[VALIDATION] {check_str} {v.comparator} {expect_fmt} => actual="
                indent_len = len(prefix.split("\n")[-1])
                actual_fmt = runner._format_log_value(actual, prefix_len=indent_len)
                runner.log.info(prefix + actual_fmt + " | PASS")

    return assertions, step_failed

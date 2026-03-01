from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from drun.models.case import Case
from drun.models.config import Config
from drun.models.report import CaseInstanceResult, StepResult
from drun.models.request import StepRequest
from drun.models.step import Step
from drun.models.validators import Validator
from drun.runner.asserting import evaluate_validators
from drun.runner.invoke import execute_invoke_step


class _DummyRunner:
    def __init__(self):
        self.log = None

    def _render(self, value, variables, funcs, envmap):
        return value

    def _resolve_check(self, check, resp):
        if check == "status_code":
            return resp.get("status_code")
        return None

    def _format_log_value(self, value, prefix_len=0):
        return str(value)


class _InvokeRunner:
    def __init__(self):
        self.log = None
        self.failfast = False

    def _render(self, value, variables, funcs, envmap):
        return value

    def run_case(self, case, global_vars, params, funcs=None, envmap=None, source=None):
        return CaseInstanceResult(
            name=case.config.name or "SubCase",
            parameters=params or {},
            steps=[StepResult(name="inner", status="passed", extracts={"token": "abc"})],
            status="passed",
            duration_ms=1.0,
            source=source,
        )


class _Ctx:
    def __init__(self):
        self.values = {}

    def set_base(self, key, value):
        self.values[key] = value


class RunnerLayersTests(unittest.TestCase):
    def test_evaluate_validators_reports_pass_and_fail(self) -> None:
        runner = _DummyRunner()
        validators = [
            Validator(check="status_code", comparator="eq", expect=200),
            Validator(check="body.user", comparator="eq", expect="alice"),
        ]
        assertions, step_failed = evaluate_validators(
            runner=runner,
            validators=validators,
            variables={},
            funcs=None,
            envmap=None,
            resp_obj={"status_code": 200},
        )
        self.assertEqual(len(assertions), 2)
        self.assertTrue(assertions[0].passed)
        self.assertFalse(assertions[1].passed)
        self.assertTrue(step_failed)
        self.assertIn("unsupported 'body.' syntax", assertions[1].message or "")

    def test_invoke_step_returns_failed_result_when_case_not_found(self) -> None:
        runner = _InvokeRunner()
        step = Step(name="Invoke Missing", invoke="not_found")
        ctx = _Ctx()
        with patch("drun.runner.invoke.resolve_invoke_path", return_value=None):
            results = execute_invoke_step(
                runner=runner,
                step=step,
                step_idx=1,
                rendered_step_name=step.name,
                variables={},
                global_vars={},
                funcs=None,
                envmap=None,
                ctx=ctx,
                params={},
            )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "failed")
        self.assertIn("Cannot find testcase", results[0].error or "")

    def test_invoke_step_auto_exports_extracted_variables(self) -> None:
        runner = _InvokeRunner()
        step = Step(name="Invoke Login", invoke="test_login")
        ctx = _Ctx()
        invoked_case = Case(
            config=Config(name="SubLogin"),
            steps=[Step(name="noop", request=StepRequest(method="GET", path="/health"))],
        )
        with patch("drun.runner.invoke.resolve_invoke_path", return_value=Path("/tmp/test_login.yaml")), patch(
            "drun.runner.invoke.load_yaml_file", return_value=([invoked_case], {})
        ):
            results = execute_invoke_step(
                runner=runner,
                step=step,
                step_idx=1,
                rendered_step_name=step.name,
                variables={},
                global_vars={},
                funcs=None,
                envmap={},
                ctx=ctx,
                params={},
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "passed")
        self.assertEqual(ctx.values.get("token"), "abc")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from drun.loader.yaml_loader import load_yaml_file
from drun.models.case import Case
from drun.models.config import Config
from drun.models.report import CaseInstanceResult, StepResult
from drun.models.request import StepRequest
from drun.models.step import Step
from drun.runner.invoke import execute_invoke_step


class _FakeLogger:
    def __init__(self) -> None:
        self.info_messages: list[str] = []
        self.warning_messages: list[str] = []
        self.error_messages: list[str] = []

    def info(self, message: str) -> None:
        self.info_messages.append(str(message))

    def warning(self, message: str) -> None:
        self.warning_messages.append(str(message))

    def error(self, message: str) -> None:
        self.error_messages.append(str(message))


class _FakeCtx:
    def __init__(self) -> None:
        self.vars: dict[str, object] = {}

    def set_base(self, key: str, value: object) -> None:
        self.vars[key] = value


class _FakeRunner:
    def __init__(self, *, failfast: bool = False, fail_case_names: list[str] | None = None) -> None:
        self.log = _FakeLogger()
        self.failfast = failfast
        self._fail_case_names = set(fail_case_names or [])
        self.called_case_names: list[str] = []

    def _render(self, value, *_args, **_kwargs):
        return value

    def run_case(self, *, case, **_kwargs) -> CaseInstanceResult:
        case_name = case.config.name or "Unnamed Case"
        self.called_case_names.append(case_name)
        is_failed = case_name in self._fail_case_names
        step_result = StepResult(
            name=f"{case_name}::step",
            status="failed" if is_failed else "passed",
            error="simulated failure" if is_failed else None,
            duration_ms=1.0,
        )
        return CaseInstanceResult(
            name=case_name,
            status="failed" if is_failed else "passed",
            steps=[step_result],
            duration_ms=1.0,
        )


def _build_case(name: str) -> Case:
    return Case(
        config=Config(name=name),
        steps=[Step(name="noop", invoke="noop_target")],
    )


class StepInvokeCaseSelectionValidationTests(unittest.TestCase):
    def test_caseflow_loader_accepts_invoke_case_selection_fields(self) -> None:
        with TemporaryDirectory() as tmp:
            suite_file = Path(tmp) / "testsuite.yaml"
            suite_file.write_text(
                """
config:
  name: Selective Suite
caseflow:
  - name: single match
    invoke: test_channel_token_flow
    invoke_case_name: 获取渠道 token
  - name: multiple matches
    invoke: test_channel_token_flow
    invoke_case_names:
      - 获取渠道 token
      - 刷新渠道 token
""".strip(),
                encoding="utf-8",
            )
            cases, _ = load_yaml_file(suite_file)

        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].steps[0].invoke_case_name, "获取渠道 token")
        self.assertEqual(cases[0].steps[0].invoke_case_names, [])
        self.assertEqual(
            cases[0].steps[1].invoke_case_names, ["获取渠道 token", "刷新渠道 token"]
        )

    def test_invoke_case_name_and_invoke_case_names_are_mutually_exclusive(self) -> None:
        with self.assertRaises(ValueError):
            Step(
                name="invalid invoke selector",
                invoke="test_target",
                invoke_case_name="Case A",
                invoke_case_names=["Case B"],
            )

    def test_request_step_cannot_use_invoke_case_selectors(self) -> None:
        with self.assertRaises(ValueError):
            Step(
                name="invalid request selector",
                request=StepRequest(method="GET", path="/ping"),
                invoke_case_name="Case A",
            )

    def test_invoke_case_name_must_be_non_empty_string(self) -> None:
        with self.assertRaises(ValueError):
            Step(name="invalid invoke selector", invoke="test_target", invoke_case_name="   ")

    def test_invoke_case_names_entries_must_be_non_empty_strings(self) -> None:
        with self.assertRaises(ValueError):
            Step(name="invalid invoke selector", invoke="test_target", invoke_case_names=["Case A", ""])

    def test_invoke_case_names_are_trimmed_and_deduplicated(self) -> None:
        step = Step(
            name="valid invoke selector",
            invoke="test_target",
            invoke_case_names=[" Case A ", "Case B", "Case A", "Case B "],
        )
        self.assertEqual(step.invoke_case_names, ["Case A", "Case B"])


class InvokeCaseSelectionExecutionTests(unittest.TestCase):
    @patch("drun.runner.invoke.resolve_invoke_path")
    @patch("drun.runner.invoke.load_yaml_file")
    def test_invoke_case_name_runs_only_selected_case(self, mock_load, mock_resolve) -> None:
        mock_resolve.return_value = Path("/tmp/testcases/test_channel_token_flow.yaml")
        mock_load.return_value = ([_build_case("Case A"), _build_case("Case B"), _build_case("Case C")], {})
        runner = _FakeRunner()
        ctx = _FakeCtx()
        step = Step(name="Invoke selected case", invoke="test_channel_token_flow", invoke_case_name="Case B")

        results = execute_invoke_step(
            runner=runner,
            step=step,
            step_idx=1,
            rendered_step_name=step.name,
            variables={},
            global_vars={},
            funcs={},
            envmap={},
            ctx=ctx,
            params={},
        )

        self.assertEqual(runner.called_case_names, ["Case B"])
        self.assertEqual([r.name for r in results], ["Case B::step"])

    @patch("drun.runner.invoke.resolve_invoke_path")
    @patch("drun.runner.invoke.load_yaml_file")
    def test_invoke_case_names_run_in_source_order(self, mock_load, mock_resolve) -> None:
        mock_resolve.return_value = Path("/tmp/testcases/test_channel_token_flow.yaml")
        mock_load.return_value = ([_build_case("Case A"), _build_case("Case B"), _build_case("Case C")], {})
        runner = _FakeRunner()
        ctx = _FakeCtx()
        step = Step(
            name="Invoke multiple selected cases",
            invoke="test_channel_token_flow",
            invoke_case_names=["Case C", "Case A"],
        )

        execute_invoke_step(
            runner=runner,
            step=step,
            step_idx=1,
            rendered_step_name=step.name,
            variables={},
            global_vars={},
            funcs={},
            envmap={},
            ctx=ctx,
            params={},
        )

        self.assertEqual(runner.called_case_names, ["Case A", "Case C"])

    @patch("drun.runner.invoke.resolve_invoke_path")
    @patch("drun.runner.invoke.load_yaml_file")
    def test_invoke_case_name_no_match_fails_with_available_names(self, mock_load, mock_resolve) -> None:
        mock_resolve.return_value = Path("/tmp/testcases/test_channel_token_flow.yaml")
        mock_load.return_value = ([_build_case("Case A"), _build_case("Case B")], {})
        runner = _FakeRunner()
        ctx = _FakeCtx()
        step = Step(name="Invoke selected case", invoke="test_channel_token_flow", invoke_case_name="Case Z")

        results = execute_invoke_step(
            runner=runner,
            step=step,
            step_idx=1,
            rendered_step_name=step.name,
            variables={},
            global_vars={},
            funcs={},
            envmap={},
            ctx=ctx,
            params={},
        )

        self.assertEqual(runner.called_case_names, [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "failed")
        self.assertIn("requested=[Case Z]", results[0].error or "")
        self.assertIn("available=[Case A, Case B]", results[0].error or "")

    @patch("drun.runner.invoke.resolve_invoke_path")
    @patch("drun.runner.invoke.load_yaml_file")
    def test_invoke_without_case_selector_keeps_backward_compatibility(self, mock_load, mock_resolve) -> None:
        mock_resolve.return_value = Path("/tmp/testcases/test_channel_token_flow.yaml")
        mock_load.return_value = ([_build_case("Case A"), _build_case("Case B")], {})
        runner = _FakeRunner()
        ctx = _FakeCtx()
        step = Step(name="Invoke default case", invoke="test_channel_token_flow")

        execute_invoke_step(
            runner=runner,
            step=step,
            step_idx=1,
            rendered_step_name=step.name,
            variables={},
            global_vars={},
            funcs={},
            envmap={},
            ctx=ctx,
            params={},
        )

        self.assertEqual(runner.called_case_names, ["Case A"])

    @patch("drun.runner.invoke.resolve_invoke_path")
    @patch("drun.runner.invoke.load_yaml_file")
    def test_invoke_case_names_respect_failfast(self, mock_load, mock_resolve) -> None:
        mock_resolve.return_value = Path("/tmp/testcases/test_channel_token_flow.yaml")
        mock_load.return_value = ([_build_case("Case A"), _build_case("Case B"), _build_case("Case C")], {})
        runner = _FakeRunner(failfast=True, fail_case_names=["Case B"])
        ctx = _FakeCtx()
        step = Step(
            name="Invoke selected cases with failfast",
            invoke="test_channel_token_flow",
            invoke_case_names=["Case A", "Case B", "Case C"],
        )

        execute_invoke_step(
            runner=runner,
            step=step,
            step_idx=1,
            rendered_step_name=step.name,
            variables={},
            global_vars={},
            funcs={},
            envmap={},
            ctx=ctx,
            params={},
        )

        self.assertEqual(runner.called_case_names, ["Case A", "Case B"])

    @patch("drun.runner.invoke.resolve_invoke_path")
    @patch("drun.runner.invoke.load_yaml_file")
    def test_invoke_case_name_matches_all_duplicates_and_warns(self, mock_load, mock_resolve) -> None:
        mock_resolve.return_value = Path("/tmp/testcases/test_channel_token_flow.yaml")
        mock_load.return_value = ([_build_case("Case A"), _build_case("Case A"), _build_case("Case B")], {})
        runner = _FakeRunner()
        ctx = _FakeCtx()
        step = Step(name="Invoke duplicate cases", invoke="test_channel_token_flow", invoke_case_name="Case A")

        execute_invoke_step(
            runner=runner,
            step=step,
            step_idx=1,
            rendered_step_name=step.name,
            variables={},
            global_vars={},
            funcs={},
            envmap={},
            ctx=ctx,
            params={},
        )

        self.assertEqual(runner.called_case_names, ["Case A", "Case A"])
        self.assertTrue(
            any("Duplicate case names matched" in message for message in runner.log.warning_messages)
        )

    @patch("drun.runner.invoke.resolve_invoke_path")
    @patch("drun.runner.invoke.load_yaml_file")
    def test_invoke_repeat_prefixes_child_step_names(self, mock_load, mock_resolve) -> None:
        mock_resolve.return_value = Path("/tmp/testcases/test_channel_token_flow.yaml")
        mock_load.return_value = ([_build_case("Case A")], {})
        runner = _FakeRunner()
        ctx = _FakeCtx()
        step = Step(name="Invoke flow", invoke="test_channel_token_flow")

        results = execute_invoke_step(
            runner=runner,
            step=step,
            step_idx=1,
            rendered_step_name="Invoke flow [repeat=2/3]",
            variables={},
            global_vars={},
            funcs={},
            envmap={},
            ctx=ctx,
            params={},
            invoke_result_prefix="Invoke flow [repeat=2/3]",
            repeat_index=1,
            repeat_no=2,
            repeat_total=3,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0].name,
            "Invoke flow [repeat=2/3] :: Case A::step",
        )
        self.assertEqual(results[0].origin_step_name, "Case A::step")
        self.assertEqual(results[0].repeat_index, 1)
        self.assertEqual(results[0].repeat_no, 2)
        self.assertEqual(results[0].repeat_total, 3)


if __name__ == "__main__":
    unittest.main()

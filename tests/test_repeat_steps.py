from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from drun.loader.yaml_loader import load_yaml_file
from drun.models.case import Case
from drun.models.config import Config
from drun.models.report import StepResult
from drun.models.request import StepRequest
from drun.models.step import Step
from drun.runner.runner import Runner


class _FakeLogger:
    def info(self, *_args, **_kwargs) -> None:
        return None

    def warning(self, *_args, **_kwargs) -> None:
        return None

    def error(self, *_args, **_kwargs) -> None:
        return None

    def debug(self, *_args, **_kwargs) -> None:
        return None


class _FakeHTTPClient:
    def __init__(self, outcomes: list[object] | None = None) -> None:
        self._outcomes = list(outcomes or [])
        self.requests: list[dict] = []

    def request(self, req: dict) -> dict:
        self.requests.append(dict(req))
        if self._outcomes:
            outcome = self._outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            if isinstance(outcome, dict):
                return {
                    "status_code": 200,
                    "elapsed_ms": 8.0,
                    "headers": {},
                    "body": {"ok": True},
                    **outcome,
                }
        return {
            "status_code": 200,
            "elapsed_ms": 8.0,
            "headers": {},
            "body": {"ok": True},
        }

    def close(self) -> None:
        return None


class RepeatRunnerTests(unittest.TestCase):
    def _build_runner(self, *, failfast: bool = False, outcomes: list[object] | None = None) -> tuple[Runner, _FakeHTTPClient]:
        fake_client = _FakeHTTPClient(outcomes=outcomes)
        runner = Runner(
            log=_FakeLogger(),
            failfast=failfast,
            reveal_secrets=True,
            log_response_headers=False,
        )
        runner._build_client = lambda _case: fake_client  # type: ignore[method-assign]
        return runner, fake_client

    def test_request_step_repeat_runs_multiple_iterations_with_metadata(self) -> None:
        step = Step(
            name="Ping",
            repeat=3,
            request=StepRequest(method="GET", path="/ping"),
        )
        case = Case(config=Config(name="Repeat Case", base_url="http://example.com"), steps=[step])
        runner, fake_client = self._build_runner()

        result = runner.run_case(case, global_vars={}, params={})

        self.assertEqual(len(fake_client.requests), 3)
        self.assertEqual(len(result.steps), 3)
        self.assertEqual(result.status, "passed")
        self.assertEqual(result.steps[0].name, "Ping [repeat=1/3]")
        self.assertEqual(result.steps[1].name, "Ping [repeat=2/3]")
        self.assertEqual(result.steps[2].name, "Ping [repeat=3/3]")
        self.assertEqual(result.steps[0].repeat_index, 0)
        self.assertEqual(result.steps[0].repeat_no, 1)
        self.assertEqual(result.steps[0].repeat_total, 3)
        self.assertEqual(result.steps[0].origin_step_name, "Ping")

    def test_request_step_repeat_supports_expression(self) -> None:
        step = Step(
            name="Ping",
            repeat="${retry_count}",
            request=StepRequest(method="GET", path="/ping"),
        )
        case = Case(config=Config(name="Repeat Expr Case", base_url="http://example.com"), steps=[step])
        runner, fake_client = self._build_runner()

        result = runner.run_case(case, global_vars={"retry_count": "2"}, params={})

        self.assertEqual(result.status, "passed")
        self.assertEqual(len(fake_client.requests), 2)
        self.assertEqual([s.name for s in result.steps], ["Ping [repeat=1/2]", "Ping [repeat=2/2]"])

    def test_repeat_zero_marks_step_skipped(self) -> None:
        step = Step(
            name="Ping",
            repeat=0,
            request=StepRequest(method="GET", path="/ping"),
        )
        case = Case(config=Config(name="Repeat Zero Case", base_url="http://example.com"), steps=[step])
        runner, fake_client = self._build_runner()

        result = runner.run_case(case, global_vars={}, params={})

        self.assertEqual(result.status, "passed")
        self.assertEqual(len(fake_client.requests), 0)
        self.assertEqual(len(result.steps), 1)
        self.assertEqual(result.steps[0].status, "skipped")
        self.assertEqual(result.steps[0].name, "Ping [repeat=0]")
        self.assertEqual(result.steps[0].repeat_total, 0)

    def test_repeat_respects_failfast(self) -> None:
        step = Step(
            name="Upload",
            repeat=3,
            request=StepRequest(method="POST", path="/upload"),
        )
        case = Case(config=Config(name="Repeat Failfast Case", base_url="http://example.com"), steps=[step])
        runner, fake_client = self._build_runner(
            failfast=True,
            outcomes=[RuntimeError("network timeout"), {"status_code": 200}],
        )

        result = runner.run_case(case, global_vars={}, params={})

        self.assertEqual(result.status, "failed")
        self.assertEqual(len(fake_client.requests), 1)
        self.assertEqual(len(result.steps), 1)
        self.assertEqual(result.steps[0].name, "Upload [repeat=1/3]")
        self.assertEqual(result.steps[0].status, "failed")

    def test_invoke_repeat_passes_prefixed_name_for_multi_repeat(self) -> None:
        step = Step(name="Invoke flow", repeat=2, invoke="test_login")
        case = Case(config=Config(name="Invoke Repeat Case"), steps=[step])
        runner, _fake_client = self._build_runner()
        captured: list[tuple[str, str | None]] = []

        def _fake_run_invoke_step(**kwargs):
            captured.append((kwargs["rendered_step_name"], kwargs.get("invoke_result_prefix")))
            return [StepResult(name=kwargs["rendered_step_name"], status="passed")]

        runner._run_invoke_step = _fake_run_invoke_step  # type: ignore[method-assign]

        result = runner.run_case(case, global_vars={}, params={})

        self.assertEqual(result.status, "passed")
        self.assertEqual(
            captured,
            [
                ("Invoke flow [repeat=1/2]", "Invoke flow [repeat=1/2]"),
                ("Invoke flow [repeat=2/2]", "Invoke flow [repeat=2/2]"),
            ],
        )

    def test_invoke_single_repeat_does_not_force_prefix(self) -> None:
        step = Step(name="Invoke flow", repeat=1, invoke="test_login")
        case = Case(config=Config(name="Invoke Single Repeat Case"), steps=[step])
        runner, _fake_client = self._build_runner()
        captured: list[tuple[str, str | None]] = []

        def _fake_run_invoke_step(**kwargs):
            captured.append((kwargs["rendered_step_name"], kwargs.get("invoke_result_prefix")))
            return [StepResult(name=kwargs["rendered_step_name"], status="passed")]

        runner._run_invoke_step = _fake_run_invoke_step  # type: ignore[method-assign]

        result = runner.run_case(case, global_vars={}, params={})

        self.assertEqual(result.status, "passed")
        self.assertEqual(captured, [("Invoke flow", None)])


class RepeatLoaderTests(unittest.TestCase):
    def test_loader_rejects_legacy_loop_field_in_case_step(self) -> None:
        with TemporaryDirectory() as tmp:
            case_file = Path(tmp) / "case.yaml"
            case_file.write_text(
                """
config:
  name: Loop Legacy
  base_url: http://example.com
steps:
  - name: ping
    loop: 3
    request:
      method: GET
      path: /ping
""".strip(),
                encoding="utf-8",
            )

            with self.assertRaises(Exception) as exc:
                load_yaml_file(case_file)

        self.assertIn("please migrate to 'repeat'", str(exc.exception))

    def test_loader_rejects_legacy_foreach_field_in_caseflow(self) -> None:
        with TemporaryDirectory() as tmp:
            suite_file = Path(tmp) / "suite.yaml"
            suite_file.write_text(
                """
config:
  name: Foreach Legacy
caseflow:
  - name: invoke ping
    foreach: [1, 2]
    invoke: test_ping
""".strip(),
                encoding="utf-8",
            )

            with self.assertRaises(Exception) as exc:
                load_yaml_file(suite_file)

        self.assertIn("Please use 'repeat'", str(exc.exception))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import call, patch

from drun.loader.yaml_loader import load_yaml_file
from drun.models.case import Case
from drun.models.config import Config
from drun.models.request import StepRequest
from drun.models.step import Step, StepResponseConfig
from drun.models.validators import Validator
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
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def request(self, req: dict) -> dict:
        self.requests.append(dict(req))
        return {
            "status_code": 200,
            "elapsed_ms": 1.0,
            "headers": {},
            "body": {"ok": True},
        }

    def close(self) -> None:
        return None


class SleepStepValidationTests(unittest.TestCase):
    def test_sleep_step_is_allowed(self) -> None:
        step = Step(name="Pause", sleep=2000)
        self.assertEqual(step.sleep, 2000)

    def test_sleep_step_rejects_negative_value(self) -> None:
        with self.assertRaises(ValueError):
            Step(name="Pause", sleep=-1)

    def test_sleep_step_rejects_request_and_sleep(self) -> None:
        with self.assertRaises(ValueError):
            Step(
                name="Pause",
                sleep=1,
                request=StepRequest(method="GET", path="/ping"),
            )

    def test_sleep_step_rejects_response_validate_extract_and_export(self) -> None:
        with self.assertRaises(ValueError):
            Step(
                name="Pause",
                sleep=1,
                response=StepResponseConfig(save_body_to="out.txt"),
                extract={"token": "$.token"},
                export={"csv": {"data": "$.items", "file": "data.csv"}},
                validators=[Validator(check="status_code", comparator="eq", expect=200)],
            )

    def test_loader_accepts_sleep_step(self) -> None:
        with TemporaryDirectory() as tmp:
            case_file = Path(tmp) / "case.yaml"
            case_file.write_text(
                """
config:
  name: Sleep Case
steps:
  - name: wait
    sleep: 2000
""".strip(),
                encoding="utf-8",
            )

            cases, _meta = load_yaml_file(case_file)

        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].steps[0].sleep, 2000)


class SleepRunnerTests(unittest.TestCase):
    def _build_runner(self) -> tuple[Runner, _FakeHTTPClient]:
        fake_client = _FakeHTTPClient()
        runner = Runner(
            log=_FakeLogger(),
            failfast=False,
            reveal_secrets=True,
            log_response_headers=False,
        )
        runner._build_client = lambda _case: fake_client  # type: ignore[method-assign]
        return runner, fake_client

    def test_sleep_step_runs_without_http_request(self) -> None:
        step = Step(name="Pause", sleep=1500)
        case = Case(config=Config(name="Sleep Case"), steps=[step])
        runner, fake_client = self._build_runner()

        with patch("drun.runner.runner.time.sleep") as mock_sleep:
            result = runner.run_case(case, global_vars={}, params={})

        mock_sleep.assert_called_once_with(1.5)
        self.assertEqual(fake_client.requests, [])
        self.assertEqual(result.status, "passed")
        self.assertEqual(len(result.steps), 1)
        self.assertEqual(result.steps[0].request["sleep"], 1500)
        self.assertEqual(result.steps[0].response["sleep_ms"], 1500)
        self.assertGreaterEqual(result.steps[0].duration_ms, 0.0)

    def test_sleep_step_supports_expression_and_repeat(self) -> None:
        step = Step(name="Pause", sleep="${wait_ms}", repeat=2)
        case = Case(config=Config(name="Sleep Repeat Case"), steps=[step])
        runner, fake_client = self._build_runner()

        with patch("drun.runner.runner.time.sleep") as mock_sleep:
            result = runner.run_case(case, global_vars={"wait_ms": "250"}, params={})

        self.assertEqual(fake_client.requests, [])
        self.assertEqual(mock_sleep.call_args_list, [call(0.25), call(0.25)])
        self.assertEqual(result.status, "passed")
        self.assertEqual([s.name for s in result.steps], ["Pause [repeat=1/2]", "Pause [repeat=2/2]"])

    def test_sleep_step_repeat_with_skip_expression_skips_last_iteration(self) -> None:
        step = Step(name="Pause", sleep=100, repeat=3, skip="${repeat_no > 2}")
        case = Case(config=Config(name="Sleep Skip Case"), steps=[step])
        runner, fake_client = self._build_runner()

        with patch("drun.runner.runner.time.sleep") as mock_sleep:
            result = runner.run_case(case, global_vars={}, params={})

        self.assertEqual(fake_client.requests, [])
        self.assertEqual(mock_sleep.call_args_list, [call(0.1), call(0.1)])
        self.assertEqual(result.status, "passed")
        self.assertEqual([s.status for s in result.steps], ["passed", "passed", "skipped"])
        self.assertEqual(result.steps[2].name, "Pause [repeat=3/3]")

    def test_sleep_step_invalid_expression_fails_step(self) -> None:
        step = Step(name="Pause", sleep="${wait_ms}")
        case = Case(config=Config(name="Sleep Error Case"), steps=[step])
        runner, fake_client = self._build_runner()

        with patch("drun.runner.runner.time.sleep") as mock_sleep:
            result = runner.run_case(case, global_vars={}, params={})

        self.assertEqual(fake_client.requests, [])
        mock_sleep.assert_not_called()
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.steps[0].status, "failed")
        self.assertIn("sleep error:", result.steps[0].error or "")


if __name__ == "__main__":
    unittest.main()

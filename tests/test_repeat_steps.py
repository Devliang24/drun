"""Tests for the unified retry model.

Covers request/invoke step retry, attempt metadata, skip, and failfast.
"""

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


class RetryRunnerTests(unittest.TestCase):
    def _build_runner(
        self,
        *,
        failfast: bool = False,
        outcomes: list[object] | None = None,
    ) -> tuple[Runner, _FakeHTTPClient]:
        fake_client = _FakeHTTPClient(outcomes=outcomes)
        runner = Runner(
            log=_FakeLogger(),
            failfast=failfast,
            reveal_secrets=True,
            log_response_headers=False,
        )
        runner._build_client = lambda _case: fake_client  # type: ignore[method-assign]
        return runner, fake_client

    # ── basic retry ──────────────────────────────────────────────

    def test_retry_int_runs_up_to_max_attempts(self) -> None:
        """retry: 2 -> max 3 attempts. First attempt passes -> only 1 runs."""
        step = Step(
            name="Ping",
            retry=2,
            request=StepRequest(method="GET", path="/ping"),
        )
        case = Case(config=Config(name="Retry Case", base_url="http://example.com"), steps=[step])
        runner, fake_client = self._build_runner()

        result = runner.run_case(case, global_vars={}, params={})

        self.assertEqual(len(fake_client.requests), 1)
        self.assertEqual(result.status, "passed")
        self.assertEqual(result.steps[0].name, "Ping [attempt 1/3]")
        self.assertEqual(result.steps[0].attempt, 1)
        self.assertEqual(result.steps[0].attempt_total, 3)

    def test_retry_retries_on_http_exception(self) -> None:
        """HTTP exception on first attempt -> retries, passes on 2nd."""
        step = Step(
            name="Upload",
            retry=2,
            request=StepRequest(method="POST", path="/upload"),
        )
        case = Case(config=Config(name="Retry Exn Case", base_url="http://example.com"), steps=[step])
        runner, fake_client = self._build_runner(
            outcomes=[RuntimeError("timeout"), {"status_code": 201}],
        )

        result = runner.run_case(case, global_vars={}, params={})

        self.assertEqual(result.status, "passed")
        self.assertEqual(len(fake_client.requests), 2)
        self.assertEqual(result.steps[0].name, "Upload [attempt 2/3]")
        self.assertEqual(result.steps[0].attempt, 2)

    def test_retry_retries_on_check_failure(self) -> None:
        """check fails on first two attempts -> passes on 3rd."""
        step = Step.model_validate_obj({
            "name": "Create",
            "retry": 2,
            "request": {"method": "POST", "path": "/items"},
            "check": [{"eq": ["status_code", 201]}],
        })
        case = Case(config=Config(name="Retry Check Case", base_url="http://example.com"), steps=[step])
        runner, fake_client = self._build_runner(
            outcomes=[
                {"status_code": 503},
                {"status_code": 502},
                {"status_code": 201},
            ],
        )

        result = runner.run_case(case, global_vars={}, params={})

        self.assertEqual(result.status, "passed")
        self.assertEqual(len(fake_client.requests), 3)
        self.assertEqual(result.steps[0].name, "Create [attempt 3/3]")
        self.assertEqual(result.steps[0].attempt, 3)

    def test_retry_exhausted_all_failed(self) -> None:
        """All retry attempts fail -> step failed."""
        step = Step(
            name="Create",
            retry=2,
            request=StepRequest(method="POST", path="/items"),
        )
        case = Case(config=Config(name="Retry Fail Case", base_url="http://example.com"), steps=[step])
        runner, fake_client = self._build_runner(
            outcomes=[RuntimeError("ERR")] * 5,
        )

        result = runner.run_case(case, global_vars={}, params={})

        self.assertEqual(result.status, "failed")
        self.assertEqual(len(fake_client.requests), 3)
        self.assertEqual(result.steps[0].status, "failed")
        self.assertEqual(result.steps[0].attempt, 3)
        self.assertEqual(result.steps[0].attempt_total, 3)
        self.assertIn("Request error", result.steps[0].error or "")

    # ── retry config ─────────────────────────────────────────────

    def test_retry_config_with_every(self) -> None:
        """retry with every field causes sleep between attempts."""
        from drun.models.retry import RetryConfig

        step = Step.model_validate_obj({
            "name": "SlowCreate",
            "retry": {"max": 4, "every": "100ms"},
            "request": {"method": "POST", "path": "/items"},
            "check": [{"eq": ["status_code", 201]}],
        })
        case = Case(config=Config(name="Retry Every Case", base_url="http://example.com"), steps=[step])
        runner, fake_client = self._build_runner(
            outcomes=[
                {"status_code": 503},
                {"status_code": 502},
                {"status_code": 201},
            ],
        )

        import time as _time

        with unittest.mock.patch("drun.runner.retry.time.sleep") as mock_sleep:
            result = runner.run_case(
                case,
                global_vars={},
                params={},
                funcs={},
                envmap={},
            )

        self.assertEqual(result.status, "passed")
        self.assertEqual(mock_sleep.call_count, 2)
        self.assertEqual(mock_sleep.call_args_list[0], unittest.mock.call(0.1))
        self.assertEqual(mock_sleep.call_args_list[1], unittest.mock.call(0.1))

    # ── skip ─────────────────────────────────────────────────────

    def test_skip_true_marks_step_skipped(self) -> None:
        step = Step(
            name="Ping",
            skip=True,
            request=StepRequest(method="GET", path="/ping"),
        )
        case = Case(config=Config(name="Skip Bool Case", base_url="http://example.com"), steps=[step])
        runner, fake_client = self._build_runner()

        result = runner.run_case(case, global_vars={}, params={})

        self.assertEqual(result.status, "passed")
        self.assertEqual(len(fake_client.requests), 0)
        self.assertEqual(result.steps[0].status, "skipped")
        self.assertEqual(result.steps[0].error, "true")

    def test_skip_string_reason_is_preserved(self) -> None:
        step = Step(
            name="Ping",
            skip="maintenance window",
            request=StepRequest(method="GET", path="/ping"),
        )
        case = Case(config=Config(name="Skip String Case", base_url="http://example.com"), steps=[step])
        runner, fake_client = self._build_runner()

        result = runner.run_case(case, global_vars={}, params={})

        self.assertEqual(result.status, "passed")
        self.assertEqual(len(fake_client.requests), 0)
        self.assertEqual(result.steps[0].status, "skipped")
        self.assertEqual(result.steps[0].error, "maintenance window")

    def test_skip_false_expression_does_not_skip(self) -> None:
        step = Step(
            name="Ping",
            skip="${false}",
            request=StepRequest(method="GET", path="/ping"),
        )
        case = Case(config=Config(name="Skip False Case", base_url="http://example.com"), steps=[step])
        runner, fake_client = self._build_runner()

        result = runner.run_case(case, global_vars={}, params={})

        self.assertEqual(result.status, "passed")
        self.assertEqual(len(fake_client.requests), 1)

    def test_skip_expression_error_fails_step(self) -> None:
        step = Step(
            name="Ping",
            skip="${undefined > 0}",
            request=StepRequest(method="GET", path="/ping"),
        )
        case = Case(config=Config(name="Skip Error Case", base_url="http://example.com"), steps=[step])
        runner, fake_client = self._build_runner(failfast=True)

        result = runner.run_case(case, global_vars={}, params={})

        self.assertEqual(result.status, "failed")
        self.assertEqual(len(fake_client.requests), 0)
        self.assertIn("skip error:", result.steps[0].error or "")

    # ── failfast ─────────────────────────────────────────────────

    def test_retry_all_failed_with_failfast(self) -> None:
        """When all retries fail, step fails. failfast stops subsequent steps."""
        step1 = Step(
            name="Upload",
            retry=1,
            request=StepRequest(method="POST", path="/upload"),
        )
        step2 = Step(
            name="Verify",
            request=StepRequest(method="GET", path="/verify"),
        )
        case = Case(
            config=Config(name="Failfast Case", base_url="http://example.com"),
            steps=[step1, step2],
        )
        runner, fake_client = self._build_runner(
            failfast=True,
            outcomes=[
                RuntimeError("timeout"),
                RuntimeError("timeout"),  # both retry attempts fail
            ],
        )

        result = runner.run_case(case, global_vars={}, params={})

        self.assertEqual(result.status, "failed")
        self.assertEqual(len(fake_client.requests), 2)  # retry exhausted
        # step2 should not run because failfast on step1
        self.assertEqual(len(result.steps), 1)

    # ── attempt variables ────────────────────────────────────────

    def test_attempt_template_variables(self) -> None:
        """$attempt and $attempt_total are available in step name."""
        step = Step(
            name="Ping attempt-$attempt/$attempt_total",
            retry=2,
            request=StepRequest(method="GET", path="/ping"),
        )
        case = Case(config=Config(name="Vars Case", base_url="http://example.com"), steps=[step])
        runner, fake_client = self._build_runner()

        result = runner.run_case(case, global_vars={}, params={})

        self.assertEqual(result.status, "passed")
        self.assertIn("attempt-1/3", result.steps[0].name)

    # ── invoke retry ─────────────────────────────────────────────

    def test_invoke_retry_calls_repeatedly_on_failure(self) -> None:
        from drun.models.retry import RetryConfig

        step = Step(
            name="Invoke flow",
            retry=RetryConfig(max=3, every="0s"),
            invoke="tc_login",
        )
        case = Case(config=Config(name="Invoke Retry Case"), steps=[step])
        runner, _fake_client = self._build_runner()
        captured: list[str] = []
        call_count = 0

        def _fake_run_invoke_step(**kwargs):
            nonlocal call_count
            captured.append(kwargs["rendered_step_name"])
            call_count += 1
            if call_count < 3:
                return [StepResult(name="child", status="failed")]
            return [StepResult(name="child", status="passed")]

        runner._run_invoke_step = _fake_run_invoke_step  # type: ignore[method-assign]

        result = runner.run_case(case, global_vars={}, params={})

        self.assertEqual(result.status, "passed")
        self.assertEqual(
            captured,
            [
                "Invoke flow [attempt 1/3]",
                "Invoke flow [attempt 2/3]",
                "Invoke flow [attempt 3/3]",
            ],
        )


class RetryLoaderTests(unittest.TestCase):
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

        self.assertIn("not supported", str(exc.exception))

    def test_loader_rejects_legacy_foreach_field_in_caseflow(self) -> None:
        with TemporaryDirectory() as tmp:
            suite_file = Path(tmp) / "ts_suite.yaml"
            suite_file.write_text(
                """
config:
  name: Foreach Legacy
caseflow:
  - name: invoke ping
    foreach: [1, 2]
    invoke: tc_ping
""".strip(),
                encoding="utf-8",
            )

            with self.assertRaises(Exception) as exc:
                load_yaml_file(suite_file)

        self.assertIn("not supported", str(exc.exception))


if __name__ == "__main__":
    unittest.main()

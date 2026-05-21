from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory
from unittest.mock import call, patch

from drun.models.case import Case
from drun.models.config import Config
from drun.models.report import StepResult
from drun.models.request import StepRequest
from drun.models.step import Step
from drun.models.validators import normalize_validators
from drun.runner.runner import Runner
from drun.runner.step_lifecycle import StepLifecycle, StepLifecycleContext
from drun.templating.context import VarContext


class _FakeLogger:
    def info(self, *_args, **_kwargs) -> None:
        return None

    def warning(self, *_args, **_kwargs) -> None:
        return None

    def error(self, *_args, **_kwargs) -> None:
        return None

    def debug(self, *_args, **_kwargs) -> None:
        return None


class StepLifecycleSleepTests(unittest.TestCase):
    def test_sleep_step_repeat_returns_step_results(self) -> None:
        runner = Runner(
            log=_FakeLogger(),
            failfast=False,
            reveal_secrets=True,
            log_response_headers=False,
        )
        lifecycle = StepLifecycle(runner)
        context = StepLifecycleContext(
            step=Step(name="Pause", sleep="${wait_ms}", repeat=2),
            step_idx=1,
            case_name="Sleep Case",
            ctx=VarContext({"wait_ms": "250"}),
            global_vars={},
            rendered_locals={},
            funcs={},
            envmap={},
        )

        with patch("drun.runner.step_lifecycle.time.sleep") as mock_sleep:
            lifecycle_result = lifecycle.execute(context)

        results = lifecycle_result.results
        self.assertEqual(mock_sleep.call_args_list, [call(0.25), call(0.25)])
        self.assertEqual(
            [result.name for result in results],
            ["Pause [repeat=1/2]", "Pause [repeat=2/2]"],
        )
        self.assertEqual([result.status for result in results], ["passed", "passed"])
        self.assertEqual(results[0].request["sleep"], 250.0)
        self.assertEqual(results[0].response["sleep_ms"], 250.0)
        self.assertEqual(results[0].repeat_index, 0)
        self.assertEqual(results[1].repeat_no, 2)
        self.assertEqual(results[1].repeat_total, 2)
        self.assertIsNotNone(lifecycle_result.last_response)
        self.assertEqual(lifecycle_result.last_response["sleep_ms"], 250.0)


class _FakeHTTPClient:
    def __init__(self) -> None:
        self.requests = []
        self.closed = False

    def request(self, req):
        self.requests.append(req)
        return {
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "body": {"id": 42, "token": "abc123"},
            "elapsed_ms": 3.5,
            "url": "https://example.test/users/42",
            "method": req.get("method", "GET"),
        }

    def close(self) -> None:
        self.closed = True


class StepLifecycleRequestTests(unittest.TestCase):
    def test_request_step_success_validates_and_extracts(self) -> None:
        with TemporaryDirectory() as tmp:
            runner = Runner(
                log=_FakeLogger(),
                failfast=False,
                reveal_secrets=True,
                log_response_headers=False,
                persist_env_file=f"{tmp}/.env",
            )
            lifecycle = StepLifecycle(runner)
            fake_client = _FakeHTTPClient()
            envmap = {}
            context = StepLifecycleContext(
                step=Step(
                    name="Fetch user ${user_id}",
                    request=StepRequest(method="GET", path="/users/${user_id}"),
                    validate=normalize_validators(
                        [
                            {"eq": ["status_code", 200]},
                            {"eq": ["$.id", "${user_id}"]},
                        ]
                    ),
                    extract={"token": "$.token"},
                ),
                step_idx=1,
                case_name="User Case",
                ctx=VarContext({"user_id": 42}),
                global_vars={},
                rendered_locals={},
                funcs={},
                envmap=envmap,
                client=fake_client,
            )

            lifecycle_result = lifecycle.execute(context)

        self.assertFalse(fake_client.closed)
        self.assertEqual(fake_client.requests[0]["path"], "/users/42")
        self.assertEqual(len(lifecycle_result.results), 1)
        step_result = lifecycle_result.results[0]
        self.assertEqual(step_result.name, "Fetch user 42")
        self.assertEqual(step_result.status, "passed")
        self.assertTrue(all(assertion.passed for assertion in step_result.asserts))
        self.assertEqual(step_result.extracts, {"token": "abc123"})
        self.assertEqual(context.ctx.get_merged({})["token"], "abc123")
        self.assertEqual(envmap["TOKEN"], "abc123")
        self.assertEqual(envmap["token"], "abc123")
        self.assertEqual(lifecycle_result.last_response["body"]["token"], "abc123")

    def test_run_case_teardown_receives_raw_last_response(self) -> None:
        runner = Runner(
            log=_FakeLogger(),
            failfast=False,
            reveal_secrets=True,
            log_response_headers=False,
        )
        fake_client = _FakeHTTPClient()
        raw_payload = b"raw-response"
        fake_client.request = lambda req: {  # type: ignore[method-assign]
            "status_code": 200,
            "headers": {"content-type": "application/octet-stream"},
            "body": None,
            "raw_bytes": raw_payload,
            "elapsed_ms": 1.0,
            "url": "https://example.test/download",
            "method": req.get("method", "GET"),
        }
        runner._build_client = lambda _case: fake_client  # type: ignore[method-assign]
        seen = {}

        def remember_case_response(response):
            seen["raw_bytes"] = response.get("raw_bytes")
            return {}

        case = Case(
            config=Config(name="Download Case", base_url="https://example.test"),
            teardown_hooks=["${remember_case_response(response)}"],
            steps=[
                Step(
                    name="Download",
                    request=StepRequest(method="GET", path="/download"),
                    validate=normalize_validators([{"eq": ["status_code", 200]}]),
                )
            ],
        )

        result = runner.run_case(
            case,
            global_vars={},
            params={},
            funcs={"remember_case_response": remember_case_response},
            envmap={},
        )

        self.assertEqual(result.status, "passed")
        self.assertEqual(seen["raw_bytes"], raw_payload)
        self.assertNotIn("raw_bytes", result.steps[0].response)
        self.assertTrue(fake_client.closed)


class StepLifecycleInvokeTests(unittest.TestCase):
    def test_invoke_step_repeat_uses_step_lifecycle_result_metadata(self) -> None:
        runner = Runner(log=_FakeLogger(), failfast=False)
        captured = []

        def _fake_run_invoke_step(**kwargs):
            captured.append((kwargs["rendered_step_name"], kwargs.get("invoke_result_prefix")))
            return [
                StepResult(
                    name=f"{kwargs['rendered_step_name']} :: child",
                    status="passed",
                    repeat_index=kwargs["repeat_index"],
                    repeat_no=kwargs["repeat_no"],
                    repeat_total=kwargs["repeat_total"],
                )
            ]

        runner._run_invoke_step = _fake_run_invoke_step  # type: ignore[method-assign]
        lifecycle = StepLifecycle(runner)
        context = StepLifecycleContext(
            step=Step(name="Invoke flow", invoke="child_case", repeat=2),
            step_idx=1,
            case_name="Parent Case",
            ctx=VarContext({}),
            global_vars={},
            rendered_locals={},
            funcs={},
            envmap={},
            params={},
        )

        lifecycle_result = lifecycle.execute(context)

        self.assertEqual(
            captured,
            [
                ("Invoke flow [repeat=1/2]", "Invoke flow [repeat=1/2]"),
                ("Invoke flow [repeat=2/2]", "Invoke flow [repeat=2/2]"),
            ],
        )
        self.assertEqual(len(lifecycle_result.results), 2)
        self.assertEqual(lifecycle_result.results[0].repeat_index, 0)
        self.assertEqual(lifecycle_result.results[1].repeat_no, 2)


if __name__ == "__main__":
    unittest.main()

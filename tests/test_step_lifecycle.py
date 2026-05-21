from __future__ import annotations

import unittest
from unittest.mock import call, patch

from drun.models.step import Step
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
            results = lifecycle.execute(context)

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


if __name__ == "__main__":
    unittest.main()

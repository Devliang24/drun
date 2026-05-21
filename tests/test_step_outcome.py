from __future__ import annotations

import base64
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from drun.models.request import StepRequest
from drun.models.step import Step, StepResponseConfig
from drun.models.validators import normalize_validators
from drun.runner.runner import Runner
from drun.runner.step_outcome import StepOutcomeContext, process_step_outcome
from drun.templating.context import VarContext


class _FakeLogger:
    def info(self, *_args, **_kwargs) -> None:
        return None

    def warning(self, *_args, **_kwargs) -> None:
        return None

    def error(self, *_args, **_kwargs) -> None:
        return None


class StepOutcomeTests(unittest.TestCase):
    def test_request_step_outcome_shapes_response_and_side_effects(self) -> None:
        with TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                runner = Runner(
                    log=_FakeLogger(),
                    reveal_secrets=True,
                    persist_env_file=str(tmpdir / ".env"),
                )
                ctx = VarContext({"download_path": str(tmpdir / "download.bin")})
                envmap = {}
                raw_bytes = b"raw-response"
                resp_obj = {
                    "status_code": 200,
                    "headers": {"content-type": "application/json"},
                    "body": {
                        "token": "abc123",
                        "items": [{"id": 1, "name": "Ada"}],
                    },
                    "raw_bytes": raw_bytes,
                    "body_size": len(raw_bytes),
                    "body_bytes_b64": base64.b64encode(raw_bytes).decode("ascii"),
                    "elapsed_ms": 2.0,
                }
                step = Step(
                    name="Fetch users",
                    request=StepRequest(method="GET", path="/users"),
                    response=StepResponseConfig(save_body_to="${download_path}"),
                    extract={"token": "$.token"},
                    export={
                        "csv": {
                            "data": "$.items",
                            "file": "items.csv",
                            "columns": ["id", "name"],
                        }
                    },
                    validate=normalize_validators(
                        [
                            {"eq": ["status_code", 200]},
                            {"eq": ["$.token", "abc123"]},
                        ]
                    ),
                )

                outcome = process_step_outcome(
                    runner=runner,
                    context=StepOutcomeContext(
                        step=step,
                        resp_obj=resp_obj,
                        variables=ctx.get_merged({}),
                        ctx=ctx,
                        global_vars={},
                        repeat_index=0,
                        funcs={},
                        envmap=envmap,
                    ),
                )

                self.assertFalse(outcome.step_failed)
                self.assertIsNone(outcome.error)
                self.assertEqual(outcome.extracts, {"token": "abc123"})
                self.assertEqual(outcome.variables["token"], "abc123")
                self.assertEqual(envmap["TOKEN"], "abc123")
                self.assertEqual(envmap["token"], "abc123")
                self.assertTrue(all(assertion.passed for assertion in outcome.assertions))
                self.assertEqual((tmpdir / "download.bin").read_bytes(), raw_bytes)
                self.assertIn(
                    "id,name",
                    (tmpdir / "items.csv").read_text(encoding="utf-8"),
                )
                self.assertNotIn("raw_bytes", outcome.report_response)
                self.assertEqual(
                    outcome.report_response["saved_body_to"],
                    str((tmpdir / "download.bin").resolve()),
                )
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()

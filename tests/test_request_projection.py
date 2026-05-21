from __future__ import annotations

import unittest

from drun.models.request import StepRequest
from drun.models.step import Step
from drun.runner.request_projection import (
    finalize_request_projection,
    render_request_for_setup,
)
from drun.runner.runner import Runner


class RequestProjectionTests(unittest.TestCase):
    def test_projection_renders_cleans_injects_and_builds_report_fields(self) -> None:
        runner = Runner(log=None, reveal_secrets=True)
        step = Step(
            name="Fetch user",
            request=StepRequest(
                method="POST",
                path="/users/${user_id}",
                headers={"Authorization": "Bearer none", "X-Trace": "${trace_id}"},
                json={"name": "${name}"},
            ),
        )
        variables = {
            "user_id": 42,
            "trace_id": "trace-1",
            "name": "Ada",
            "token": "jwt-token",
        }

        rendered = render_request_for_setup(
            runner=runner,
            step=step,
            variables=variables,
            funcs={},
            envmap={},
        )
        projection = finalize_request_projection(
            runner=runner,
            rendered_request=rendered,
            variables=variables,
            response_url="https://example.test/users/42",
        )

        self.assertEqual(projection.runtime_request["path"], "/users/42")
        self.assertEqual(
            projection.runtime_request["headers"],
            {"X-Trace": "trace-1", "Authorization": "Bearer jwt-token"},
        )
        self.assertEqual(projection.report_request["body"], {"name": "Ada"})
        self.assertNotIn("json", projection.report_request)
        self.assertIn("Authorization: Bearer jwt-token", projection.curl)
        self.assertIn("https://example.test/users/42", projection.curl)


if __name__ == "__main__":
    unittest.main()

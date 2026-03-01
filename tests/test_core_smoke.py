from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from drun import __version__
from drun.cli import _get_drun_version
from drun.exporters.curl import step_placeholders
from drun.loader.yaml_loader import load_yaml_file
from drun.models.case import Case
from drun.models.config import Config
from drun.models.request import StepRequest
from drun.models.step import Step


class CoreSmokeTests(unittest.TestCase):
    def test_step_placeholders_uses_path_and_handles_invoke_step(self) -> None:
        case = Case(
            config=Config(name="demo"),
            steps=[
                Step(
                    name="with-placeholders",
                    request=StepRequest(
                        method="GET",
                        path="/users/$user_id",
                        headers={"Authorization": "Bearer $token"},
                        body={"trace": "${uuid()}"},
                    ),
                )
            ],
        )

        vars_set, exprs_set = step_placeholders(case, 0)
        self.assertIn("$user_id", vars_set)
        self.assertIn("$token", vars_set)
        self.assertIn("${uuid()}", exprs_set)

        invoke_case = Case(config=Config(name="invoke"), steps=[Step(name="invoke", invoke="test_login")])
        vars_set, exprs_set = step_placeholders(invoke_case, 0)
        self.assertEqual(vars_set, set())
        self.assertEqual(exprs_set, set())

    def test_cli_version_matches_package_version(self) -> None:
        self.assertEqual(_get_drun_version(), __version__)

    def test_load_yaml_file_parses_minimal_case(self) -> None:
        content = """
config:
  name: Demo
  base_url: https://api.example.com

steps:
  - name: Ping
    request:
      method: GET
      path: /ping
    validate:
      - eq: [status_code, 200]
"""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "test_demo.yaml"
            path.write_text(content.strip() + "\n", encoding="utf-8")
            cases, meta = load_yaml_file(path)

        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].config.name, "Demo")
        self.assertEqual(cases[0].steps[0].request.path, "/ping")
        self.assertEqual(meta["file"], str(path))


if __name__ == "__main__":
    unittest.main()

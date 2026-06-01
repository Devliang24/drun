from __future__ import annotations

from pathlib import Path
import tempfile
import textwrap
import unittest

from drun.loader.yaml_loader import load_yaml_file
from drun.utils.errors import DiagnosticError


class YamlLayoutRulesTests(unittest.TestCase):
    def test_tcase_file_with_caseflow_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tcases" / "tc_smoke.yaml"
            path.parent.mkdir()
            path.write_text(
                textwrap.dedent(
                    """
                    config:
                      name: Smoke
                    caseflow: []
                    """
                ).lstrip(),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(DiagnosticError, "tc_.*must contain steps"):
                load_yaml_file(path)
    def test_tsuite_file_with_steps_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tsuites" / "ts_login.yaml"
            path.parent.mkdir()
            path.write_text(
                textwrap.dedent(
                    """
                    config:
                      name: Login
                    steps: []
                    """
                ).lstrip(),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(DiagnosticError, "ts_.*must contain caseflow"):
                load_yaml_file(path)
    def test_caseflow_invoke_must_use_tc_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tsuites" / "ts_smoke.yaml"
            path.parent.mkdir()
            path.write_text(
                textwrap.dedent(
                    """
                    config:
                      name: Smoke
                    caseflow:
                      - name: Login
                        invoke: test_login
                    """
                ).lstrip(),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(DiagnosticError, "invoke.*tc_"):
                load_yaml_file(path)
    def test_caseflow_invoke_may_use_module_tc_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tsuites" / "ts_smoke.yaml"
            path.parent.mkdir()
            path.write_text(
                textwrap.dedent(
                    """
                    config:
                      name: Smoke
                    caseflow:
                      - name: Login
                        invoke: auth/tc_login
                    """
                ).lstrip(),
                encoding="utf-8",
            )

            cases, _ = load_yaml_file(path)

            self.assertEqual(cases[0].steps[0].invoke, "auth/tc_login")
    def test_case_step_invoke_must_be_static_tc_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tcases" / "tc_flow.yaml"
            path.parent.mkdir()
            path.write_text(
                textwrap.dedent(
                    """
                    config:
                      name: Flow
                    steps:
                      - name: Invoke templated target
                        invoke: ${ENV(TARGET)}
                    """
                ).lstrip(),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(DiagnosticError, "invoke.*static tc_"):
                load_yaml_file(path)


if __name__ == "__main__":
    unittest.main()

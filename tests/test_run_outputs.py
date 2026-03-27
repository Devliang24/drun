from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import logging

from drun.commands.run import _build_run_output_plan, run_cases
from drun.models.report import CaseInstanceResult, RunReport


class _StubRunner:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def run_case(self, case, **kwargs) -> CaseInstanceResult:
        return CaseInstanceResult(
            name=case.config.name or "Unnamed",
            status="passed",
            steps=[],
            duration_ms=1.0,
        )

    def build_report(self, results) -> RunReport:
        return RunReport(
            summary={
                "total": len(results),
                "passed": len(results),
                "failed": 0,
                "skipped": 0,
                "duration_ms": 1.0,
            },
            cases=list(results),
        )


class RunOutputPlanTests(unittest.TestCase):
    def test_build_output_plan_for_temporary_single_file_uses_cwd_log_only(self) -> None:
        with TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            target = tmpdir / "test_tts.yaml"
            target.write_text("config:\n  name: Demo\nsteps: []\n", encoding="utf-8")

            plan = _build_run_output_plan(
                str(target),
                [target],
                ts="20260327-101010",
                system_name="Demo System",
                log_file=None,
                html=None,
                snippet_output=None,
                no_snippet=False,
                cwd=tmpdir,
            )

            self.assertTrue(plan.temporary_single_file)
            self.assertIsNone(plan.scaffold_root)
            self.assertEqual(plan.log_path, "test_tts-20260327-101010.log")
            self.assertIsNone(plan.html_path)
            self.assertFalse(plan.generate_snippets)
            self.assertIsNone(plan.snippet_output)

    def test_build_output_plan_for_scaffold_single_file_uses_project_root_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo-project"
            testcase_dir = project / "testcases"
            testsuite_dir = project / "testsuites"
            subdir = project / "workbench"
            testcase_dir.mkdir(parents=True)
            testsuite_dir.mkdir()
            subdir.mkdir()
            (project / ".env").write_text("BASE_URL=http://localhost:8000\n", encoding="utf-8")
            (project / "drun_hooks.py").write_text("", encoding="utf-8")
            target = testcase_dir / "test_login.yaml"
            target.write_text("config:\n  name: Demo\nsteps: []\n", encoding="utf-8")

            plan = _build_run_output_plan(
                "../testcases/test_login.yaml",
                [target],
                ts="20260327-101010",
                system_name="My Test System",
                log_file=None,
                html=None,
                snippet_output=None,
                no_snippet=False,
                cwd=subdir,
            )

            self.assertFalse(plan.temporary_single_file)
            self.assertEqual(plan.scaffold_root, project.resolve())
            self.assertEqual(plan.log_path, str((project / "logs" / "My-Test-System-20260327-101010.log").resolve()))
            self.assertEqual(plan.html_path, str((project / "reports" / "My-Test-System-20260327-101010.html").resolve()))
            self.assertTrue(plan.generate_snippets)
            self.assertEqual(plan.snippet_output, str((project / "snippets" / "20260327-101010").resolve()))

    def test_build_output_plan_respects_explicit_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            target = tmpdir / "test_tts.yaml"
            target.write_text("config:\n  name: Demo\nsteps: []\n", encoding="utf-8")

            plan = _build_run_output_plan(
                str(target),
                [target],
                ts="20260327-101010",
                system_name="Demo System",
                log_file="custom.log",
                html="artifacts/report.html",
                snippet_output="exports/snippets",
                no_snippet=False,
                cwd=tmpdir,
            )

            self.assertEqual(plan.log_path, "custom.log")
            self.assertEqual(plan.html_path, "artifacts/report.html")
            self.assertTrue(plan.generate_snippets)
            self.assertEqual(plan.snippet_output, "exports/snippets")


class RunOutputsIntegrationTests(unittest.TestCase):
    def test_run_cases_temporary_single_file_does_not_create_project_dirs(self) -> None:
        with TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            (tmpdir / "demo.env").write_text("BASE_URL=http://localhost:8000\n", encoding="utf-8")
            target = tmpdir / "test_temp.yaml"
            target.write_text(
                """config:
  name: Temporary File
  base_url: http://example.com

steps:
  - name: Ping
    request:
      method: GET
      path: /ping
""",
                encoding="utf-8",
            )

            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                with patch("drun.commands.run.Runner", _StubRunner), patch("drun.commands.run.get_functions_for", return_value={}):
                    with patch("drun.reporter.html_reporter.write_html", side_effect=AssertionError("write_html should not be called")):
                        with patch("drun.commands.run._save_code_snippets", side_effect=AssertionError("snippets should not be generated")):
                            run_cases(
                                path="test_temp.yaml",
                                k=None,
                                vars=[],
                                failfast=False,
                                report=None,
                                html=None,
                                allure_results=None,
                                log_level="WARNING",
                                env=None,
                                env_file="demo.env",
                                persist_env=None,
                                log_file=None,
                                httpx_logs=False,
                                reveal_secrets=True,
                                response_headers=False,
                                notify=None,
                                notify_only=None,
                                notify_attach_html=False,
                                no_snippet=False,
                                snippet_output=None,
                                snippet_lang="all",
                            )
            finally:
                os.chdir(old_cwd)
                logging.shutdown()

            log_files = list(tmpdir.glob("test_temp-*.log"))
            self.assertEqual(len(log_files), 1)
            self.assertFalse((tmpdir / "logs").exists())
            self.assertFalse((tmpdir / "reports").exists())
            self.assertFalse((tmpdir / "snippets").exists())

    def test_run_cases_scaffold_single_file_from_subdir_keeps_project_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo-project"
            testcase_dir = project / "testcases"
            testsuite_dir = project / "testsuites"
            subdir = project / "scratch"
            testcase_dir.mkdir(parents=True)
            testsuite_dir.mkdir()
            subdir.mkdir()
            (project / ".env").write_text("BASE_URL=http://localhost:8000\n", encoding="utf-8")
            (project / "drun_hooks.py").write_text("", encoding="utf-8")
            target = testcase_dir / "test_login.yaml"
            target.write_text(
                """config:
  name: Scaffold File
  base_url: http://example.com

steps:
  - name: Login
    request:
      method: GET
      path: /login
""",
                encoding="utf-8",
            )

            old_cwd = os.getcwd()
            os.chdir(subdir)
            try:
                with patch("drun.commands.run.Runner", _StubRunner), patch("drun.commands.run.get_functions_for", return_value={}):
                    run_cases(
                        path="../testcases/test_login.yaml",
                        k=None,
                        vars=[],
                        failfast=False,
                        report=None,
                        html=None,
                        allure_results=None,
                        log_level="WARNING",
                        env=None,
                        env_file=str(project / ".env"),
                        persist_env=None,
                        log_file=None,
                        httpx_logs=False,
                        reveal_secrets=True,
                        response_headers=False,
                        notify=None,
                        notify_only=None,
                        notify_attach_html=False,
                        no_snippet=False,
                        snippet_output=None,
                        snippet_lang="curl",
                    )
            finally:
                os.chdir(old_cwd)
                logging.shutdown()

            self.assertTrue(any((project / "logs").glob("*.log")))
            self.assertTrue(any((project / "reports").glob("*.html")))
            self.assertTrue((project / "snippets").exists())
            self.assertFalse((subdir / "logs").exists())
            self.assertFalse((subdir / "reports").exists())
            self.assertFalse((subdir / "snippets").exists())


if __name__ == "__main__":
    unittest.main()

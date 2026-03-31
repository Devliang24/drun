from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import logging

import typer

from drun.commands.run import (
    _build_run_output_plan,
    _build_run_summary_text,
    _format_failed_cases_block,
    run_cases,
)
from drun.models.report import (
    AssertionResult,
    CaseInstanceResult,
    RunReport,
    StepResult,
)


class _StubRunner:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def run_case(self, case, **kwargs) -> CaseInstanceResult:
        case_name = case.config.name or "Unnamed"
        fail_case = "Broken" in case_name or "Temporary" in case_name
        steps: list[StepResult] = []
        for idx, step in enumerate(case.steps or []):
            if fail_case:
                if idx == 0:
                    steps.append(
                        StepResult(
                            name=step.name,
                            status="failed",
                            error="request.files.file path not found: ./data/demo.wav",
                            duration_ms=12.0,
                        )
                    )
                else:
                    steps.append(
                        StepResult(
                            name=step.name,
                            status="failed",
                            asserts=[
                                AssertionResult(
                                    check="status_code",
                                    comparator="eq",
                                    expect=200,
                                    actual=500,
                                    passed=False,
                                    message="expected=200 actual=500",
                                )
                            ],
                            duration_ms=15.0,
                        )
                    )
            else:
                steps.append(
                    StepResult(name=step.name, status="passed", duration_ms=8.0)
                )

        if not steps:
            steps = [StepResult(name="Default Step", status="passed", duration_ms=8.0)]

        status = "failed" if fail_case else "passed"
        return CaseInstanceResult(
            name=case_name,
            status=status,
            steps=steps,
            duration_ms=sum(step.duration_ms or 0.0 for step in steps),
        )

    def build_report(self, results) -> RunReport:
        total = len(results)
        failed = sum(1 for r in results if r.status == "failed")
        skipped = sum(1 for r in results if r.status == "skipped")
        passed = total - failed - skipped
        duration = sum(r.duration_ms for r in results)

        step_total = 0
        step_failed = 0
        step_skipped = 0
        step_duration = 0.0
        for case in results:
            for step in case.steps or []:
                step_total += 1
                step_duration += step.duration_ms or 0.0
                if step.status == "failed":
                    step_failed += 1
                elif step.status == "skipped":
                    step_skipped += 1

        step_passed = step_total - step_failed - step_skipped
        return RunReport(
            summary={
                "total": total,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "duration_ms": duration,
                "steps_total": step_total,
                "steps_passed": step_passed,
                "steps_failed": step_failed,
                "steps_skipped": step_skipped,
                "steps_duration_ms": step_duration,
            },
            cases=list(results),
        )


class SummaryFormattingTests(unittest.TestCase):
    def test_build_run_summary_text_single_file_includes_case_rows(self) -> None:
        report = RunReport(
            summary={
                "total": 1,
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "duration_ms": 12345.0,
                "steps_total": 3,
                "steps_passed": 1,
                "steps_failed": 2,
                "steps_skipped": 0,
            },
            cases=[],
        )

        text = _build_run_summary_text(report)
        self.assertIn("[SUMMARY]", text)
        self.assertIn("Duration", text)
        self.assertIn("Cases Total", text)
        self.assertIn("Cases Pass Rate", text)
        self.assertIn("Steps Total", text)

    def test_build_run_summary_text_multi_file_includes_case_rows(self) -> None:
        report = RunReport(
            summary={
                "total": 2,
                "passed": 1,
                "failed": 1,
                "skipped": 0,
                "duration_ms": 19090.0,
                "steps_total": 11,
                "steps_passed": 9,
                "steps_failed": 2,
                "steps_skipped": 0,
            },
            cases=[],
        )

        text = _build_run_summary_text(report)
        self.assertIn("Cases Total", text)
        self.assertIn("Cases Pass Rate", text)
        self.assertIn("Steps Total", text)

    def test_failed_cases_block_lists_failed_steps_and_reasons(self) -> None:
        report = RunReport(
            summary={},
            cases=[
                CaseInstanceResult(
                    name="Broken Case",
                    status="failed",
                    steps=[
                        StepResult(
                            name="Step 1: Upload",
                            status="failed",
                            error="request.files.file path not found: ./data/demo.wav",
                        ),
                        StepResult(
                            name="Step 2: Validate",
                            status="failed",
                            asserts=[
                                AssertionResult(
                                    check="status_code",
                                    comparator="eq",
                                    expect=200,
                                    actual=500,
                                    passed=False,
                                    message="expected=200 actual=500",
                                )
                            ],
                        ),
                    ],
                ),
                CaseInstanceResult(
                    name="Passing Case",
                    status="passed",
                    steps=[StepResult(name="Step 1: Ping", status="passed")],
                ),
            ],
        )

        text = _format_failed_cases_block(report)
        self.assertIn("[FAILED CASES]", text)
        self.assertIn("- Broken Case", text)
        self.assertIn("  failed_step: Step 1: Upload", text)
        self.assertIn("  failed_step: Step 2: Validate", text)
        self.assertIn(
            "  reason: request.files.file path not found: ./data/demo.wav", text
        )
        self.assertIn("  reason: expected=200 actual=500", text)


class RunOutputPlanTests(unittest.TestCase):
    def test_build_output_plan_for_temporary_single_file_uses_cwd_log_only(
        self,
    ) -> None:
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

    def test_build_output_plan_for_scaffold_single_file_uses_project_root_outputs(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo-project"
            testcase_dir = project / "testcases"
            testsuite_dir = project / "testsuites"
            subdir = project / "workbench"
            testcase_dir.mkdir(parents=True)
            testsuite_dir.mkdir()
            subdir.mkdir()
            (project / ".env").write_text(
                "BASE_URL=http://localhost:8000\n", encoding="utf-8"
            )
            (project / "Dhook.py").write_text("", encoding="utf-8")
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
            self.assertEqual(
                plan.log_path,
                str(
                    (project / "logs" / "My-Test-System-20260327-101010.log").resolve()
                ),
            )
            self.assertEqual(
                plan.html_path,
                str(
                    (
                        project / "reports" / "My-Test-System-20260327-101010.html"
                    ).resolve()
                ),
            )
            self.assertTrue(plan.generate_snippets)
            self.assertEqual(
                plan.snippet_output,
                str((project / "snippets" / "20260327-101010").resolve()),
            )

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
    def test_run_cases_temporary_single_file_logs_case_and_step_summary_and_failed_cases(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            (tmpdir / "demo.env").write_text(
                "BASE_URL=http://localhost:8000\n", encoding="utf-8"
            )
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
                with (
                    patch("drun.commands.run.Runner", _StubRunner),
                    patch("drun.commands.run.get_functions_for", return_value={}),
                ):
                    with patch(
                        "drun.reporter.html_reporter.write_html",
                        side_effect=AssertionError("write_html should not be called"),
                    ):
                        with patch(
                            "drun.commands.run._save_code_snippets",
                            side_effect=AssertionError(
                                "snippets should not be generated"
                            ),
                        ):
                            with self.assertRaises(typer.Exit) as ctx:
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

            self.assertEqual(ctx.exception.exit_code, 1)
            log_files = list(tmpdir.glob("test_temp-*.log"))
            self.assertEqual(len(log_files), 1)
            self.assertFalse((tmpdir / "logs").exists())
            self.assertFalse((tmpdir / "reports").exists())
            self.assertFalse((tmpdir / "snippets").exists())
            log_text = log_files[0].read_text(encoding="utf-8")
            self.assertIn("[SUMMARY]", log_text)
            self.assertIn("Cases Total", log_text)
            self.assertIn("Cases Pass Rate", log_text)
            self.assertIn("Steps Total", log_text)
            self.assertIn("[FAILED CASES]", log_text)
            self.assertIn("- Temporary File", log_text)
            self.assertIn("  failed_step: Ping", log_text)

    def test_run_cases_scaffold_single_file_from_subdir_keeps_project_outputs(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo-project"
            testcase_dir = project / "testcases"
            testsuite_dir = project / "testsuites"
            subdir = project / "scratch"
            testcase_dir.mkdir(parents=True)
            testsuite_dir.mkdir()
            subdir.mkdir()
            (project / ".env").write_text(
                "BASE_URL=http://localhost:8000\n", encoding="utf-8"
            )
            (project / "Dhook.py").write_text("", encoding="utf-8")
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
                with (
                    patch("drun.commands.run.Runner", _StubRunner),
                    patch("drun.commands.run.get_functions_for", return_value={}),
                ):
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

            log_files = list((project / "logs").glob("*.log"))
            self.assertTrue(log_files)
            log_text = log_files[0].read_text(encoding="utf-8")
            self.assertIn("[SUMMARY]", log_text)
            self.assertIn("Cases Total", log_text)
            self.assertIn("Cases Pass Rate", log_text)
            self.assertIn("Steps Total", log_text)
            self.assertFalse((subdir / "logs").exists())
            self.assertFalse((subdir / "reports").exists())
            self.assertFalse((subdir / "snippets").exists())

    def test_run_cases_directory_input_includes_case_summary_and_multiple_failed_case_steps(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo-project"
            testcase_dir = project / "testcases"
            testsuite_dir = project / "testsuites"
            testcase_dir.mkdir(parents=True)
            testsuite_dir.mkdir()
            (project / ".env").write_text(
                "BASE_URL=http://localhost:8000\n", encoding="utf-8"
            )
            (project / "Dhook.py").write_text("", encoding="utf-8")

            good = testcase_dir / "case_good.yaml"
            good.write_text(
                """config:
  name: Passed Case
  base_url: http://example.com

steps:
  - name: "Step 1: Ping"
    request:
      method: GET
      path: /ping
""",
                encoding="utf-8",
            )
            broken = testcase_dir / "case_broken.yaml"
            broken.write_text(
                """config:
  name: Broken Case
  base_url: http://example.com

steps:
  - name: "Step 1: Upload"
    request:
      method: POST
      path: /upload
  - name: "Step 2: Validate"
    request:
      method: GET
      path: /status
""",
                encoding="utf-8",
            )
            broken_two = testcase_dir / "case_broken_two.yaml"
            broken_two.write_text(
                """config:
  name: Another Broken Case
  base_url: http://example.com

steps:
  - name: "Step 1: Upload"
    request:
      method: POST
      path: /upload
""",
                encoding="utf-8",
            )

            old_cwd = os.getcwd()
            os.chdir(project)
            try:
                with (
                    patch("drun.commands.run.Runner", _StubRunner),
                    patch("drun.commands.run.get_functions_for", return_value={}),
                ):
                    with self.assertRaises(typer.Exit) as ctx:
                        run_cases(
                            path="testcases",
                            k=None,
                            vars=[],
                            failfast=False,
                            report=None,
                            html=None,
                            allure_results=None,
                            log_level="WARNING",
                            env=None,
                            env_file=".env",
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

            self.assertEqual(ctx.exception.exit_code, 1)
            log_files = list((project / "logs").glob("*.log"))
            self.assertTrue(log_files)
            log_text = log_files[0].read_text(encoding="utf-8")
            self.assertIn("[SUMMARY]", log_text)
            self.assertIn("Cases Total", log_text)
            self.assertIn("Cases Pass Rate", log_text)
            self.assertIn("Steps Total", log_text)
            self.assertIn("[FAILED CASES]", log_text)
            self.assertIn("- Broken Case", log_text)
            self.assertIn("- Another Broken Case", log_text)
            self.assertIn("  failed_step: Step 1: Upload", log_text)
            self.assertIn("  failed_step: Step 2: Validate", log_text)
            self.assertIn(
                "  reason: request.files.file path not found: ./data/demo.wav", log_text
            )


if __name__ == "__main__":
    unittest.main()

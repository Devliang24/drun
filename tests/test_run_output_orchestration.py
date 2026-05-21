from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from drun.commands.run_outputs import (
    build_run_output_plan,
    build_run_summary_text,
    format_failed_cases_block,
    write_report_artifacts,
    write_snippet_artifacts,
)
from drun.models.report import CaseInstanceResult, RunReport, StepResult


class _MemoryLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def info(self, message: str, *args) -> None:
        self.messages.append(message % args if args else message)

    def error(self, message: str, *args) -> None:
        self.messages.append(message % args if args else message)


class RunOutputOrchestrationTests(unittest.TestCase):
    def test_outputs_keep_paths_reports_summary_failures_and_snippets(self) -> None:
        with TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo-project"
            testcase_dir = project / "testcases"
            testsuite_dir = project / "testsuites"
            workbench_dir = project / "workbench"
            testcase_dir.mkdir(parents=True)
            testsuite_dir.mkdir()
            workbench_dir.mkdir()
            (project / ".env").write_text(
                "BASE_URL=http://localhost:8000\n", encoding="utf-8"
            )
            (project / "Dhook.py").write_text("", encoding="utf-8")
            target = testcase_dir / "test_demo.yaml"
            target.write_text("config:\n  name: Demo\nsteps: []\n", encoding="utf-8")

            plan = build_run_output_plan(
                str(testcase_dir),
                [target],
                ts="20260521-101010",
                system_name="Demo System",
                log_file=None,
                html=None,
                snippet_output=None,
                no_snippet=False,
                cwd=workbench_dir,
            )
            report = RunReport(
                summary={
                    "total": 1,
                    "passed": 0,
                    "failed": 1,
                    "skipped": 0,
                    "duration_ms": 1234.0,
                    "steps_total": 1,
                    "steps_passed": 0,
                    "steps_failed": 1,
                    "steps_skipped": 0,
                },
                cases=[
                    CaseInstanceResult(
                        name="Broken Case",
                        status="failed",
                        steps=[
                            StepResult(
                                name="Upload",
                                status="failed",
                                error="request.files.file path not found",
                            )
                        ],
                    )
                ],
            )
            logger = _MemoryLogger()
            json_path = project / "reports" / "result.json"

            write_report_artifacts(
                report,
                json_path=str(json_path),
                html_path=plan.html_path,
                allure_results=None,
                environment="dev",
                log=logger,
            )
            snippet_calls: list[tuple[str, str]] = []

            def fake_snippet_writer(
                items, output_dir, languages, env_store, log
            ) -> None:
                snippet_calls.append((output_dir, languages))

            write_snippet_artifacts(
                plan,
                items=[(object(), {"file": str(target)})],
                snippet_lang="curl",
                env_store={"BASE_URL": "http://localhost:8000"},
                log=logger,
                snippet_writer=fake_snippet_writer,
            )

            summary_text = build_run_summary_text(report)
            failed_cases_text = format_failed_cases_block(report)

            self.assertEqual(
                plan.log_path,
                str(
                    (project / "logs" / "Demo-System-20260521-101010.log").resolve()
                ),
            )
            self.assertEqual(
                plan.html_path,
                str(
                    (
                        project / "reports" / "Demo-System-20260521-101010.html"
                    ).resolve()
                ),
            )
            self.assertEqual(
                plan.snippet_output,
                str((project / "snippets" / "20260521-101010").resolve()),
            )
            self.assertTrue(json_path.exists())
            self.assertTrue(Path(plan.html_path or "").exists())
            self.assertIn("[SUMMARY]", summary_text)
            self.assertIn("Cases Failed", summary_text)
            self.assertIn("[FAILED CASES]", failed_cases_text)
            self.assertIn("failed_step: Upload", failed_cases_text)
            self.assertEqual(snippet_calls, [(plan.snippet_output or "", "curl")])


if __name__ == "__main__":
    unittest.main()

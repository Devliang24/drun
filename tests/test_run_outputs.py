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
    _parse_run_target_with_case_selector,
    run_cases,
)
from drun.commands.run_outputs import (
    RunOutputPlan,
    RunPlanContext,
    build_artifacts_text,
    build_run_plan_text,
    has_scaffold_markers,
    render_key_value_block,
)
from drun.models.report import (
    CaseInstanceResult,
    CheckResult,
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
                            checks=[
                                CheckResult(
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
                            name="Step 2: Check",
                            status="failed",
                            checks=[
                                CheckResult(
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
        self.assertIn("  failed_step: Step 2: Check", text)
        self.assertIn(
            "  reason: request.files.file path not found: ./data/demo.wav", text
        )
    def test_failed_cases_block_can_include_rerun_hint_and_parameter_note(self) -> None:
        report = RunReport(
            summary={},
            cases=[
                CaseInstanceResult(
                    name="Broken Case",
                    parameters={"user": "alice"},
                    status="failed",
                    steps=[StepResult(name="Login", status="failed", error="boom")],
                )
            ],
        )

        text = _format_failed_cases_block(
            report,
            run_target="tcases",
            env="dev",
            env_file=".env.local",
        )

        self.assertIn("  rerun: drun r 'tcases:Broken Case' -env-file .env.local", text)
        self.assertIn(
            "  note: rerun executes all parameter sets for this Case", text
        )
        self.assertNotIn("-env dev", text)

    def test_failed_cases_block_omits_rerun_for_unsupported_case_selector_name(self) -> None:
        report = RunReport(
            summary={},
            cases=[
                CaseInstanceResult(
                    name="Broken: Case, Variant",
                    status="failed",
                    steps=[StepResult(name="Login", status="failed", error="boom")],
                )
            ],
        )

        text = _format_failed_cases_block(report, run_target="tcases", env="dev")

        self.assertNotIn("rerun:", text)
        self.assertIn(
            "note: rerun hint unavailable because Case name contains ',' or ':'",
            text,
        )


    def test_render_key_value_block_sanitizes_multiline_values(self) -> None:
        text = render_key_value_block(
            "DEMO",
            [
                ("Single", " value "),
                ("Multi", "first\nsecond\rthird"),
            ],
        )

        self.assertEqual(text, "[DEMO]\nSingle: value\nMulti: first second third")

    def test_build_run_plan_text_masks_base_url_userinfo_and_lists_var_keys(self) -> None:
        output_plan = RunOutputPlan(
            single_file_target=None,
            scaffold_root=Path("/repo").resolve(),
            temporary_single_file=False,
            log_path="logs/run.log",
            html_path="reports/report.html",
            snippet_output="snippets/20260603",
            generate_snippets=True,
        )

        text = build_run_plan_text(
            RunPlanContext(
                target="tcases",
                environment="dev",
                env_file="/repo/.env.dev",
                base_url="https://user:pass@example.test/v1",
                files_count=2,
                cases_count=3,
                case_instances_count=5,
                tag_filter="smoke",
                case_selector=["Case A"],
                failfast=True,
                cli_vars_keys=["token", "BASE_URL"],
                output_plan=output_plan,
                json_report="reports/result.json",
                allure_results="allure-results",
                log_level="INFO",
                reveal_secrets=False,
                response_headers=True,
                httpx_logs=True,
                snippet_lang="curl",
            )
        )

        self.assertIn("[RUN PLAN]", text)
        self.assertIn("Target: tcases", text)
        self.assertIn("Base URL: https://***@example.test/v1", text)
        self.assertIn("Cases: 3", text)
        self.assertIn("Case instances: 5", text)
        self.assertIn("Case selector: Case A", text)
        self.assertIn("CLI vars: BASE_URL, token", text)
        self.assertIn("Secrets mode: mask", text)
        self.assertNotIn("user:pass", text)

    def test_build_artifacts_text_lists_disabled_outputs_and_open_hint(self) -> None:
        output_plan = RunOutputPlan(
            single_file_target=None,
            scaffold_root=None,
            temporary_single_file=False,
            log_path="run.log",
            html_path="report.html",
            snippet_output=None,
            generate_snippets=False,
        )

        text = build_artifacts_text(
            output_plan=output_plan,
            json_report=None,
            allure_results=None,
            snippet_lang="all",
        )

        self.assertIn("[ARTIFACTS]", text)
        self.assertIn("HTML report: report.html", text)
        self.assertIn("JSON report: disabled", text)
        self.assertIn("Allure results: disabled", text)
        self.assertIn("Log file: run.log", text)
        self.assertIn("Snippets: disabled", text)
        self.assertIn("Open reports: drun s", text)


class RunPathCaseSelectorParseTests(unittest.TestCase):
    def test_parse_single_case_selector(self) -> None:
        target, selected = _parse_run_target_with_case_selector(
            "tc_channel_token_flow:获取渠道 token"
        )
        self.assertEqual(target, "tc_channel_token_flow")
        self.assertEqual(selected, ["获取渠道 token"])

    def test_parse_multi_case_selector_deduplicates_names(self) -> None:
        target, selected = _parse_run_target_with_case_selector(
            "tc_channel_token_flow:Case C, Case A,Case C, Case A "
        )
        self.assertEqual(target, "tc_channel_token_flow")
        self.assertEqual(selected, ["Case C", "Case A"])

    def test_parse_case_selector_rejects_empty_names(self) -> None:
        with self.assertRaises(ValueError):
            _parse_run_target_with_case_selector("tc_channel_token_flow:Case A,")

        with self.assertRaises(ValueError):
            _parse_run_target_with_case_selector("tc_channel_token_flow: , ")

        with self.assertRaises(ValueError):
            _parse_run_target_with_case_selector("tc_channel_token_flow:")


class RunOutputPlanTests(unittest.TestCase):
    def test_build_output_plan_for_temporary_single_file_uses_cwd_log_only(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            target = tmpdir / "tc_tts.yaml"
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
            self.assertEqual(plan.log_path, "tc_tts-20260327-101010.log")
            self.assertIsNone(plan.html_path)
            self.assertFalse(plan.generate_snippets)
            self.assertIsNone(plan.snippet_output)

    def test_has_scaffold_markers_accepts_lowercase_dhook(self) -> None:
        with TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "tcases").mkdir()
            (project / "dhook.py").write_text("", encoding="utf-8")

            self.assertTrue(has_scaffold_markers(project))

    def test_has_scaffold_markers_ignores_legacy_Dhook(self) -> None:
        with TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "tcases").mkdir()
            (project / "Dhook.py").write_text("", encoding="utf-8")

            self.assertFalse(has_scaffold_markers(project))

    def test_build_output_plan_for_scaffold_single_file_uses_project_root_outputs(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo-project"
            testcase_dir = project / "tcases"
            testsuite_dir = project / "tsuites"
            subdir = project / "workbench"
            testcase_dir.mkdir(parents=True)
            testsuite_dir.mkdir()
            subdir.mkdir()
            (project / ".env").write_text(
                "BASE_URL=http://localhost:8000\n", encoding="utf-8"
            )
            (project / "dhook.py").write_text("", encoding="utf-8")
            target = testcase_dir / "tc_login.yaml"
            target.write_text("config:\n  name: Demo\nsteps: []\n", encoding="utf-8")

            plan = _build_run_output_plan(
                "../tcases/tc_login.yaml",
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
            target = tmpdir / "tc_tts.yaml"
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
            target = tmpdir / "tc_temp.yaml"
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
                                    path="tc_temp.yaml",
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
            log_files = list(tmpdir.glob("tc_temp-*.log"))
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
            self.assertIn("[ARTIFACTS]", log_text)
            self.assertIn("HTML report: disabled", log_text)
            self.assertNotIn("Open reports: drun s", log_text)
            self.assertIn("- Temporary File", log_text)
            self.assertIn("  failed_step: Ping", log_text)

    def test_run_cases_scaffold_single_file_from_subdir_keeps_project_outputs(
        self,
    ) -> None:
        with TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo-project"
            testcase_dir = project / "tcases"
            testsuite_dir = project / "tsuites"
            subdir = project / "scratch"
            testcase_dir.mkdir(parents=True)
            testsuite_dir.mkdir()
            subdir.mkdir()
            (project / ".env").write_text(
                "BASE_URL=http://localhost:8000\n", encoding="utf-8"
            )
            (project / "dhook.py").write_text("", encoding="utf-8")
            target = testcase_dir / "tc_login.yaml"
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
                        path="../tcases/tc_login.yaml",
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
            self.assertIn("[ARTIFACTS]", log_text)
            self.assertIn("Open reports: drun s", log_text)
            self.assertLess(log_text.index("[SUMMARY]"), log_text.index("[ARTIFACTS]"))
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
            testcase_dir = project / "tcases"
            testsuite_dir = project / "tsuites"
            testcase_dir.mkdir(parents=True)
            testsuite_dir.mkdir()
            (project / ".env").write_text(
                "BASE_URL=http://localhost:8000\n", encoding="utf-8"
            )
            (project / "dhook.py").write_text("", encoding="utf-8")

            good = testcase_dir / "tc_case_good.yaml"
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
            broken = testcase_dir / "tc_case_broken.yaml"
            broken.write_text(
                """config:
  name: Broken Case
  base_url: http://example.com

steps:
  - name: "Step 1: Upload"
    request:
      method: POST
      path: /upload
  - name: "Step 2: Check"
    request:
      method: GET
      path: /status
""",
                encoding="utf-8",
            )
            broken_two = testcase_dir / "tc_case_broken_two.yaml"
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
                            path="tcases",
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
            self.assertIn("[ARTIFACTS]", log_text)
            self.assertLess(log_text.index("[FAILED CASES]"), log_text.index("[ARTIFACTS]"))
            self.assertIn("Cases Total", log_text)
            self.assertIn("Cases Pass Rate", log_text)
            self.assertIn("Steps Total", log_text)
            self.assertIn("[FAILED CASES]", log_text)
            self.assertIn("- Broken Case", log_text)
            self.assertIn("- Another Broken Case", log_text)
            self.assertIn("  failed_step: Step 1: Upload", log_text)
            self.assertIn("  failed_step: Step 2: Check", log_text)
            self.assertIn(
                "  reason: request.files.file path not found: ./data/demo.wav", log_text
            )
    def test_run_cases_no_match_tag_output_is_concise(self) -> None:
        with TemporaryDirectory() as tmp:
            project = Path(tmp)
            tcases = project / "tcases"
            tsuites = project / "tsuites"
            tcases.mkdir(parents=True)
            tsuites.mkdir()
            (project / ".env").write_text(
                "BASE_URL=http://localhost:8000\n", encoding="utf-8"
            )
            (tcases / "tc_case.yaml").write_text(
                """config:
  name: Smoke Case
  tags: [smoke]
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
            os.chdir(project)
            try:
                with (
                    patch("drun.commands.run.Runner", _StubRunner),
                    patch("drun.commands.run.get_functions_for", return_value={}),
                    patch("drun.commands.run.typer.echo") as echo_mock,
                ):
                    with self.assertRaises(typer.Exit) as ctx:
                        run_cases(
                            path="tcases",
                            k="regression",
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
                            snippet_lang="all",
                        )
            finally:
                os.chdir(old_cwd)
                logging.shutdown()

            self.assertEqual(ctx.exception.exit_code, 2)
            emitted = "\n".join(
                call.args[0] for call in echo_mock.call_args_list if call.args
            )
            self.assertIn("[ERROR] No Cases matched tag expression.", emitted)
            self.assertIn("Files: 1", emitted)
            self.assertIn("Cases: 1", emitted)
            self.assertIn("drun t tcases", emitted)
            self.assertIn("drun r tcases", emitted)
            self.assertNotIn("file=", emitted)
            self.assertNotIn("[RUN PLAN]", emitted)


class _RecordingRunner(_StubRunner):
    executed_case_names: list[str] = []

    @classmethod
    def reset(cls) -> None:
        cls.executed_case_names = []

    def run_case(self, case, **kwargs) -> CaseInstanceResult:
        case_name = case.config.name or "Unnamed"
        type(self).executed_case_names.append(case_name)
        return super().run_case(case, **kwargs)


class RunCaseSelectorExecutionTests(unittest.TestCase):
    def test_run_cases_single_case_selector_runs_only_target_case(self) -> None:
        with TemporaryDirectory() as tmp:
            project = Path(tmp)
            tcases = project / "tcases"
            tsuites = project / "tsuites"
            tcases.mkdir(parents=True)
            tsuites.mkdir()
            (project / ".env").write_text(
                "BASE_URL=http://localhost:8000\n", encoding="utf-8"
            )
            case_a = tcases / "tc_case_a.yaml"
            case_a.write_text(
                """config:
  name: Case A
  base_url: http://example.com
steps:
  - name: Step A
    request:
      method: GET
      path: /a
""",
                encoding="utf-8",
            )
            case_b = tcases / "tc_case_b.yaml"
            case_b.write_text(
                """config:
  name: Case B
  base_url: http://example.com
steps:
  - name: Step B
    request:
      method: GET
      path: /b
""",
                encoding="utf-8",
            )

            _RecordingRunner.reset()
            old_cwd = os.getcwd()
            os.chdir(project)
            try:
                with (
                    patch("drun.commands.run.Runner", _RecordingRunner),
                    patch("drun.commands.run.get_functions_for", return_value={}),
                ):
                    run_cases(
                        path="tcases:Case B",
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
                        snippet_lang="all",
                    )
            finally:
                os.chdir(old_cwd)
                logging.shutdown()

            self.assertEqual(_RecordingRunner.executed_case_names, ["Case B"])

    def test_run_cases_multi_case_selector_runs_in_source_order(self) -> None:
        with TemporaryDirectory() as tmp:
            project = Path(tmp)
            tcases = project / "tcases"
            tsuites = project / "tsuites"
            tcases.mkdir(parents=True)
            tsuites.mkdir()
            (project / ".env").write_text(
                "BASE_URL=http://localhost:8000\n", encoding="utf-8"
            )
            case_a = tcases / "tc_case_a.yaml"
            case_a.write_text(
                """config:
  name: Case A
  base_url: http://example.com
steps:
  - name: Step A
    request:
      method: GET
      path: /a
""",
                encoding="utf-8",
            )
            case_b = tcases / "tc_case_b.yaml"
            case_b.write_text(
                """config:
  name: Case B
  base_url: http://example.com
steps:
  - name: Step B
    request:
      method: GET
      path: /b
""",
                encoding="utf-8",
            )
            case_c = tcases / "tc_case_c.yaml"
            case_c.write_text(
                """config:
  name: Case C
  base_url: http://example.com
steps:
  - name: Step C
    request:
      method: GET
      path: /c
""",
                encoding="utf-8",
            )

            _RecordingRunner.reset()
            old_cwd = os.getcwd()
            os.chdir(project)
            try:
                with (
                    patch("drun.commands.run.Runner", _RecordingRunner),
                    patch("drun.commands.run.get_functions_for", return_value={}),
                ):
                    run_cases(
                        path="tcases:Case C,Case A",
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
                        snippet_lang="all",
                    )
            finally:
                os.chdir(old_cwd)
                logging.shutdown()

            self.assertEqual(_RecordingRunner.executed_case_names, ["Case A", "Case C"])

    def test_run_cases_selector_matches_all_duplicate_case_names(self) -> None:
        with TemporaryDirectory() as tmp:
            project = Path(tmp)
            tcases = project / "tcases"
            tsuites = project / "tsuites"
            tcases.mkdir(parents=True)
            tsuites.mkdir()
            (project / ".env").write_text(
                "BASE_URL=http://localhost:8000\n", encoding="utf-8"
            )
            case_a = tcases / "tc_case_a.yaml"
            case_a.write_text(
                """config:
  name: Case A
  base_url: http://example.com
steps:
  - name: Step A
    request:
      method: GET
      path: /a
""",
                encoding="utf-8",
            )
            case_a_dup = tcases / "tc_case_a_dup.yaml"
            case_a_dup.write_text(
                """config:
  name: Case A
  base_url: http://example.com
steps:
  - name: Step A Dup
    request:
      method: GET
      path: /a-dup
""",
                encoding="utf-8",
            )

            _RecordingRunner.reset()
            old_cwd = os.getcwd()
            os.chdir(project)
            try:
                with (
                    patch("drun.commands.run.Runner", _RecordingRunner),
                    patch("drun.commands.run.get_functions_for", return_value={}),
                ):
                    run_cases(
                        path="tcases:Case A",
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
                        snippet_lang="all",
                    )
            finally:
                os.chdir(old_cwd)
                logging.shutdown()

            self.assertEqual(_RecordingRunner.executed_case_names, ["Case A", "Case A"])

    def test_run_cases_selector_no_match_fails_with_available_case_names(self) -> None:
        with TemporaryDirectory() as tmp:
            project = Path(tmp)
            tcases = project / "tcases"
            tsuites = project / "tsuites"
            tcases.mkdir(parents=True)
            tsuites.mkdir()
            (project / ".env").write_text(
                "BASE_URL=http://localhost:8000\n", encoding="utf-8"
            )
            case_a = tcases / "tc_case_a.yaml"
            case_a.write_text(
                """config:
  name: Case A
  base_url: http://example.com
steps:
  - name: Step A
    request:
      method: GET
      path: /a
""",
                encoding="utf-8",
            )
            case_b = tcases / "tc_case_b.yaml"
            case_b.write_text(
                """config:
  name: Case B
  base_url: http://example.com
steps:
  - name: Step B
    request:
      method: GET
      path: /b
""",
                encoding="utf-8",
            )

            _RecordingRunner.reset()
            old_cwd = os.getcwd()
            os.chdir(project)
            try:
                with (
                    patch("drun.commands.run.Runner", _RecordingRunner),
                    patch("drun.commands.run.get_functions_for", return_value={}),
                    patch("drun.commands.run.typer.echo") as echo_mock,
                ):
                    with self.assertRaises(typer.Exit) as ctx:
                        run_cases(
                            path="tcases:Case Z",
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
                            snippet_lang="all",
                        )
            finally:
                os.chdir(old_cwd)
                logging.shutdown()

            self.assertEqual(ctx.exception.exit_code, 2)
            emitted = "\n".join(
                call.args[0] for call in echo_mock.call_args_list if call.args
            )
            self.assertIn("requested=[Case Z]", emitted)
            self.assertIn("available=[Case A, Case B]", emitted)


if __name__ == "__main__":
    unittest.main()

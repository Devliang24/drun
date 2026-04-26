from __future__ import annotations

import re
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from drun.models.report import AssertionResult, CaseInstanceResult, RunReport, StepResult
from drun.reporter.html_reporter import _build_step, write_html


class HtmlReporterLayoutTests(unittest.TestCase):
    def _build_step_result(self) -> StepResult:
        return StepResult(
            name="审批-列表定位审批单",
            status="passed",
            duration_ms=150.9,
            request={
                "method": "GET",
                "path": "/api_v2/approvals?page_number=1&page_size=20&status=1&type=1&applicant_name=lab1&created_start_time=1776949634&created_end_time=1776949644",
            },
            response={"status_code": 200, "body": {"ok": True}},
            asserts=[
                AssertionResult(
                    check="status_code",
                    comparator="eq",
                    expect=200,
                    actual=200,
                    passed=True,
                ),
                AssertionResult(
                    check="$.data.total",
                    comparator="ge",
                    expect=1,
                    actual=1,
                    passed=True,
                ),
                AssertionResult(
                    check="$.data.items[0].id",
                    comparator="exists",
                    expect=True,
                    actual=True,
                    passed=True,
                ),
            ],
        )

    def test_build_step_uses_dedicated_single_line_status_container(self) -> None:
        html = _build_step(self._build_step_result(), step_idx=2)

        self.assertIn("class='st-head-main'", html)
        self.assertIn("class='st-head-side'", html)
        self.assertIn("class='st-head-duration muted'>150.9 ms</span>", html)
        self.assertIn("class='st-head-asserts muted'>断言: 3 ✓ / 0 ✗</span>", html)

    def test_build_step_uses_icon_only_copy_button(self) -> None:
        html = _build_step(self._build_step_result(), step_idx=2)

        self.assertIn("class='icon-btn copy-btn'", html)
        self.assertIn("aria-label='复制'", html)
        self.assertNotIn(">复制</button>", html)

    def test_write_html_includes_nowrap_step_header_styles(self) -> None:
        report = RunReport(
            summary={
                "total": 1,
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "duration_ms": 150.9,
                "steps_total": 1,
                "steps_passed": 1,
                "steps_failed": 0,
                "steps_skipped": 0,
            },
            cases=[
                CaseInstanceResult(
                    name="审批全链路用例",
                    status="passed",
                    duration_ms=150.9,
                    steps=[self._build_step_result()],
                )
            ],
        )

        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.html"
            write_html(report, output)
            html = output.read_text(encoding="utf-8")

        self.assertRegex(
            html,
            r"\.step \.st-head-side \{[^}]*white-space:nowrap;[^}]*\}",
        )
        self.assertRegex(
            html,
            r"\.step \.st-head-side \{[^}]*flex-wrap:nowrap;[^}]*\}",
        )
        self.assertRegex(
            html,
            r"\.step \.st-head-main \{[^}]*min-width:0;[^}]*flex:1 1 auto;[^}]*\}",
        )
        self.assertRegex(
            html,
            r"\.panel \.p-head button\.copy-btn \{[^}]*border:none;[^}]*background:transparent;[^}]*\}",
        )


if __name__ == "__main__":
    unittest.main()

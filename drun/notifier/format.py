from __future__ import annotations

from typing import List, Tuple

from drun.models.report import RunReport, CaseInstanceResult, StepResult


def collect_failures(report: RunReport, topn: int = 5) -> List[Tuple[str, str, str]]:
    out: List[Tuple[str, str, str]] = []
    for c in report.cases:
        if c.status != "failed":
            continue
        step_name = ""
        message = ""
        for s in c.steps:
            if s.status == "failed":
                step_name = s.name
                # prefer assertion message
                for a in s.asserts:
                    if not a.passed:
                        message = a.message or "assertion failed"
                        break
                if not message and s.error:
                    message = s.error
                break
        out.append((c.name, step_name or "(unknown step)", message or "(no message)"))
        if len(out) >= max(1, int(topn)):
            break
    return out


def collect_failed_steps(report: RunReport, topn: int = 5) -> List[Tuple[str, str, str, float]]:
    """收集失败步骤的详细信息

    Returns:
        List of (case_name, step_name, error_message, duration_ms)
    """
    out: List[Tuple[str, str, str, float]] = []
    for case in report.cases:
        for step in case.steps:
            if step.status == "failed":
                # 获取错误信息，优先使用断言失败信息
                error_msg = ""
                for assertion in step.asserts:
                    if not assertion.passed:
                        error_msg = assertion.message or "assertion failed"
                        break
                if not error_msg and step.error:
                    error_msg = step.error
                if not error_msg:
                    error_msg = "(no error message)"

                out.append((
                    case.name,
                    step.name,
                    error_msg,
                    step.duration_ms
                ))

                if len(out) >= max(1, int(topn)):
                    return out
    return out


def collect_test_files(report: RunReport, max_display: int = 3) -> str:
    """收集执行的测试文件列表

    Returns:
        格式化的文件列表字符串
    """
    # 从所有用例中提取源文件，去重
    files = list({case.source for case in report.cases if case.source})

    if not files:
        return ""

    if len(files) == 1:
        return f"执行文件: {files[0]}"
    else:
        lines = [f"执行文件: {len(files)}个"]
        for f in files[:max_display]:
            lines.append(f"  • {f}")
        if len(files) > max_display:
            lines.append(f"  • ...等{len(files) - max_display}个")
        return "\n".join(lines)


def build_summary_text(report: RunReport, *, html_path: str | None, log_path: str | None, topn: int = 5) -> str:
    s = report.summary or {}
    total = s.get("total", 0)
    passed = s.get("passed", 0)
    failed = s.get("failed", 0)
    skipped = s.get("skipped", 0)
    dur_ms = s.get("duration_ms", 0.0)

    # 步骤统计
    steps_total = s.get("steps_total", 0)
    steps_passed = s.get("steps_passed", 0)
    steps_failed = s.get("steps_failed", 0)
    steps_skipped = s.get("steps_skipped", 0)

    lines: List[str] = []
    # 用例级别摘要
    lines.append(f"Drun 执行完成：总 {total} | 通过 {passed} | 失败 {failed} | 跳过 {skipped} | {dur_ms/1000.0:.1f}s")

    # 步骤级别统计
    lines.append(f"步骤统计：总 {steps_total} | 通过 {steps_passed} | 失败 {steps_failed}")

    # 如果有失败，显示失败步骤详情
    failed_steps = collect_failed_steps(report, topn=topn)
    if failed_steps:
        lines.append("")  # 空行
        lines.append("失败步骤详情：")
        for i, (case_name, step_name, error_msg, duration) in enumerate(failed_steps, 1):
            # clamp message length
            msg = str(error_msg)
            if len(msg) > 150:
                msg = msg[:150] + "..."
            lines.append(f"{i}. [{case_name}] {step_name}")
            lines.append(f"   • 错误: {msg}")
            lines.append(f"   • 耗时: {duration:.1f}ms")

    # 添加执行文件信息（在失败详情之后，报告链接之前）
    files_info = collect_test_files(report, max_display=3)
    if files_info:
        lines.append("")  # 空行
        lines.append(files_info)

    # 添加报告和日志链接
    if html_path or log_path:
        lines.append("")  # 空行
    if html_path:
        lines.append(f"报告: {html_path}")
    if log_path:
        lines.append(f"日志: {log_path}")

    return "\n".join(lines)


def build_text_message(report: RunReport, *, html_path: str | None, log_path: str | None, topn: int = 5) -> str:
    # Only Dollar-style rendering is supported for test templates; notifications use built-in summary text
    return build_summary_text(report, html_path=html_path, log_path=log_path, topn=topn)

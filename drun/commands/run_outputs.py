from __future__ import annotations

from dataclasses import dataclass
import re
import shlex
import unicodedata
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

from drun.models.case import Case
from drun.models.report import RunReport
from drun.reporter.json_reporter import write_json


@dataclass(frozen=True)
class RunOutputPlan:
    single_file_target: Path | None
    scaffold_root: Path | None
    temporary_single_file: bool
    log_path: str
    html_path: str | None
    snippet_output: str | None
    generate_snippets: bool


@dataclass(frozen=True)
class RunPlanContext:
    target: str
    environment: str
    env_file: str
    base_url: str | None
    files_count: int
    cases_count: int
    case_instances_count: int
    tag_filter: str | None
    case_selector: List[str] | None
    failfast: bool
    cli_vars_keys: Iterable[str]
    output_plan: RunOutputPlan
    json_report: str | None
    allure_results: str | None
    log_level: str
    reveal_secrets: bool
    response_headers: bool
    httpx_logs: bool
    snippet_lang: str


SnippetWriter = Callable[
    [List[tuple[Case, Dict[str, str]]], str, str, Dict[str, Any], Any],
    None,
]


def render_key_value_block(title: str, rows: List[Tuple[str, Any]]) -> str:
    header = title if title.startswith("[") else f"[{title}]"
    lines = [header]
    for key, value in rows:
        value_text = str(value).replace("\r", " ").replace("\n", " ").strip()
        lines.append(f"{key}: {value_text}")
    return "\n".join(lines)


def _display_value(value: Any, fallback: str = "(none)") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _mask_url_userinfo(value: str | None, *, reveal_secrets: bool) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or reveal_secrets:
        return text
    try:
        parts = urlsplit(text)
        if parts.netloc and "@" in parts.netloc:
            _, host_part = parts.netloc.rsplit("@", 1)
            return urlunsplit(
                (parts.scheme, f"***@{host_part}", parts.path, parts.query, parts.fragment)
            )
    except Exception:
        pass
    if "://" in text and "@" in text:
        scheme, rest = text.split("://", 1)
        _, tail = rest.rsplit("@", 1)
        return f"{scheme}://***@{tail}"
    return text


def _output_mode_text(output_plan: RunOutputPlan) -> str:
    if output_plan.temporary_single_file:
        return "temporary single-file"
    if output_plan.scaffold_root is not None:
        return "project"
    return "standard"


def _project_root_text(output_plan: RunOutputPlan) -> str:
    if output_plan.scaffold_root is not None:
        return str(output_plan.scaffold_root)
    return "(none)"


def _snippet_text(output_plan: RunOutputPlan, snippet_lang: str) -> str:
    if output_plan.generate_snippets and output_plan.snippet_output:
        return f"{output_plan.snippet_output} ({snippet_lang})"
    return "disabled"


def build_run_plan_text(context: RunPlanContext) -> str:
    cli_var_keys = sorted({str(key) for key in context.cli_vars_keys if str(key).strip()})
    case_selector = ", ".join(context.case_selector or []) or "(none)"
    base_url = _mask_url_userinfo(
        context.base_url, reveal_secrets=context.reveal_secrets
    )
    rows: List[Tuple[str, Any]] = [
        ("Target", context.target),
        ("Environment", _display_value(context.environment)),
        ("Env file", _display_value(context.env_file)),
        ("Base URL", _display_value(base_url, "case config / unresolved")),
        ("Files", context.files_count),
        ("Cases", context.cases_count),
        ("Case instances", context.case_instances_count),
        ("Tag filter", _display_value(context.tag_filter)),
        ("Case selector", case_selector),
        ("Failfast", _bool_text(context.failfast)),
        ("CLI vars", ", ".join(cli_var_keys) if cli_var_keys else "(none)"),
        ("Output mode", _output_mode_text(context.output_plan)),
        ("Project root", _project_root_text(context.output_plan)),
        ("Log file", context.output_plan.log_path),
        ("HTML report", context.output_plan.html_path or "disabled"),
        ("JSON report", context.json_report or "disabled"),
        ("Allure results", context.allure_results or "disabled"),
        ("Snippets", _snippet_text(context.output_plan, context.snippet_lang)),
        ("Log level", context.log_level),
        ("Secrets mode", "plain" if context.reveal_secrets else "mask"),
        ("Response headers", _bool_text(context.response_headers)),
        ("HTTPX logs", _bool_text(context.httpx_logs)),
    ]
    return render_key_value_block("RUN PLAN", rows)


def build_artifacts_text(
    *,
    output_plan: RunOutputPlan,
    json_report: str | None,
    allure_results: str | None,
    snippet_lang: str,
) -> str:
    rows: List[Tuple[str, Any]] = [
        ("HTML report", output_plan.html_path or "disabled"),
        ("JSON report", json_report or "disabled"),
        ("Allure results", allure_results or "disabled"),
        ("Log file", output_plan.log_path),
        ("Snippets", _snippet_text(output_plan, snippet_lang)),
    ]
    if output_plan.html_path:
        rows.append(("Open reports", "drun s"))
    return render_key_value_block("ARTIFACTS", rows)


def sanitize_filename_component(value: str, fallback: str) -> str:
    value = (value or "").strip()
    if not value:
        return fallback
    normalized = unicodedata.normalize("NFKC", value)
    invalid_chars = {"<", ">", ":", '"', "/", "\\", "|", "?", "*"}
    cleaned_chars = []
    for ch in normalized:
        if ord(ch) < 32:
            cleaned_chars.append("-")
            continue
        if ch in invalid_chars:
            cleaned_chars.append("-")
            continue
        cleaned_chars.append(ch)
    candidate = "".join(cleaned_chars)
    candidate = re.sub(r"\s+", "-", candidate)
    candidate = re.sub(r"-{2,}", "-", candidate)
    candidate = candidate.strip(" .-")
    return candidate or fallback


def sanitize_name(name: str) -> str:
    name = name.lower()
    name = name.replace(" ", "_")
    name = name.replace("/", "_")
    name = name.replace("-", "_")
    name = re.sub(r"[^\w_]", "", name)
    return name


def format_duration_seconds(duration_ms: float) -> str:
    return f"{(duration_ms or 0.0) / 1000.0:.2f}s"


def format_rate(passed: int, total: int) -> str:
    if total <= 0:
        return "0.00%"
    return f"{(passed / total) * 100.0:.2f}%"


def normalize_summary_rows(report: RunReport) -> List[Tuple[str, str]]:
    s = report.summary or {}
    rows: List[Tuple[str, str]] = [
        ("Duration", format_duration_seconds(float(s.get("duration_ms", 0.0) or 0.0)))
    ]

    total = int(s.get("total", 0) or 0)
    passed = int(s.get("passed", 0) or 0)
    failed = int(s.get("failed", 0) or 0)
    skipped = int(s.get("skipped", 0) or 0)
    rows.extend(
        [
            ("Cases Total", str(total)),
            ("Cases Passed", str(passed)),
            ("Cases Failed", str(failed)),
            ("Cases Skipped", str(skipped)),
            ("Cases Pass Rate", format_rate(passed, total)),
        ]
    )

    steps_total = int(s.get("steps_total", 0) or 0)
    steps_passed = int(s.get("steps_passed", 0) or 0)
    steps_failed = int(s.get("steps_failed", 0) or 0)
    steps_skipped = int(s.get("steps_skipped", 0) or 0)
    rows.extend(
        [
            ("Steps Total", str(steps_total)),
            ("Steps Passed", str(steps_passed)),
            ("Steps Failed", str(steps_failed)),
            ("Steps Skipped", str(steps_skipped)),
            ("Steps Pass Rate", format_rate(steps_passed, steps_total)),
        ]
    )
    return rows


def render_ascii_table(rows: List[Tuple[str, str]]) -> str:
    if not rows:
        return ""

    header_key = "Key"
    header_value = "Value"
    key_width = max(len(header_key), max(len(key) for key, _ in rows)) + 2
    value_width = max(len(header_value), max(len(value) for _, value in rows)) + 2

    def border(fill: str) -> str:
        return f"+{fill * key_width}+{fill * value_width}+"

    lines = [
        border("-"),
        f"| {header_key:<{key_width - 2}} | {header_value:>{value_width - 2}} |",
        border("="),
    ]
    for key, value in rows:
        lines.append(f"| {key:<{key_width - 2}} | {value:>{value_width - 2}} |")
        lines.append(border("-"))
    return "\n".join(lines)


def summarize_failure_reason(step) -> str:
    error = getattr(step, "error", None)
    if error:
        return str(error).replace("\n", " ").strip()

    for check in getattr(step, "checks", []) or []:
        if not getattr(check, "passed", True):
            msg = getattr(check, "message", None) or "check failed"
            return str(msg).replace("\n", " ").strip()

    return "(no error message)"


def _build_rerun_command(
    *,
    run_target: str,
    case_name: str,
    env: str | None,
    env_file: str | None,
) -> str:
    target_arg = shlex.quote(f"{run_target}:{case_name}")
    parts = ["drun", "r", target_arg]
    if env_file:
        parts.extend(["-env-file", shlex.quote(env_file)])
    elif env:
        parts.extend(["-env", shlex.quote(env)])
    return " ".join(parts)


def format_failed_cases_block(
    report: RunReport,
    *,
    run_target: str | None = None,
    env: str | None = None,
    env_file: str | None = None,
) -> str:
    failed_cases: List[Tuple[str, List[Tuple[str, str]], bool]] = []
    for case in report.cases:
        if case.status != "failed":
            continue

        failed_steps: List[Tuple[str, str]] = []
        for step in case.steps or []:
            if step.status != "failed":
                continue
            failed_step_name = step.name or "(unknown step)"
            failed_steps.append((failed_step_name, summarize_failure_reason(step)))

        if not failed_steps:
            failed_steps.append(("(unknown step)", "(no error message)"))

        failed_cases.append(
            (case.name or "Unnamed", failed_steps, bool(case.parameters))
        )

    if not failed_cases:
        return ""

    case_indent = ""
    detail_indent = " " * 2
    lines = ["[FAILED CASES]"]
    for idx, (case_name, failed_steps, has_parameters) in enumerate(failed_cases):
        lines.append(f"{case_indent}- {case_name}")
        for step_name, reason in failed_steps:
            lines.append(f"{detail_indent}failed_step: {step_name}")
            lines.append(f"{detail_indent}reason: {reason}")
        if run_target:
            if "," in case_name or ":" in case_name:
                lines.append(
                    f"{detail_indent}note: rerun hint unavailable because Case name "
                    "contains ',' or ':'"
                )
            else:
                rerun = _build_rerun_command(
                    run_target=run_target,
                    case_name=case_name,
                    env=env,
                    env_file=env_file,
                )
                lines.append(f"{detail_indent}rerun: {rerun}")
        if has_parameters:
            lines.append(
                f"{detail_indent}note: rerun executes all parameter sets for this Case"
            )
        if idx < len(failed_cases) - 1:
            lines.append("")
    return "\n".join(lines)


def build_run_summary_text(report: RunReport) -> str:
    rows = normalize_summary_rows(report)
    table = render_ascii_table(rows)
    return "\n".join(["[SUMMARY]", table]) if table else "[SUMMARY]"


def has_scaffold_markers(root: Path) -> bool:
    has_case_dirs = (root / "tcases").is_dir() or (root / "tsuites").is_dir()
    has_project_files = (root / ".env").exists() or (root / "Dhook.py").exists()
    return has_case_dirs and has_project_files


def find_scaffold_root(start: Path | None) -> Path | None:
    if start is None:
        return None

    current = start.resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if has_scaffold_markers(candidate):
            return candidate
    return None


def resolve_default_output_path(
    root: Path | None, relative_path: str, cwd: Path
) -> str:
    if root is None or root.resolve() == cwd.resolve():
        return relative_path
    return str((root / relative_path).resolve())


def build_run_output_plan(
    path: str,
    discovered_files: List[Path],
    *,
    ts: str,
    system_name: str,
    log_file: Optional[str],
    html: Optional[str],
    snippet_output: Optional[str],
    no_snippet: bool,
    cwd: Path | None = None,
) -> RunOutputPlan:
    current_dir = (cwd or Path.cwd()).resolve()
    raw_path = Path(path)
    is_directory_target = raw_path.exists() and raw_path.is_dir()
    single_file_target = (
        discovered_files[0].resolve()
        if (not is_directory_target and len(discovered_files) == 1)
        else None
    )

    search_start: Path | None = None
    if single_file_target is not None:
        search_start = single_file_target.parent
    elif raw_path.exists():
        search_start = raw_path.resolve()

    scaffold_root = find_scaffold_root(search_start)
    temporary_single_file = single_file_target is not None and scaffold_root is None

    log_component = sanitize_filename_component(system_name, "run")
    html_component = sanitize_filename_component(system_name, "report")
    single_file_component = sanitize_filename_component(
        single_file_target.stem if single_file_target is not None else "",
        "run",
    )

    default_log_path = log_file or (
        f"{single_file_component}-{ts}.log"
        if temporary_single_file
        else resolve_default_output_path(
            scaffold_root, f"logs/{log_component}-{ts}.log", current_dir
        )
    )
    default_html_path = (
        html
        if html is not None
        else (
            None
            if temporary_single_file
            else resolve_default_output_path(
                scaffold_root, f"reports/{html_component}-{ts}.html", current_dir
            )
        )
    )

    resolved_snippet_output = snippet_output
    generate_snippets = False
    if not no_snippet:
        if snippet_output is not None:
            generate_snippets = True
        elif not temporary_single_file:
            generate_snippets = True
            resolved_snippet_output = resolve_default_output_path(
                scaffold_root, f"snippets/{ts}", current_dir
            )

    return RunOutputPlan(
        single_file_target=single_file_target,
        scaffold_root=scaffold_root,
        temporary_single_file=temporary_single_file,
        log_path=default_log_path,
        html_path=default_html_path,
        snippet_output=resolved_snippet_output,
        generate_snippets=generate_snippets,
    )


def save_code_snippets(
    items: List[tuple[Case, Dict[str, str]]],
    output_dir: str,
    languages: str,
    env_store: Dict[str, Any],
    log,
) -> None:
    from drun.exporters.snippet import SnippetGenerator

    generator = SnippetGenerator()
    target_dir = Path(output_dir)

    target_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []
    is_multi_case = len(items) > 1

    for case, meta in items:
        case_name = case.config.name or Path(meta.get("file", "snippet")).stem
        safe_case_name = sanitize_name(case_name)

        for step_idx, step in enumerate(case.steps):
            if step.invoke is not None:
                continue
            if step.sleep is not None:
                log.info("[SNIPPET] Skip sleep step: %s", step.name)
                continue

            step_num = step_idx + 1
            safe_step_name = sanitize_name(step.name)

            if is_multi_case:
                file_prefix = f"step{step_num}_{safe_case_name}_{safe_step_name}"
            else:
                file_prefix = f"step{step_num}_{safe_step_name}"

            langs = ["curl", "python"] if languages == "all" else [languages]

            if "curl" in langs:
                shell_file = target_dir / f"{file_prefix}_curl.sh"
                content = generator.generate_shell_script_for_step(
                    case, step_idx, len(case.steps), env_store
                )
                shell_file.write_text(content, encoding="utf-8")
                shell_file.chmod(0o755)
                saved_files.append(shell_file.name)

            if "python" in langs:
                python_file = target_dir / f"{file_prefix}_python.py"
                content = generator.generate_python_script_for_step(
                    case, step_idx, len(case.steps), env_store
                )
                python_file.write_text(content, encoding="utf-8")
                python_file.chmod(0o755)
                saved_files.append(python_file.name)

    if saved_files:
        log.info("[SNIPPET] Code snippets saved to %s/", target_dir)
        for file in saved_files:
            log.info("[SNIPPET] - %s", file)


def write_report_artifacts(
    report_obj: RunReport,
    *,
    json_path: Optional[str],
    html_path: Optional[str],
    allure_results: Optional[str],
    environment: Optional[str],
    log,
) -> None:
    if json_path:
        write_json(report_obj, json_path)
        log.info("[CASE] JSON report written to %s", json_path)
    if html_path:
        from drun.reporter.html_reporter import write_html

        write_html(report_obj, html_path, environment=environment)
        log.info("[CASE] HTML report written to %s", html_path)

    if allure_results:
        try:
            from drun.reporter.allure_reporter import write_allure_results

            write_allure_results(report_obj, allure_results)
            log.info("[CASE] Allure results written to %s", allure_results)
        except Exception as e:
            log.error("Failed to write Allure results: %s", e)


def write_snippet_artifacts(
    output_plan: RunOutputPlan,
    items: List[tuple[Case, Dict[str, str]]],
    snippet_lang: str,
    env_store: Dict[str, Any],
    log,
    *,
    snippet_writer: SnippetWriter = save_code_snippets,
) -> None:
    if output_plan.generate_snippets and output_plan.snippet_output:
        try:
            snippet_writer(
                items, output_plan.snippet_output, snippet_lang, env_store, log
            )
        except Exception as e:
            log.error("[SNIPPET] Failed to generate code snippets: %s", str(e))


def log_run_summary_outputs(
    report_obj: RunReport,
    *,
    log,
    log_path: str | None = None,
    run_target: str | None = None,
    env: str | None = None,
    env_file: str | None = None,
    artifacts_text: str | None = None,
) -> None:
    summary_text = build_run_summary_text(report_obj)
    log.warning(summary_text)

    failed_cases_text = format_failed_cases_block(
        report_obj,
        run_target=run_target,
        env=env,
        env_file=env_file,
    )
    if failed_cases_text:
        log.error(failed_cases_text)

    if artifacts_text:
        log.warning(artifacts_text)

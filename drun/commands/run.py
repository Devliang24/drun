from __future__ import annotations

from dataclasses import dataclass
import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import typer

from drun.loader.collector import discover, match_tags
from drun.loader.env import load_environment
from drun.loader.hooks import get_functions_for
from drun.loader.yaml_loader import (
    expand_parameters,
    format_variables_multiline,
    load_yaml_file,
)
from drun.models.case import Case
from drun.models.report import NotifyResult, RunReport
from drun.reporter.json_reporter import write_json
from drun.runner.runner import Runner
from drun.templating.engine import TemplateEngine
from drun.utils.config import get_env_clean, get_system_name
from drun.utils.errors import LoadError
from drun.utils.logging import get_logger, setup_logging


def _sanitize_filename_component(value: str, fallback: str) -> str:
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


def _iter_unique_env_items(env: Dict[str, Any]) -> Iterator[Tuple[str, Any]]:
    seen: set[str] = set()
    for key, value in env.items():
        lowered = key.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        yield key, value


def _parse_kv(items: List[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for it in items:
        if "=" not in it:
            continue
        k, v = it.split("=", 1)
        out[k] = v
    return out


def _parse_run_target_with_case_selector(path: str) -> Tuple[str, List[str] | None]:
    run_target = (path or "").strip()
    if not run_target:
        raise ValueError("Run path cannot be empty.")

    if ":" not in run_target:
        return run_target, None

    target_path, selector_raw = run_target.rsplit(":", 1)
    target_path = target_path.strip()
    selector_raw = selector_raw.strip()
    if not target_path:
        raise ValueError("Invalid run target: missing file path before ':'.")
    if not selector_raw:
        raise ValueError(
            "Invalid case selector: provide at least one case name after ':'."
        )

    selected_case_names: List[str] = []
    seen_names: set[str] = set()
    for raw_name in selector_raw.split(","):
        case_name = raw_name.strip()
        if not case_name:
            raise ValueError(
                "Invalid case selector: case names must be non-empty and comma-separated."
            )
        if case_name in seen_names:
            continue
        seen_names.add(case_name)
        selected_case_names.append(case_name)

    if not selected_case_names:
        raise ValueError(
            "Invalid case selector: provide at least one non-empty case name."
        )
    return target_path, selected_case_names


def _sanitize_name(name: str) -> str:
    name = name.lower()
    name = name.replace(" ", "_")
    name = name.replace("/", "_")
    name = name.replace("-", "_")
    name = re.sub(r"[^\w_]", "", name)
    return name


@dataclass(frozen=True)
class RunOutputPlan:
    single_file_target: Path | None
    scaffold_root: Path | None
    temporary_single_file: bool
    log_path: str
    html_path: str | None
    snippet_output: str | None
    generate_snippets: bool


def _format_duration_seconds(duration_ms: float) -> str:
    return f"{(duration_ms or 0.0) / 1000.0:.2f}s"


def _format_rate(passed: int, total: int) -> str:
    if total <= 0:
        return "0.00%"
    return f"{(passed / total) * 100.0:.2f}%"


def _normalize_summary_rows(report: RunReport) -> List[Tuple[str, str]]:
    s = report.summary or {}
    rows: List[Tuple[str, str]] = [
        ("Duration", _format_duration_seconds(float(s.get("duration_ms", 0.0) or 0.0)))
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
            ("Cases Pass Rate", _format_rate(passed, total)),
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
            ("Steps Pass Rate", _format_rate(steps_passed, steps_total)),
        ]
    )
    return rows


def _render_ascii_table(rows: List[Tuple[str, str]]) -> str:
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
    for idx, (key, value) in enumerate(rows):
        lines.append(f"| {key:<{key_width - 2}} | {value:>{value_width - 2}} |")
        lines.append(border("-"))
    return "\n".join(lines)


def _summarize_failure_reason(step) -> str:
    error = getattr(step, "error", None)
    if error:
        return str(error).replace("\n", " ").strip()

    for assertion in getattr(step, "asserts", []) or []:
        if not getattr(assertion, "passed", True):
            msg = getattr(assertion, "message", None) or "assertion failed"
            return str(msg).replace("\n", " ").strip()

    return "(no error message)"


def _format_failed_cases_block(report: RunReport) -> str:
    failed_cases: List[Tuple[str, List[Tuple[str, str]]]] = []
    for case in report.cases:
        if case.status != "failed":
            continue

        failed_steps: List[Tuple[str, str]] = []
        for step in case.steps or []:
            if step.status != "failed":
                continue
            failed_step_name = step.name or "(unknown step)"
            failed_steps.append((failed_step_name, _summarize_failure_reason(step)))

        if not failed_steps:
            failed_steps.append(("(unknown step)", "(no error message)"))

        failed_cases.append((case.name or "Unnamed", failed_steps))

    if not failed_cases:
        return ""

    case_indent = ""
    detail_indent = " " * 2
    lines = ["[FAILED CASES]"]
    for idx, (case_name, failed_steps) in enumerate(failed_cases):
        lines.append(f"{case_indent}- {case_name}")
        for step_name, reason in failed_steps:
            lines.append(f"{detail_indent}failed_step: {step_name}")
            lines.append(f"{detail_indent}reason: {reason}")
        if idx < len(failed_cases) - 1:
            lines.append("")
    return "\n".join(lines)


def _build_run_summary_text(report: RunReport) -> str:
    rows = _normalize_summary_rows(report)
    table = _render_ascii_table(rows)
    return "\n".join(["[SUMMARY]", table]) if table else "[SUMMARY]"


def _has_scaffold_markers(root: Path) -> bool:
    has_case_dirs = (root / "testcases").is_dir() or (root / "testsuites").is_dir()
    has_project_files = (root / ".env").exists() or (root / "Dhook.py").exists()
    return has_case_dirs and has_project_files


def _find_scaffold_root(start: Path | None) -> Path | None:
    if start is None:
        return None

    current = start.resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if _has_scaffold_markers(candidate):
            return candidate
    return None


def _resolve_default_output_path(
    root: Path | None, relative_path: str, cwd: Path
) -> str:
    if root is None or root.resolve() == cwd.resolve():
        return relative_path
    return str((root / relative_path).resolve())


def _build_run_output_plan(
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

    scaffold_root = _find_scaffold_root(search_start)
    temporary_single_file = single_file_target is not None and scaffold_root is None

    log_component = _sanitize_filename_component(system_name, "run")
    html_component = _sanitize_filename_component(system_name, "report")
    single_file_component = _sanitize_filename_component(
        single_file_target.stem if single_file_target is not None else "",
        "run",
    )

    default_log_path = log_file or (
        f"{single_file_component}-{ts}.log"
        if temporary_single_file
        else _resolve_default_output_path(
            scaffold_root, f"logs/{log_component}-{ts}.log", current_dir
        )
    )
    default_html_path = (
        html
        if html is not None
        else (
            None
            if temporary_single_file
            else _resolve_default_output_path(
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
            resolved_snippet_output = _resolve_default_output_path(
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


def _save_code_snippets(
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
        safe_case_name = _sanitize_name(case_name)

        for step_idx, step in enumerate(case.steps):
            if step.invoke is not None:
                continue
            if step.sleep is not None:
                log.info("[SNIPPET] Skip sleep step: %s", step.name)
                continue

            step_num = step_idx + 1
            safe_step_name = _sanitize_name(step.name)

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


def _resolve_runtime_env_file(
    env: Optional[str], env_file: Optional[str]
) -> Optional[Path]:
    cwd = Path.cwd()

    explicit_env_file: Optional[Path] = None
    if env_file:
        explicit_env_file = Path(env_file).expanduser()
        if not explicit_env_file.is_absolute():
            explicit_env_file = cwd / explicit_env_file
        explicit_env_file = explicit_env_file.resolve()
        if not explicit_env_file.exists():
            typer.echo(f"[ERROR] Environment file not found: {explicit_env_file}")
            typer.echo()
            typer.echo("Hint: Check if -env-file path is correct")
            raise typer.Exit(code=2)

    named_env_file: Optional[Path] = None
    if env:
        candidate = cwd / f".env.{env}"
        if candidate.exists():
            named_env_file = candidate.resolve()

    default_env_file = (cwd / ".env").resolve() if (cwd / ".env").exists() else None

    if explicit_env_file is not None:
        return explicit_env_file
    if named_env_file is not None:
        return named_env_file
    if default_env_file is not None:
        return default_env_file
    return None


def run_cases(
    path: str,
    k: Optional[str],
    vars: List[str],
    failfast: bool,
    report: Optional[str],
    html: Optional[str],
    allure_results: Optional[str],
    log_level: str,
    env: Optional[str],
    env_file: Optional[str],
    persist_env: Optional[str],
    log_file: Optional[str],
    httpx_logs: bool,
    reveal_secrets: bool,
    response_headers: bool,
    notify: Optional[str],
    notify_only: Optional[str],
    notify_attach_html: bool,
    no_snippet: bool,
    snippet_output: Optional[str],
    snippet_lang: str,
) -> None:
    input_path = path
    try:
        path, selected_case_names = _parse_run_target_with_case_selector(path)
    except ValueError as exc:
        typer.echo(f"[ERROR] {exc}")
        raise typer.Exit(code=2)

    runtime_env_file = _resolve_runtime_env_file(env, env_file)
    if env is None and runtime_env_file is None:
        typer.echo(
            "[ERROR] Environment not found. Use -env, -env-file, or provide .env in current directory."
        )
        typer.echo()
        typer.echo("Usage:")
        typer.echo("  drun run <path> -env <env_name>")
        typer.echo("  drun run <path> -env-file /path/to/.env")
        typer.echo("  drun run <path>   # auto-loads .env when present")
        typer.echo()
        typer.echo("Environment file naming:")
        typer.echo("  .env.dev    -> -env dev")
        typer.echo("  .env.uat    -> -env uat")
        typer.echo("  .env.prod   -> -env prod")
        typer.echo("  .env        -> default (single-file mode)")
        typer.echo()
        typer.echo("Examples:")
        typer.echo("  drun run demo -env dev")
        typer.echo("  drun run demo -env-file ./demo.env")
        typer.echo("  drun run test_smoke.yaml")
        typer.echo("  drun run testcases -env uat")
        typer.echo("  drun run testsuites -env prod")
        raise typer.Exit(code=2)

    ts = time.strftime("%Y%m%d-%H%M%S")
    setup_logging(log_level, log_file=None)
    log = get_logger("drun.commands.run")
    import logging as _logging

    _httpx_logger = _logging.getLogger("httpx")
    _httpx_logger.setLevel(_logging.INFO if httpx_logs else _logging.WARNING)

    env_label = env or "default"
    env_file_label = (
        str(runtime_env_file) if runtime_env_file is not None else "(OS env only)"
    )
    env_store = load_environment(
        env, str(runtime_env_file) if runtime_env_file is not None else None
    )
    for env_key, env_val in env_store.items():
        if env_key and isinstance(env_val, str) and env_key.upper() == env_key:
            os.environ.setdefault(env_key, env_val)
    cli_vars = _parse_kv(vars)
    global_vars: Dict[str, str] = {}
    for k2, v2 in cli_vars.items():
        global_vars[k2] = v2
        global_vars[k2.lower()] = v2

    files = discover([path])
    if not files:
        typer.echo(f"No YAML test files found at: {path}")
        pth = Path(path)
        hints: list[str] = []
        if not pth.exists():
            hints.append(
                "Path does not exist. Create it or use an existing directory/file."
            )
            if not pth.suffix:
                for ext in (".yaml", ".yml"):
                    cand = pth.with_suffix(ext)
                    if cand.exists():
                        hints.append(f"Did you mean: drun run {cand}")
                        break
        else:
            if pth.is_file():
                if pth.suffix.lower() not in {".yaml", ".yml"}:
                    hints.append("Only .yaml/.yml files are recognized.")
                    for ext in (".yaml", ".yml"):
                        cand = pth.with_suffix(ext)
                        if cand.exists():
                            hints.append(f"Try: drun run {cand}")
                            break
            elif pth.is_dir():
                hints.append(
                    "Provide a YAML file or a directory containing YAML tests under testcases/ or testsuites/."
                )
        hints.append("Examples:")
        hints.append("  drun run testcases")
        hints.append("  drun run testcases/test_hello.yaml")
        hints.append("  drun run testsuites/testsuite_smoke.yaml")
        for h in hints:
            typer.echo(h)
        raise typer.Exit(code=2)

    system_name = get_system_name()
    output_plan = _build_run_output_plan(
        path,
        files,
        ts=ts,
        system_name=system_name,
        log_file=log_file,
        html=html,
        snippet_output=snippet_output,
        no_snippet=no_snippet,
    )
    default_log = output_plan.log_path

    setup_logging(log_level, log_file=default_log)
    log = get_logger("drun.commands.run")
    _httpx_logger = _logging.getLogger("httpx")
    _httpx_logger.setLevel(_logging.INFO if httpx_logs else _logging.WARNING)
    log.info("[ENV] Using environment: %s -> %s", env_label, env_file_label)

    if output_plan.temporary_single_file:
        log.info("[OUTPUT] Temporary single-file mode enabled")
    elif output_plan.scaffold_root is not None:
        log.info("[OUTPUT] Project mode enabled (root=%s)", output_plan.scaffold_root)
    else:
        log.info("[OUTPUT] Standard mode enabled")
    log.info("[OUTPUT] Log file: %s", default_log)
    if output_plan.html_path:
        log.info("[OUTPUT] HTML report: %s", output_plan.html_path)
    else:
        log.info("[OUTPUT] HTML report: disabled by default")
    if output_plan.generate_snippets and output_plan.snippet_output:
        log.info("[OUTPUT] Snippets: %s", output_plan.snippet_output)
    else:
        log.info("[OUTPUT] Snippets: disabled by default")

    _base_any = os.environ.get("BASE_URL") or os.environ.get("base_url") or None
    if not _base_any:
        _base_any = env_store.get("BASE_URL") or env_store.get("base_url")
    if not _base_any:
        log.warning(
            "[ENV] BASE_URL not found in %s. Relative URLs may fail. Add BASE_URL to %s.",
            env_file_label,
            env_file_label,
        )
    log.info("[FILTER] expression: %r", k)
    if selected_case_names:
        log.info(
            "[FILTER] case names (path selector): %s",
            ", ".join(selected_case_names),
        )

    items: List[tuple[Case, Dict[str, str]]] = []
    debug_info: List[str] = []
    selected_name_set = set(selected_case_names or [])
    selected_hits: Dict[str, int] = {name: 0 for name in selected_case_names or []}
    available_case_names: List[str] = []
    for f in files:
        try:
            loaded, meta = load_yaml_file(f)
        except LoadError as exc:
            log.error(str(exc))
            raise typer.Exit(code=2)
        debug_info.append(f"file={f} cases={len(loaded)}")
        for c in loaded:
            case_name = c.config.name or "Unnamed Case"
            available_case_names.append(case_name)
            if selected_case_names:
                if case_name not in selected_name_set:
                    continue
                selected_hits[case_name] = selected_hits.get(case_name, 0) + 1

            tags = c.config.tags or []
            m = match_tags(tags, k)
            debug_info.append(f"  case={case_name!r} tags={tags} match={m}")
            if m:
                items.append((c, meta))

    if selected_case_names:
        missing_case_names = [
            name for name in selected_case_names if selected_hits.get(name, 0) <= 0
        ]
        if missing_case_names:
            requested_display = ", ".join(selected_case_names)
            available_display = (
                ", ".join(available_case_names) if available_case_names else "(none)"
            )
            error_message = (
                "No matched case names for run target "
                f"'{path}': requested=[{requested_display}] available=[{available_display}]"
            )
            log.error("[FILTER] %s", error_message)
            typer.echo(f"[ERROR] {error_message}")
            raise typer.Exit(code=2)

        duplicate_names = [name for name, count in selected_hits.items() if count > 1]
        if duplicate_names:
            log.warning(
                "[FILTER] Duplicate case names matched and all will run: %s",
                ", ".join(duplicate_names),
            )

    if not items:
        typer.echo("No cases matched tag expression.")
        for line in debug_info:
            typer.echo(line)
        raise typer.Exit(code=2)

    persist_file = (
        persist_env
        or env_file
        or (str(runtime_env_file) if runtime_env_file is not None else ".env")
    )

    runner = Runner(
        log=log,
        failfast=failfast,
        log_debug=(log_level.upper() == "DEBUG"),
        reveal_secrets=reveal_secrets,
        log_response_headers=response_headers,
        persist_env_file=persist_file,
    )
    templater = TemplateEngine()
    instance_results = []
    log.info(
        "[RUN] Discovered files: %s | Matched cases: %s | Failfast=%s",
        len(files),
        len(items),
        failfast,
    )

    def _need_base_url(case: Case) -> bool:
        try:
            for st in case.steps:
                if st.invoke:
                    continue
                if not st.request:
                    continue
                step_path = getattr(st.request, "path", "") or ""
                u = str(step_path).strip()
                if u and not (u.startswith("http://") or u.startswith("https://")):
                    return True
            return False
        except Exception:
            return False

    for c, meta in items:
        funcs = get_functions_for(Path(meta.get("file", path)).resolve())
        param_sets = expand_parameters(c.parameters, source_path=meta.get("file"))
        for ps in param_sets:
            if (not c.config.base_url) and (
                base := global_vars.get("BASE_URL")
                or global_vars.get("base_url")
                or env_store.get("BASE_URL")
                or env_store.get("base_url")
            ):
                c.config.base_url = base
            if c.config.base_url and (
                "{{" in c.config.base_url or "${" in c.config.base_url
            ):
                c.config.base_url = templater.render_value(
                    c.config.base_url, global_vars, funcs, envmap=env_store
                )
            if _need_base_url(c) and not (
                c.config.base_url and str(c.config.base_url).strip()
            ):
                env_hint_lines = []
                if runtime_env_file is not None:
                    env_hint_lines = [
                        f"          - Add to env file: {env_file_label}",
                        "              BASE_URL=http://localhost:8000",
                    ]
                msg_lines = [
                    "[ERROR] base_url is required for cases using relative URLs.",
                    f"        Case: {c.config.name or 'Unnamed'} | Source: {meta.get('file', input_path)}",
                    "        Provide base_url in one of the following ways:",
                    *env_hint_lines,
                    "          - Or pass CLI vars: -vars base_url=http://localhost:8000",
                    "          - Or export env:   export BASE_URL=http://localhost:8000",
                ]
                for line in msg_lines:
                    typer.echo(line)
                raise typer.Exit(code=2)
            log.info("[CASE] Start: %s | params=%s", c.config.name or "Unnamed", ps)

            if env_store:
                for key, value in _iter_unique_env_items(env_store):
                    log.info("[ENV] %s = %r", key, value)

            if c.config.base_url:
                log.info("[CONFIG] base_url: %s", c.config.base_url)

            if c.config.variables:
                vars_str = format_variables_multiline(
                    c.config.variables, "[CONFIG] variables: "
                )
                log.info(vars_str)

            res = runner.run_case(
                c,
                global_vars=global_vars,
                params=ps,
                funcs=funcs,
                envmap=env_store,
                source=meta.get("file"),
            )
            log.info(
                "[CASE] Result: %s | status=%s | duration=%.1fms",
                res.name,
                res.status,
                res.duration_ms,
            )
            instance_results.append(res)
            if failfast and res.status == "failed":
                break

    report_obj: RunReport = runner.build_report(instance_results)
    s = report_obj.summary
    log.info(
        "[CASE] Total: %s Passed: %s Failed: %s Skipped: %s",
        s["total"],
        s.get("passed", 0),
        s.get("failed", 0),
        s.get("skipped", 0),
    )
    if "steps_total" in s:
        log.info(
            "[STEP] Total: %s Passed: %s Failed: %s Skipped: %s",
            s.get("steps_total", 0),
            s.get("steps_passed", 0),
            s.get("steps_failed", 0),
            s.get("steps_skipped", 0),
        )

    html_target = output_plan.html_path

    if report:
        write_json(report_obj, report)
        log.info("[CASE] JSON report written to %s", report)
    if html_target:
        from drun.reporter.html_reporter import write_html

        write_html(report_obj, html_target, environment=env)
        log.info("[CASE] HTML report written to %s", html_target)

    if allure_results:
        try:
            from drun.reporter.allure_reporter import write_allure_results

            write_allure_results(report_obj, allure_results)
            log.info("[CASE] Allure results written to %s", allure_results)
        except Exception as e:
            log = get_logger("drun.commands.run")
            log.error("Failed to write Allure results: %s", e)

    try:
        from drun.notifier import (
            DingTalkNotifier,
            EmailNotifier,
            FeishuNotifier,
            NotifyContext,
        )

        env_channels = get_env_clean("DRUN_NOTIFY") or ""
        channels_spec = notify.strip() if (notify and notify.strip()) else env_channels
        channels = [c.strip().lower() for c in channels_spec.split(",") if c.strip()]

        feishu_webhook = get_env_clean("FEISHU_WEBHOOK")
        dingtalk_webhook = get_env_clean("DINGTALK_WEBHOOK")
        smtp_host_env = get_env_clean("SMTP_HOST")
        mail_to_env = get_env_clean("MAIL_TO")

        if not channels:
            auto_channels: List[str] = []
            if feishu_webhook:
                auto_channels.append("feishu")
            if dingtalk_webhook:
                auto_channels.append("dingtalk")
            if smtp_host_env or mail_to_env:
                auto_channels.append("email")
            if auto_channels:
                log.info(
                    "[NOTIFY] Auto-enabling channels from environment: %s",
                    ", ".join(auto_channels),
                )
            channels = auto_channels
        seen = set()
        channels = [c for c in channels if not (c in seen or seen.add(c))]
        policy_source = (
            notify_only.strip()
            if (notify_only and notify_only.strip())
            else get_env_clean("DRUN_NOTIFY_ONLY", "failed")
        )
        policy = (policy_source or "failed").lower()
        topn_raw = get_env_clean("NOTIFY_TOPN", "5") or "5"
        topn = int(topn_raw)

        log.info("[NOTIFY] channels=%s policy=%s", channels, policy)

        should_send = (policy == "always") or (
            policy == "failed" and (s.get("failed", 0) or 0) > 0
        )
        log.info(
            "[NOTIFY] should_send=%s (failed_count=%s)", should_send, s.get("failed", 0)
        )

        if channels and should_send:
            log.info(
                "[NOTIFY] Preparing to send notifications to: %s", ", ".join(channels)
            )
            if notify_attach_html and not html_target:
                log.info(
                    "[NOTIFY] HTML attachment requested but no HTML report path is configured; pass -html to attach a report"
                )
            ctx = NotifyContext(
                html_path=html_target,
                log_path=default_log,
                notify_only=policy,
                topn=topn,
            )
            notifiers = []

            if "feishu" in channels:
                fw = feishu_webhook or ""
                if fw:
                    fs = get_env_clean("FEISHU_SECRET")
                    fm = get_env_clean("FEISHU_MENTION")
                    style = (get_env_clean("FEISHU_STYLE", "text") or "text").lower()
                    notifiers.append(
                        FeishuNotifier(webhook=fw, secret=fs, mentions=fm, style=style)
                    )
                    log.info("[NOTIFY] Feishu notifier created (style=%s)", style)
                else:
                    log.warning(
                        "[NOTIFY] Feishu channel requested but FEISHU_WEBHOOK not configured"
                    )

            if "email" in channels:
                host = smtp_host_env or ""
                if host:
                    notifiers.append(
                        EmailNotifier(
                            smtp_host=host,
                            smtp_port=int(get_env_clean("SMTP_PORT", "465") or 465),
                            smtp_user=get_env_clean("SMTP_USER"),
                            smtp_pass=get_env_clean("SMTP_PASS"),
                            mail_from=get_env_clean("MAIL_FROM"),
                            mail_to=mail_to_env,
                            use_ssl=(
                                (get_env_clean("SMTP_SSL", "true") or "true").lower()
                                != "false"
                            ),
                            attach_html=bool(
                                notify_attach_html
                                or (
                                    (get_env_clean("NOTIFY_ATTACH_HTML") or "").lower()
                                    in {"1", "true", "yes"}
                                )
                            ),
                            html_body=(
                                (
                                    get_env_clean("NOTIFY_HTML_BODY", "true") or "true"
                                ).lower()
                                != "false"
                            ),
                        )
                    )

            if "dingtalk" in channels:
                dw = dingtalk_webhook or ""
                if dw:
                    ds = get_env_clean("DINGTALK_SECRET")
                    mobiles = get_env_clean("DINGTALK_AT_MOBILES") or ""
                    at_mobiles = [m.strip() for m in mobiles.split(",") if m.strip()]
                    at_all = (get_env_clean("DINGTALK_AT_ALL") or "").lower() in {
                        "1",
                        "true",
                        "yes",
                    }
                    style = (get_env_clean("DINGTALK_STYLE", "text") or "text").lower()
                    notifiers.append(
                        DingTalkNotifier(
                            webhook=dw,
                            secret=ds,
                            at_mobiles=at_mobiles,
                            at_all=at_all,
                            style=style,
                        )
                    )

            log.info(
                "[NOTIFY] Sending notifications via %d notifier(s)", len(notifiers)
            )

            notifier_channel_map = {
                "FeishuNotifier": "feishu",
                "EmailNotifier": "email",
                "DingTalkNotifier": "dingtalk",
            }

            active_channels = [
                notifier_channel_map.get(
                    n.__class__.__name__, n.__class__.__name__.lower()
                )
                for n in notifiers
            ]
            for case in report_obj.cases:
                case.notify_channels = active_channels.copy()

            notify_results: List[NotifyResult] = []
            for n in notifiers:
                notifier_name = n.__class__.__name__
                channel = notifier_channel_map.get(notifier_name, notifier_name.lower())
                try:
                    log.info("[NOTIFY] Sending via %s...", notifier_name)
                    n.send(report_obj, ctx)
                    log.info(
                        "[NOTIFY] %s notification sent successfully", notifier_name
                    )
                    notify_results.append(
                        NotifyResult(channel=channel, status="success")
                    )
                except Exception as e:
                    log.error(
                        "[NOTIFY] Failed to send via %s: %s", notifier_name, str(e)
                    )
                    notify_results.append(
                        NotifyResult(channel=channel, status="failed")
                    )

            for case in report_obj.cases:
                case.notify_results = notify_results.copy()

            if html_target:
                from drun.reporter.html_reporter import write_html

                write_html(report_obj, html_target)
                log.info("[NOTIFY] HTML report updated with notification status")
    except Exception as e:
        log.error("[NOTIFY] Notification module error: %s", str(e))

    if output_plan.generate_snippets and output_plan.snippet_output:
        try:
            _save_code_snippets(
                items, output_plan.snippet_output, snippet_lang, env_store, log
            )
        except Exception as e:
            log.error("[SNIPPET] Failed to generate code snippets: %s", str(e))

    log.info("[CASE] Logs written to %s", default_log)
    summary_text = _build_run_summary_text(report_obj)
    log.warning(summary_text)

    failed_cases_text = _format_failed_cases_block(report_obj)
    if failed_cases_text:
        log.error(failed_cases_text)

    if s.get("failed", 0) > 0:
        raise typer.Exit(code=1)

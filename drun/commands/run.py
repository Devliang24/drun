from __future__ import annotations

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
from drun.loader.yaml_loader import expand_parameters, format_variables_multiline, load_yaml_file
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
    invalid_chars = {'<', '>', ':', '"', '/', '\\', '|', '?', '*'}
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


def _sanitize_name(name: str) -> str:
    name = name.lower()
    name = name.replace(" ", "_")
    name = name.replace("/", "_")
    name = name.replace("-", "_")
    name = re.sub(r"[^\w_]", "", name)
    return name


def _save_code_snippets(
    items: List[tuple[Case, Dict[str, str]]],
    output_dir: Optional[str],
    languages: str,
    env_store: Dict[str, Any],
    timestamp: str,
    log,
) -> None:
    from drun.exporters.snippet import SnippetGenerator

    generator = SnippetGenerator()

    if output_dir:
        target_dir = Path(output_dir)
    else:
        target_dir = Path("snippets") / timestamp

    target_dir.mkdir(parents=True, exist_ok=True)

    saved_files = []
    is_multi_case = len(items) > 1

    for case, meta in items:
        case_name = case.config.name or Path(meta.get("file", "snippet")).stem
        safe_case_name = _sanitize_name(case_name)

        for step_idx, step in enumerate(case.steps):
            if step.invoke is not None:
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
                content = generator.generate_shell_script_for_step(case, step_idx, len(case.steps), env_store)
                shell_file.write_text(content, encoding="utf-8")
                shell_file.chmod(0o755)
                saved_files.append(shell_file.name)

            if "python" in langs:
                python_file = target_dir / f"{file_prefix}_python.py"
                content = generator.generate_python_script_for_step(case, step_idx, len(case.steps), env_store)
                python_file.write_text(content, encoding="utf-8")
                python_file.chmod(0o755)
                saved_files.append(python_file.name)

    if saved_files:
        log.info("[SNIPPET] Code snippets saved to %s/", target_dir)
        for file in saved_files:
            log.info("[SNIPPET] - %s", file)


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
    if env is None:
        typer.echo("[ERROR] 未指定环境，请使用 --env 参数")
        typer.echo()
        typer.echo("使用方式:")
        typer.echo("  drun run <path> --env <环境名>")
        typer.echo()
        typer.echo("环境文件命名规范:")
        typer.echo("  .env.dev    → --env dev")
        typer.echo("  .env.uat    → --env uat")
        typer.echo("  .env.prod   → --env prod")
        typer.echo()
        typer.echo("示例:")
        typer.echo("  drun run demo --env dev")
        typer.echo("  drun run testcases --env uat")
        typer.echo("  drun run testsuites --env prod")
        raise typer.Exit(code=2)

    env_file = f".env.{env}"
    if not Path(env_file).exists():
        typer.echo(f"[ERROR] 环境文件不存在: {env_file}")
        typer.echo()
        typer.echo("请创建环境文件，例如:")
        typer.echo(f"  touch {env_file}")
        typer.echo()
        typer.echo("或检查环境名称是否正确")
        raise typer.Exit(code=2)

    ts = time.strftime("%Y%m%d-%H%M%S")
    default_log = None
    setup_logging(log_level, log_file=None)
    log = get_logger("drun.commands.run")
    import logging as _logging

    _httpx_logger = _logging.getLogger("httpx")
    _httpx_logger.setLevel(_logging.INFO if httpx_logs else _logging.WARNING)

    log.info("[ENV] Using environment: %s -> %s", env, env_file)

    env_store = load_environment(env, env_file)
    for env_key, env_val in env_store.items():
        if env_key and isinstance(env_val, str) and env_key.upper() == env_key:
            os.environ.setdefault(env_key, env_val)

    system_name = get_system_name()
    log_component = _sanitize_filename_component(system_name, "run")
    default_log = log_file or f"logs/{log_component}-{ts}.log"
    setup_logging(log_level, log_file=default_log)
    log = get_logger("drun.commands.run")
    _base_any = os.environ.get("BASE_URL") or os.environ.get("base_url") or None
    if not _base_any:
        _base_any = env_store.get("BASE_URL") or env_store.get("base_url")
    if not _base_any:
        log.warning(
            "[ENV] BASE_URL not found in %s. Relative URLs may fail. Add BASE_URL to %s.",
            env_file,
            env_file,
        )
    cli_vars = _parse_kv(vars)
    global_vars: Dict[str, str] = {}
    for k2, v2 in cli_vars.items():
        global_vars[k2] = v2
        global_vars[k2.lower()] = v2

    log.info("[FILTER] expression: %r", k)
    files = discover([path])
    if not files:
        typer.echo(f"No YAML test files found at: {path}")
        pth = Path(path)
        hints: list[str] = []
        if not pth.exists():
            hints.append("Path does not exist. Create it or use an existing directory/file.")
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

    items: List[tuple[Case, Dict[str, str]]] = []
    debug_info: List[str] = []
    for f in files:
        try:
            loaded, meta = load_yaml_file(f)
        except LoadError as exc:
            log.error(str(exc))
            raise typer.Exit(code=2)
        debug_info.append(f"file={f} cases={len(loaded)}")
        for c in loaded:
            tags = c.config.tags or []
            m = match_tags(tags, k)
            debug_info.append(f"  case={c.config.name!r} tags={tags} match={m}")
            if m:
                items.append((c, meta))

    if not items:
        typer.echo("No cases matched tag expression.")
        for line in debug_info:
            typer.echo(line)
        raise typer.Exit(code=2)

    persist_file = persist_env or env_file or ".env"

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
    log.info("[RUN] Discovered files: %s | Matched cases: %s | Failfast=%s", len(files), len(items), failfast)

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
            if c.config.base_url and ("{{" in c.config.base_url or "${" in c.config.base_url):
                c.config.base_url = templater.render_value(c.config.base_url, global_vars, funcs, envmap=env_store)
            if _need_base_url(c) and not (c.config.base_url and str(c.config.base_url).strip()):
                msg_lines = [
                    "[ERROR] base_url is required for cases using relative URLs.",
                    f"        Case: {c.config.name or 'Unnamed'} | Source: {meta.get('file', path)}",
                    "        Provide base_url in one of the following ways:",
                    f"          - Add to env file: {env_file}",
                    "              BASE_URL=http://localhost:8000",
                    "          - Or pass CLI vars: --vars base_url=http://localhost:8000",
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
                vars_str = format_variables_multiline(c.config.variables, "[CONFIG] variables: ")
                log.info(vars_str)

            res = runner.run_case(c, global_vars=global_vars, params=ps, funcs=funcs, envmap=env_store, source=meta.get("file"))
            log.info("[CASE] Result: %s | status=%s | duration=%.1fms", res.name, res.status, res.duration_ms)
            instance_results.append(res)
            if failfast and res.status == "failed":
                break

    report_obj: RunReport = runner.build_report(instance_results)
    s = report_obj.summary
    log.info("[CASE] Total: %s Passed: %s Failed: %s Skipped: %s", s["total"], s.get("passed", 0), s.get("failed", 0), s.get("skipped", 0))
    if "steps_total" in s:
        log.info(
            "[STEP] Total: %s Passed: %s Failed: %s Skipped: %s",
            s.get("steps_total", 0),
            s.get("steps_passed", 0),
            s.get("steps_failed", 0),
            s.get("steps_skipped", 0),
        )

    html_component = _sanitize_filename_component(system_name, "report")
    html_target = html or f"reports/{html_component}-{ts}.html"

    if report:
        write_json(report_obj, report)
        log.info("[CASE] JSON report written to %s", report)
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
        from drun.notifier import DingTalkNotifier, EmailNotifier, FeishuNotifier, NotifyContext

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
                log.info("[NOTIFY] Auto-enabling channels from environment: %s", ", ".join(auto_channels))
            channels = auto_channels
        seen = set()
        channels = [c for c in channels if not (c in seen or seen.add(c))]
        policy_source = notify_only.strip() if (notify_only and notify_only.strip()) else get_env_clean("DRUN_NOTIFY_ONLY", "failed")
        policy = (policy_source or "failed").lower()
        topn_raw = get_env_clean("NOTIFY_TOPN", "5") or "5"
        topn = int(topn_raw)

        log.info("[NOTIFY] channels=%s policy=%s", channels, policy)

        should_send = (policy == "always") or (policy == "failed" and (s.get("failed", 0) or 0) > 0)
        log.info("[NOTIFY] should_send=%s (failed_count=%s)", should_send, s.get("failed", 0))

        if channels and should_send:
            log.info("[NOTIFY] Preparing to send notifications to: %s", ", ".join(channels))
            ctx = NotifyContext(html_path=html_target, log_path=default_log, notify_only=policy, topn=topn)
            notifiers = []

            if "feishu" in channels:
                fw = feishu_webhook or ""
                if fw:
                    fs = get_env_clean("FEISHU_SECRET")
                    fm = get_env_clean("FEISHU_MENTION")
                    style = (get_env_clean("FEISHU_STYLE", "text") or "text").lower()
                    notifiers.append(FeishuNotifier(webhook=fw, secret=fs, mentions=fm, style=style))
                    log.info("[NOTIFY] Feishu notifier created (style=%s)", style)
                else:
                    log.warning("[NOTIFY] Feishu channel requested but FEISHU_WEBHOOK not configured")

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
                            use_ssl=((get_env_clean("SMTP_SSL", "true") or "true").lower() != "false"),
                            attach_html=bool(
                                notify_attach_html
                                or ((get_env_clean("NOTIFY_ATTACH_HTML") or "").lower() in {"1", "true", "yes"})
                            ),
                            html_body=((get_env_clean("NOTIFY_HTML_BODY", "true") or "true").lower() != "false"),
                        )
                    )

            if "dingtalk" in channels:
                dw = dingtalk_webhook or ""
                if dw:
                    ds = get_env_clean("DINGTALK_SECRET")
                    mobiles = get_env_clean("DINGTALK_AT_MOBILES") or ""
                    at_mobiles = [m.strip() for m in mobiles.split(",") if m.strip()]
                    at_all = (get_env_clean("DINGTALK_AT_ALL") or "").lower() in {"1", "true", "yes"}
                    style = (get_env_clean("DINGTALK_STYLE", "text") or "text").lower()
                    notifiers.append(DingTalkNotifier(webhook=dw, secret=ds, at_mobiles=at_mobiles, at_all=at_all, style=style))

            log.info("[NOTIFY] Sending notifications via %d notifier(s)", len(notifiers))

            notifier_channel_map = {
                "FeishuNotifier": "feishu",
                "EmailNotifier": "email",
                "DingTalkNotifier": "dingtalk",
            }

            active_channels = [notifier_channel_map.get(n.__class__.__name__, n.__class__.__name__.lower()) for n in notifiers]
            for case in report_obj.cases:
                case.notify_channels = active_channels.copy()

            notify_results: List[NotifyResult] = []
            for n in notifiers:
                notifier_name = n.__class__.__name__
                channel = notifier_channel_map.get(notifier_name, notifier_name.lower())
                try:
                    log.info("[NOTIFY] Sending via %s...", notifier_name)
                    n.send(report_obj, ctx)
                    log.info("[NOTIFY] %s notification sent successfully", notifier_name)
                    notify_results.append(NotifyResult(channel=channel, status="success"))
                except Exception as e:
                    log.error("[NOTIFY] Failed to send via %s: %s", notifier_name, str(e))
                    notify_results.append(NotifyResult(channel=channel, status="failed"))

            for case in report_obj.cases:
                case.notify_results = notify_results.copy()

            write_html(report_obj, html_target)
            log.info("[NOTIFY] HTML report updated with notification status")
    except Exception as e:
        log.error("[NOTIFY] Notification module error: %s", str(e))

    if not no_snippet:
        try:
            _save_code_snippets(items, snippet_output, snippet_lang, env_store, ts, log)
        except Exception as e:
            log.error("[SNIPPET] Failed to generate code snippets: %s", str(e))

    log.info("[CASE] Logs written to %s", default_log)
    if s.get("failed", 0) > 0:
        raise typer.Exit(code=1)

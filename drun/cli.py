from __future__ import annotations

import json
import os
import re
import shutil
import sys
from importlib import metadata as _im
from pathlib import Path
from typing import List, Optional, Tuple

import click
import typer

from drun.commands.check import run_check
from drun.commands.convert import apply_convert_filters, convert_curl, convert_har, convert_postman
from drun.commands.fix import run_fix
from drun.commands.run import run_cases
from drun.commands.tags import run_tags
from drun.commands.yaml_dump import build_cases_from_import, write_imported_cases
from drun.extensions import require_importer

from drun.commands.quick import quick


def _get_drun_version() -> str:
    """Best-effort version detection for help banner.

    Priority:
    1) drun.__version__ attribute
    2) pyproject.toml under a project root (if available when running from source)
    3) Installed package metadata (importlib.metadata)
    4) "unknown"
    """
    # 1) module attribute
    try:
        from drun import __version__ as _v  # type: ignore

        if _v:
            return str(_v)
    except Exception:
        pass

    # 2) pyproject.toml (running from source without installed metadata)
    try:
        here = Path(__file__).resolve()
        for parent in [here.parent, *here.parents]:
            pp = parent / "pyproject.toml"
            if pp.exists():
                text = pp.read_text(encoding="utf-8", errors="ignore")
                in_project = False
                for line in text.splitlines():
                    s = line.strip()
                    if s.startswith("[") and s.endswith("]"):
                        in_project = s == "[project]"
                    elif in_project and s.startswith("version") and "=" in s:
                        # naive TOML parse: version = "x.y.z"
                        try:
                            _, rhs = s.split("=", 1)
                            v = rhs.strip().strip('"').strip("'")
                            if v:
                                return v
                        except Exception:
                            pass
                break
    except Exception:
        pass

    # 3) package metadata (installed/installed in editable)
    try:
        return _im.version("drun")
    except Exception:
        pass

    # 4) fallback
    return "unknown"


_APP_HELP = f"drun v{_get_drun_version()} · Zero-code HTTP API test framework"


def _resolve_help_width() -> int:
    columns_raw = os.environ.get("COLUMNS")
    if columns_raw is not None:
        try:
            columns = int(columns_raw.strip())
            if columns > 0:
                return columns
        except (TypeError, ValueError):
            pass

    try:
        columns = shutil.get_terminal_size(fallback=(120, 24)).columns
        if columns > 0:
            return columns
    except Exception:
        pass

    return 120


_HELP_WIDTH = _resolve_help_width()
_CLI_CONTEXT_SETTINGS = {
    "terminal_width": _HELP_WIDTH,
    "max_content_width": _HELP_WIDTH,
}
_SUBCOMMAND_HELP_GUIDE = "Subcommand help is disabled. Please use: drun --help"


def _looks_like_subcommand_help(args: List[str]) -> bool:
    if not args:
        return False

    first_command_idx: Optional[int] = None
    for idx, token in enumerate(args):
        if not token.startswith("-"):
            first_command_idx = idx
            break

    if first_command_idx is None:
        return False

    for idx, token in enumerate(args):
        if token in {"--help", "-h"} or token.startswith("--help="):
            return idx > first_command_idx
    return False


def _is_command_group(command: click.Command) -> bool:
    return isinstance(command, click.Group) or isinstance(
        getattr(command, "commands", None), dict
    )


def _is_argument_param(param: click.Parameter) -> bool:
    return (
        isinstance(param, click.Argument)
        or getattr(param, "param_type_name", None) == "argument"
    )


def _iter_visible_commands(
    group: click.Command, prefix: str = ""
) -> List[Tuple[str, click.Command]]:
    entries: List[Tuple[str, click.Command]] = []
    commands = getattr(group, "commands", {}) or {}
    for name, command in commands.items():
        if getattr(command, "hidden", False):
            continue
        full_name = f"{prefix}{name}".strip()
        entries.append((full_name, command))
        if _is_command_group(command):
            entries.extend(_iter_visible_commands(command, prefix=f"{full_name} "))
    return entries


def _collect_command_help_rows(
    command: click.Command, command_path: str
) -> Tuple[str, List[Tuple[str, str]]]:
    def _strip_type_suffix(left: str) -> str:
        # Strip trailing Click type tokens like "TEXT"/"INTEGER"/"FLOAT".
        return re.sub(r"\s+[A-Z][A-Z0-9_]*(?:\s+[A-Z][A-Z0-9_]*)*$", "", left).strip()

    def _unescape_brackets(text: str) -> str:
        return text.replace("\\[", "[").replace("\\]", "]")

    ctx = click.Context(command, info_name=f"drun {command_path}")
    argument_rows: List[Tuple[str, str]] = []
    option_rows: List[Tuple[str, str]] = []
    for param in command.get_params(ctx):
        if getattr(param, "hidden", False):
            continue
        record = param.get_help_record(ctx)
        if not record:
            continue
        left, right = record
        cleaned_left = _strip_type_suffix(left.strip())
        cleaned_right = _unescape_brackets((right or "-").strip())
        if _is_argument_param(param):
            argument_rows.append((cleaned_left, cleaned_right))
        else:
            option_rows.append((cleaned_left, cleaned_right))

    command_header = f"drun {command_path}"
    if argument_rows:
        args_part = " ".join(left for left, _ in argument_rows if left)
        if args_part:
            command_header = f"{command_header} {args_part}"
        desc_part = " ; ".join(
            right for _, right in argument_rows if right and right != "-"
        )
        if desc_part:
            command_header = f"{command_header}  {desc_part}"
    elif not argument_rows and (getattr(command, "short_help", None) or getattr(command, "help", None)):
        # Commands with no arguments (groups or option-only commands) get
        # a short description appended so the line is not empty. Prefer
        # short_help to keep the output narrow; fall back to first line of
        # help for commands that only set a long docstring.
        desc = command.short_help or command.help.strip().splitlines()[0]
        command_header = f"{command_header}  {desc.strip()}"
    return command_header, option_rows


# v8.1.0 migration: long command names were renamed to single letters.
# This map lets the CLI surface a clear "renamed to" hint instead of
# the generic "No such command" error.
_DEPRECATED_TO_LETTER = {
    "init": "i",
    "run": "r",
    "check": "c",
    "fix": "f",
    "tags": "t",
    "convert": "o",
    "convert-openapi": "w",
    "server": "s",
    "export": "e",
}


class _DrunRootGroup(typer.core.TyperGroup):
    def get_command(
        self, ctx: click.Context, cmd_name: str
    ) -> Optional[click.Command]:
        # v8.1.0 migration hint: long command names were renamed to single
        # letters. Surface a clear migration message instead of the generic
        # "No such command" so existing users get actionable feedback.
        if cmd_name in _DEPRECATED_TO_LETTER:
            letter = _DEPRECATED_TO_LETTER[cmd_name]
            raise click.UsageError(
                f"Command '{cmd_name}' has been renamed to single-letter form. "
                f"Use 'drun {letter}' instead.",
                ctx=ctx,
            )
        return super().get_command(ctx, cmd_name)

    def parse_args(self, ctx: click.Context, args: List[str]) -> List[str]:
        if _looks_like_subcommand_help(args):
            raise click.UsageError(_SUBCOMMAND_HELP_GUIDE, ctx=ctx)
        if args and args[0] == "q" and any(
            token == "-validate" or token.startswith("-validate=") for token in args[1:]
        ):
            raise click.UsageError(
                "`-validate` has been renamed to `-check`. Use `-check` instead.",
                ctx=ctx,
            )
        # `e` is a group; default to `e curl` only when called bare.
        # If a second arg is given (option or subcommand), pass through
        # to click's normal resolution. This avoids surprising behavior
        # like `drun e -port` silently becoming `drun e curl -port`.
        # NOTE: v8.1.0 convenience. If more subcommands are added to `e`,
        # users will be required to use the explicit `drun e <subcommand>`
        # form.
        if args and args[0] == "e" and len(args) == 1:
            args = ["e", "curl"]
        return super().parse_args(ctx, args)

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        super().format_help(ctx, formatter)

        expanded_entries = _iter_visible_commands(self)
        if not expanded_entries:
            return

        formatter.write_paragraph()
        with formatter.section("Expanded Help (All Commands)"):
            formatter.write_text(_SUBCOMMAND_HELP_GUIDE)
            for command_path, command in expanded_entries:
                command_header, rows = _collect_command_help_rows(command, command_path)
                formatter.write_paragraph()
                formatter.write_text(command_header)
                if rows:
                    formatter.write_dl(rows)


def _version_callback(value: bool):
    """Display version and exit."""
    if value:
        typer.echo(f"drun version {_get_drun_version()}")
        raise typer.Exit()


app = typer.Typer(
    add_completion=False,
    help=_APP_HELP,
    rich_markup_mode=None,
    cls=_DrunRootGroup,
    context_settings=_CLI_CONTEXT_SETTINGS,
)
export_app = typer.Typer(
    help="导出测试用例到其他格式",
    add_help_option=False,
    context_settings=_CLI_CONTEXT_SETTINGS,
)
app.add_typer(export_app, name="e")


@export_app.callback()
def export_main() -> None:
    """导出测试用例到其他格式"""
    pass


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=_version_callback,
        is_eager=True,
    ),
):
    """drun - Zero-code HTTP API test framework"""
    pass


# Unified convert entrypoint (auto-detect by suffix)
@app.command("o", add_help_option=False)
def convert_auto(
    infile: str = typer.Argument(..., help="待转换的源文件 (.curl/.har/.json)"),
    outfile: Optional[str] = typer.Option(None, "-outfile", help="输出到指定文件"),
    into: Optional[str] = typer.Option(None, "-into", help="追加到已存在的 YAML 文件"),
    case_name: Optional[str] = typer.Option(
        None, "-case-name", help="覆盖生成的用例名称"
    ),
    base_url: Optional[str] = typer.Option(
        None, "-base-url", help="覆盖生成用例的 base_url"
    ),
    postman_env: Optional[str] = typer.Option(
        None, "-postman-env", help="Postman 环境 JSON 文件，用于导入变量"
    ),
    suite_out: Optional[str] = typer.Option(
        None,
        "-suite-out",
        help="生成引用测试套件 YAML（需配合 -output-mode split 或 -outfile）",
    ),
    output_mode: str = typer.Option(
        "single",
        "-output-mode",
        help="输出模式 single|split",
        metavar="",
    ),
    # Pass-through options for specific converters (available at top-level for convenience)
    redact: Optional[str] = typer.Option(
        None,
        "-redact",
        help="逗号分隔的需要脱敏的请求头名称，如 Authorization,Cookie",
    ),
    placeholders_mode: str = typer.Option(
        "off",
        "-placeholders",
        help="敏感请求头变量化 on|off",
        metavar="",
    ),
) -> None:
    """转换格式（支持 .curl/.har/.json）到 YAML 测试用例"""
    resolved_output_mode = (output_mode or "single").strip().lower()
    if resolved_output_mode not in {"single", "split"}:
        typer.echo("[CONVERT] Invalid -output-mode value. Use 'single' or 'split'.")
        raise typer.Exit(code=2)

    resolved_placeholders_mode = (placeholders_mode or "off").strip().lower()
    if resolved_placeholders_mode not in {"on", "off"}:
        typer.echo("[CONVERT] Invalid -placeholders value. Use 'on' or 'off'.")
        raise typer.Exit(code=2)

    split_output = resolved_output_mode == "split"
    placeholders = resolved_placeholders_mode == "on"

    # Enforce: options must be after INFILE (no legacy compatibility)
    try:
        argv = list(sys.argv)
        i_convert = argv.index("convert")
    except ValueError:
        i_convert = -1
    if i_convert >= 0:
        tail = argv[i_convert + 1 :]
        # locate infile token in raw argv
        cand_suffix = (".curl", ".har", ".json")
        pos = None
        for i, tok in enumerate(tail):
            if tok == "-" or tok.lower().endswith(cand_suffix):
                pos = i
                break
        if pos is not None and any(t.startswith("-") for t in tail[:pos]):
            typer.echo(
                "[CONVERT] Options must follow INFILE. Example:\n  drun convert file.curl -outfile out.yaml"
            )
            raise typer.Exit(code=2)
    # Enforce: no bare conversion without any options
    any_option = any(
        [
            outfile is not None,
            into is not None,
            case_name is not None,
            base_url is not None,
            postman_env is not None,
            suite_out is not None,
            resolved_output_mode != "single",
            (redact is not None),
            resolved_placeholders_mode != "off",
        ]
    )
    if not any_option:
        typer.echo(
            "[CONVERT] No options provided. Bare conversion is not supported. Place options after INFILE, e.g.:\n  drun convert my.curl -outfile tcases/tc_from_curl.yaml"
        )
        raise typer.Exit(code=2)

    if infile == "-":
        # stdin: treat as curl text
        convert_curl(
            infile=infile,
            outfile=outfile,
            into=into,
            case_name=case_name,
            base_url=base_url,
            split_output=split_output,
            redact=redact,
            placeholders=placeholders,
        )
        return
    suffix = Path(infile).suffix.lower()
    if suffix == ".curl":
        convert_curl(
            infile=infile,
            outfile=outfile,
            into=into,
            case_name=case_name,
            base_url=base_url,
            split_output=split_output,
            redact=redact,
            placeholders=placeholders,
        )
    elif suffix == ".har":
        convert_har(
            infile=infile,
            outfile=outfile,
            into=into,
            case_name=case_name,
            base_url=base_url,
            split_output=split_output,
            redact=redact,
            placeholders=placeholders,
            exclude_static=True,
            only_2xx=False,
            exclude_pattern=None,
        )
    elif suffix == ".json":
        # Try Postman by default; if 'openapi' field detected, prefer OpenAPI
        data = {}
        try:
            data = json.loads(Path(infile).read_text(encoding="utf-8"))
        except Exception:
            pass
        if isinstance(data, dict) and data.get("openapi"):
            convert_openapi(
                spec=infile,
                outfile=outfile,
                case_name=case_name,
                base_url=base_url,
                output_mode=resolved_output_mode,
                redact=redact,
                placeholders_mode=resolved_placeholders_mode,
                tags=None,
            )
        else:
            convert_postman(
                collection=infile,
                outfile=outfile,
                into=into,
                case_name=case_name,
                base_url=base_url,
                split_output=split_output,
                redact=redact,
                placeholders=placeholders,
                postman_env=postman_env,
                suite_out=suite_out,
            )
    else:
        typer.echo(
            "[CONVERT] Unrecognized file format. Supported suffixes: .curl, .har, .json"
        )
        raise typer.Exit(code=2)


# Helper for curl conversion
@export_app.command("curl", add_help_option=False)
def export_curl(
    path: str = typer.Argument(..., help="要导出的用例/套件 YAML 文件或目录"),
    case_name: Optional[str] = typer.Option(
        None, "-case-name", help="仅导出指定名称的用例"
    ),
    steps: Optional[str] = typer.Option(None, "-steps", help="步骤索引，如 '1,3-5'（从 1 开始）"),
    layout: str = typer.Option(
        "multiline",
        "-layout",
        help="输出布局 multiline|oneline",
        metavar="",
    ),
    shell: str = typer.Option("sh", "-shell", help="续行符风格：sh|ps"),
    redact: Optional[str] = typer.Option(
        None, "-redact", help="逗号分隔的需要脱敏的请求头名称，如 Authorization,Cookie"
    ),
    comments: str = typer.Option(
        "off",
        "-comments",
        help="注释模式 on|off",
        metavar="",
    ),
    outfile: Optional[str] = typer.Option(
        None, "-outfile", help="输出到文件（必须以 .curl 结尾）"
    ),
) -> None:
    """导出测试用例为 curl 命令"""
    from drun.commands.convert import export_curl as _export_curl

    _export_curl(
        path=path,
        case_name=case_name,
        steps=steps,
        layout=layout,
        shell=shell,
        redact=redact,
        comments=comments,
        outfile=outfile,
    )


@app.command("t", add_help_option=False)
def list_tags(
    path: str = typer.Argument("tcases", help="要扫描的文件或目录"),
) -> None:
    """列出所有测试用例使用的标签"""
    run_tags(path)


def _run_impl(
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
):
    return run_cases(
        path=path,
        k=k,
        vars=vars,
        failfast=failfast,
        report=report,
        html=html,
        allure_results=allure_results,
        log_level=log_level,
        env=env,
        env_file=env_file,
        persist_env=persist_env,
        log_file=log_file,
        httpx_logs=httpx_logs,
        reveal_secrets=reveal_secrets,
        response_headers=response_headers,
        notify=notify,
        notify_only=notify_only,
        notify_attach_html=notify_attach_html,
        no_snippet=no_snippet,
        snippet_output=snippet_output,
        snippet_lang=snippet_lang,
    )


quick = app.command("q", add_help_option=False)(quick)


@app.command("r", add_help_option=False)
def r(
    path: str = typer.Argument(
        ...,
        help="运行目标（文件/目录；支持 <path>:<case[,case]>）。例: tcases:登录",
    ),
    k: Optional[str] = typer.Option(
        None, "-k", help='标签过滤表达式。例: -k "smoke and not slow"', metavar=""
    ),
    vars: List[str] = typer.Option([], "-vars", help="变量覆盖 k=v（可重复）。例: -vars token=abc", metavar=""),
    failfast: bool = typer.Option(False, "-failfast", help="遇到首个失败即停止。例: -failfast"),
    report: Optional[str] = typer.Option(None, "-report", help="输出 JSON 报告文件。例: -report reports/result.json", metavar=""),
    html: Optional[str] = typer.Option(
        None,
        "-html",
        help="输出 HTML 报告文件。例: -html reports/report.html",
        metavar="",
    ),
    allure_results: Optional[str] = typer.Option(
        None, "-allure-results", help="输出 Allure 结果目录。例: -allure-results allure-results", metavar=""
    ),
    log_level: str = typer.Option("INFO", "-log-level", help="日志级别。例: -log-level DEBUG", metavar=""),
    env: Optional[str] = typer.Option(
        None,
        "-env",
        help="环境名（对应 .env.<name>）。例: -env dev",
        metavar="",
    ),
    env_file: Optional[str] = typer.Option(
        None,
        "-env-file",
        help="显式环境文件路径。例: -env-file .env.local",
        metavar="",
    ),
    persist_env: Optional[str] = typer.Option(
        None, "-persist-env", help="提取变量持久化文件。例: -persist-env .env.runtime", metavar=""
    ),
    log_file: Optional[str] = typer.Option(
        None,
        "-log-file",
        help="控制台日志输出文件。例: -log-file logs/run.log",
        metavar="",
    ),
    httpx_logs: bool = typer.Option(
        False,
        "-httpx-logs",
        help="启用 httpx 内部请求日志。例: -httpx-logs",
        show_default=False,
    ),
    secrets: str = typer.Option(
        "plain",
        "-secrets",
        help="敏感信息模式 plain|mask。例: -secrets mask",
        metavar="",
    ),
    response_headers: bool = typer.Option(
        False,
        "-response-headers",
        help="记录 HTTP 响应头。例: -response-headers",
        show_default=False,
    ),
    notify: Optional[str] = typer.Option(
        None, "-notify", help="通知渠道（逗号分隔）。例: -notify feishu,email", metavar=""
    ),
    notify_only: Optional[str] = typer.Option(
        None,
        "-notify-only",
        help="通知策略 failed|always。例: -notify-only always",
        show_default=False,
        metavar="",
    ),
    notify_attach_html: bool = typer.Option(
        False,
        "-notify-attach-html",
        help="邮件附加 HTML 报告。例: -notify-attach-html",
        show_default=False,
    ),
    snippet: str = typer.Option(
        "all",
        "-snippet",
        help="代码片段模式 off|all|curl|python。例: -snippet curl",
        metavar="",
    ),
    snippet_output: Optional[str] = typer.Option(
        None,
        "-snippet-output",
        help="代码片段输出目录。例: -snippet-output snippets_out",
        metavar="",
    ),
):
    """Run test cases or suites."""
    secrets_mode = (secrets or "plain").strip().lower()
    if secrets_mode not in {"plain", "mask"}:
        typer.echo("[ERROR] Invalid -secrets value. Use 'plain' or 'mask'.")
        raise typer.Exit(code=2)

    snippet_mode = (snippet or "all").strip().lower()
    if snippet_mode not in {"off", "all", "curl", "python"}:
        typer.echo(
            "[ERROR] Invalid -snippet value. Use one of: off, all, curl, python."
        )
        raise typer.Exit(code=2)

    resolved_reveal_secrets = secrets_mode == "plain"
    resolved_no_snippet = snippet_mode == "off"
    resolved_snippet_lang = (
        "all" if snippet_mode == "off" else snippet_mode
    )

    return _run_impl(
        path,
        k,
        vars,
        failfast,
        report,
        html,
        allure_results,
        log_level,
        env,
        env_file,
        persist_env,
        log_file,
        httpx_logs,
        resolved_reveal_secrets,
        response_headers,
        notify,
        notify_only,
        notify_attach_html,
        resolved_no_snippet,
        snippet_output,
        resolved_snippet_lang,
    )


@app.command("c", add_help_option=False)
def check(
    path: str = typer.Argument(..., help="要验证的文件或目录"),
):
    """验证 YAML 测试文件的语法和风格（不执行）

    检查规则：
    - Extract 仅使用 `$` 语法
    - Check 对 body 使用 `$`，对元数据使用 `status_code`/`headers.*`
    - request.files 结构需符合上传规范
    - Hooks 函数名格式需符合前缀要求
    """
    run_check(path)


@app.command("f", add_help_option=False)
def fix(
    paths: List[str] = typer.Argument(
        ...,
        help="要修复的文件或目录（移动 hooks 到 config.* / 步骤间距）",
        metavar="PATH...",
    ),
    mode: str = typer.Option(
        "all",
        "-mode",
        help="修复模式 all|spacing|hooks",
        metavar="",
    ),
):
    """自动修复 YAML 文件的格式和结构

    - 将 suite/case 级别的 hooks 移动到 `config.setup_hooks/config.teardown_hooks` 下
    - 确保 `steps:` 下相邻步骤之间有一个空行
    """
    resolved_mode = (mode or "all").strip().lower()
    if resolved_mode not in {"all", "spacing", "hooks"}:
        typer.echo("[FIX] Invalid -mode value. Use 'all', 'spacing', or 'hooks'.")
        raise typer.Exit(code=2)

    run_fix(
        paths=paths,
        only_spacing=resolved_mode == "spacing",
        only_hooks=resolved_mode == "hooks",
    )


@app.command("i", add_help_option=False)
def init_project(
    name: Optional[str] = typer.Argument(
        None, help="Project name (default: current directory)"
    ),
    force: bool = typer.Option(False, "-force", help="Overwrite existing files"),
    ci: bool = typer.Option(False, "-ci", help="Generate CI workflow (GitHub Actions)"),
) -> None:
    """Initialize Drun test project scaffold.

    Examples:
        drun init                    # Initialize in current directory
        drun init my-api-test        # Create new project directory
        drun init -force             # Overwrite existing files
        drun init -ci                # Include GitHub Actions workflow
    """
    from drun import scaffolds

    # Display version
    typer.echo(f"Drun v{_get_drun_version()}")

    # 确定目标目录
    if name:
        target_dir = Path(name)
        if target_dir.exists() and not target_dir.is_dir():
            typer.echo(f"[ERROR] '{name}' exists but is not a directory.")
            raise typer.Exit(code=2)
    else:
        target_dir = Path.cwd()

    # 检查是否已存在关键文件
    key_files = ["tcases", "tsuites", ".env", "Dhook.py", ".gitignore"]
    legacy_files = ["testcases", "testsuites"]
    existing_files = [f for f in key_files if (target_dir / f).exists()]
    existing_legacy_files = [f for f in legacy_files if (target_dir / f).exists()]

    if existing_legacy_files:
        typer.echo(
            f"[WARNING] Legacy Drun directories detected: {', '.join(existing_legacy_files)}"
        )
        typer.echo(
            "They are no longer supported and will not be modified. Use tcases/ and tsuites/."
        )

    if (existing_files or existing_legacy_files) and not force:
        all_existing = existing_files + existing_legacy_files
        typer.echo(
            f"[WARNING] Directory already contains Drun project files: {', '.join(all_existing)}"
        )
        typer.echo(
            "Use -force to overwrite existing files. Existing files will be kept otherwise."
        )
        if not typer.confirm(
            "Continue without overwriting existing files?", default=False
        ):
            raise typer.Exit(code=0)

    # 开始创建项目
    if name:
        typer.echo(f"\nCreating Drun project: {target_dir}/\n")
    else:
        typer.echo(f"\nInitializing Drun project in current directory\n")

    # Create directory structure
    dirs_to_create = {
        "tcases": "Test cases",
        "tsuites": "Test suites",
        "data": "Test data",
        "converts": "Format conversion",
        "reports": "Reports output",
        "logs": "Logs output",
        "snippets": "Code snippets",
    }

    for dir_name, desc in dirs_to_create.items():
        dir_path = target_dir / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)

    # CI workflow directory (optional)
    if ci:
        (target_dir / ".github/workflows").mkdir(parents=True, exist_ok=True)

    # 在 reports、logs 和 snippets 目录放置 .gitkeep
    for empty_dir in ["reports", "logs", "snippets"]:
        gitkeep_path = target_dir / empty_dir / ".gitkeep"
        gitkeep_path.write_text(scaffolds.GITKEEP_CONTENT, encoding="utf-8")

    # 写入文件
    skipped_files: List[str] = []
    overwritten_files: List[str] = []

    def _write_template(rel_path: str, content: str) -> None:
        file_path = target_dir / rel_path
        existed_before = file_path.exists()
        if existed_before and not force:
            skipped_files.append(rel_path)
            typer.echo(f"[SKIP] {rel_path} exists, use -force to overwrite")
            return
        file_path.write_text(content, encoding="utf-8")
        if existed_before and force:
            overwritten_files.append(rel_path)

    # Test cases
    _write_template("tcases/tc_demo.yaml", scaffolds.DEMO_TESTCASE)
    _write_template("tcases/tc_api_health.yaml", scaffolds.HEALTH_TESTCASE)
    _write_template("tcases/tc_import_users.yaml", scaffolds.CSV_DATA_TESTCASE)

    # Test data
    _write_template("data/users.csv", scaffolds.CSV_USERS_SAMPLE)

    # Test suites
    _write_template("tsuites/ts_smoke.yaml", scaffolds.DEMO_TESTSUITE)

    # Format conversion sample
    _write_template("converts/sample.curl", scaffolds.SAMPLE_CURL)

    # Config files
    _write_template(".env", scaffolds.ENV_TEMPLATE)
    _write_template("Dhook.py", scaffolds.HOOKS_TEMPLATE)
    _write_template(".gitignore", scaffolds.GITIGNORE_TEMPLATE)

    # CI workflow (optional)
    if ci:
        _write_template(
            ".github/workflows/test.yml", scaffolds.GITHUB_WORKFLOW_TEMPLATE
        )

    # Output file tree
    project_name = name if name else "."

    tree_entries = [
        ("├── ", "tcases/", "Test cases"),
        ("│   ├── ", "tc_demo.yaml", "HTTP demo"),
        ("│   ├── ", "tc_api_health.yaml", "Health check"),
        ("│   └── ", "tc_import_users.yaml", "CSV data-driven"),
        ("├── ", "tsuites/", "Test suites"),
        ("│   └── ", "ts_smoke.yaml", "Smoke test suite"),
        ("├── ", "data/", ""),
        ("│   └── ", "users.csv", "Sample CSV data"),
        ("├── ", "converts/", ""),
        ("│   └── ", "sample.curl", "cURL sample"),
        ("├── ", "reports/", "Reports output"),
        ("├── ", "logs/", "Logs output"),
        ("├── ", "snippets/", "Code snippets"),
    ]

    if ci:
        tree_entries.extend(
            [
                ("├── ", ".github/workflows/", ""),
                ("│   └── ", "test.yml", "CI workflow"),
            ]
        )

    tree_entries.extend(
        [
            ("├── ", ".env", "Environment config"),
            ("├── ", "Dhook.py", "Custom hooks"),
            ("└── ", ".gitignore", "Git ignore"),
        ]
    )

    pad = max(len(prefix + entry) for prefix, entry, desc in tree_entries if desc) + 4

    typer.echo(f"{project_name}")
    for prefix, entry, desc in tree_entries:
        full = f"{prefix}{entry}"
        if desc:
            typer.echo(f"{full.ljust(pad)}{desc}")
        else:
            typer.echo(full)
    typer.echo("")

    dir_count = 8 if ci else 7
    file_count = 10 if ci else 9
    typer.echo(f"{dir_count} directories, {file_count} files")

    if skipped_files:
        typer.echo("")
        typer.echo("Skipped (already exists):")
        for rel_path in skipped_files:
            typer.echo(f"  - {rel_path}")

    if overwritten_files:
        typer.echo("")
        typer.echo("Overwritten (-force):")
        for rel_path in overwritten_files:
            typer.echo(f"  - {rel_path}")

    typer.echo("")
    typer.echo("Project initialized!")
    typer.echo("")
    typer.echo("Quick start:")
    if name:
        typer.echo(f"  cd {name}")
    typer.echo("  drun run tcases -env dev")
    typer.echo("  drun run tc_demo -env dev")
    typer.echo("  drun run ts_smoke -env dev")
    typer.echo("")
    typer.echo("Docs: https://github.com/Devliang24/drun")


@app.command("w", add_help_option=False)
def convert_openapi(
    spec: str = typer.Argument(..., help="OpenAPI 3.x 规范文件（.json 或 .yaml）"),
    outfile: Optional[str] = typer.Option(None, "-outfile", help="输出文件路径"),
    case_name: Optional[str] = typer.Option(None, "-case-name", help="用例名称"),
    base_url: Optional[str] = typer.Option(None, "-base-url", help="基础 URL"),
    tags: Optional[str] = typer.Option(
        None, "-tags", help="逗号分隔的标签列表（区分大小写）"
    ),
    output_mode: str = typer.Option(
        "single",
        "-output-mode",
        help="输出模式 single|split",
        metavar="",
    ),
    redact: Optional[str] = typer.Option(
        None, "-redact", help="逗号分隔的需要脱敏的请求头名称，如 Authorization,Cookie"
    ),
    placeholders_mode: str = typer.Option(
        "off",
        "-placeholders",
        help="敏感请求头变量化 on|off",
        metavar="",
    ),
) -> None:
    """转换 OpenAPI 规范到 YAML 测试用例"""
    resolved_output_mode = (output_mode or "single").strip().lower()
    if resolved_output_mode not in {"single", "split"}:
        typer.echo("[CONVERT] Invalid -output-mode value. Use 'single' or 'split'.")
        raise typer.Exit(code=2)

    resolved_placeholders_mode = (placeholders_mode or "off").strip().lower()
    if resolved_placeholders_mode not in {"on", "off"}:
        typer.echo("[CONVERT] Invalid -placeholders value. Use 'on' or 'off'.")
        raise typer.Exit(code=2)

    split_output = resolved_output_mode == "split"
    placeholders = resolved_placeholders_mode == "on"

    parse_openapi = require_importer("openapi")
    text = Path(spec).read_text(encoding="utf-8")
    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]
    icase = parse_openapi(
        text, case_name=case_name, base_url=base_url, tags=tag_list or None
    )
    if not icase.steps:
        typer.echo("[CONVERT] No operations detected in OpenAPI spec.")
        return
    cases = build_cases_from_import(icase, split_output=split_output)
    redact_list = [x.strip() for x in (redact or "").split(",") if x.strip()]
    cases = [
        (
            apply_convert_filters(
                case, redact_headers=redact_list, placeholders=placeholders
            ),
            idx,
        )
        for case, idx in cases
    ]
    write_imported_cases(
        cases,
        outfile=outfile,
        into=None,
        split_output=split_output,
        source_path=spec,
    )


@app.command("s", add_help_option=False)
def serve_reports(
    port: int = typer.Option(8080, "-port", help="监听端口"),
    host: str = typer.Option(
        "0.0.0.0", "-host", help="监听地址 (0.0.0.0 允许外部访问)"
    ),
    reports_dir: str = typer.Option("reports", "-reports-dir", help="报告目录路径"),
    reload: bool = typer.Option(
        False, "-reload", help="开发模式（热重载）", show_default=False
    ),
    headless: bool = typer.Option(
        False, "-headless", help="不自动打开浏览器", show_default=False
    ),
):
    """启动 Web Server 查看测试报告"""
    resolved_open_browser = not headless

    try:
        import uvicorn
        import webbrowser
        import threading
    except ImportError:
        typer.echo("[ERROR] FastAPI and uvicorn are required for the serve command.")
        typer.echo("Install them with: pip install fastapi uvicorn")
        raise typer.Exit(code=1)

    # Convert to absolute path and ensure directory exists
    reports_path = Path(reports_dir).resolve()
    if not reports_path.exists():
        typer.echo(f"[WARN] Reports directory not found: {reports_dir}")
        typer.echo(f"[INFO] Creating directory: {reports_dir}")
        reports_path.mkdir(parents=True, exist_ok=True)

    # Pass absolute path to server via environment variable
    os.environ["DRUN_REPORTS_DIR"] = str(reports_path)

    url = f"http://{host}:{port}"
    typer.echo(f"[SERVER] Starting Drun Report Server")
    typer.echo(f"[SERVER] Web UI: {url}")
    typer.echo(f"[SERVER] API docs: {url}/docs")
    typer.echo(f"[SERVER] Reports directory: {reports_path}")
    typer.echo(f"[SERVER] Listening on: {host}:{port}")
    if host == "0.0.0.0":
        typer.echo(f"[SERVER] ⚠️  Server is accessible from public network")
    typer.echo(f"[SERVER] Press Ctrl+C to stop")

    if resolved_open_browser and not reload and host in ["127.0.0.1", "localhost"]:
        # Open browser after a short delay (only for local access)
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    try:
        uvicorn.run(
            "drun.server.app:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
        )
    except KeyboardInterrupt:
        typer.echo("\n[SERVER] Stopped")


if __name__ == "__main__":
    app()

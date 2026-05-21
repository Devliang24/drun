from __future__ import annotations

from pathlib import Path

import typer

from drun.loader.collector import discover
from drun.loader.yaml_loader import collect_yaml_diagnostics, load_yaml_file
from drun.utils.errors import Diagnostic


MAX_DIAGNOSTICS_PER_FILE = 5


def _format_check_diagnostic(diag, *, indent: str = "  ") -> str:
    return "\n".join(f"{indent}{line}" if line else "" for line in diag.format().splitlines())


def run_check(path: str) -> None:
    files = discover([path])
    if not files:
        typer.echo("No YAML test files found.")
        raise typer.Exit(code=2)

    def _check_steps_spacing(filepath: Path) -> tuple[bool, str | None]:
        try:
            text = Path(filepath).read_text(encoding="utf-8")
        except Exception as e:
            return False, f"read error: {e}"
        lines = text.splitlines()
        import re as _re

        i = 0
        while i < len(lines):
            m = _re.match(r"^(\s*)steps:\s*$", lines[i])
            if not m:
                i += 1
                continue
            base = len(m.group(1))
            step_indent = base + 2
            seen_first = False
            j = i + 1
            while j < len(lines):
                ln = lines[j]
                if ln.strip() and (len(ln) - len(ln.lstrip(" ")) <= base) and not ln.lstrip().startswith("-"):
                    break
                if ln.startswith(" " * step_indent + "-"):
                    if seen_first:
                        prev = lines[j - 1] if j - 1 >= 0 else ""
                        if prev.strip() != "":
                            return (
                                False,
                                f"steps spacing error near line {j + 1}: add a blank line between step items",
                            )
                    else:
                        seen_first = True
                j += 1
            i = j
        return True, None

    ok = 0
    failed = 0
    total_errors = 0
    for f in files:
        diagnostics = collect_yaml_diagnostics(Path(f))
        if not diagnostics:
            try:
                load_yaml_file(f)
                spacing_ok, spacing_msg = _check_steps_spacing(Path(f))
                if not spacing_ok:
                    diagnostics = [
                        Diagnostic(
                            code="DRUN-YAML-014",
                            message="Invalid step spacing",
                            file=str(f),
                            hint=spacing_msg,
                            example=(
                                "steps:\n"
                                "  - name: First\n"
                                "    request:\n"
                                "      method: GET\n"
                                "      path: /one\n"
                                "\n"
                                "  - name: Second\n"
                                "    request:\n"
                                "      method: GET\n"
                                "      path: /two"
                            ),
                        )
                    ]
            except Exception as e:
                diag = getattr(e, "diagnostic", None)
                if diag is not None:
                    diagnostics = [diag]
                else:
                    diagnostics = [
                        Diagnostic(
                            code="DRUN-YAML-999",
                            message="Failed to load YAML",
                            file=str(f),
                            hint=str(e),
                        )
                    ]

        if diagnostics:
            failed += 1
            total_errors += len(diagnostics)
            typer.echo(f"FAIL {f}")
            shown = diagnostics[:MAX_DIAGNOSTICS_PER_FILE]
            for diag in shown:
                typer.echo(_format_check_diagnostic(diag))
            hidden_count = len(diagnostics) - len(shown)
            if hidden_count > 0:
                typer.echo(f"  ... {hidden_count} more diagnostic(s) hidden for this file")
            typer.echo("")
            continue

        ok += 1
        typer.echo(f"OK {f}")

    if failed:
        typer.echo(
            f"Checked {len(files)} file(s): {ok} OK, {failed} failed, {total_errors} error(s)."
        )
        raise typer.Exit(code=2)

    typer.echo(f"Checked {len(files)} file(s): {ok} OK, 0 failed, 0 error(s).")

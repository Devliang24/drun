from __future__ import annotations

from pathlib import Path

import typer

from drun.loader.collector import discover
from drun.loader.yaml_loader import load_yaml_file


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
    for f in files:
        try:
            load_yaml_file(f)
            spacing_ok, spacing_msg = _check_steps_spacing(Path(f))
            if not spacing_ok:
                typer.echo(f"FAIL: {f} -> {spacing_msg}")
                raise typer.Exit(code=2)
            ok += 1
            typer.echo(f"OK: {f}")
        except Exception as e:
            typer.echo(f"FAIL: {f} -> {e}")
            raise typer.Exit(code=2)
    typer.echo(f"Validated {ok} file(s).")

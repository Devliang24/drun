from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import typer

from drun.loader.collector import AmbiguousTestTargetError, InvalidTestPathError, discover
from drun.loader.yaml_loader import load_yaml_file


def run_tags(path: str) -> None:
    try:
        files = discover([path])
    except (InvalidTestPathError, AmbiguousTestTargetError) as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=2)
    if not files:
        typer.echo(f"No YAML test files found at: {path}")
        pth = Path(path)
        hints: list[str] = []
        if not pth.exists():
            if not pth.suffix:
                for ext in (".yaml", ".yml"):
                    cand = pth.with_suffix(ext)
                    if cand.exists():
                        hints.append(f"Did you mean: drun r {cand}")
                        break
        else:
            if pth.is_file():
                if pth.suffix.lower() not in {".yaml", ".yml"}:
                    hints.append("Only .yaml/.yml files are recognized.")
                    for ext in (".yaml", ".yml"):
                        cand = pth.with_suffix(ext)
                        if cand.exists():
                            hints.append(f"Try: drun r {cand}")
                            break
            elif pth.is_dir():
                hints.append(
                    "Provide a YAML file or a directory containing YAML tests under tcases/ or tsuites/."
                )
        hints.append("Examples:")
        hints.append("  drun r tcases")
        hints.append("  drun r tc_demo")
        hints.append("  drun r tcases/tc_hello.yaml")
        hints.append("  drun r ts_smoke")
        for h in hints:
            typer.echo(h)
        raise typer.Exit(code=2)

    collected: Dict[str, set[tuple[str, str]]] = {}
    diagnostics: List[str] = []

    for f in files:
        try:
            cases, _meta = load_yaml_file(f)
        except Exception as exc:  # pragma: no cover - defensive
            diagnostics.append(f"[WARN] Failed to parse {f}: {exc}")
            continue
        if not cases:
            diagnostics.append(f"[INFO] No cases found in {f}")
            continue
        diagnostics.append(f"[OK] {f} -> {len(cases)} cases")
        for c in cases:
            tags = c.config.tags or []
            case_name = c.config.name or "Unnamed"
            entry = (case_name, str(f))
            if not tags:
                collected.setdefault("<no-tag>", set()).add(entry)
            for tag in tags:
                collected.setdefault(tag, set()).add(entry)

    for line in diagnostics:
        typer.echo(line)
    typer.echo("\nTag Summary:")
    for tag, cases_for_tag in sorted(collected.items(), key=lambda item: item[0]):
        typer.echo(f"- {tag}: {len(cases_for_tag)} cases")
        for case_name, case_path in sorted(cases_for_tag):
            typer.echo(f"    • {case_name} -> {case_path}")

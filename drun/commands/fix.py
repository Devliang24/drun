from __future__ import annotations

import re
from pathlib import Path
from typing import List

import typer
import yaml

from drun.loader.collector import discover


class _YamlDumper(yaml.SafeDumper):
    def increase_indent(self, flow: bool = False, indentless: bool = False):
        return super().increase_indent(flow, False)


def run_fix(paths: List[str], only_spacing: bool, only_hooks: bool) -> None:
    files = discover(paths)
    if not files:
        typer.echo("No YAML test files found.")
        raise typer.Exit(code=2)

    def _merge_hooks(dst_cfg: dict, src_obj: dict) -> bool:
        changed = False
        for hk in ("setup_hooks", "teardown_hooks"):
            if hk in src_obj and isinstance(src_obj.get(hk), list):
                items = [it for it in src_obj.get(hk) or []]
                if items:
                    existing = list(dst_cfg.get(hk) or [])
                    dst_cfg[hk] = existing + items
                    changed = True
                src_obj.pop(hk, None)
        return changed

    def _fix_steps_spacing(filepath: Path) -> bool:
        try:
            text = filepath.read_text(encoding="utf-8")
        except Exception:
            return False
        lines = text.splitlines()
        changed = False
        i = 0
        while i < len(lines):
            m = re.match(r"^(\s*)steps:\s*$", lines[i])
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
                            lines.insert(j, "")
                            changed = True
                            j += 1
                    else:
                        seen_first = True
                j += 1
            i = j
        if changed:
            filepath.write_text("\n".join(lines) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
        return changed

    def _fix_url_to_path(filepath: Path) -> bool:
        try:
            text = filepath.read_text(encoding="utf-8")
        except Exception:
            return False

        lines = text.splitlines()
        changed = False
        in_request = False
        request_indent = None

        for i in range(len(lines)):
            line = lines[i]
            stripped = line.lstrip()
            indent = len(line) - len(stripped)

            if stripped.startswith("request:"):
                in_request = True
                request_indent = indent
                continue

            if in_request and stripped and request_indent is not None and indent <= request_indent:
                in_request = False
                request_indent = None

            if in_request and stripped.startswith("url:"):
                lines[i] = " " * indent + "path:" + line.split("url:", 1)[1]
                changed = True

        if changed:
            filepath.write_text("\n".join(lines) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
        return changed

    def _fix_invalid_dash_before_fields(filepath: Path) -> bool:
        try:
            text = filepath.read_text(encoding="utf-8")
        except Exception:
            return False

        lines = text.splitlines()
        changed = False
        fields_to_fix = ("validate:", "extract:", "setup_hooks:", "teardown_hooks:")

        for i in range(len(lines)):
            line = lines[i]
            stripped = line.lstrip()
            for field in fields_to_fix:
                if stripped.startswith("- " + field):
                    indent = len(line) - len(stripped)
                    lines[i] = " " * indent + stripped[2:]
                    changed = True
                    break

        if changed:
            filepath.write_text("\n".join(lines) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
        return changed

    changed_files = []
    for f in files:
        text_fixed = False
        path_obj = Path(f)
        if not only_hooks:
            if _fix_invalid_dash_before_fields(path_obj):
                text_fixed = True
            if _fix_url_to_path(path_obj):
                text_fixed = True
            if _fix_steps_spacing(path_obj):
                text_fixed = True

        if text_fixed and str(f) not in changed_files:
            changed_files.append(str(f))

        if only_spacing:
            continue

        raw = path_obj.read_text(encoding="utf-8")
        try:
            obj = yaml.safe_load(raw) or {}
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        modified = False
        if "cases" in obj and isinstance(obj["cases"], list):
            cfg = obj.get("config") or {}
            if not isinstance(cfg, dict):
                cfg = {}
            if _merge_hooks(cfg, obj):
                obj["config"] = cfg
                modified = True
            new_cases = []
            for c in obj["cases"]:
                if not isinstance(c, dict):
                    new_cases.append(c)
                    continue
                c_cfg = c.get("config") or {}
                if not isinstance(c_cfg, dict):
                    c_cfg = {}
                if _merge_hooks(c_cfg, c):
                    c["config"] = c_cfg
                    modified = True
                new_cases.append(c)
            obj["cases"] = new_cases
        elif "steps" in obj and isinstance(obj["steps"], list):
            cfg = obj.get("config") or {}
            if not isinstance(cfg, dict):
                cfg = {}
            if _merge_hooks(cfg, obj):
                obj["config"] = cfg
                modified = True

        if modified:
            path_obj.write_text(yaml.dump(obj, Dumper=_YamlDumper, sort_keys=False, allow_unicode=True), encoding="utf-8")
            if str(f) not in changed_files:
                changed_files.append(str(f))

    if changed_files:
        typer.echo("Fixed files:")
        for p in changed_files:
            typer.echo(f"- {p}")
    else:
        typer.echo("No changes needed.")

from __future__ import annotations

import hashlib
import importlib.util
import os
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, Optional, Sequence


def _module_name_for(path: Path) -> str:
    h = hashlib.sha1(str(path).encode()).hexdigest()[:10]
    return f"drun_hooks_{h}"


def _candidate_filenames() -> Sequence[str]:
    # Allow override via env; support comma-separated list
    env_val = os.environ.get("DRUN_HOOKS_FILE")
    if env_val:
        return [x.strip() for x in env_val.split(",") if x.strip()]
    return ["drun_hooks.py", "hooks.py"]


def find_hooks(start: Path) -> Optional[Path]:
    """Search upwards from start directory for a hooks file.
    Default names: drun_hooks.py, hooks.py (configurable via DRUN_HOOKS_FILE)
    """
    d = start if start.is_dir() else start.parent
    root = Path(d.anchor)
    names = _candidate_filenames()
    while True:
        for name in names:
            candidate = d / name
            if candidate.exists():
                return candidate
        if d == root:
            return None
        d = d.parent


def _import_module_from_path(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(_module_name_for(path), str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load hooks module: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def _collect_callables(mod: ModuleType) -> Dict[str, Any]:
    funcs: Dict[str, Any] = {}
    for name in dir(mod):
        if name.startswith("_"):
            continue
        obj = getattr(mod, name)
        if callable(obj):
            funcs[name] = obj
    return funcs


@lru_cache(maxsize=64)
def get_functions_for(start: Path) -> Dict[str, Any]:
    path = find_hooks(start)
    if not path:
        return {}
    mod = _import_module_from_path(path)
    return _collect_callables(mod)

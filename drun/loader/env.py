from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional, Tuple

import yaml


def _read_kv_file(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    return data


def _read_yaml_vars(path: Path) -> Dict[str, str]:
    obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out: Dict[str, str] = {}
    if isinstance(obj, dict):
        # two forms supported:
        # 1) plain variables dict: { base_url: ..., var1: ..., var2: ... }
        # 2) structured dict: { base_url: ..., headers: {...}, variables: {...} }
        # We flatten variables, and keep base_url/headers if present
        if "variables" in obj and isinstance(obj["variables"], dict):
            for k, v in obj["variables"].items():
                out[str(k)] = v
        for k in ("base_url", "headers"):
            if k in obj:
                out[k] = obj[k]
        # also merge top-level primitive values as variables
        for k, v in obj.items():
            if k not in ("variables", "base_url", "headers") and not isinstance(v, (dict, list)):
                out[str(k)] = v
    return out


def _find_env_yaml_by_name(name: str) -> Optional[Path]:
    candidates = [
        Path("env") / f"{name}.yaml",
        Path("env") / f"{name}.yml",
        Path("envs") / f"{name}.yaml",
        Path("envs") / f"{name}.yml",
        Path("environments") / f"{name}.yaml",
        Path("environments") / f"{name}.yml",
    ]
    for p in candidates:
        if p.exists():
            return p
    # single file with mapping (env.yaml) is optional; if present and has key name, read that subset
    for single in [Path("env.yaml"), Path("env.yml")]:
        if single.exists():
            obj = yaml.safe_load(single.read_text(encoding="utf-8")) or {}
            if isinstance(obj, dict) and name in obj and isinstance(obj[name], dict):
                # write a temp merged file alternative via in-memory
                tmp = obj[name]
                # dump to temp path is unnecessary; handle in caller
                return single  # signal caller to read and pick subsection
    return None


def _read_env_yaml_named(single: Path, name: str) -> Dict[str, str]:
    obj = yaml.safe_load(single.read_text(encoding="utf-8")) or {}
    sec = obj.get(name, {}) if isinstance(obj, dict) else {}
    if not isinstance(sec, dict):
        return {}
    # reuse reader on subsection by dumping to flattened dict
    out: Dict[str, str] = {}
    if "variables" in sec and isinstance(sec["variables"], dict):
        for k, v in sec["variables"].items():
            out[str(k)] = v
    for k in ("base_url", "headers"):
        if k in sec:
            out[k] = sec[k]
    for k, v in sec.items():
        if k not in ("variables", "base_url", "headers") and not isinstance(v, (dict, list)):
            out[str(k)] = v
    return out


def load_environment(env_name: Optional[str], env_file: Optional[str]) -> Dict[str, str]:
    """Load environment variables from named YAML env and/or explicit env file.

    Merge order (low -> high): named YAML env < explicit env file < OS ENV
    Keys are duplicated in lowercase for convenient templating.
    Recognized special keys: base_url, headers.
    """
    merged: Dict[str, str] = {}

    if env_name:
        p = _find_env_yaml_by_name(env_name)
        if p:
            if p.name in ("env.yaml", "env.yml"):
                data = _read_env_yaml_named(p, env_name)
            else:
                data = _read_yaml_vars(p)
            merged.update({k: data[k] for k in data})

    if env_file:
        fp = Path(env_file)
        if fp.exists():
            if fp.suffix.lower() in {".yaml", ".yml"}:
                data = _read_yaml_vars(fp)
            else:
                data = _read_kv_file(fp)
            merged.update(data)

    # OS environment passthrough (ENV_* copied; also copy BASE_URL if present)
    for k, v in os.environ.items():
        if k.startswith("ENV_") or k in {"BASE_URL"}:
            merged[k] = v

    # duplicate lowercase keys for convenience
    lower: Dict[str, str] = {k.lower(): v for k, v in merged.items() if isinstance(v, (str, int, float))}
    merged.update(lower)
    return merged


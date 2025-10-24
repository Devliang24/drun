from __future__ import annotations

import sys
from typing import Any, Dict, List

import yaml


def _ask(prompt: str, *, default: str | None = None, required: bool = False) -> str:
    while True:
        d = f" [{default}]" if default is not None else ""
        v = input(f"{prompt}{d}: ").strip()
        if not v and default is not None:
            v = default
        if v or not required:
            return v
        print("This field is required.")


def generate_mysql_config() -> str:
    """Interactive helper to generate a MYSQL_CONFIG YAML string."""
    cfg: Dict[str, Any] = {}
    print("Generate MYSQL_CONFIG (YAML). Press Enter to accept defaults.")
    while True:
        db_name = _ask("Database name (e.g., main)", required=True)
        roles: List[Dict[str, Any]] = []
        while True:
            print(f"Configure role for '{db_name}' (first role becomes 'default'):")
            mode = _ask("Use DSN string? (y/n)", default="y").lower()
            entry: Dict[str, Any] = {}
            if mode.startswith("y"):
                entry["dsn"] = _ask("DSN", required=True)
            else:
                entry["host"] = _ask("host", default="127.0.0.1")
                entry["port"] = int(_ask("port", default="3306"))
                entry["user"] = _ask("user", required=True)
                entry["password"] = _ask("password", required=True)
                entry["database"] = _ask("database", required=True)
                ch = _ask("charset", default="utf8mb4")
                if ch:
                    entry["charset"] = ch
            tags = _ask("tags (comma-separated)", default="").strip()
            if tags:
                entry["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
            roles.append(entry)
            more = _ask("Add another role to this database? (y/n)", default="n").lower()
            if not more.startswith("y"):
                break

        cfg[db_name] = roles
        cont = _ask("Add another database? (y/n)", default="n").lower()
        if not cont.startswith("y"):
            break

    text = yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True)
    return text


if __name__ == "__main__":
    out = generate_mysql_config()
    sys.stdout.write(out)

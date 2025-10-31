from __future__ import annotations

import sys
from typing import Dict, List


def _ask(prompt: str, *, default: str | None = None, required: bool = False) -> str:
    while True:
        d = f" [{default}]" if default is not None else ""
        v = input(f"{prompt}{d}: ").strip()
        if not v and default is not None:
            v = default
        if v or not required:
            return v
        print("This field is required.")


def _sanitize_name(name: str) -> str:
    return name.upper().strip().replace("-", "_")


def generate_mysql_config() -> str:
    """Interactive helper to generate MYSQL_* environment variable snippets."""

    lines: List[str] = []
    print("Generate MYSQL_* environment variables. Press Enter to accept defaults.")
    while True:
        db_name = _ask("Database name (e.g., main)", required=True)
        db_token = _sanitize_name(db_name or "main")

        db_enabled = _ask("Database enabled? (y/n)", default="y").lower()
        if db_enabled.startswith("n"):
            lines.append(f"MYSQL_{db_token}__ENABLED=false")

        db_tags = _ask("Database tags (comma-separated)", default="").strip()
        if db_tags:
            lines.append(f"MYSQL_{db_token}__TAGS={db_tags}")

        role_index = 0
        while True:
            suggested_role = "default" if role_index == 0 else f"role{role_index+1}"
            role_name = _ask("Role name", default=suggested_role, required=True)
            role_token = _sanitize_name(role_name or suggested_role)

            mode = _ask("Provide DSN string? (y/n)", default="y").lower()
            if mode.startswith("y"):
                dsn = _ask("DSN", required=True)
                lines.append(f"MYSQL_{db_token}__{role_token}__DSN={dsn}")
            else:
                host = _ask("host", default="127.0.0.1")
                port = _ask("port", default="3306")
                user = _ask("user", required=True)
                password = _ask("password", required=True)
                database = _ask("database", required=True)
                charset = _ask("charset", default="utf8mb4")
                lines.append(f"MYSQL_{db_token}__{role_token}__HOST={host}")
                lines.append(f"MYSQL_{db_token}__{role_token}__PORT={port}")
                lines.append(f"MYSQL_{db_token}__{role_token}__USER={user}")
                lines.append(f"MYSQL_{db_token}__{role_token}__PASSWORD={password}")
                lines.append(f"MYSQL_{db_token}__{role_token}__DATABASE={database}")
                if charset:
                    lines.append(f"MYSQL_{db_token}__{role_token}__CHARSET={charset}")

            role_enabled = _ask("Role enabled? (y/n)", default="y").lower()
            if role_enabled.startswith("n"):
                lines.append(f"MYSQL_{db_token}__{role_token}__ENABLED=false")

            role_tags = _ask("Role tags (comma-separated)", default="").strip()
            if role_tags:
                lines.append(f"MYSQL_{db_token}__{role_token}__TAGS={role_tags}")

            role_index += 1
            more_roles = _ask("Add another role for this database? (y/n)", default="n").lower()
            if not more_roles.startswith("y"):
                break

        cont = _ask("Add another database? (y/n)", default="n").lower()
        if not cont.startswith("y"):
            break

    return "\n".join(lines) + ("\n" if lines else "")


if __name__ == "__main__":
    out = generate_mysql_config()
    sys.stdout.write(out)

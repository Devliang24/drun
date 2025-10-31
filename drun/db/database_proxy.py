from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Tuple
from urllib.parse import urlparse

from drun.utils.logging import get_logger
from drun.utils.mask import mask_body


# Local exceptions (exported via utils.errors in a follow-up for reuse)
class InvalidMySQLConfigError(Exception):
    pass


class DatabaseNotConfiguredError(Exception):
    pass


# ---- MySQL driver helpers (kept local so hooks can reuse them without extra deps) ----
_MYSQL_DRIVER_NAME: str | None = None
_MYSQL_DRIVER_MODULE: Any | None = None


def _load_mysql_driver() -> tuple[str, Any]:
    global _MYSQL_DRIVER_NAME, _MYSQL_DRIVER_MODULE
    if _MYSQL_DRIVER_NAME and _MYSQL_DRIVER_MODULE:
        return _MYSQL_DRIVER_NAME, _MYSQL_DRIVER_MODULE
    try:
        import pymysql  # type: ignore

        _MYSQL_DRIVER_NAME = "pymysql"
        _MYSQL_DRIVER_MODULE = pymysql
        return _MYSQL_DRIVER_NAME, _MYSQL_DRIVER_MODULE
    except Exception:
        pass
    try:
        import mysql.connector  # type: ignore

        _MYSQL_DRIVER_NAME = "mysql-connector"
        _MYSQL_DRIVER_MODULE = mysql.connector
        return _MYSQL_DRIVER_NAME, _MYSQL_DRIVER_MODULE
    except Exception:
        pass
    try:
        import MySQLdb  # type: ignore

        _MYSQL_DRIVER_NAME = "mysqlclient"
        _MYSQL_DRIVER_MODULE = MySQLdb
        return _MYSQL_DRIVER_NAME, _MYSQL_DRIVER_MODULE
    except Exception:
        pass
    raise RuntimeError(
        "MySQL support requires installing one of: 'pymysql', 'mysql-connector-python', or 'mysqlclient'."
    )


def _is_connection_alive(driver_name: str, conn: Any) -> bool:
    try:
        if driver_name == "pymysql":
            conn.ping(reconnect=True)
            return True
        if driver_name == "mysql-connector":
            if conn.is_connected():
                return True
            conn.reconnect(attempts=3, delay=1)  # type: ignore[call-arg]
            return conn.is_connected()
        if driver_name == "mysqlclient":
            conn.ping(True)
            return True
    except Exception:
        return False
    return True


def _create_connection(driver_name: str, driver_module: Any, dsn: Mapping[str, Any]) -> Any:
    if driver_name == "pymysql":
        return driver_module.connect(
            host=dsn.get("host"),
            port=int(dsn.get("port") or 3306),
            user=dsn.get("user"),
            password=dsn.get("password"),
            database=dsn.get("database"),
            charset=dsn.get("charset") or "utf8mb4",
            autocommit=True,
            cursorclass=driver_module.cursors.DictCursor,
        )
    if driver_name == "mysql-connector":
        charset = dsn.get("charset") or "utf8mb4"
        conn = driver_module.connect(
            host=dsn.get("host"),
            port=int(dsn.get("port") or 3306),
            user=dsn.get("user"),
            password=dsn.get("password"),
            database=dsn.get("database"),
            charset=charset,
        )
        try:
            conn.autocommit = True  # type: ignore[attr-defined]
        except Exception:
            try:
                conn.autocommit(True)  # type: ignore[call-arg]
            except Exception:
                pass
        if hasattr(conn, "set_charset_collation"):
            try:
                conn.set_charset_collation(charset)
            except Exception:
                pass
        return conn
    if driver_name == "mysqlclient":
        import MySQLdb.cursors  # type: ignore

        charset = dsn.get("charset") or "utf8mb4"
        conn = driver_module.connect(
            host=dsn.get("host"),
            port=int(dsn.get("port") or 3306),
            user=dsn.get("user"),
            passwd=dsn.get("password"),
            db=dsn.get("database"),
            charset=charset,
            cursorclass=MySQLdb.cursors.DictCursor,
        )
        try:
            conn.autocommit(True)
        except Exception:
            try:
                conn.autocommit = True  # type: ignore[attr-defined]
            except Exception:
                pass
        return conn
    raise RuntimeError(f"Unsupported MySQL driver: {driver_name}")


def _open_cursor(driver_name: str, conn: Any):
    if driver_name == "mysql-connector":
        return conn.cursor(dictionary=True)
    return conn.cursor()


# ---- Config parsing helpers ----
def _parse_dsn_string(dsn: str) -> Dict[str, Any]:
    parsed = urlparse(dsn)
    if parsed.scheme and not parsed.scheme.startswith("mysql"):
        raise ValueError(f"Unsupported DSN scheme for MySQL: {parsed.scheme}")
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 3306,
        "user": parsed.username,
        "password": parsed.password,
        "database": parsed.path[1:] if parsed.path.startswith("/") else parsed.path or None,
    }


_BOOL_TRUE = {"1", "true", "yes", "y", "on"}


def _parse_bool(value: str | None, *, default: bool = True) -> bool:
    if value is None:
        return default
    text = str(value).strip().lower()
    if text == "":
        return default
    if text in _BOOL_TRUE:
        return True
    return False


def _split_tags(value: str | None) -> List[str]:
    if not value:
        return []
    items = []
    for part in value.replace(";", ",").split(","):
        token = part.strip()
        if token:
            items.append(token)
    return items


def _strip_quotes(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        return text[1:-1]
    return text


def _parse_env_block(text: str) -> Dict[str, str]:
    pairs: Dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key, val = stripped.split("=", 1)
        pairs[key.strip()] = _strip_quotes(val)
    return pairs


def _split_mysql_key(key: str) -> Tuple[str, Optional[str], str] | None:
    if not key.upper().startswith("MYSQL_"):
        return None
    body = key[6:]
    if "__" in body:
        parts = [p for p in body.split("__") if p != ""]
        if len(parts) == 2:
            return parts[0], None, parts[1]
        if len(parts) >= 3:
            return parts[0], parts[1], "__".join(parts[2:])
        return None
    # Fallback: MYSQL_DB_ROLE_FIELD or MYSQL_DB_FIELD
    if "_" not in body:
        return None
    segments = body.rsplit("_", 2)
    if len(segments) == 2:
        db, field = segments
        return db, None, field
    if len(segments) == 3:
        db, role, field = segments
        return db, role, field
    return None


def _build_config_from_env(source: Mapping[str, str]) -> Tuple[Dict[str, DatabaseConfig], List[str]]:
    db_store: Dict[str, Dict[str, Any]] = {}
    errors: List[str] = []

    for raw_key, raw_value in source.items():
        spec = _split_mysql_key(raw_key)
        if spec is None:
            continue
        db_raw, role_raw, field_raw = spec
        if not db_raw:
            continue
        db_key = db_raw.strip().lower()
        db_entry = db_store.setdefault(
            db_key,
            {
                "name": db_raw.strip() or db_key,
                "enabled": True,
                "tags": set(),
                "roles": {},
            },
        )

        value = _strip_quotes(raw_value)
        field = field_raw.strip().upper()

        if role_raw is None or role_raw.strip() == "":
            if field == "ENABLED":
                db_entry["enabled"] = _parse_bool(value, default=True)
            elif field == "TAGS":
                db_entry["tags"].update(_split_tags(value))
            else:
                errors.append(f"{db_entry['name']}: unsupported field '{field}'")
            continue

        role_key = role_raw.strip().lower()
        role_entry = db_entry["roles"].setdefault(
            role_key,
            {
                "name": role_raw.strip() or role_key,
                "enabled": True,
                "tags": set(),
                "dsn": None,
                "fields": {},
                "order": len(db_entry["roles"]),
            },
        )

        if field == "DSN":
            role_entry["dsn"] = value
        elif field in {"HOST", "USER", "PASSWORD", "DATABASE", "CHARSET"}:
            role_entry["fields"][field.lower()] = value
        elif field == "PORT":
            try:
                role_entry["fields"]["port"] = int(value)
            except Exception:
                errors.append(f"{db_entry['name']}.{role_entry['name']}: PORT must be an integer")
        elif field == "ENABLED":
            role_entry["enabled"] = _parse_bool(value, default=True)
        elif field == "TAGS":
            role_entry["tags"].update(_split_tags(value))
        else:
            errors.append(f"{db_entry['name']}.{role_entry['name']}: unsupported field '{field}'")

    parsed: Dict[str, DatabaseConfig] = {}

    for db_key, db_entry in db_store.items():
        role_configs: Dict[str, RoleConfig] = {}
        for role_key, role_entry in sorted(db_entry["roles"].items(), key=lambda item: item[1]["order"]):
            dsn_info: Dict[str, Any] = {
                "host": "127.0.0.1",
                "port": 3306,
                "user": None,
                "password": None,
                "database": None,
                "charset": "utf8mb4",
            }

            if role_entry["dsn"]:
                try:
                    parsed_dsn = _parse_dsn_string(role_entry["dsn"])
                    for key, val in parsed_dsn.items():
                        if val is not None:
                            dsn_info[key] = val
                except Exception as exc:
                    errors.append(f"{db_entry['name']}.{role_entry['name']}: invalid DSN ({exc})")

            for field_name, field_value in role_entry["fields"].items():
                if field_name == "port":
                    dsn_info["port"] = field_value
                else:
                    dsn_info[field_name] = field_value

            missing = [k for k in ("database", "user", "password") if not dsn_info.get(k)]
            if missing:
                errors.append(
                    f"{db_entry['name']}.{role_entry['name']}: missing {', '.join(missing)}"
                )

            all_tags = set(db_entry["tags"]) | set(role_entry["tags"])
            role_configs[role_key] = RoleConfig(
                name=role_key,
                enabled=bool(role_entry["enabled"]),
                tags=sorted(all_tags),
                dsn=dsn_info,
            )

        if not role_configs:
            errors.append(f"{db_entry['name']}: define at least one role")

        parsed[db_key] = DatabaseConfig(
            name=db_key,
            enabled=bool(db_entry["enabled"]),
            tags=sorted(db_entry["tags"]),
            roles=role_configs,
        )

    return parsed, errors


def _env_hint(db_name: str, role: Optional[str] = None) -> str:
    base = db_name.upper().replace("-", "_")
    if role:
        role_part = role.upper().replace("-", "_")
        return f"MYSQL_{base}__{role_part}__DSN"
    return f"MYSQL_{base}__<ROLE>__DSN"


@dataclass
class RoleConfig:
    name: str
    enabled: bool
    tags: List[str]
    dsn: Dict[str, Any]


@dataclass
class DatabaseConfig:
    name: str
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    roles: MutableMapping[str, RoleConfig] = field(default_factory=dict)


def _sorted_role_names(names: Iterable[str]) -> List[str]:
    def _key(n: str) -> Tuple[int, str]:
        if n == "default":
            return (0, "")
        if n.startswith("default_"):
            try:
                i = int(n.split("_", 1)[1])
                return (1, f"{i:06d}")
            except Exception:
                return (1, n)
        return (2, n)

    return sorted(names, key=_key)


def _mask_dsn(d: Mapping[str, Any]) -> Dict[str, Any]:
    # rely on mask_body for password key
    return mask_body(dict(d))


class DatabaseRoleProxy:
    def __init__(self, manager: "DatabaseManager", db_name: str, role_name: str, role_cfg: RoleConfig, *, logger: Optional[logging.Logger] = None) -> None:
        self._manager = manager
        self.db_name = db_name
        self.role_name = role_name
        self._cfg = role_cfg
        self._driver_name: Optional[str] = None
        self._driver_module: Any = None
        self._conn: Any = None
        self._lock = threading.RLock()
        self._log = logger or get_logger(f"drun.db.{db_name}.{role_name}")
        # stats
        self._create_count = 0
        self._fail_count = 0
        self._query_ms_total = 0.0

    # Allow chained role access: db.main.read
    def __getattr__(self, item: str):  # role switch or method fallback
        if item in {"query", "execute", "ping", "close", "connection"}:
            return getattr(self, item)
        # Treat attribute as another role under the same db (e.g., db.main.read)
        try:
            return self._manager.get(self.db_name, item)
        except Exception:
            raise AttributeError(item)

    def __getitem__(self, role: str) -> "DatabaseRoleProxy":
        return self._manager.get(self.db_name, role)

    @property
    def dsn(self) -> Dict[str, Any]:
        return dict(self._cfg.dsn)

    def _ensure_conn(self) -> Tuple[str, Any]:
        with self._lock:
            if self._conn is not None and self._driver_name is not None:
                if _is_connection_alive(self._driver_name, self._conn):
                    return self._driver_name, self._conn
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

            try:
                dn, dm = _load_mysql_driver()
                self._driver_name, self._driver_module = dn, dm
                conn = _create_connection(dn, dm, self._cfg.dsn)
                self._create_count += 1
                self._conn = conn
                return dn, conn
            except Exception as e:
                self._fail_count += 1
                raise e

    def connection(self) -> Any:
        # Get a live connection (caller must not close it directly unless used via context manager)
        _, conn = self._ensure_conn()
        return conn

    def __enter__(self) -> Any:
        # Provide direct connection for manual usage
        return self.connection()

    def __exit__(self, exc_type, exc, tb) -> None:
        # Keep connection cached; do not close on exit
        return None

    def ping(self) -> bool:
        try:
            dn, conn = self._ensure_conn()
            return _is_connection_alive(dn, conn)
        except Exception:
            return False

    def close(self) -> None:
        with self._lock:
            try:
                if self._conn is not None:
                    self._conn.close()
            except Exception:
                pass
            finally:
                self._conn = None

    def query(self, sql: str) -> Optional[Mapping[str, Any]]:
        dn, conn = self._ensure_conn()
        cur = _open_cursor(dn, conn)
        t0 = time.perf_counter()
        try:
            cur.execute(sql)
            row = cur.fetchone()
            return row
        finally:
            try:
                cur.close()
            except Exception:
                pass
            self._query_ms_total += (time.perf_counter() - t0) * 1000.0

    def execute(self, sql: str) -> int:
        dn, conn = self._ensure_conn()
        cur = _open_cursor(dn, conn)
        t0 = time.perf_counter()
        try:
            affected = cur.execute(sql)
            return int(affected or 0)
        finally:
            try:
                cur.close()
            except Exception:
                pass
            self._query_ms_total += (time.perf_counter() - t0) * 1000.0


class _DBNameAccessor:  # Kept for backward compatibility if referenced elsewhere
    def __init__(self, manager: "DatabaseManager", db_name: str) -> None:
        self._m = manager
        self._db = db_name
    def __getattr__(self, role: str) -> DatabaseRoleProxy:  # pragma: no cover - compat
        return self._m.get(self._db, role)
    def __getitem__(self, role: str) -> DatabaseRoleProxy:  # pragma: no cover - compat
        return self._m.get(self._db, role)
    def __call__(self) -> DatabaseRoleProxy:  # pragma: no cover - compat
        return self._m.get(self._db, None)
    def query(self, sql: str):  # pragma: no cover - compat
        return self().__call__().query(sql)
    def execute(self, sql: str) -> int:  # pragma: no cover - compat
        return self().__call__().execute(sql)
    def ping(self) -> bool:  # pragma: no cover - compat
        return self().__call__().ping()
    def close(self) -> None:  # pragma: no cover - compat
        return self().__call__().close()


class DatabaseManager:
    def __init__(self, config_str: Optional[str] = None, *, logger: Optional[logging.Logger] = None) -> None:
        self._log = logger or get_logger("drun.db")
        self._lock = threading.RLock()
        self._configs: Dict[str, DatabaseConfig] = {}
        self._proxies: Dict[Tuple[str, str], DatabaseRoleProxy] = {}
        self.reload(config_str)

    # Public API
    def available(self, *, tags: Optional[List[str]] = None, include_disabled: bool = False) -> List[str]:
        with self._lock:
            names: List[str] = []
            for cfg in self._configs.values():
                if not include_disabled and not cfg.enabled:
                    continue
                if tags:
                    # Match if DB tags or any role tags overlap
                    tagset = set(cfg.tags)
                    for rc in cfg.roles.values():
                        tagset.update(rc.tags)
                    if not (set(tags) & tagset):
                        continue
                names.append(cfg.name)
            return sorted(names)

    def describe(self, *, mask: bool = True) -> Dict[str, Any]:
        with self._lock:
            out: Dict[str, Any] = {}
            for dbname, cfg in self._configs.items():
                entry: Dict[str, Any] = {
                    "enabled": cfg.enabled,
                    "tags": list(cfg.tags),
                    "roles": {},
                }
                for rn in _sorted_role_names(cfg.roles.keys()):
                    rc = cfg.roles[rn]
                    dsn = rc.dsn if not mask else _mask_dsn(rc.dsn)
                    entry["roles"][rn] = {
                        "enabled": rc.enabled,
                        "tags": list(rc.tags),
                        "dsn": dsn,
                    }
                out[dbname] = entry
            return out

    def get(self, db_name: str, role: Optional[str] = None) -> DatabaseRoleProxy:
        with self._lock:
            key_name = (db_name or "").lower()
            if key_name not in self._configs:
                raise DatabaseNotConfiguredError(
                    f"{db_name}.<role> not configured; define {_env_hint(db_name, role)}"
                )
            cfg = self._configs[key_name]
            role_key = role.lower() if role else None
            if role_key is None:
                role_key = "default" if "default" in cfg.roles else next(iter(_sorted_role_names(cfg.roles.keys())), None)
            if role_key is None or role_key not in cfg.roles:
                missing_role = role or "default"
                raise DatabaseNotConfiguredError(
                    f"{db_name}.{missing_role} not configured; define {_env_hint(db_name, missing_role)}"
                )
            key = (key_name, role_key)
            proxy = self._proxies.get(key)
            if proxy is None:
                rc = cfg.roles[role_key]
                if not cfg.enabled or not rc.enabled:
                    raise DatabaseNotConfiguredError(
                        f"{db_name}.{rc.name} is disabled via MYSQL_* env settings"
                    )
                proxy = DatabaseRoleProxy(self, cfg.name, rc.name, rc, logger=get_logger(f"drun.db.{cfg.name}.{rc.name}"))
                self._proxies[key] = proxy
            return proxy

    # Attribute/index access
    def __getattr__(self, db_name: str) -> DatabaseRoleProxy:
        # Directly return default role proxy so that db.main.query() works
        try:
            return self.get(db_name, None)
        except DatabaseNotConfiguredError as exc:  # pragma: no cover - defensive
            raise AttributeError(db_name) from exc

    def __getitem__(self, db_name: str) -> DatabaseRoleProxy:
        key = db_name.lower()
        if key not in self._configs:
            raise KeyError(db_name)
        return self.get(db_name, None)

    def close_all(self) -> None:
        with self._lock:
            for proxy in list(self._proxies.values()):
                try:
                    proxy.close()
                except Exception:
                    pass
            self._proxies.clear()

    def reload(self, config_str: Optional[str] = None) -> None:
        if config_str is not None and config_str.strip():
            source = _parse_env_block(config_str)
        else:
            source = {k: v for k, v in os.environ.items() if k.upper().startswith("MYSQL_")}

        if not source:
            with self._lock:
                old_proxies = list(self._proxies.values())
                self._proxies.clear()
                self._configs = {}
            for proxy in old_proxies:
                try:
                    proxy.close()
                except Exception:
                    pass
            self._log.info("[DB] Loaded 0 database(s), 0 role(s)")
            if self._log.isEnabledFor(logging.DEBUG):
                self._log.debug("[DB] Config: {}")
            return

        parsed, errors = _build_config_from_env(source)

        if errors:
            raise InvalidMySQLConfigError("Invalid MySQL configuration:\n- " + "\n- ".join(errors))

        with self._lock:
            old_proxies = list(self._proxies.values())
            self._proxies.clear()
            self._configs = parsed
            total_dbs = len(parsed)
            total_roles = sum(len(cfg.roles) for cfg in parsed.values())
            debug_enabled = self._log.isEnabledFor(logging.DEBUG)
            details = json.dumps(self.describe(mask=True), ensure_ascii=False) if debug_enabled else ""

        for proxy in old_proxies:
            try:
                proxy.close()
            except Exception:
                pass

        self._log.info("[DB] Loaded %d database(s), %d role(s)", total_dbs, total_roles)
        if debug_enabled:
            self._log.debug("[DB] Config: %s", details)


_GLOBAL_DB_MANAGER: Optional[DatabaseManager] = None
_GLOBAL_DB_LOCK = threading.Lock()


def get_db(config_str: Optional[str] = None) -> DatabaseManager:
    """Factory to obtain a singleton DatabaseManager.

    When config_str is provided, hot-reload the singleton with new config.
    """
    global _GLOBAL_DB_MANAGER
    with _GLOBAL_DB_LOCK:
        if _GLOBAL_DB_MANAGER is None:
            _GLOBAL_DB_MANAGER = DatabaseManager(config_str)
        elif config_str is not None:
            _GLOBAL_DB_MANAGER.reload(config_str)
        return _GLOBAL_DB_MANAGER


__all__ = [
    "DatabaseManager",
    "DatabaseRoleProxy",
    "InvalidMySQLConfigError",
    "DatabaseNotConfiguredError",
    "get_db",
]

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Tuple
from urllib.parse import urlparse

import yaml

from drun.utils.logging import get_logger
from drun.utils.mask import mask_body
from drun.utils.errors import LoadError  # backward compat alias for parse errors


# Local exceptions (exported via utils.errors in a follow-up for reuse)
class InvalidMySQLConfigError(Exception):
    pass


class DatabaseNotConfiguredError(Exception):
    pass


# ---- MySQL driver helpers (kept local to avoid coupling with sql_validate internals) ----
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


def _normalize_role_entry(value: Any, *, path: str, errors: List[str]) -> Dict[str, Any]:
    meta_enabled = True
    meta_tags: List[str] = []
    raw: Dict[str, Any]
    if value is None:
        errors.append(f"{path}: role entry cannot be null")
        raw = {}
    elif isinstance(value, str):
        raw = {"dsn": value}
    elif isinstance(value, Mapping):
        raw = dict(value)
        # read meta
        if "enabled" in raw and not isinstance(raw["enabled"], bool):
            errors.append(f"{path}.enabled must be boolean")
        else:
            meta_enabled = bool(raw.get("enabled", True))
        tags_val = raw.get("tags")
        if tags_val is not None:
            if isinstance(tags_val, list) and all(isinstance(t, (str, int, float)) for t in tags_val):
                meta_tags = [str(t) for t in tags_val]
            else:
                errors.append(f"{path}.tags must be a list of strings")
        # drop meta keys for DSN normalization
        raw = {k: v for k, v in raw.items() if k not in {"enabled", "tags"}}
    else:
        errors.append(f"{path}: unsupported role entry type {type(value).__name__}")
        raw = {}

    dsn: Dict[str, Any] = {
        "host": "127.0.0.1",
        "port": 3306,
        "user": None,
        "password": None,
        "database": None,
        "charset": "utf8mb4",
    }

    if "dsn" in raw and raw["dsn"] not in (None, ""):
        try:
            parsed = _parse_dsn_string(str(raw["dsn"]))
            dsn.update({k: v for k, v in parsed.items() if v is not None})
        except Exception as e:
            errors.append(f"{path}.dsn invalid: {e}")

    # explicit fields override DSN
    for k in ("host", "user", "password", "database", "charset"):
        v = raw.get(k)
        if v not in (None, ""):
            dsn[k] = v

    if raw.get("port") not in (None, ""):
        try:
            dsn["port"] = int(raw.get("port"))
        except Exception:
            errors.append(f"{path}.port must be an integer")

    # required fields
    if not dsn.get("database"):
        errors.append(f"{path}.database is required (or provide it in DSN)")
    if not dsn.get("user"):
        errors.append(f"{path}.user is required (or provide it in DSN)")
    if dsn.get("password") in (None, ""):
        errors.append(f"{path}.password is required (or provide it in DSN)")

    return {
        "enabled": meta_enabled,
        "tags": meta_tags,
        "dsn": dsn,
    }


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
            for dbname, cfg in self._configs.items():
                if not include_disabled and not cfg.enabled:
                    continue
                if tags:
                    # Match if DB tags or any role tags overlap
                    tagset = set(cfg.tags)
                    for rc in cfg.roles.values():
                        tagset.update(rc.tags)
                    if not (set(tags) & tagset):
                        continue
                names.append(dbname)
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
            if db_name not in self._configs:
                raise DatabaseNotConfiguredError(f"{db_name}.<role> not configured; add it in MYSQL_CONFIG")
            cfg = self._configs[db_name]
            role_name = role or ("default" if "default" in cfg.roles else next(iter(_sorted_role_names(cfg.roles.keys())), None))
            if role_name is None or role_name not in cfg.roles:
                raise DatabaseNotConfiguredError(f"{db_name}.{role or 'default'} not configured; add it in MYSQL_CONFIG")
            key = (db_name, role_name)
            proxy = self._proxies.get(key)
            if proxy is None:
                rc = cfg.roles[role_name]
                if not cfg.enabled or not rc.enabled:
                    raise DatabaseNotConfiguredError(f"{db_name}.{role_name} is disabled in MYSQL_CONFIG")
                proxy = DatabaseRoleProxy(self, db_name, role_name, rc, logger=get_logger(f"drun.db.{db_name}.{role_name}"))
                self._proxies[key] = proxy
            return proxy

    # Attribute/index access
    def __getattr__(self, db_name: str) -> DatabaseRoleProxy:
        # Directly return default role proxy so that db.main.query() works
        if db_name not in self._configs:
            raise AttributeError(db_name)
        return self.get(db_name, None)

    def __getitem__(self, db_name: str) -> DatabaseRoleProxy:
        if db_name not in self._configs:
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
        config_text = config_str if config_str is not None else os.environ.get("MYSQL_CONFIG", "").strip()
        if not config_text:
            # Empty config -> clear
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

        # Parse YAML/JSON via yaml.safe_load (YAML is a superset of JSON)
        try:
            raw = yaml.safe_load(config_text)
        except Exception as e:
            raise InvalidMySQLConfigError(f"Failed to parse MYSQL_CONFIG: {e}") from e

        if raw is None:
            raw = {}
        if not isinstance(raw, Mapping):
            raise InvalidMySQLConfigError("MYSQL_CONFIG must be a mapping of <db_name>: <roles|list>")

        # Build config
        errors: List[str] = []
        parsed: Dict[str, DatabaseConfig] = {}

        for db_name, db_value in raw.items():
            path_base = str(db_name)
            enabled = True
            tags: List[str] = []
            roles_spec: Any = db_value

            if isinstance(db_value, Mapping):
                # DB-level meta
                if "enabled" in db_value and not isinstance(db_value["enabled"], bool):
                    errors.append(f"{path_base}.enabled must be boolean")
                else:
                    enabled = bool(db_value.get("enabled", True))
                tags_val = db_value.get("tags")
                if tags_val is not None:
                    if isinstance(tags_val, list) and all(isinstance(t, (str, int, float)) for t in tags_val):
                        tags = [str(t) for t in tags_val]
                    else:
                        errors.append(f"{path_base}.tags must be a list of strings")
                # Remaining keys are roles
                # But support explicit { roles: {...} } if users prefer nesting
                if "roles" in db_value and isinstance(db_value["roles"], Mapping):
                    roles_spec = db_value["roles"]
                else:
                    # exclude meta keys
                    roles_spec = {k: v for k, v in db_value.items() if k not in {"enabled", "tags"}}

            # Normalize roles
            role_map: Dict[str, RoleConfig] = {}
            if isinstance(roles_spec, list):
                for idx, entry in enumerate(roles_spec):
                    role_name = "default" if idx == 0 else f"default_{idx}"
                    rc_raw = _normalize_role_entry(entry, path=f"{path_base}[{idx}]", errors=errors)
                    role_map[role_name] = RoleConfig(
                        name=role_name,
                        enabled=bool(rc_raw["enabled"]),
                        tags=list(tags) + list(rc_raw.get("tags", [])),
                        dsn=rc_raw["dsn"],
                    )
            elif isinstance(roles_spec, Mapping):
                for role_name, entry in roles_spec.items():
                    rc_raw = _normalize_role_entry(entry, path=f"{path_base}.{role_name}", errors=errors)
                    role_map[str(role_name)] = RoleConfig(
                        name=str(role_name),
                        enabled=bool(rc_raw["enabled"]),
                        tags=list(tags) + list(rc_raw.get("tags", [])),
                        dsn=rc_raw["dsn"],
                    )
            else:
                errors.append(f"{path_base}: roles must be an object or a list")

            parsed[db_name] = DatabaseConfig(name=str(db_name), enabled=enabled, tags=tags, roles=role_map)

        # Validate at least one role per DB and default role presence for convenient access
        for dbname, cfg in parsed.items():
            if not cfg.roles:
                errors.append(f"{dbname}: must define at least one role")

        if errors:
            raise InvalidMySQLConfigError("Invalid MYSQL_CONFIG:\n- " + "\n- ".join(errors))

        # Apply
        with self._lock:
            old_proxies = list(self._proxies.values())
            self._proxies.clear()
            self._configs = parsed
            # Logging: INFO only counts, DEBUG details
            total_dbs = len(parsed)
            total_roles = sum(len(c.roles) for c in parsed.values())
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

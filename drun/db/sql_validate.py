from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple
from urllib.parse import urlparse

from drun.models.sql_validate import SQLValidateConfig
from drun.models.report import AssertionResult
from drun.runner.assertions import compare
from drun.runner.extractors import extract_from_body

SQLValidateConfigLike = Mapping[str, Any] | SQLValidateConfig
RenderFn = Callable[[Any], Any]

_MYSQL_DRIVER_NAME: str | None = None
_MYSQL_DRIVER_MODULE: Any | None = None
_MYSQL_CONN_CACHE: Dict[str, Any] = {}


def _load_mysql_driver() -> tuple[str, Any]:
    """Load an available MySQL driver (prefers PyMySQL)."""
    global _MYSQL_DRIVER_NAME, _MYSQL_DRIVER_MODULE
    if _MYSQL_DRIVER_NAME and _MYSQL_DRIVER_MODULE:
        return _MYSQL_DRIVER_NAME, _MYSQL_DRIVER_MODULE
    try:
        import pymysql  # type: ignore

        _MYSQL_DRIVER_NAME = "pymysql"
        _MYSQL_DRIVER_MODULE = pymysql
        return _MYSQL_DRIVER_NAME, _MYSQL_DRIVER_MODULE
    except ImportError:
        pass
    try:
        import mysql.connector  # type: ignore

        _MYSQL_DRIVER_NAME = "mysql-connector"
        _MYSQL_DRIVER_MODULE = mysql.connector
        return _MYSQL_DRIVER_NAME, _MYSQL_DRIVER_MODULE
    except ImportError:
        pass
    try:
        import MySQLdb  # type: ignore

        _MYSQL_DRIVER_NAME = "mysqlclient"
        _MYSQL_DRIVER_MODULE = MySQLdb
        return _MYSQL_DRIVER_NAME, _MYSQL_DRIVER_MODULE
    except ImportError:
        pass
    raise RuntimeError(
        "MySQL support requires installing one of: 'pymysql', 'mysql-connector-python', or 'mysqlclient'."
    )


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


def _normalize_dsn(value: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "host": "127.0.0.1",
        "port": 3306,
        "user": None,
        "password": None,
        "database": None,
        "charset": "utf8mb4",
    }
    if value is None:
        return base
    if isinstance(value, str):
        base.update({k: v for k, v in _parse_dsn_string(value).items() if v is not None})
        return base
    if isinstance(value, Mapping):
        for key in ("host", "user", "password", "database", "charset"):
            if value.get(key) not in (None, ""):
                base[key] = value[key]
        if value.get("port"):
            base["port"] = int(value["port"])
        return base
    raise TypeError(f"Unsupported DSN type: {type(value)}")


def _collect_env_dsn(env: Mapping[str, Any] | None) -> Dict[str, Any]:
    mapping: Dict[str, Any] = {}
    if not env:
        return mapping
    if env.get("MYSQL_DSN"):
        mapping.update(_normalize_dsn(env["MYSQL_DSN"]))
    key_map = {
        "MYSQL_HOST": "host",
        "MYSQL_PORT": "port",
        "MYSQL_USER": "user",
        "MYSQL_PASSWORD": "password",
        "MYSQL_PASS": "password",
        "MYSQL_DB": "database",
        "MYSQL_DATABASE": "database",
        "MYSQL_CHARSET": "charset",
    }
    for env_key, target_key in key_map.items():
        if env_key in env and env[env_key] not in (None, ""):
            if target_key == "port":
                mapping[target_key] = int(env[env_key])
            else:
                mapping[target_key] = env[env_key]
    return mapping


def _merge_dsn(dsn_override: Any, variables: Mapping[str, Any], env: Mapping[str, Any] | None) -> Dict[str, Any]:
    base = _normalize_dsn(None)
    base.update({k: v for k, v in _collect_env_dsn(env).items() if v not in (None, "")})
    base.update({k: v for k, v in _collect_env_dsn(variables).items() if v not in (None, "")})
    if variables.get("mysql_dsn"):
        base.update({k: v for k, v in _normalize_dsn(variables["mysql_dsn"]).items() if v not in (None, "")})
    if isinstance(variables.get("mysql"), Mapping):
        base.update({k: v for k, v in _normalize_dsn(variables["mysql"]).items() if v not in (None, "")})
    if dsn_override is not None:
        base.update({k: v for k, v in _normalize_dsn(dsn_override).items() if v not in (None, "")})
    if not base.get("database"):
        raise ValueError(
            "MySQL assertion requires a database name. Set MYSQL_DB / MYSQL_DATABASE or provide dsn.database."
        )
    if not base.get("user"):
        raise ValueError("MySQL assertion requires MYSQL_USER or dsn.user.")
    if base.get("password") in (None, ""):
        raise ValueError("MySQL assertion requires MYSQL_PASSWORD or dsn.password.")
    return base


def _mysql_conn_key(dsn: Mapping[str, Any]) -> str:
    return f"{dsn.get('host')}:{dsn.get('port')}:{dsn.get('database')}:{dsn.get('user')}"


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


def _ensure_connection(dsn: Mapping[str, Any]) -> Tuple[str, Any]:
    driver_name, driver_module = _load_mysql_driver()
    key = _mysql_conn_key(dsn)
    conn = _MYSQL_CONN_CACHE.get(key)
    if conn is not None:
        if _is_connection_alive(driver_name, conn):
            return driver_name, conn
        try:
            conn.close()
        except Exception:
            pass
        _MYSQL_CONN_CACHE.pop(key, None)
    conn = _create_connection(driver_name, driver_module, dsn)
    _MYSQL_CONN_CACHE[key] = conn
    return driver_name, conn


def _open_cursor(driver_name: str, conn: Any):
    if driver_name == "mysql-connector":
        return conn.cursor(dictionary=True)
    return conn.cursor()


def _response_lookup(expr: str, response: Mapping[str, Any]) -> Any:
    e = expr.strip()
    if e in ("$", "$body"):
        return response.get("body")
    if e == "$response":
        return response
    if e == "$status_code":
        return response.get("status_code")
    if e == "$headers":
        return response.get("headers")
    if e == "$elapsed_ms":
        return response.get("elapsed_ms")
    if e == "$url":
        return response.get("url")
    if e == "$method":
        return response.get("method")
    if e.startswith("$headers."):
        key = e.split(".", 1)[1]
        headers = response.get("headers") or {}
        key_lower = key.lower()
        for h_key, h_val in headers.items():
            if str(h_key).lower() == key_lower:
                return h_val
        return None
    body = response.get("body")
    if e.startswith("$."):
        return extract_from_body(body, e[2:])
    if e.startswith("$["):
        return extract_from_body(body, e[1:])
    if e.startswith("$"):
        return extract_from_body(body, e.lstrip("$"))
    return expr


def _resolve_expected(value: Any, response: Mapping[str, Any], variables: Mapping[str, Any], env: Mapping[str, Any]) -> Any:
    if isinstance(value, str):
        if value.startswith("$env."):
            return env.get(value[5:])
        if value.startswith("$var.") or value.startswith("$variables."):
            key = value.split(".", 1)[1]
            return variables.get(key)
        if value.startswith("$") and not value.startswith("$env.") and not value.startswith("$var.") and not value.startswith("$variables."):
            return _response_lookup(value, response)
        if value.startswith("var:"):
            key = value[4:]
            return variables.get(key)
        if value.startswith("env:"):
            key = value[4:]
            return env.get(key)
    if isinstance(value, Mapping):
        source = value.get("source")
        if source == "response":
            path = value.get("path", value.get("value"))
            if path is None:
                return None
            return _response_lookup(str(path), response)
        if source in ("variables", "var"):
            key = value.get("key", value.get("value"))
            if key is None:
                return None
            return variables.get(str(key))
        if source in ("env", "environment"):
            key = value.get("key", value.get("value"))
            if key is None:
                return None
            return env.get(str(key))
        if "value" in value:
            nested = _resolve_expected(value["value"], response, variables, env)
            return nested
    return value


def _format_query_label(query: str) -> str:
    q = " ".join(str(query).split())
    return q[:60] + ("..." if len(q) > 60 else "")


def _extract_sql_value(row: Mapping[str, Any], expr: str) -> Any:
    if not isinstance(expr, str):
        raise TypeError("sql_validate.extract expressions must be strings starting with '$'.")
    path = expr.strip()
    if not path.startswith("$"):
        raise ValueError("sql_validate.extract expressions must start with '$', e.g. '$status'.")
    jmes_expr = path[1:]
    if jmes_expr.startswith("."):
        jmes_expr = jmes_expr[1:]
    if not jmes_expr:
        return row
    return extract_from_body(row, jmes_expr)


def _iter_expectations(expectations: Any) -> Iterable[Tuple[str, str, Any]]:
    if isinstance(expectations, Mapping):
        for column, expect_cfg in expectations.items():
            comparator = "eq"
            target = expect_cfg
            if isinstance(expect_cfg, Mapping):
                comparator = str(expect_cfg.get("comparator", comparator))
                if "value" in expect_cfg:
                    target = expect_cfg["value"]
                elif "expect" in expect_cfg:
                    target = expect_cfg["expect"]
            yield str(column), comparator, target
        return

    if isinstance(expectations, Sequence) and not isinstance(expectations, (str, bytes, bytearray)):
        for entry in expectations:
            if not isinstance(entry, Mapping):
                raise TypeError("sql_validate expect list items must be mappings of comparator -> [column, expect]")
            if len(entry) != 1:
                raise TypeError("sql_validate expect list items must contain exactly one comparator key")
            comparator, payload = next(iter(entry.items()))
            if isinstance(payload, (list, tuple)):
                if len(payload) < 2:
                    raise TypeError("sql_validate expect comparator payload must be [column, expected]")
                column = payload[0]
                target = payload[1]
            elif isinstance(payload, Mapping):
                column = payload.get("check") or payload.get("column") or payload.get("field")
                target = payload.get("value") if "value" in payload else payload.get("expect")
                if column is None or target is None:
                    raise TypeError("sql_validate expect dict payload must include column/check and value/expect")
            else:
                raise TypeError("sql_validate expect comparator payload must be list or mapping")
            yield str(column), str(comparator), target
        return

    raise TypeError("sql_validate.expect must be a mapping or comparator list")


def run_sql_validate(
    configs: Sequence[SQLValidateConfigLike],
    *,
    response: Mapping[str, Any],
    variables: Mapping[str, Any],
    env: Mapping[str, Any] | None,
    render: RenderFn | None = None,
    logger: logging.Logger | None = None,
) -> Tuple[List[AssertionResult], Dict[str, Any]]:
    if not configs:
        return [], {}

    env_map = env or {}
    results: List[AssertionResult] = []
    updates: Dict[str, Any] = {}

    for cfg in configs:
        cfg_obj = cfg if isinstance(cfg, SQLValidateConfig) else SQLValidateConfig.model_validate(cfg)
        rendered_cfg_raw = cfg_obj.model_dump()
        rendered_cfg = render(rendered_cfg_raw) if render else rendered_cfg_raw
        if not isinstance(rendered_cfg, Mapping):
            raise TypeError("Rendered sql_validate configuration must be a mapping.")

        query = str(rendered_cfg.get("query") or cfg_obj.query).strip()
        if "| params=" in query:
            raise ValueError("sql_validate.query no longer supports '| params=...'; inline variables directly in SQL.")
        dsn = _merge_dsn(rendered_cfg.get("dsn"), variables, env_map)
        driver_name, conn = _ensure_connection(dsn)
        cursor = _open_cursor(driver_name, conn)
        query_label = _format_query_label(query)
        if logger:
            logger.info(f"[SQL] {query_label}")
        description = None
        try:
            cursor.execute(query)
            description = cursor.description
            fetch_mode = str(rendered_cfg.get("fetch") or "one").lower()
            if fetch_mode not in ("one", "first", "single"):
                raise ValueError("sql_validate.fetch currently only supports 'one'")
            row = cursor.fetchone()
        finally:
            try:
                cursor.close()
            except Exception:
                pass

        allow_empty = bool(rendered_cfg.get("allow_empty") or rendered_cfg.get("optional"))
        q_label = query_label

        if not row:
            if allow_empty:
                results.append(
                    AssertionResult(
                        check=f"sql.row_exists[{q_label}]",
                        comparator="eq",
                        expect=False,
                        actual=False,
                        passed=True,
                        message="Query returned no rows (allowed).",
                    )
                )
                continue
            else:
                results.append(
                    AssertionResult(
                        check=f"sql.row_exists[{q_label}]",
                        comparator="eq",
                        expect=True,
                        actual=False,
                        passed=False,
                        message="SQL validation: query returned no rows.",
                    )
                )
                if logger:
                    logger.error(f"[SQL] validation failed: no rows for {q_label}")
                continue

        results.append(
            AssertionResult(
                check=f"sql.row_exists[{q_label}]",
                comparator="eq",
                expect=True,
                actual=True,
                passed=True,
            )
        )

        if isinstance(row, Mapping):
            row_map: MutableMapping[str, Any] = dict(row)
        else:
            row_map = {}
            if description:
                cols = [col[0] for col in description]
                row_map.update({col: val for col, val in zip(cols, row)})

        expectations = rendered_cfg.get("expect") or rendered_cfg.get("expects")
        if expectations is not None:
            for column, comparator, target in _iter_expectations(expectations):
                actual = row_map.get(column)
                expected_value = _resolve_expected(target, response, variables, env_map)
                passed, err = compare(comparator, actual, expected_value)
                results.append(
                    AssertionResult(
                        check=f"sql.{column}",
                        comparator=comparator,
                        expect=expected_value,
                        actual=actual,
                        passed=bool(passed),
                        message=err,
                    )
                )
                if not passed and logger:
                    logger.error(
                        f"[SQL] expectation failed for column '{column}': "
                        f"actual={actual!r} comparator={comparator} expected={expected_value!r} ({err})"
                    )
                elif logger:
                    logger.info(
                        f"[SQL] expectation ok for column '{column}': "
                        f"actual={actual!r} comparator={comparator} expected={expected_value!r}"
                    )

        extract_cfg = rendered_cfg.get("extract")
        if isinstance(extract_cfg, Mapping):
            for var_name, expr in extract_cfg.items():
                value = _extract_sql_value(row_map, expr)
                updates[str(var_name)] = value
                if logger:
                    logger.info(f"[SQL] extract var: {var_name} = {value!r}")

    return results, updates


__all__ = ["run_sql_validate", "SQLValidateConfigLike"]

"""
Drun Hooks - Custom functions for test cases

Usage:
- Template functions: ${ts()}, ${uid()}, ${md5($password)}
- Setup hooks: setup_hooks: [${setup_hook_sign_request($request)}]
"""
import hashlib
import hmac
import time
import uuid
from typing import Any

from drun.db.database_proxy import get_db


# ==================== Template Functions ====================

def ts() -> int:
    """Return current Unix timestamp (seconds)"""
    return int(time.time())


def uid() -> str:
    """Generate UUID with hyphens"""
    return str(uuid.uuid4())


def short_uid(length: int = 8) -> str:
    """Generate short UUID (no hyphens, truncated)"""
    return str(uuid.uuid4()).replace("-", "")[:length]


def md5(text: str) -> str:
    """Calculate MD5 hash"""
    return hashlib.md5(str(text).encode("utf-8")).hexdigest()


def sha256(text: str) -> str:
    """Calculate SHA256 hash"""
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


# ==================== Setup Hooks ====================

def setup_hook_sign_request(request: dict, variables: dict = None, env: dict = None) -> dict:
    """Add HMAC-SHA256 signature to request headers"""
    env = env or {}
    secret = env.get("APP_SECRET", "default-secret").encode()
    method = request.get("method", "GET")
    url = request.get("url", "")
    timestamp = str(int(time.time()))

    message = f"{method}|{url}|{timestamp}".encode()
    signature = hmac.new(secret, message, hashlib.sha256).hexdigest()

    headers = request.setdefault("headers", {})
    headers["X-Timestamp"] = timestamp
    headers["X-Signature"] = signature

    return {"last_signature": signature, "last_timestamp": timestamp}


# ==================== Database Functions ====================

def _get_db_proxy(db_name: str = "main", role: str | None = None):
    """Get database proxy by name/role"""
    return get_db().get(db_name, role)


def setup_hook_assert_sql(
    identifier: Any,
    *,
    query: str | None = None,
    db_name: str = "main",
    role: str | None = None,
) -> dict:
    """Assert SQL query returns non-empty result before step execution"""
    proxy = _get_db_proxy(db_name=db_name, role=role)
    sql = query or f"SELECT * FROM users WHERE id = {identifier}"
    if not proxy.query(sql):
        raise AssertionError(f"SQL returned empty: {sql}")
    return {"sql_assert_ok": True}


def expected_sql_value(
    identifier: Any,
    *,
    query: str | None = None,
    column: str = "status",
    db_name: str = "main",
    role: str | None = None,
) -> Any:
    """Get column value from SQL query for validation"""
    proxy = _get_db_proxy(db_name=db_name, role=role)
    sql = query or f"SELECT {column} FROM users WHERE id = {identifier}"
    row = proxy.query(sql)
    if not row:
        raise AssertionError(f"SQL returned empty: {sql}")
    return row.get(column)

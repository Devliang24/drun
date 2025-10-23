"""
示例 hooks：在 YAML 模板中可调用以下函数。

支持用法（仅 Dollar 表达式）：
- ${ts()}, ${md5('abc')}, ${sign('demo', 123)}
"""

import hashlib
import time
import uuid
from typing import Any
import hmac


def ts() -> int:
    return int(time.time())


def md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


def sign(app_key: str, ts: int) -> str:
    return md5(f"{app_key}{ts}")


def uuid4() -> str:
    return str(uuid.uuid4())


def echo(x: Any) -> Any:
    return x


def sum_two_int(a: int, b: int) -> int:
    return int(a) + int(b)


def uid() -> str:
    """Hex-only unique id (32 chars)."""
    return uuid.uuid4().hex


def short_uid(n: int = 8) -> str:
    """Short hex id, default 8 chars (alphanumeric)."""
    n = int(n)
    if n < 1:
        n = 1
    if n > 32:
        n = 32
    return uuid.uuid4().hex[:n]


# ---------- Hooks examples ----------

def sign_request(request: dict, variables: dict | None = None, env: dict | None = None) -> dict | None:
    """Example setup hook: add a simple signature header.
    In real cases compute HMAC of method+url+ts with secret from env.
    """
    headers = request.setdefault('headers', {})
    ts_val = str(int(time.time()))
    raw = f"{request.get('method','GET')}|{request.get('url','')}|{ts_val}"
    sig = hashlib.md5(raw.encode()).hexdigest()
    headers['X-Timestamp'] = ts_val
    headers['X-Signature'] = sig
    return {'last_signature': sig}


def assert_status_ok(response: dict, variables: dict | None = None, env: dict | None = None) -> None:
    """Example teardown hook: ensure status_code==200 else raise."""
    if int(response.get('status_code', 0)) != 200:
        raise AssertionError(f"status not 200: {response.get('status_code')}")


def capture_request_id(response: dict, variables: dict | None = None, env: dict | None = None) -> dict | None:
    """Extract request_id from response body (if present) into variables."""
    body = response.get('body') or {}
    if isinstance(body, dict) and 'request_id' in body:
        return {'request_id': body['request_id']}
    return None


# Prefixed wrappers (DSL-style naming convention)
def setup_hook_sign_request(request: dict, variables: dict | None = None, env: dict | None = None) -> dict | None:
    
    return sign_request(request=request, variables=variables or {}, env=env or {})


def teardown_hook_assert_status_ok(response: dict, variables: dict | None = None, env: dict | None = None) -> None:
    return assert_status_ok(response=response, variables=variables or {}, env=env or {})


def teardown_hook_capture_request_id(response: dict, variables: dict | None = None, env: dict | None = None) -> dict | None:
    return capture_request_id(response=response, variables=variables or {}, env=env or {})


def setup_hook_api_key(request: dict, variables: dict | None = None, env: dict | None = None) -> None:
    """Inject API Key header from environment/variables.
    Priority: env['API_KEY'] > variables['API_KEY'] > env['X_API_KEY'] > variables['X_API_KEY'].
    """
    api_key = None
    srcs = [
        (env or {}).get('API_KEY'),
        (variables or {}).get('API_KEY'),
        (env or {}).get('X_API_KEY'),
        (variables or {}).get('X_API_KEY'),
    ]
    for v in srcs:
        if isinstance(v, str) and v.strip():
            api_key = v.strip()
            break
    if api_key:
        headers = request.setdefault('headers', {})
        headers['X-API-Key'] = api_key
    return None


def setup_hook_hmac_sign(request: dict, variables: dict | None = None, env: dict | None = None) -> dict | None:
    """HMAC-SHA256 签名示例：使用 APP_SECRET 对 'METHOD|URL|TS' 计算 HMAC，写入 X-HMAC/X-Timestamp。
    APP_SECRET 从 env['APP_SECRET'] 或 variables['APP_SECRET'] 读取。
    """
    secret = ((env or {}).get('APP_SECRET') or (variables or {}).get('APP_SECRET') or '').encode()
    method = str(request.get('method', 'GET')).upper()
    url = str(request.get('url', ''))
    ts_val = str(int(time.time()))
    raw = f"{method}|{url}|{ts_val}".encode()
    sig = hmac.new(secret, raw, hashlib.sha256).hexdigest()
    headers = request.setdefault('headers', {})
    headers['X-Timestamp'] = ts_val
    headers['X-HMAC'] = sig
    return {'last_hmac': sig}

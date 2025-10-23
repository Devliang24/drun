from __future__ import annotations

import base64
import hashlib
import hmac
import os
import random
import time
import uuid as _uuid
from typing import Any


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())


def uuid() -> str:
    return str(_uuid.uuid4())


def random_int(min: int, max: int) -> int:  # noqa: A002 - shadowing
    return random.randint(int(min), int(max))


def base64_encode(s: Any) -> str:
    if isinstance(s, str):
        s = s.encode()
    return base64.b64encode(s).decode()


def hmac_sha256(key: str, msg: str) -> str:
    return hmac.new(key.encode(), msg.encode(), hashlib.sha256).hexdigest()


BUILTINS = {
    "now": now,
    "uuid": uuid,
    "random_int": random_int,
    "base64_encode": base64_encode,
    "hmac_sha256": hmac_sha256,
}

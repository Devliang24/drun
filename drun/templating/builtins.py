from __future__ import annotations

import base64
import hashlib
import hmac
import os
import random
import time
import uuid as _uuid
from typing import Any

try:
    from faker import Faker
    _faker = Faker()
except ImportError:
    _faker = None


def _check_faker():
    if _faker is None:
        raise ImportError("Using 'fake_*' functions requires the 'Faker' library. Install it via 'pip install Faker'.")


def fake_name() -> str:
    _check_faker()
    return _faker.name()


def fake_email() -> str:
    _check_faker()
    return _faker.email()


def fake_address() -> str:
    _check_faker()
    return _faker.address()


def fake_city() -> str:
    _check_faker()
    return _faker.city()


def fake_text(max_nb_chars: int = 200) -> str:
    _check_faker()
    return _faker.text(max_nb_chars=max_nb_chars)


def fake_url() -> str:
    _check_faker()
    return _faker.url()


def fake_phone_number() -> str:
    _check_faker()
    return _faker.phone_number()


def fake_company() -> str:
    _check_faker()
    return _faker.company()


def fake_date() -> str:
    _check_faker()
    return _faker.date()


def fake_ipv4() -> str:
    _check_faker()
    return _faker.ipv4()


def fake_user_agent() -> str:
    _check_faker()
    return _faker.user_agent()


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
    "fake_name": fake_name,
    "fake_email": fake_email,
    "fake_address": fake_address,
    "fake_city": fake_city,
    "fake_text": fake_text,
    "fake_url": fake_url,
    "fake_phone_number": fake_phone_number,
    "fake_company": fake_company,
    "fake_date": fake_date,
    "fake_ipv4": fake_ipv4,
    "fake_user_agent": fake_user_agent,
}

"""Retry configuration model.

``retry: 3`` is shorthand for ``{"max": 4}`` — 1 initial attempt + 3 retries.
``retry: {max: 10, every: "2s"}`` polls every 2 seconds up to 10 times.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RetryConfig(BaseModel):
    """Full retry configuration.

    Fields:
        max: Total attempts (including the first).  Must be >= 1.
        every: Duration string between attempts (e.g. "2s", "500ms").
    """

    max: int = Field(ge=1)
    every: str = "0s"


def get_retry_max(retry: int | RetryConfig | None) -> int:
    """Return total attempts (at least 1)."""
    if retry is None:
        return 1
    if isinstance(retry, RetryConfig):
        return retry.max
    if isinstance(retry, int):
        return max(retry + 1, 1)  # N extra retries = N+1 total
    return 1


def get_retry_every(retry: int | RetryConfig | None) -> str:
    """Return the every duration string (default "0s")."""
    if isinstance(retry, RetryConfig):
        return retry.every
    return "0s"

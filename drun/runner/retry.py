"""Retry utilities: duration parsing and backoff computation."""

from __future__ import annotations

import re
import time


def parse_duration(s: str) -> float:
    """Parse a duration string like "2s", "500ms", "0.5s" into seconds (float).

    Supports: s (seconds), ms (milliseconds).  Returns seconds.
    """
    s = s.strip().lower()
    if not s:
        return 0.0

    if s.endswith("ms"):
        try:
            return float(s[:-2].strip()) / 1000.0
        except ValueError:
            raise ValueError(f"Invalid duration: {s!r}")

    if s.endswith("s"):
        try:
            return float(s[:-1].strip())
        except ValueError:
            raise ValueError(f"Invalid duration: {s!r}")

    raise ValueError(f"Invalid duration: {s!r} (expected e.g. '2s' or '500ms')")


def sleep_every(every: str, attempt: int) -> None:
    """Sleep for the duration given by *every* (constant delay)."""
    secs = parse_duration(every)
    if secs > 0:
        time.sleep(secs)

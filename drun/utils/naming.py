"""Naming utilities shared across CLI, importers, and convert logic."""

from __future__ import annotations

import re
from typing import Optional


def derive_case_name(base: Optional[str], step_name: Optional[str], idx: int) -> str:
    label = (step_name or "").strip() or f"Step {idx}"
    base = (base or "Imported Case").strip() or "Imported Case"
    combined = f"{base} - {label}"
    return combined.strip()


def sanitize_var_name(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_]", "_", str(name or "").strip())
    if not s:
        s = "var"
    if s[0].isdigit():
        s = f"v_{s}"
    return s
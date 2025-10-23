from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ImportedStep:
    name: str
    method: str
    url: str  # absolute or path
    params: Dict[str, Any] | None = None
    headers: Dict[str, str] | None = None
    body: Any | None = None
    data: Any | None = None
    files: Any | None = None
    auth: Dict[str, str] | None = None  # {type: basic|bearer, ...}


@dataclass
class ImportedCase:
    name: str
    base_url: Optional[str] = None
    steps: List[ImportedStep] = field(default_factory=list)
    variables: Optional[Dict[str, Any]] = None

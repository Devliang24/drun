from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Config(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    variables: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, str] = Field(default_factory=dict)
    timeout: Optional[float] = None
    verify: Optional[bool] = None
    tags: List[str] = Field(default_factory=list)


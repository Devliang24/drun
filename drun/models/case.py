from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .config import Config
from .step import Step


class Case(BaseModel):
    config: Config = Field(default_factory=Config)
    parameters: Optional[Any] = None  # list[dict] or dict[str, list]
    steps: List[Step]
    setup_hooks: List[str] = Field(default_factory=list)
    teardown_hooks: List[str] = Field(default_factory=list)
    # inherited from suite (loader will fill)
    suite_setup_hooks: List[str] = Field(default_factory=list)
    suite_teardown_hooks: List[str] = Field(default_factory=list)


class Suite(BaseModel):
    config: Config = Field(default_factory=Config)
    cases: List[Case]
    setup_hooks: List[str] = Field(default_factory=list)
    teardown_hooks: List[str] = Field(default_factory=list)

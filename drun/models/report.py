from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AssertionResult(BaseModel):
    check: str
    comparator: str
    expect: Any
    actual: Any
    passed: bool
    message: Optional[str] = None


class StepResult(BaseModel):
    name: str
    request: Dict[str, Any] = Field(default_factory=dict)
    response: Dict[str, Any] = Field(default_factory=dict)
    asserts: List[AssertionResult] = Field(default_factory=list)
    extracts: Dict[str, Any] = Field(default_factory=dict)
    curl: Optional[str] = None
    status: str  # passed|failed|skipped
    duration_ms: float = 0.0
    error: Optional[str] = None


class CaseInstanceResult(BaseModel):
    name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    steps: List[StepResult] = Field(default_factory=list)
    status: str  # passed|failed|skipped
    duration_ms: float = 0.0
    # Optional source file path for better reporting grouping (e.g., Allure suite label)
    source: Optional[str] = None


class RunReport(BaseModel):
    summary: Dict[str, Any]
    cases: List[CaseInstanceResult]

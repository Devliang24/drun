from __future__ import annotations

import base64
from os import PathLike
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def to_report_safe(value: Any) -> Any:
    if isinstance(value, memoryview):
        value = value.tobytes()
    elif isinstance(value, bytearray):
        value = bytes(value)

    if isinstance(value, bytes):
        return {
            "type": "bytes",
            "length": len(value),
            "base64": base64.b64encode(value).decode("ascii"),
        }

    if isinstance(value, PathLike):
        return str(value)

    if hasattr(value, "read"):
        return {
            "type": "file-like",
            "name": getattr(value, "name", None),
        }

    if isinstance(value, list):
        return [to_report_safe(item) for item in value]

    if isinstance(value, tuple):
        return [to_report_safe(item) for item in value]

    if isinstance(value, dict):
        return {str(key): to_report_safe(item) for key, item in value.items()}

    return value


class NotifyResult(BaseModel):
    channel: str   # feishu, email, dingtalk
    status: str    # success, failed


class AssertionResult(BaseModel):
    check: str
    comparator: str
    expect: Any
    actual: Any
    passed: bool
    message: Optional[str] = None


class StepResult(BaseModel):
    name: str
    origin_step_name: Optional[str] = None
    repeat_index: Optional[int] = None
    repeat_no: Optional[int] = None
    repeat_total: Optional[int] = None
    request: Dict[str, Any] = Field(default_factory=dict)
    response: Dict[str, Any] = Field(default_factory=dict)
    asserts: List[AssertionResult] = Field(default_factory=list)
    extracts: Dict[str, Any] = Field(default_factory=dict)
    curl: Optional[str] = None
    status: str  # passed|failed|skipped
    duration_ms: float = 0.0
    error: Optional[str] = None
    # httpstat 字段已移除


class CaseInstanceResult(BaseModel):
    name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    steps: List[StepResult] = Field(default_factory=list)
    status: str  # passed|failed|skipped
    duration_ms: float = 0.0
    # Optional source file path for better reporting grouping (e.g., Allure suite label)
    source: Optional[str] = None
    # Notification info
    notify_channels: List[str] = Field(default_factory=list)
    notify_results: List[NotifyResult] = Field(default_factory=list)


class RunReport(BaseModel):
    summary: Dict[str, Any]
    cases: List[CaseInstanceResult]
    environment: Optional[str] = None  # 环境名称 (如: dev, staging, prod)

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from .request import StepRequest
from .validators import Validator, normalize_validators
class Step(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str
    variables: Dict[str, Any] = Field(default_factory=dict)
    request: StepRequest
    extract: Dict[str, str] = Field(default_factory=dict)
    validators: List[Validator] = Field(default_factory=list, alias="validate")
    setup_hooks: List[str] = Field(default_factory=list)
    teardown_hooks: List[str] = Field(default_factory=list)
    skip: Optional[str | bool] = None
    retry: int = 0
    retry_backoff: float = 0.5

    @classmethod
    def model_validate_obj(cls, data: Dict[str, Any]) -> "Step":
        if "validate" in data:
            data = {**data, "validate": normalize_validators(data["validate"]) }
        if "sql_validate" in data:
            raise ValueError(
                "'sql_validate' is no longer supported in steps. Use setup/teardown hooks to perform SQL checks."
            )
        return cls.model_validate(data)

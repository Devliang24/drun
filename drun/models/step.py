from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from pydantic.config import ConfigDict

from .request import StepRequest
from .validators import Validator, normalize_validators
from .sql_validate import SQLValidateConfig


class Step(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str
    variables: Dict[str, Any] = Field(default_factory=dict)
    request: StepRequest
    extract: Dict[str, str] = Field(default_factory=dict)
    validators: List[Validator] = Field(default_factory=list, alias="validate")
    setup_hooks: List[str] = Field(default_factory=list)
    teardown_hooks: List[str] = Field(default_factory=list)
    sql_validate: List[SQLValidateConfig] = Field(default_factory=list)
    skip: Optional[str | bool] = None
    retry: int = 0
    retry_backoff: float = 0.5

    @classmethod
    def model_validate_obj(cls, data: Dict[str, Any]) -> "Step":
        if "validate" in data:
            data = {**data, "validate": normalize_validators(data["validate"]) }
        return cls.model_validate(data)

    @field_validator("sql_validate", mode="before")
    @classmethod
    def _normalize_sql_validate(cls, value: Any) -> List[Any]:
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            seq = list(value)
        else:
            seq = [value]

        fixed: List[Any] = []
        for item in seq:
            if isinstance(item, dict):
                if "optional" in item and "allow_empty" not in item:
                    item = {**item, "allow_empty": item["optional"]}
            fixed.append(item)
        return fixed

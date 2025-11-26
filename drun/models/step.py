from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, model_validator
from pydantic.config import ConfigDict

from .request import StepRequest
from .validators import Validator, normalize_validators


class Step(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str
    variables: Dict[str, Any] = Field(default_factory=dict)
    request: Optional[StepRequest] = None
    invoke: Optional[str] = None
    extract: Dict[str, str] = Field(default_factory=dict)
    export: Optional[Union[Dict[str, Any], List[str]]] = None
    validators: List[Validator] = Field(default_factory=list, alias="validate")
    setup_hooks: List[str] = Field(default_factory=list)
    teardown_hooks: List[str] = Field(default_factory=list)
    skip: Optional[str | bool] = None
    retry: int = 0
    retry_backoff: float = 0.5

    @model_validator(mode="after")
    def check_request_or_invoke(self) -> "Step":
        """Ensure step has either request or invoke, not both."""
        if self.request is not None and self.invoke is not None:
            raise ValueError("Step cannot have both 'request' and 'invoke'. Use one or the other.")
        if self.request is None and self.invoke is None:
            raise ValueError("Step must have either 'request' or 'invoke'.")
        return self

    @classmethod
    def model_validate_obj(cls, data: Dict[str, Any]) -> "Step":
        if "validate" in data:
            data = {**data, "validate": normalize_validators(data["validate"]) }
        if "sql_validate" in data:
            raise ValueError(
                "'sql_validate' is no longer supported in steps. Use setup/teardown hooks to perform SQL checks."
            )
        return cls.model_validate(data)

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, model_validator
from pydantic.config import ConfigDict

from .request import StepRequest
from .validators import Validator, normalize_validators


class StepResponseConfig(BaseModel):
    save_body_to: Optional[str] = None


class Step(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str
    variables: Dict[str, Any] = Field(default_factory=dict)
    request: Optional[StepRequest] = None
    response: Optional[StepResponseConfig] = None
    invoke: Optional[str] = None
    invoke_case_name: Optional[str] = None
    invoke_case_names: List[str] = Field(default_factory=list)
    extract: Dict[str, str] = Field(default_factory=dict)
    export: Optional[Union[Dict[str, Any], List[str]]] = None
    validators: List[Validator] = Field(default_factory=list, alias="validate")
    setup_hooks: List[str] = Field(default_factory=list)
    teardown_hooks: List[str] = Field(default_factory=list)
    skip: Optional[str | bool] = None
    repeat: Union[int, str, None] = 1
    retry: int = 0
    retry_backoff: float = 0.5

    @model_validator(mode="after")
    def check_request_or_invoke(self) -> "Step":
        """Ensure step has either request or invoke, not both."""
        if self.request is not None and self.invoke is not None:
            raise ValueError("Step cannot have both 'request' and 'invoke'. Use one or the other.")
        if self.request is None and self.invoke is None:
            raise ValueError("Step must have either 'request' or 'invoke'.")

        has_single_case_selector = self.invoke_case_name is not None
        has_multi_case_selector = bool(self.invoke_case_names)

        if self.request is not None and (has_single_case_selector or has_multi_case_selector):
            raise ValueError("Step with 'request' cannot use 'invoke_case_name' or 'invoke_case_names'.")
        if has_single_case_selector and has_multi_case_selector:
            raise ValueError("Use either 'invoke_case_name' or 'invoke_case_names', not both.")
        if has_single_case_selector:
            cleaned_name = self.invoke_case_name.strip() if isinstance(self.invoke_case_name, str) else ""
            if not cleaned_name:
                raise ValueError("'invoke_case_name' must be a non-empty string.")
            self.invoke_case_name = cleaned_name
        if self.invoke_case_names:
            deduped_names: List[str] = []
            seen: set[str] = set()
            for name in self.invoke_case_names:
                cleaned_name = name.strip() if isinstance(name, str) else ""
                if not cleaned_name:
                    raise ValueError("'invoke_case_names' entries must be non-empty strings.")
                if cleaned_name in seen:
                    continue
                seen.add(cleaned_name)
                deduped_names.append(cleaned_name)
            self.invoke_case_names = deduped_names

        if self.repeat is None:
            self.repeat = 1
        elif isinstance(self.repeat, bool):
            raise ValueError("'repeat' must be an integer or expression string, not boolean.")
        elif isinstance(self.repeat, int):
            if self.repeat < 0:
                raise ValueError("'repeat' must be >= 0.")
        elif isinstance(self.repeat, str):
            cleaned_repeat = self.repeat.strip()
            if not cleaned_repeat:
                raise ValueError("'repeat' must be a non-empty integer or expression string.")
            self.repeat = cleaned_repeat
        else:
            raise ValueError("'repeat' must be an integer or expression string.")

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

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from pydantic import BaseModel, Field, model_validator


class SQLValidateConfig(BaseModel):
    """Configuration for an SQL validation executed after a step response."""

    query: str
    expect: Dict[str, Any] | Sequence[Any] | None = None
    store: Dict[str, str] | None = None
    allow_empty: bool = Field(default=False)
    dsn: Mapping[str, Any] | str | None = None

    @model_validator(mode="after")
    def _validate_expect(self) -> "SQLValidateConfig":
        if self.expect is not None and not isinstance(self.expect, (Mapping, Sequence)):
            raise TypeError("sql_validate.expect must be a mapping or comparator list")
        if self.store is not None and not isinstance(self.store, Mapping):
            raise TypeError("sql_validate.store must be a mapping of var -> column")
        if isinstance(self.query, str) and "| params=" in self.query:
            raise ValueError("sql_validate.query no longer supports '| params=...'; inline variables directly in the SQL text.")
        return self

    @model_validator(mode="before")
    @classmethod
    def _normalize_input(cls, data: Any) -> Any:
        if isinstance(data, Mapping):
            if "params" in data:
                raise ValueError("sql_validate does not support a separate 'params' field; inline variables directly in the SQL text.")
            query_val = data.get("query")
            if isinstance(query_val, str) and "| params=" in query_val:
                raise ValueError("sql_validate.query does not support '| params=...'; inline variables directly in SQL.")
            if "optional" in data and "allow_empty" not in data:
                data = {**data, "allow_empty": data["optional"]}
        return data

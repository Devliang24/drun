from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from pydantic import BaseModel, Field, model_validator


class SQLValidateConfig(BaseModel):
    """Configuration for an SQL validation executed after a step response."""

    query: str
    expect: Dict[str, Any] | Sequence[Any] | None = None
    extract: Dict[str, str] | None = None
    allow_empty: bool = Field(default=False)
    dsn: Mapping[str, Any] | str | None = None

    @model_validator(mode="after")
    def _validate_expect(self) -> "SQLValidateConfig":
        if self.expect is not None and not isinstance(self.expect, (Mapping, Sequence)):
            raise TypeError("sql_validate.expect must be a mapping or comparator list")
        if self.extract is not None and not isinstance(self.extract, Mapping):
            raise TypeError("sql_validate.extract must be a mapping of var -> expression")
        if self.extract:
            for expr in self.extract.values():
                if not isinstance(expr, str):
                    raise TypeError("sql_validate.extract expressions must be strings starting with '$'.")
                if not expr.strip().startswith("$"):
                    raise ValueError("sql_validate.extract expressions must start with '$', e.g. '$status'.")
        if isinstance(self.query, str) and "| params=" in self.query:
            raise ValueError("sql_validate.query no longer supports '| params=...'; inline variables directly in the SQL text.")
        return self

    @model_validator(mode="before")
    @classmethod
    def _normalize_input(cls, data: Any) -> Any:
        if isinstance(data, Mapping):
            if "store" in data:
                raise ValueError("sql_validate now uses 'extract'; rename 'store' to 'extract' and reference columns with '$'.")
            if "params" in data:
                raise ValueError("sql_validate does not support a separate 'params' field; inline variables directly in the SQL text.")
            query_val = data.get("query")
            if isinstance(query_val, str) and "| params=" in query_val:
                raise ValueError("sql_validate.query does not support '| params=...'; inline variables directly in SQL.")
            if "optional" in data and "allow_empty" not in data:
                data = {**data, "allow_empty": data["optional"]}
        return data

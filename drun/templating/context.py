from __future__ import annotations

from typing import Any, Dict, List


class VarContext:
    """Layered variables with simple precedence.

    Precedence (low -> high when merging): env_file < case.config.variables < case.config.parameters < step.variables < CLI overrides
    """

    def __init__(self, base: Dict[str, Any] | None = None) -> None:
        self.stack: List[Dict[str, Any]] = [base or {}]

    def push(self, layer: Dict[str, Any] | None) -> None:
        self.stack.append(layer or {})

    def pop(self) -> None:
        if len(self.stack) > 1:
            self.stack.pop()

    def set(self, key: str, value: Any) -> None:
        self.stack[-1][key] = value

    def set_base(self, key: str, value: Any) -> None:
        """Set a variable in the base layer (stack[0]) so it persists across steps.
        Used for extracted variables that should be available to all subsequent steps."""
        self.stack[0][key] = value

    def set_many(self, data: Dict[str, Any]) -> None:
        for k, v in (data or {}).items():
            self.set(k, v)

    def get_merged(self, overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        for layer in self.stack:
            merged.update(layer)
        if overrides:
            merged.update(overrides)
        return merged

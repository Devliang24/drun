"""Shared base for execution contexts consumed by StepLifecycle and StepOutcome.

Both ``StepLifecycleContext`` and ``StepOutcomeContext`` carry the same
per-step metadata (step, variable context, globals, hooks, env).  Extracting
those into a common ``ExecutionContext`` base avoids field duplication and
makes the relationship between the two contexts explicit.

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from drun.models.step import Step
from drun.templating.context import VarContext


@dataclass
class ExecutionContext:
    """Fields shared by every step execution context."""

    step: Step
    ctx: VarContext
    global_vars: Dict[str, Any]
    funcs: Dict[str, Any] | None
    envmap: Dict[str, Any] | None
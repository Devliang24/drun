"""Protocol defining the Runner interface consumed by sub-modules.

Previously every sub-module (StepLifecycle, StepOutcome, invoke, checking,
request_projection, response_capture, hooks) accepted `runner: Any`, which
made the implicit contract invisible and hard to refactor.  This module
declares the exact interface so that `Runner` is the canonical implementor
and sub-modules can hint `RunnerProtocol` instead of `Any`.

Design note:
  The protocol intentionally uses positional-only / keyword-only annotations
  that match the Runner's actual signatures.  Sub-modules are free to receive
  a concrete `Runner` instance; the protocol exists purely for documentation
  and type-checking.

"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from drun.models.step import Step


class LoggerProtocol(Protocol):
    """Narrow logging interface so `runner.log` can be typed."""
    def info(self, msg: str) -> None: ...
    def error(self, msg: str) -> None: ...
    def warning(self, msg: str) -> None: ...
    def debug(self, msg: str) -> None: ...


class TemplateEngineProtocol(Protocol):
    """Narrow interface for `runner.templater`."""

    def render_value(
        self,
        data: Any,
        variables: Dict[str, Any],
        functions: Optional[Dict[str, Any]] = None,
        envmap: Optional[Dict[str, Any]] = None,
        *,
        strict: bool = False,
    ) -> Any: ...

    def render_expression(
        self,
        expr: str,
        variables: Dict[str, Any],
        functions: Optional[Dict[str, Any]] = None,
        envmap: Optional[Dict[str, Any]] = None,
    ) -> Any: ...


class RunnerProtocol(Protocol):
    """The Runner interface consumed by all sub-modules.

    Every method listed here is called by at least one sub-module
    (StepLifecycle, StepOutcome, invoke, checking, request_projection,
    response_capture) instead of `runner: Any`.
    """

    # -- configuration flags exposed to sub-modules -------------------------
    log: LoggerProtocol
    failfast: bool
    reveal: bool
    log_response_headers: bool
    log_debug: bool
    persist_env_file: str
    templater: TemplateEngineProtocol

    # -- rendering ----------------------------------------------------------
    def _render(
        self,
        data: Any,
        variables: Dict[str, Any],
        functions: Optional[Dict[str, Any]] = None,
        envmap: Optional[Dict[str, Any]] = None,
        *,
        strict: bool = False,
    ) -> Any: ...

    # -- repeat / skip / sleep helpers -------------------------------------
    def _resolve_repeat_count(
        self,
        step: Step,
        variables: Dict[str, Any],
        funcs: Optional[Dict[str, Any]],
        envmap: Optional[Dict[str, Any]],
    ) -> int: ...

    def _build_repeat_variables(
        self,
        variables: Dict[str, Any],
        repeat_index: int,
    ) -> Dict[str, Any]: ...

    def _format_repeat_step_name(
        self,
        step_name: str,
        repeat_index: int,
        repeat_total: int,
    ) -> str: ...

    def _resolve_skip_decision(
        self,
        step: Step,
        variables: Dict[str, Any],
        funcs: Optional[Dict[str, Any]],
        envmap: Optional[Dict[str, Any]],
    ) -> tuple[bool, Optional[str]]: ...

    def _resolve_sleep_milliseconds(
        self,
        step: Step,
        variables: Dict[str, Any],
        funcs: Optional[Dict[str, Any]],
        envmap: Optional[Dict[str, Any]],
    ) -> float: ...

    # -- request dictionary ------------------------------------------------
    def _request_dict(self, step: Step) -> Dict[str, Any]: ...

    # -- hook wrappers -----------------------------------------------------
    def _run_setup_hooks(
        self,
        names: List[str],
        *,
        funcs: Optional[Dict[str, Any]],
        req: Dict[str, Any],
        variables: Dict[str, Any],
        envmap: Optional[Dict[str, Any]],
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]: ...

    def _run_teardown_hooks(
        self,
        names: List[str],
        *,
        funcs: Optional[Dict[str, Any]],
        resp: Dict[str, Any],
        variables: Dict[str, Any],
        envmap: Optional[Dict[str, Any]],
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]: ...

    # -- invoke delegation -------------------------------------------------
    def _run_invoke_step(
        self,
        step: Step,
        step_idx: int,
        rendered_step_name: str,
        variables: Dict[str, Any],
        global_vars: Dict[str, Any],
        funcs: Optional[Dict[str, Any]],
        envmap: Optional[Dict[str, Any]],
        ctx: Any,  # VarContext (circular-import safe)
        params: Optional[Dict[str, Any]],
        invoke_result_prefix: Optional[str] = None,
        repeat_index: Optional[int] = None,
        repeat_no: Optional[int] = None,
        repeat_total: Optional[int] = None,
    ) -> List: ...  # List[StepResult]

    # -- check / extract ---------------------------------------------------
    def _resolve_check(self, check: str, resp: Dict[str, Any]) -> Any: ...

    def _eval_extract(self, expr: Any, resp: Dict[str, Any]) -> Any: ...

    # -- response body persistence -----------------------------------------
    def _save_response_body(
        self,
        *,
        target: str,
        resp: Dict[str, Any],
        variables: Dict[str, Any],
        funcs: Optional[Dict[str, Any]],
        envmap: Optional[Dict[str, Any]],
    ) -> str: ...

    # -- logging / formatting helpers used by sub-modules ------------------
    def _log_render_diffs(
        self,
        req_dict: Dict[str, Any],
        req_rendered: Dict[str, Any],
    ) -> None: ...

    def _fmt_aligned(self, section: str, label: str, text: str) -> str: ...

    def _fmt_json(self, obj: Any) -> str: ...

    def _format_log_value(self, value: Any, *, prefix_len: int = 0) -> str: ...
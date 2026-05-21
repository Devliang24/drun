from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from drun.models.report import to_report_safe
from drun.models.step import Step
from drun.utils.curl import to_curl
from drun.utils.mask import mask_body, mask_headers


@dataclass
class RequestProjection:
    runtime_request: Dict[str, Any]
    report_request: Dict[str, Any]
    curl: str


def render_request_for_setup(
    *,
    runner: Any,
    step: Step,
    variables: Dict[str, Any],
    funcs: Dict[str, Any] | None,
    envmap: Dict[str, Any] | None,
) -> Dict[str, Any]:
    req_dict = runner._request_dict(step)
    return runner._render(req_dict, variables, funcs, envmap, strict=True)


def finalize_request_projection(
    *,
    runner: Any,
    rendered_request: Dict[str, Any],
    variables: Dict[str, Any],
    response_url: str | None = None,
) -> RequestProjection:
    runtime_request = dict(rendered_request or {})
    _clean_authorization_headers(runtime_request)
    _inject_token_header(runtime_request, variables)
    return RequestProjection(
        runtime_request=runtime_request,
        report_request=_build_report_request(runtime_request),
        curl=_build_curl(runner=runner, runtime_request=runtime_request, response_url=response_url),
    )


def _clean_authorization_headers(request: Dict[str, Any]) -> None:
    if not isinstance(request.get("headers"), dict):
        return
    headers = dict(request["headers"])
    for hk, hv in list(headers.items()):
        if hv is None:
            headers.pop(hk, None)
        elif isinstance(hv, str) and (
            hv.strip() == "" or hv.strip().lower() in {"bearer", "bearer none"}
        ):
            headers.pop(hk, None)
    request["headers"] = headers


def _inject_token_header(request: Dict[str, Any], variables: Dict[str, Any]) -> None:
    if isinstance(request.get("headers"), dict) and any(
        k.lower() == "authorization" for k in request["headers"]
    ):
        return
    tok = variables.get("token") if isinstance(variables, dict) else None
    if isinstance(tok, str) and tok.strip():
        headers = dict(request.get("headers") or {})
        headers["Authorization"] = f"Bearer {tok}"
        request["headers"] = headers


def _build_report_request(request: Dict[str, Any]) -> Dict[str, Any]:
    return {
        k: to_report_safe(v)
        for k, v in request.items()
        if k in ("method", "path", "url", "params", "headers", "body", "data", "files")
    }


def _build_curl(
    *,
    runner: Any,
    runtime_request: Dict[str, Any],
    response_url: str | None,
) -> str:
    url = response_url or runtime_request.get("path")
    headers = runtime_request.get("headers") or {}
    if not runner.reveal and isinstance(headers, dict):
        headers = mask_headers(headers)
    data = (
        runtime_request.get("body")
        if runtime_request.get("body") is not None
        else runtime_request.get("data")
    )
    if not runner.reveal and isinstance(data, (dict, list)):
        data = mask_body(data)
    curl = to_curl(
        runtime_request.get("method", "GET"),
        url,
        headers=headers if isinstance(headers, dict) else {},
        data=data,
    )
    if runner.log_debug:
        runner.log.debug("cURL: %s", curl)
    return curl

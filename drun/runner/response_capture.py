from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from drun.runner.protocols import RunnerProtocol
from drun.utils.mask import mask_body


@dataclass
class StepResponseCapture:
    raw_response: Dict[str, Any]
    report_response: Dict[str, Any]


def capture_step_response(*, runner: RunnerProtocol, resp_obj: Dict[str, Any]) -> StepResponseCapture:
    return StepResponseCapture(
        raw_response=resp_obj,
        report_response=_build_report_response(runner=runner, resp_obj=resp_obj),
    )


def _build_report_response(*, runner: RunnerProtocol, resp_obj: Dict[str, Any]) -> Dict[str, Any]:
    body_masked = resp_obj.get("body")
    if not runner.reveal:
        body_masked = mask_body(body_masked)

    response_dict: Dict[str, Any] = {
        "status_code": resp_obj.get("status_code"),
    }

    if resp_obj.get("is_stream"):
        response_dict["is_stream"] = True
        response_dict["stream_events"] = resp_obj.get("stream_events", [])
        response_dict["stream_summary"] = resp_obj.get("stream_summary", {})
        response_dict["stream_raw_chunks"] = resp_obj.get("stream_raw_chunks", [])
        if not runner.reveal:
            masked_events = []
            for event in response_dict["stream_events"]:
                masked_event = event.copy()
                if isinstance(masked_event.get("data"), (dict, list)):
                    masked_event["data"] = mask_body(masked_event["data"])
                masked_events.append(masked_event)
            response_dict["stream_events"] = masked_events
        return response_dict

    if isinstance(body_masked, (dict, list)):
        response_dict["body"] = body_masked
    elif body_masked is None:
        response_dict["body"] = None
    elif isinstance(body_masked, (str, bytes)):
        if isinstance(body_masked, bytes):
            text = body_masked.decode("utf-8", errors="replace")
        else:
            text = body_masked
        response_dict["body"] = text if len(text) <= 2048 else text[:2048] + "..."
    elif isinstance(body_masked, (bool, int, float)):
        response_dict["body"] = body_masked
    else:
        text = str(body_masked)
        response_dict["body"] = text if len(text) <= 2048 else text[:2048] + "..."

    if resp_obj.get("content_type") is not None:
        response_dict["content_type"] = resp_obj.get("content_type")
    if resp_obj.get("body_size") is not None:
        response_dict["body_size"] = resp_obj.get("body_size")
    if resp_obj.get("body_bytes_b64") is not None:
        response_dict["body_bytes_b64"] = resp_obj.get("body_bytes_b64")
    if resp_obj.get("saved_body_to") is not None:
        response_dict["saved_body_to"] = resp_obj.get("saved_body_to")
    if resp_obj.get("save_error") is not None:
        response_dict["save_error"] = resp_obj.get("save_error")

    return response_dict

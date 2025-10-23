from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from drun.models.report import RunReport, CaseInstanceResult, StepResult, AssertionResult


def _now_ms() -> int:
    return int(time.time() * 1000)


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _as_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        return json.dumps(str(obj), ensure_ascii=False)


def _align_like_console(text: str, pad_cols: int = 50) -> str:
    """Pad multiline text so subsequent lines visually align like console logs.

    This keeps content valid JSON while improving readability in Allure viewer.
    """
    if not text:
        return text
    lines = text.splitlines()
    if len(lines) <= 1:
        return text
    pad = " " * max(pad_cols, 0)
    return lines[0] + "\n" + "\n".join(pad + ln for ln in lines[1:])


def _status_details(case: CaseInstanceResult) -> Dict[str, Any] | None:
    if case.status != "failed":
        return None
    # Prefer the first failed step's error or first failed assertion message
    for st in case.steps:
        if st.status == "failed":
            # step error (e.g., hook error)
            if st.error:
                return {"message": st.error}
            # first failed assertion
            for a in st.asserts:
                if not a.passed:
                    msg = a.message or "assertion failed"
                    # compact context
                    detail = f"check={a.check!r} cmp={a.comparator!r} expect={a.expect!r} actual={a.actual!r} | {msg}"
                    return {"message": detail}
            # generic
            return {"message": f"step failed: {st.name}"}
    return {"message": "test failed"}


def _attach(out_dir: Path, base: str, name: str, content: str, ctype: str, ext: str) -> Dict[str, str]:
    # Allure requires attachment files placed in results dir; 'source' references the filename
    fname = f"{base}-{uuid.uuid4().hex[:8]}{ext}"
    (out_dir / fname).write_text(content, encoding="utf-8")
    return {"name": name, "type": ctype, "source": fname}


def _step_to_allure(out_dir: Path, case_uuid: str, st: StepResult, start_ms: int) -> Dict[str, Any]:
    dur = int(round(st.duration_ms or 0.0))
    stop_ms = start_ms + max(dur, 0)
    step_obj: Dict[str, Any] = {
        "name": st.name,
        "status": st.status,
        "stage": "finished",
        "start": start_ms,
        "stop": stop_ms,
        "steps": [],
        "attachments": [],
        "parameters": [],
    }

    # Attach request/response/cURL/asserts/extracts
    # Use already-masked request/response in StepResult
    try:
        if st.request:
            req_txt = _align_like_console(_as_json(st.request))
            step_obj["attachments"].append(
                _attach(out_dir, case_uuid, "Request", req_txt, "application/json", ".json")
            )
    except Exception:
        pass
    try:
        if st.response:
            resp_txt = _align_like_console(_as_json(st.response))
            step_obj["attachments"].append(
                _attach(out_dir, case_uuid, "Response", resp_txt, "application/json", ".json")
            )
    except Exception:
        pass
    if st.curl:
        try:
            step_obj["attachments"].append(
                _attach(out_dir, case_uuid, "cURL", st.curl, "text/plain", ".txt")
            )
        except Exception:
            pass
    try:
        if st.asserts:
            asserts_txt = _as_json([a.model_dump() for a in st.asserts])
            step_obj["attachments"].append(
                _attach(out_dir, case_uuid, "Asserts", asserts_txt, "application/json", ".json")
            )
    except Exception:
        pass
    try:
        if st.extracts:
            extracts_txt = _as_json(st.extracts)
            step_obj["attachments"].append(
                _attach(out_dir, case_uuid, "Extracts", extracts_txt, "application/json", ".json")
            )
    except Exception:
        pass

    return step_obj


def write_allure_results(report: RunReport, out_dir: str | Path) -> None:
    """Write Allure 2 results files (.result.json + attachments) for the run.

    Users can then run:
      allure generate <out_dir> -o allure-report --clean
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    now = _now_ms()

    for case in report.cases:
        test_uuid = uuid.uuid4().hex
        # Timing: backfill based on duration
        case_dur = int(round(case.duration_ms or 0.0))
        case_stop = now
        case_start = case_stop - max(case_dur, 0)

        # Suite label from source file if available
        suite_label = None
        if getattr(case, "source", None):
            try:
                suite_label = Path(case.source).stem
            except Exception:
                suite_label = str(case.source)
        if not suite_label:
            suite_label = "Drun"

        full_name = f"{suite_label}::{case.name}" if suite_label else case.name
        history_id = _md5(full_name)

        # Steps with attachments
        steps: List[Dict[str, Any]] = []
        offset = 0
        for st in case.steps:
            st_start = case_start + offset
            steps.append(_step_to_allure(out, test_uuid, st, st_start))
            offset += int(round(st.duration_ms or 0.0))

        parameters = [
            {"name": str(k), "value": json.dumps(v, ensure_ascii=False) if not isinstance(v, (str, int, float, bool, type(None))) else v}
            for k, v in (case.parameters or {}).items()
        ]

        labels = [
            {"name": "language", "value": "python"},
            {"name": "framework", "value": "drun"},
            {"name": "suite", "value": suite_label},
        ]

        test_result: Dict[str, Any] = {
            "uuid": test_uuid,
            "name": case.name,
            "fullName": full_name,
            "status": case.status,
            "statusDetails": _status_details(case) or {},
            "stage": "finished",
            "start": case_start,
            "stop": case_stop,
            "parameters": parameters,
            "labels": labels,
            "steps": steps,
            "attachments": [],  # top-level attachments not used for now
            "historyId": history_id,
            "testCaseId": history_id,
        }

        # Persist test result
        (out / f"{test_uuid}-result.json").write_text(
            json.dumps(test_result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )

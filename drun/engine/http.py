from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Dict, Optional, List
import httpx
import json
import time

from drun.engine.request_files import RequestFilesError, _close_opened_files, normalize_request_files


class HTTPClient:
    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None, verify: Optional[bool] = None, headers: Optional[Dict[str, str]] = None) -> None:
        self.base_url = base_url or ""
        self.timeout = timeout
        self.verify = verify
        self.headers = headers or {}
        event_hooks: Dict[str, list] = {}
        # httpstat 功能已移除，保留空 hooks

        # NOTE: httpx.Client(base_url=None) raises TypeError in newer httpx versions.
        # Keep base_url as a string ("" when unset) for compatibility.
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout or 10.0,
            verify=self.verify if self.verify is not None else True,
            headers=self.headers,
            event_hooks=event_hooks
        )

    def close(self) -> None:
        self.client.close()

    def _parse_sse_stream(self, response: httpx.Response, start_time: float) -> Dict[str, Any]:
        """Parse Server-Sent Events (SSE) stream"""
        events: List[Dict[str, Any]] = []
        raw_chunks: List[str] = []
        
        try:
            current_event: Dict[str, Any] = {}
            current_data_lines: List[str] = []
            
            for line in response.iter_lines():
                current_time_ms = (time.perf_counter() - start_time) * 1000.0
                raw_chunks.append(line + "\n")
                
                # Empty line marks end of event
                if not line or line.strip() == "":
                    if current_data_lines:
                        # Join data lines and try to parse as JSON
                        data_str = "\n".join(current_data_lines)
                        
                        # Handle [DONE] marker
                        if data_str.strip() == "[DONE]":
                            events.append({
                                "index": len(events),
                                "timestamp_ms": current_time_ms,
                                "event": current_event.get("event", "done"),
                                "data": None
                            })
                        else:
                            # Try to parse as JSON
                            try:
                                data_obj = json.loads(data_str)
                            except json.JSONDecodeError:
                                data_obj = data_str
                            
                            events.append({
                                "index": len(events),
                                "timestamp_ms": current_time_ms,
                                "event": current_event.get("event", "message"),
                                "data": data_obj
                            })
                        
                        # Reset for next event
                        current_event = {}
                        current_data_lines = []
                    continue
                
                # Parse SSE fields
                if ":" in line:
                    field, _, value = line.partition(":")
                    field = field.strip()
                    value = value.lstrip()
                    
                    if field == "data":
                        current_data_lines.append(value)
                    elif field == "event":
                        current_event["event"] = value
                    elif field == "id":
                        current_event["id"] = value
                    elif field == "retry":
                        current_event["retry"] = value
        
        except Exception as e:
            # Add error event if stream parsing fails
            events.append({
                "index": len(events),
                "timestamp_ms": (time.perf_counter() - start_time) * 1000.0,
                "event": "error",
                "data": {"error": str(e)}
            })
        
        # Calculate summary
        summary = {
            "event_count": len(events),
            "first_chunk_ms": events[0]["timestamp_ms"] if events else 0,
            "last_chunk_ms": events[-1]["timestamp_ms"] if events else 0
        }
        
        # Extract progressive content for display (OpenAI format)
        progressive_content = []
        accumulated = ""
        for event in events:
            data = event.get("data")
            if data and isinstance(data, dict):
                # Try to extract content from OpenAI streaming format
                choices = data.get("choices", [])
                if choices and isinstance(choices, list) and len(choices) > 0:
                    delta = choices[0].get("delta", {})
                    if isinstance(delta, dict):
                        content = delta.get("content", "")
                        if content:  # Only record non-empty content
                            accumulated += content
                            progressive_content.append({
                                "index": len(progressive_content) + 1,
                                "timestamp_ms": event.get("timestamp_ms", 0),
                                "content": accumulated
                            })
        
        return {
            "stream_events": events,
            "stream_raw_chunks": raw_chunks,
            "stream_summary": summary,
            "progressive_content": progressive_content
        }

    def request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        method = req.get("method", "GET")
        path = req.get("path", "")
        # Ensure path is not None or empty when no base_url
        if not path:
            path = "/"
        params = req.get("params")
        headers = req.get("headers") or {}
        # 'body' holds JSON object or raw content from test step
        json_data = req.get("body")
        data = req.get("data")
        files = req.get("files")
        timeout = req.get("timeout", self.timeout)
        verify = req.get("verify", self.verify)
        allow_redirects = req.get("allow_redirects", True)
        auth = req.get("auth")
        
        # Check if streaming mode is enabled
        is_stream = req.get("stream", False)
        stream_timeout = req.get("stream_timeout", 30.0)

        # auth support: basic, bearer
        if auth and isinstance(auth, dict):
            if auth.get("type") == "basic":
                username = auth.get("username", "")
                password = auth.get("password", "")
                auth_tuple = (username, password)
            elif auth.get("type") == "bearer":
                token = auth.get("token", "")
                headers = {**headers, "Authorization": f"Bearer {token}"}
                auth_tuple = None
            else:
                auth_tuple = None
        else:
            auth_tuple = None

        if files is not None and json_data is not None:
            raise RequestFilesError(
                "request.body cannot be used with request.files. Use request.data for multipart form fields."
            )

        normalized_files = None
        opened_files = []
        if files is not None:
            normalized_files, opened_files = normalize_request_files(
                files,
                cwd=Path.cwd(),
                source="request.files",
            )

        # Handle streaming requests
        try:
            if is_stream:
                start_time = time.perf_counter()

                # Use streaming timeout if specified
                actual_timeout = stream_timeout if stream_timeout else timeout

                with self.client.stream(
                    method=method,
                    url=path,
                    params=params,
                    headers=headers,
                    json=json_data,
                    data=data,
                    files=normalized_files,
                    timeout=actual_timeout,
                    follow_redirects=bool(allow_redirects),
                    auth=auth_tuple,
                ) as resp:
                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                    # Parse SSE stream
                    stream_data = self._parse_sse_stream(resp, start_time)

                    result = {
                        "status_code": resp.status_code,
                        "headers": dict(resp.headers),
                        "content_type": resp.headers.get("content-type"),
                        "body_size": 0,
                        "raw_bytes": b"",
                        "is_stream": True,
                        "elapsed_ms": elapsed_ms,
                        "url": str(resp.url),
                        "method": method,
                    }
                    result.update(stream_data)
                    return result

            # Non-streaming request (original behavior)
            resp = self.client.request(
                method=method,
                url=path,
                params=params,
                headers=headers,
                json=json_data,
                data=data,
                files=normalized_files,
                timeout=timeout,
                follow_redirects=bool(allow_redirects),
                auth=auth_tuple,
            )

            content_type = resp.headers.get("content-type")
            raw_bytes = resp.content
            body_text: Optional[str] = None
            body_json: Any = None

            if _should_try_json(content_type):
                try:
                    body_json = resp.json()
                except Exception:
                    body_json = None

            if body_json is None and _should_decode_text(content_type, raw_bytes):
                try:
                    body_text = resp.text
                except Exception:
                    body_text = None

            if body_json is None and body_text is None and content_type is None:
                try:
                    body_json = resp.json()
                except Exception:
                    if _should_decode_text(content_type, raw_bytes):
                        try:
                            body_text = resp.text
                        except Exception:
                            body_text = None

            result = {
                "status_code": resp.status_code,
                "headers": dict(resp.headers),
                "body": body_json if body_json is not None else body_text,
                "content_type": content_type,
                "body_size": len(raw_bytes),
                "raw_bytes": raw_bytes,
                "elapsed_ms": _get_elapsed_ms(resp),
                "url": str(resp.request.url),
                "method": str(resp.request.method),
            }
            if _should_capture_binary_payload(content_type, body_json, body_text, raw_bytes):
                result["body_bytes_b64"] = base64.b64encode(raw_bytes).decode("ascii")
            return result
        finally:
            _close_opened_files(opened_files)


def _should_try_json(content_type: str | None) -> bool:
    if not content_type:
        return True
    normalized = content_type.split(";", 1)[0].strip().lower()
    return normalized == "application/json" or normalized.endswith("+json")


def _should_decode_text(content_type: str | None, raw_bytes: bytes) -> bool:
    if not content_type:
        return not _looks_binary_payload(raw_bytes)
    normalized = content_type.split(";", 1)[0].strip().lower()
    if normalized.startswith("text/"):
        return True
    return normalized in {
        "application/json",
        "application/problem+json",
        "application/xml",
        "application/javascript",
        "application/x-www-form-urlencoded",
    } or normalized.endswith("+json") or normalized.endswith("+xml")


def _should_capture_binary_payload(content_type: str | None, body_json: Any, body_text: str | None, raw_bytes: bytes) -> bool:
    if body_json is not None or body_text is not None:
        return False
    if content_type:
        return True
    return _looks_binary_payload(raw_bytes)


def _looks_binary_payload(raw_bytes: bytes) -> bool:
    if not raw_bytes:
        return False
    sample = raw_bytes[:1024]
    if b"\x00" in sample:
        return True
    text_bytes = set(range(32, 127)) | {9, 10, 13}
    non_text = sum(1 for byte in sample if byte not in text_bytes)
    return (non_text / len(sample)) > 0.3


def _get_elapsed_ms(resp: httpx.Response) -> float | None:
    try:
        if resp.elapsed:
            return resp.elapsed.total_seconds() * 1000.0
    except RuntimeError:
        return None
    return None

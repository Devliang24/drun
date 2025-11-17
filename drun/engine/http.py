from __future__ import annotations

from typing import Any, Dict, Optional, List
import httpx
import json
import time


class HTTPClient:
    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None, verify: Optional[bool] = None, headers: Optional[Dict[str, str]] = None) -> None:
        self.base_url = base_url or ""
        self.timeout = timeout
        self.verify = verify
        self.headers = headers or {}
        event_hooks: Dict[str, list] = {}
        # httpstat 功能已移除，保留空 hooks

        self.client = httpx.Client(
            base_url=self.base_url or None,
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

        # Handle streaming requests
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
                files=files,
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
            files=files,
            timeout=timeout,
            follow_redirects=bool(allow_redirects),
            auth=auth_tuple,
        )

        body_text: Optional[str] = None
        body_json: Any = None
        try:
            body_json = resp.json()
        except Exception:
            try:
                body_text = resp.text
            except Exception:
                body_text = None

        result = {
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "body": body_json if body_json is not None else body_text,
            "elapsed_ms": resp.elapsed.total_seconds() * 1000.0 if resp.elapsed else None,
            "url": str(resp.request.url),
            "method": str(resp.request.method),
        }
        return result

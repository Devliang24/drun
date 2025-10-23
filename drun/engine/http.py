from __future__ import annotations

from typing import Any, Dict, Optional
import httpx


class HTTPClient:
    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None, verify: Optional[bool] = None, headers: Optional[Dict[str, str]] = None) -> None:
        self.base_url = base_url or ""
        self.timeout = timeout
        self.verify = verify
        self.headers = headers or {}
        self.client = httpx.Client(base_url=self.base_url or None, timeout=self.timeout or 10.0, verify=self.verify if self.verify is not None else True, headers=self.headers)

    def close(self) -> None:
        self.client.close()

    def request(self, req: Dict[str, Any]) -> Dict[str, Any]:
        method = req.get("method", "GET")
        url = req.get("url", "")
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

        resp = self.client.request(
            method=method,
            url=url,
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

        return {
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "body": body_json if body_json is not None else body_text,
            "elapsed_ms": resp.elapsed.total_seconds() * 1000.0 if resp.elapsed else None,
            "url": str(resp.request.url),
            "method": str(resp.request.method),
        }

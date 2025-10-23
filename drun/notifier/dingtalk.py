from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from typing import List, Optional

import httpx

from .base import Notifier, NotifyContext
from .format import build_text_message
from drun.models.report import RunReport


class DingTalkNotifier(Notifier):
    def __init__(
        self,
        *,
        webhook: str,
        secret: Optional[str] = None,
        at_mobiles: Optional[List[str]] = None,
        at_all: bool = False,
        timeout: float = 6.0,
        style: str = "text",
    ) -> None:
        self.webhook = webhook
        self.secret = secret
        self.at_mobiles = [m for m in (at_mobiles or []) if m]
        self.at_all = bool(at_all)
        self.timeout = timeout
        self.style = (style or "text").lower()

    def _sign_params(self) -> dict:
        if not self.secret:
            return {}
        ts = str(int(time.time() * 1000))  # ms timestamp required by DingTalk
        string_to_sign = f"{ts}\n{self.secret}"
        h = hmac.new(self.secret.encode("utf-8"), string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
        sign = base64.b64encode(h).decode()
        return {"timestamp": ts, "sign": sign}

    def _send_json(self, payload: dict) -> None:
        params = self._sign_params()
        headers = {"Content-Type": "application/json"}
        with httpx.Client(timeout=self.timeout) as client:
            _ = client.post(self.webhook, params=params, json=payload, headers=headers)

    def send(self, report: RunReport, ctx: NotifyContext) -> None:  # pragma: no cover - integration
        if not self.webhook:
            return
        try:
            text = build_text_message(report, html_path=ctx.html_path, log_path=ctx.log_path, topn=ctx.topn)
            at_block = {
                "atMobiles": self.at_mobiles,
                "isAtAll": self.at_all,
            }
            if self.style == "markdown":
                title = os.environ.get("DINGTALK_TITLE", "Drun 测试结果")
                payload = {"msgtype": "markdown", "markdown": {"title": title, "text": text}, "at": at_block}
            else:
                payload = {"msgtype": "text", "text": {"content": text}, "at": at_block}
            self._send_json(payload)
        except Exception:
            return

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from typing import Optional

import httpx

from .base import Notifier, NotifyContext
from .format import build_summary_text, build_text_message
from drun.models.report import RunReport


class FeishuNotifier(Notifier):
    def __init__(self, *, webhook: str, secret: Optional[str] = None, mentions: Optional[str] = None, timeout: float = 6.0, style: str = "text") -> None:
        self.webhook = webhook
        self.secret = secret
        self.mentions = mentions or ""
        self.timeout = timeout
        self.style = (style or "text").lower()

    def _sign(self, ts: str) -> str:
        # sign = base64(hmac_sha256(ts + '\n' + secret, secret))
        msg = (ts + "\n" + (self.secret or "")).encode()
        dig = hmac.new((self.secret or "").encode(), msg, digestmod=hashlib.sha256).digest()
        return base64.b64encode(dig).decode()

    def _send_json(self, payload: dict) -> None:
        headers = {"Content-Type": "application/json"}
        url = self.webhook
        if self.secret:
            ts = str(int(time.time()))
            payload.update({"timestamp": ts, "sign": self._sign(ts)})
        with httpx.Client(timeout=self.timeout) as client:
            _ = client.post(url, json=payload, headers=headers)

    def _card_payload(self, report: RunReport, ctx: NotifyContext) -> dict:
        # Build interactive card with summary and links
        text = build_summary_text(report, html_path=ctx.html_path, log_path=ctx.log_path, topn=ctx.topn)
        if self.mentions:
            text = f"提醒: {self.mentions}\n\n" + text
        report_url = os.environ.get("REPORT_URL")
        if (not report_url) and ctx.html_path and (ctx.html_path.startswith("http://") or ctx.html_path.startswith("https://")):
            report_url = ctx.html_path
        elements = [
            {"tag": "div", "text": {"tag": "lark_md", "content": text}},
        ]
        if report_url:
            elements.append({
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "查看报告"},
                        "type": "primary",
                        "url": report_url,
                    }
                ],
            })
        # 从环境变量读取系统名称，支持 SYSTEM_NAME 或 PROJECT_NAME
        system_name = os.environ.get("SYSTEM_NAME", os.environ.get("PROJECT_NAME", "Drun 测试结果"))
        card = {
            "config": {"wide_screen_mode": True},
            "header": {"template": "blue", "title": {"tag": "plain_text", "content": system_name}},
            "elements": elements,
        }
        return {"msg_type": "interactive", "card": card}

    def send(self, report: RunReport, ctx: NotifyContext) -> None:  # pragma: no cover - integration
        if not self.webhook:
            return
        try:
            if self.style == "card":
                payload = self._card_payload(report, ctx)
            else:
                text = build_text_message(report, html_path=ctx.html_path, log_path=ctx.log_path, topn=ctx.topn)
                if self.mentions:
                    text = f"提醒: {self.mentions}\n" + text
                payload = {"msg_type": "text", "content": {"text": text}}
            self._send_json(payload)
        except Exception:
            return

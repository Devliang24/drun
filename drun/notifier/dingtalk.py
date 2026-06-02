from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import List, Optional

import httpx

from .base import BestEffortNotifier, NotifyContext, resolve_report_url
from .format import build_text_message, build_markdown_message
from drun.models.report import RunReport
from drun.utils.config import get_env_clean, get_system_name


class DingTalkNotifier(BestEffortNotifier):
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
        # 构建完整的 URL，包含签名参数
        url = self.webhook
        sign_params = self._sign_params()
        if sign_params:
            # 将签名参数附加到 URL，避免覆盖 access_token
            timestamp = sign_params["timestamp"]
            sign = sign_params["sign"]
            url = f"{self.webhook}&timestamp={timestamp}&sign={sign}"
        
        headers = {"Content-Type": "application/json"}
        with httpx.Client(timeout=self.timeout) as client:
            _ = client.post(url, json=payload, headers=headers)

    def _send(self, report: RunReport, ctx: NotifyContext) -> None:
        if not self.webhook:
            return
        # 获取报告 URL（优先使用 REPORT_URL 环境变量）
        report_url = resolve_report_url(ctx)

        # 构建消息内容 - 根据 style 选择不同的格式
        html_path_display = report_url if report_url else ctx.html_path

        if self.style == "markdown":
            # 使用 Markdown 格式
            text = build_markdown_message(
                report,
                html_path=html_path_display,
                log_path=ctx.log_path,
                topn=ctx.topn,
            )
        else:
            # 使用纯文本格式
            text = build_text_message(
                report,
                html_path=html_path_display,
                log_path=ctx.log_path,
                topn=ctx.topn,
            )

        at_block = {
            "atMobiles": self.at_mobiles,
            "isAtAll": self.at_all,
        }
        if self.style == "markdown":
            system_name = get_system_name()
            title = get_env_clean("DINGTALK_TITLE") or f"{system_name} 测试结果"
            payload = {
                "msgtype": "markdown",
                "markdown": {"title": title, "text": text},
                "at": at_block,
            }
        else:
            payload = {"msgtype": "text", "text": {"content": text}, "at": at_block}
        self._send_json(payload)

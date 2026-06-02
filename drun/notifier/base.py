from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from drun.models.report import RunReport
from drun.utils.config import get_env_clean


@dataclass
class NotifyContext:
    html_path: Optional[str] = None
    log_path: Optional[str] = None
    notify_only: str = "failed"  # or "always"
    topn: int = 5


class Notifier:
    def send(self, report: RunReport, ctx: NotifyContext) -> None:  # pragma: no cover - integration
        raise NotImplementedError


def is_http_url(value: Optional[str]) -> bool:
    return bool(value and value.startswith(("http://", "https://")))


def resolve_report_url(ctx: NotifyContext) -> Optional[str]:
    report_url = get_env_clean("REPORT_URL")
    if not report_url and is_http_url(ctx.html_path):
        report_url = ctx.html_path
    return report_url or None


class BestEffortNotifier(Notifier):
    def send(self, report: RunReport, ctx: NotifyContext) -> None:  # pragma: no cover - integration
        try:
            self._send(report, ctx)
        except Exception:
            return

    def _send(self, report: RunReport, ctx: NotifyContext) -> None:
        raise NotImplementedError

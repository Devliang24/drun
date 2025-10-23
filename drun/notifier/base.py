from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from drun.models.report import RunReport


@dataclass
class NotifyContext:
    html_path: Optional[str] = None
    log_path: Optional[str] = None
    notify_only: str = "failed"  # or "always"
    topn: int = 5


class Notifier:
    def send(self, report: RunReport, ctx: NotifyContext) -> None:  # pragma: no cover - integration
        raise NotImplementedError

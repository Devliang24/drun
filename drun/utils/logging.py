from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

try:
    from logging import LogRecord
    from rich.logging import RichHandler as _RichHandler  # type: ignore
    from rich.text import Text

    class RichHandler(_RichHandler):  # type: ignore
        """Trim level text padding from Rich's default handler."""

        def get_level_text(self, record: LogRecord) -> Text:  # type: ignore[override]
            level_name = record.levelname
            return Text.styled(level_name, f"logging.level.{level_name.lower()}")

    _HAS_RICH = True
except Exception:  # pragma: no cover
    RichHandler = None  # type: ignore
    _HAS_RICH = False


class ColumnFormatter(logging.Formatter):
    """Formatter that keeps multi-line messages aligned with the log prefix."""

    def __init__(self, fmt: str, datefmt: Optional[str] = None, *, align_continuation: bool = True) -> None:
        super().__init__(fmt, datefmt)
        self.align = align_continuation and "%(message)s" in fmt

    def _tweak_message(self, message: str) -> str:
        return message

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        original_msg = record.msg
        original_args = record.args
        exc_text_exists = hasattr(record, "exc_text")
        original_exc_text = getattr(record, "exc_text", None)
        try:
            message = record.getMessage()
            message = self._tweak_message(message)
            if self.usesTime():
                record.asctime = self.formatTime(record, self.datefmt)

            indent = ""
            if self.align:
                prefix_record = logging.makeLogRecord(record.__dict__.copy())
                prefix_record.msg = ""
                prefix_record.args = ()
                prefix_record.message = ""
                if self.usesTime():
                    prefix_record.asctime = record.asctime
                prefix = self.formatMessage(prefix_record)
                indent = " " * len(prefix)
                if indent and "\n" in message:
                    message = message.replace("\n", "\n" + indent)

            record.message = message
            s = self.formatMessage(record)

            if record.exc_info:
                if not record.exc_text:
                    record.exc_text = self.formatException(record.exc_info)
            if record.exc_text:
                if s and s[-1] != "\n":
                    s += "\n"
                s += record.exc_text
            if record.stack_info:
                if s and s[-1] != "\n":
                    s += "\n"
                s += self.formatStack(record.stack_info)
            return s
        finally:
            record.msg = original_msg
            record.args = original_args
            if exc_text_exists:
                record.exc_text = original_exc_text
            elif hasattr(record, "exc_text"):
                delattr(record, "exc_text")


class JSONAwareFormatter(ColumnFormatter):
    """Formatter for file logs that mirrors terminal alignment for multiline messages."""

    def __init__(self, fmt: str, datefmt: Optional[str] = None, *, align_continuation: bool = True) -> None:
        # Enable continuation alignment by default so files match terminal output
        super().__init__(fmt, datefmt, align_continuation=align_continuation)

    def _tweak_message(self, message: str) -> str:  # type: ignore[override]
        return message


def setup_logging(level: str = "INFO", *, log_file: Optional[str] = None) -> None:
    lvl = getattr(logging, level.upper(), logging.INFO)

    # Clear existing handlers on root
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    handlers: list[logging.Handler] = []
    console_handler: Optional[logging.Handler] = None
    if _HAS_RICH:
        console_handler = RichHandler(
            rich_tracebacks=True,
            show_path=False,
            show_time=False,
            show_level=False,
            markup=False,
        )
    else:
        console_handler = logging.StreamHandler()
    handlers.append(console_handler)

    if log_file:
        p = Path(log_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(p, encoding="utf-8")
        handlers.append(fh)

    fmt_console = "%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s"
    fmt_file = "%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(level=lvl, handlers=handlers, format=fmt_console, datefmt=datefmt)

    for h in handlers:
        if isinstance(h, logging.FileHandler):
            h.setFormatter(JSONAwareFormatter(fmt_file, datefmt))
        elif h is console_handler:
            # Enable continuation alignment so multiline messages align under the prefix
            h.setFormatter(ColumnFormatter(fmt_console, datefmt, align_continuation=True))

    if lvl > logging.DEBUG:
        logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name or "drun")

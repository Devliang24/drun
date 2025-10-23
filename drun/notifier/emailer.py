from __future__ import annotations

import mimetypes
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional

from .base import Notifier, NotifyContext
from .format import build_summary_text, build_text_message
from drun.models.report import RunReport


class EmailNotifier(Notifier):
    def __init__(
        self,
        *,
        smtp_host: str,
        smtp_port: int = 465,
        smtp_user: Optional[str] = None,
        smtp_pass: Optional[str] = None,
        mail_from: Optional[str] = None,
        mail_to: Optional[str] = None,
        use_ssl: bool = True,
        timeout: float = 8.0,
        attach_html: bool = False,
        html_body: bool = True,
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = int(smtp_port)
        self.smtp_user = smtp_user
        self.smtp_pass = smtp_pass
        self.mail_from = mail_from or smtp_user or ""
        self.mail_to = mail_to or ""
        self.use_ssl = use_ssl
        self.timeout = timeout
        self.attach_html = attach_html
        self.html_body = html_body

    def send(self, report: RunReport, ctx: NotifyContext) -> None:  # pragma: no cover - integration
        if not (self.smtp_host and self.mail_from and self.mail_to):
            return
        s = report.summary or {}
        subject = f"[Drun] 测试结果: {s.get('failed',0)}/{s.get('total',0)} 失败"
        body = build_text_message(report, html_path=ctx.html_path, log_path=ctx.log_path, topn=ctx.topn)

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.mail_from
        msg["To"] = self.mail_to
        # Plain text
        msg.set_content(body)
        # HTML alternative
        if self.html_body:
            from html import escape as _esc
            s = report.summary or {}
            total = s.get("total", 0)
            passed = s.get("passed", 0)
            failed = s.get("failed", 0)
            skipped = s.get("skipped", 0)
            dur = f"{(s.get('duration_ms', 0.0) or 0.0)/1000.0:.1f}s"
            # Build simple HTML
            fails = []
            from .format import collect_failures
            for name, step, msg_txt in collect_failures(report, topn=ctx.topn):
                fails.append(f"<li><b>{_esc(name)}</b>: {_esc(step)} → {_esc(str(msg_txt))}</li>")
            html_lines = [
                "<html><body>",
                "<h3>Drun 测试结果</h3>",
                f"<p>总 {total} | 通过 {passed} | 失败 {failed} | 跳过 {skipped} | {dur}</p>",
                "<ul>" + ("".join(fails) or "<li>无失败</li>") + "</ul>",
            ]
            if ctx.html_path:
                html_lines.append(f"<p>报告: {_esc(ctx.html_path)}</p>")
            if ctx.log_path:
                html_lines.append(f"<p>日志: {_esc(ctx.log_path)}</p>")
            html_lines.append("</body></html>")
            msg.add_alternative("\n".join(html_lines), subtype="html")

        if self.attach_html and ctx.html_path and os.path.isfile(ctx.html_path):
            ctype, _ = mimetypes.guess_type(ctx.html_path)
            maintype, subtype = (ctype or "text/html").split("/", 1)
            with open(ctx.html_path, "rb") as fp:
                data = fp.read()
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=os.path.basename(ctx.html_path))

        try:
            if self.use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=self.timeout, context=context) as server:
                    if self.smtp_user and self.smtp_pass:
                        server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.timeout) as server:
                    server.ehlo()
                    try:
                        server.starttls(context=ssl.create_default_context())
                    except Exception:
                        pass
                    if self.smtp_user and self.smtp_pass:
                        server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
        except Exception:
            # best-effort, ignore failures
            return

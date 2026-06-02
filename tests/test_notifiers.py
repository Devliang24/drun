from __future__ import annotations

import os
import unittest
from unittest.mock import Mock, patch

from drun.models.report import CaseInstanceResult, RunReport, StepResult
from drun.notifier import DingTalkNotifier, EmailNotifier, FeishuNotifier, NotifyContext
from drun.notifier.emailer import _build_html_body


def _sample_report() -> RunReport:
    return RunReport(
        summary={
            "total": 1,
            "passed": 0,
            "failed": 1,
            "skipped": 0,
            "duration_ms": 1234.0,
            "steps_total": 1,
            "steps_passed": 0,
            "steps_failed": 1,
        },
        cases=[
            CaseInstanceResult(
                name="demo case",
                status="failed",
                steps=[
                    StepResult(
                        name="demo step",
                        status="failed",
                        error="boom",
                        duration_ms=12.3,
                    )
                ],
            )
        ],
    )


class DingTalkNotifierTests(unittest.TestCase):
    def test_empty_webhook_does_not_send(self) -> None:
        notifier = DingTalkNotifier(webhook="")
        with patch("drun.notifier.dingtalk.httpx.Client") as client_cls:
            notifier.send(_sample_report(), NotifyContext())
        client_cls.assert_not_called()

    def test_text_payload_uses_report_url_and_signed_url(self) -> None:
        client = Mock()
        client.__enter__ = Mock(return_value=client)
        client.__exit__ = Mock(return_value=None)
        client.post.return_value = Mock()

        with patch.dict(os.environ, {"REPORT_URL": "https://reports.example/run/1"}, clear=True), \
            patch("drun.notifier.dingtalk.time.time", return_value=1700000000.0), \
            patch("drun.notifier.dingtalk.httpx.Client", return_value=client):
            DingTalkNotifier(
                webhook="https://oapi.dingtalk.com/robot/send?access_token=abc",
                secret="secret",
                at_mobiles=["13800000000", ""],
                style="text",
            ).send(_sample_report(), NotifyContext(html_path="local/report.html"))

        client.post.assert_called_once()
        url = client.post.call_args.args[0]
        payload = client.post.call_args.kwargs["json"]
        self.assertIn("timestamp=1700000000000", url)
        self.assertIn("sign=", url)
        self.assertEqual(payload["msgtype"], "text")
        self.assertIn("https://reports.example/run/1", payload["text"]["content"])
        self.assertEqual(payload["at"]["atMobiles"], ["13800000000"])

    def test_send_swallow_http_errors(self) -> None:
        client = Mock()
        client.__enter__ = Mock(return_value=client)
        client.__exit__ = Mock(return_value=None)
        client.post.side_effect = RuntimeError("network down")

        with patch("drun.notifier.dingtalk.httpx.Client", return_value=client):
            DingTalkNotifier(webhook="https://example.test/hook").send(
                _sample_report(), NotifyContext()
            )


class FeishuNotifierTests(unittest.TestCase):
    def test_empty_webhook_does_not_send(self) -> None:
        notifier = FeishuNotifier(webhook="")
        with patch("drun.notifier.feishu.httpx.Client") as client_cls:
            notifier.send(_sample_report(), NotifyContext())
        client_cls.assert_not_called()

    def test_card_payload_uses_http_html_path_as_report_url_and_signs_payload(self) -> None:
        client = Mock()
        client.__enter__ = Mock(return_value=client)
        client.__exit__ = Mock(return_value=None)
        client.post.return_value = Mock()

        with patch.dict(os.environ, {}, clear=True), \
            patch("drun.notifier.feishu.get_env_clean", side_effect=lambda key, default=None: default), \
            patch("drun.notifier.feishu.time.time", return_value=1700000000.0), \
            patch("drun.notifier.feishu.httpx.Client", return_value=client):
            FeishuNotifier(
                webhook="https://open.feishu.cn/hook",
                secret="secret",
                mentions="@all",
                style="card",
            ).send(
                _sample_report(),
                NotifyContext(html_path="https://reports.example/run/2"),
            )

        client.post.assert_called_once()
        payload = client.post.call_args.kwargs["json"]
        self.assertEqual(payload["msg_type"], "interactive")
        self.assertEqual(payload["timestamp"], "1700000000")
        self.assertIn("sign", payload)
        actions = payload["card"]["elements"][1]["actions"]
        self.assertEqual(actions[0]["url"], "https://reports.example/run/2")
        first_text = payload["card"]["elements"][0]["text"]["content"]
        self.assertIn("提醒: @all", first_text)

    def test_send_swallow_http_errors(self) -> None:
        client = Mock()
        client.__enter__ = Mock(return_value=client)
        client.__exit__ = Mock(return_value=None)
        client.post.side_effect = RuntimeError("network down")

        with patch("drun.notifier.feishu.httpx.Client", return_value=client):
            FeishuNotifier(webhook="https://example.test/hook").send(
                _sample_report(), NotifyContext()
            )


class EmailNotifierTests(unittest.TestCase):
    def test_build_html_body_escapes_failures_and_includes_paths(self) -> None:
        report = RunReport(
            summary={
                "total": 1,
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "duration_ms": 2500.0,
            },
            cases=[
                CaseInstanceResult(
                    name="<case&>",
                    status="failed",
                    steps=[
                        StepResult(
                            name="<step>",
                            status="failed",
                            error="bad <token>",
                        )
                    ],
                )
            ],
        )
        html = _build_html_body(
            report,
            NotifyContext(html_path="reports/<r>.html", log_path="logs/<run>.log"),
        )

        self.assertIn("总 1 | 通过 0 | 失败 1 | 跳过 0 | 2.5s", html)
        self.assertIn("&lt;case&amp;&gt;", html)
        self.assertIn("&lt;step&gt;", html)
        self.assertIn("bad &lt;token&gt;", html)
        self.assertIn("reports/&lt;r&gt;.html", html)
        self.assertIn("logs/&lt;run&gt;.log", html)

    def test_missing_config_does_not_send(self) -> None:
        notifier = EmailNotifier(smtp_host="", mail_from="", mail_to="")
        with patch("drun.notifier.emailer.smtplib.SMTP_SSL") as smtp_cls:
            notifier.send(_sample_report(), NotifyContext())
        smtp_cls.assert_not_called()

    def test_smtp_ssl_logs_in_and_sends_message(self) -> None:
        server = Mock()
        server.__enter__ = Mock(return_value=server)
        server.__exit__ = Mock(return_value=None)

        with patch("drun.notifier.emailer.smtplib.SMTP_SSL", return_value=server):
            EmailNotifier(
                smtp_host="smtp.example.test",
                smtp_user="user",
                smtp_pass="pass",
                mail_to="ops@example.test",
                html_body=True,
            ).send(
                _sample_report(),
                NotifyContext(html_path="reports/report.html", log_path="logs/run.log"),
            )

        server.login.assert_called_once_with("user", "pass")
        server.send_message.assert_called_once()
        msg = server.send_message.call_args.args[0]
        self.assertEqual(msg["To"], "ops@example.test")
        self.assertIn("测试结果", msg["Subject"])
        self.assertIn("报告: reports/report.html", msg.get_body(preferencelist=("plain",)).get_content())
        self.assertIsNotNone(msg.get_body(preferencelist=("html",)))

    def test_send_swallow_smtp_errors(self) -> None:
        with patch("drun.notifier.emailer.smtplib.SMTP_SSL", side_effect=RuntimeError("smtp down")):
            EmailNotifier(
                smtp_host="smtp.example.test",
                smtp_user="user",
                smtp_pass="pass",
                mail_to="ops@example.test",
            ).send(_sample_report(), NotifyContext())


if __name__ == "__main__":
    unittest.main()

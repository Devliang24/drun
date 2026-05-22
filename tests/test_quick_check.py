from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from typer.testing import CliRunner

import drun.cli as cli


class _FakeHTTPClient:
    def request(self, req):
        return {
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "body": {"ok": True},
            "elapsed_ms": 1.0,
            "url": "https://example.test/ping",
            "method": req.get("method", "GET"),
        }

    def close(self) -> None:
        return None


class QuickCheckCommandTests(unittest.TestCase):
    def test_q_check_runs_checks_and_prints_check_output(self) -> None:
        runner = CliRunner()

        with patch("drun.engine.http.HTTPClient", _FakeHTTPClient):
            result = runner.invoke(
                cli.app,
                [
                    "q",
                    "https://example.test/ping",
                    "-check",
                    "status_code=200",
                    "-check",
                    "$.ok=true",
                ],
            )

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Check: status_code eq 200 -> PASS", result.output)
        self.assertIn("Check: $.ok eq True -> PASS", result.output)

    def test_q_save_yaml_emits_check_field(self) -> None:
        runner = CliRunner()

        with runner.isolated_filesystem():
            with patch("drun.engine.http.HTTPClient", _FakeHTTPClient):
                result = runner.invoke(
                    cli.app,
                    [
                        "q",
                        "https://example.test/ping",
                        "-check",
                        "status_code=200",
                        "-save-yaml",
                        "case.yaml",
                    ],
                )

            self.assertEqual(result.exit_code, 0)
            text = Path("case.yaml").read_text(encoding="utf-8")

        self.assertIn("check:", text)
        self.assertNotIn("validate:", text)

    def test_q_validate_option_fails_with_check_hint(self) -> None:
        runner = CliRunner()

        result = runner.invoke(
            cli.app,
            ["q", "https://example.test/ping", "-validate", "status_code=200"],
        )

        self.assertEqual(result.exit_code, 2)
        self.assertIn("Use `-check` instead", result.output)


if __name__ == "__main__":
    unittest.main()

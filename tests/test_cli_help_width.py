from __future__ import annotations

import os
from collections import namedtuple
import unittest
from unittest.mock import patch

import drun.cli as cli
from typer.testing import CliRunner


class CliHelpWidthTests(unittest.TestCase):
    def test_columns_env_takes_precedence(self) -> None:
        with patch.dict(os.environ, {"COLUMNS": "160"}, clear=False):
            with patch("drun.cli.shutil.get_terminal_size", return_value=namedtuple("TS", "columns lines")(90, 24)):
                self.assertEqual(cli._resolve_help_width(), 160)

    def test_invalid_columns_env_falls_back_to_terminal_width(self) -> None:
        with patch.dict(os.environ, {"COLUMNS": "invalid"}, clear=False):
            with patch("drun.cli.shutil.get_terminal_size", return_value=namedtuple("TS", "columns lines")(110, 24)):
                self.assertEqual(cli._resolve_help_width(), 110)

    def test_missing_columns_uses_terminal_width(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch("drun.cli.shutil.get_terminal_size", return_value=namedtuple("TS", "columns lines")(132, 24)):
                self.assertEqual(cli._resolve_help_width(), 132)

    def test_terminal_probe_failure_uses_default_width(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with patch("drun.cli.shutil.get_terminal_size", side_effect=OSError("no tty")):
                self.assertEqual(cli._resolve_help_width(), 120)

    def test_cli_apps_share_context_settings(self) -> None:
        self.assertIn("terminal_width", cli.app.info.context_settings)
        self.assertIn("max_content_width", cli.app.info.context_settings)
        self.assertEqual(cli.app.info.context_settings, cli.export_app.info.context_settings)

    def test_root_help_lists_q_not_quick(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.app, ["--help"])
        self.assertEqual(result.exit_code, 0)
        out = result.stdout
        self.assertIn("\n  q", out)
        self.assertNotIn("quick", out)

    def test_run_help_uses_single_dash_long_options(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.app, ["run", "--help"])
        self.assertEqual(result.exit_code, 0)
        out = result.stdout
        self.assertIn("-env", out)
        self.assertIn("-report", out)
        self.assertIn("-secrets", out)
        self.assertIn("-snippet", out)
        self.assertIn("-httpx-logs", out)
        self.assertIn("-response-headers", out)
        self.assertIn("-notify-attach-html", out)
        self.assertNotIn("-nosnippet", out)
        self.assertNotIn("-snippet-lang", out)
        self.assertNotIn("-mask-secrets", out)
        self.assertNotIn("--env", out)
        self.assertNotIn("--report", out)

    def test_q_help_uses_single_dash_long_options(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.app, ["q", "--help"])
        self.assertEqual(result.exit_code, 0)
        out = result.stdout
        self.assertIn("-method", out)
        self.assertIn("-data-file", out)
        self.assertIn("-save-yaml", out)
        self.assertIn("-secrets", out)
        self.assertNotIn("-mask-secrets", out)
        self.assertNotIn("--method", out)
        self.assertNotIn("--data-file", out)

    def test_quick_command_is_removed(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.app, ["quick", "--help"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("No such command 'quick'", result.output)

    def test_server_help_uses_single_dash_long_options(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.app, ["server", "--help"])
        self.assertEqual(result.exit_code, 0)
        out = result.stdout
        self.assertIn("-port", out)
        self.assertIn("-reports-dir", out)
        self.assertIn("-headless", out)
        self.assertNotIn("-noreload", out)
        self.assertNotIn("-noopen", out)
        self.assertNotIn("--port", out)

    def test_run_accepts_single_dash_env_option(self) -> None:
        runner = CliRunner()
        with patch.object(cli, "_run_impl", return_value=None) as run_impl:
            result = runner.invoke(cli.app, ["run", "demo", "-env", "dev"])
        self.assertEqual(result.exit_code, 0)
        run_impl.assert_called_once()
        self.assertEqual(run_impl.call_args.args[8], "dev")

    def test_run_rejects_double_dash_env_option(self) -> None:
        runner = CliRunner()
        with patch.object(cli, "_run_impl", return_value=None) as run_impl:
            result = runner.invoke(cli.app, ["run", "demo", "--env", "dev"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("No such option: --env", result.output)
        run_impl.assert_not_called()

    def test_run_maps_snippet_and_secrets_modes(self) -> None:
        runner = CliRunner()
        with patch.object(cli, "_run_impl", return_value=None) as run_impl:
            result = runner.invoke(
                cli.app,
                ["run", "demo", "-secrets", "mask", "-snippet", "off"],
            )
        self.assertEqual(result.exit_code, 0)
        run_impl.assert_called_once()
        self.assertFalse(run_impl.call_args.args[13])  # reveal_secrets
        self.assertTrue(run_impl.call_args.args[18])  # no_snippet
        self.assertEqual(run_impl.call_args.args[20], "all")  # snippet_lang

    def test_run_rejects_invalid_snippet_mode(self) -> None:
        runner = CliRunner()
        with patch.object(cli, "_run_impl", return_value=None) as run_impl:
            result = runner.invoke(cli.app, ["run", "demo", "-snippet", "java"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Invalid -snippet value", result.output)
        run_impl.assert_not_called()


if __name__ == "__main__":
    unittest.main()

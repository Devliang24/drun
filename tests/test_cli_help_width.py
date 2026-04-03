from __future__ import annotations

import os
import re
from collections import namedtuple
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

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

    def test_root_help_expands_command_options(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.app, ["--help"])
        self.assertEqual(result.exit_code, 0)
        out = result.stdout
        self.assertIn("Expanded Help (All Commands)", out)
        self.assertIn("drun run", out)
        self.assertIn("-env", out)
        self.assertIn("-report", out)
        self.assertIn("-secrets", out)
        self.assertIn("-snippet", out)
        self.assertIn("drun q", out)
        self.assertIn("drun q URL", out)
        self.assertIn("-X", out)
        self.assertIn("-d", out)
        self.assertIn("-save-yaml", out)
        self.assertNotIn("-data-file", out)
        self.assertNotIn("-X, -method", out)
        self.assertNotIn("-H, -header", out)
        self.assertNotIn("-p, -param", out)
        self.assertIn("drun convert", out)
        self.assertIn("-output-mode", out)
        self.assertIn("-placeholders", out)
        self.assertIn("drun server", out)
        self.assertIn("-port", out)
        self.assertIn("-headless", out)
        self.assertIn("drun fix", out)
        self.assertIn("-mode", out)
        self.assertNotIn("--only-spacing", out)
        self.assertNotIn("--only-hooks", out)
        self.assertIn("drun init", out)
        self.assertIn("drun init [NAME]", out)
        self.assertIn("-force", out)
        self.assertIn("-ci", out)
        self.assertIn("drun export curl", out)
        self.assertIn("drun export curl PATH", out)
        self.assertIn("-case-name", out)
        self.assertIn("-outfile", out)
        self.assertIn("-layout", out)
        self.assertIn("-comments", out)
        self.assertIn("drun run PATH", out)
        self.assertIn("drun convert INFILE", out)
        self.assertNotIn("--case-name", out)
        self.assertNotIn("--outfile", out)
        self.assertNotIn("-outfile TEXT", out)
        self.assertNotIn("-max-body INTEGER", out)
        self.assertNotIn("-X TEXT", out)
        self.assertNotIn("\\[required]", out)
        self.assertNotIn("\\[default:", out)
        self.assertIn("[required]", out)
        self.assertIn("[default: single]", out)
        self.assertNotRegex(
            out,
            re.compile(r"(?m)^\s{2}(PATH|URL|INFILE|SPEC|\[NAME\]|PATH\.\.\.)\s"),
        )

    def test_quick_command_is_removed(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.app, ["quick"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("No such command 'quick'", result.output)

    def test_subcommand_help_is_disabled_and_redirected(self) -> None:
        runner = CliRunner()
        cases = [
            ["run", "--help"],
            ["q", "--help"],
            ["server", "--help"],
            ["check", "--help"],
            ["fix", "--help"],
            ["tags", "--help"],
            ["init", "--help"],
            ["convert", "--help"],
            ["convert-openapi", "--help"],
            ["export", "--help"],
            ["export", "curl", "--help"],
        ]
        for argv in cases:
            result = runner.invoke(cli.app, argv)
            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("Subcommand help is disabled. Please use: drun --help", result.output)

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

    def test_q_supports_d_at_file_and_rejects_legacy_data_file_option(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("body.json").write_text('{"name":"alice"}', encoding="utf-8")
            http_client = Mock()
            http_client.request.return_value = {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "body": {"ok": True},
                "method": "POST",
                "url": "https://example.com/demo",
                "elapsed_ms": 1.0,
            }
            with patch("drun.engine.http.HTTPClient", return_value=http_client):
                result = runner.invoke(
                    cli.app,
                    ["q", "https://example.com/demo", "-X", "POST", "-d", "@body.json"],
                )
            self.assertEqual(result.exit_code, 0)
            req = http_client.request.call_args.args[0]
            self.assertEqual(req["method"], "POST")
            self.assertEqual(req["body"], {"name": "alice"})

            legacy = runner.invoke(
                cli.app,
                ["q", "https://example.com/demo", "-data-file", "body.json"],
            )
            self.assertNotEqual(legacy.exit_code, 0)
            self.assertTrue(
                "No such option: -data-file" in legacy.output
                or "Got unexpected extra argument" in legacy.output
            )

    def test_convert_uses_new_mode_options_and_rejects_legacy_split_flags(self) -> None:
        runner = CliRunner()
        with patch.object(cli, "convert_curl", return_value=None) as convert_curl:
            result = runner.invoke(
                cli.app,
                [
                    "convert",
                    "sample.curl",
                    "-outfile",
                    "out.yaml",
                    "-output-mode",
                    "split",
                    "-placeholders",
                    "on",
                ],
            )
        self.assertEqual(result.exit_code, 0)
        convert_curl.assert_called_once()
        self.assertTrue(convert_curl.call_args.kwargs["split_output"])
        self.assertTrue(convert_curl.call_args.kwargs["placeholders"])

        legacy = runner.invoke(
            cli.app,
            ["convert", "sample.curl", "--split-output", "-outfile", "out.yaml"],
        )
        self.assertNotEqual(legacy.exit_code, 0)
        self.assertIn("No such option: --split-output", legacy.output)

    def test_export_curl_uses_layout_and_comments_modes(self) -> None:
        runner = CliRunner()
        render_step = Mock(return_value="curl https://example.com/demo")
        exporter = SimpleNamespace(
            render_step=render_step,
            describe_placeholders=Mock(return_value=(set(), set())),
        )
        case = SimpleNamespace(
            config=SimpleNamespace(name="Case A", base_url="https://example.com"),
            steps=[SimpleNamespace(name="Step 1")],
        )
        with runner.isolated_filesystem():
            Path("demo.yaml").write_text("config: {}\nsteps: []\n", encoding="utf-8")
            with (
                patch.object(cli, "_require_exporter", return_value=exporter),
                patch.object(cli, "load_yaml_file", return_value=([case], {})),
                patch.object(cli, "load_environment", return_value={}),
            ):
                result = runner.invoke(
                    cli.app,
                    [
                        "export",
                        "curl",
                        "demo.yaml",
                        "-layout",
                        "oneline",
                        "-comments",
                        "on",
                        "-outfile",
                        "out.curl",
                    ],
                )
            self.assertEqual(result.exit_code, 0)
            self.assertFalse(render_step.call_args.kwargs["multiline"])
            content = Path("out.curl").read_text(encoding="utf-8")
            self.assertIn("# Case: Case A | Step 1: Step 1", content)

            legacy = runner.invoke(
                cli.app,
                ["export", "curl", "demo.yaml", "--with-comments"],
            )
            self.assertNotEqual(legacy.exit_code, 0)
            self.assertIn("No such option: --with-comments", legacy.output)

    def test_fix_mode_maps_to_existing_run_fix_flags(self) -> None:
        runner = CliRunner()
        with patch.object(cli, "run_fix", return_value=None) as run_fix:
            result = runner.invoke(cli.app, ["fix", "testcases", "-mode", "spacing"])
        self.assertEqual(result.exit_code, 0)
        run_fix.assert_called_once_with(
            paths=["testcases"], only_spacing=True, only_hooks=False
        )

        invalid = runner.invoke(cli.app, ["fix", "testcases", "-mode", "unknown"])
        self.assertNotEqual(invalid.exit_code, 0)
        self.assertIn("Invalid -mode value", invalid.output)

    def test_init_uses_single_dash_flags_and_rejects_legacy_double_dash(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli.app, ["init", "demo_proj", "-ci", "-force"])
            self.assertEqual(result.exit_code, 0)
            self.assertTrue(Path("demo_proj").is_dir())

            legacy = runner.invoke(cli.app, ["init", "demo_proj2", "--ci"])
            self.assertNotEqual(legacy.exit_code, 0)
            self.assertIn("No such option: --ci", legacy.output)

    def test_convert_openapi_rejects_legacy_double_dash_options(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli.app,
            ["convert-openapi", "openapi.json", "--outfile", "out.yaml"],
        )
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("No such option: --outfile", result.output)


if __name__ == "__main__":
    unittest.main()

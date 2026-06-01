"""Test single-letter command resolution.

Validates that:
1. Each command is registered under its single-letter name.
2. Long names (init, run, check, ...) are no longer registered.
3. Help output lists single-letter names.
4. `c` is check, `o` is convert, `w` is convert-openapi (no overloading).
"""
from __future__ import annotations

import unittest
from pathlib import Path

import drun.cli as cli
from tests.cli_runner import CliRunner


SINGLE_LETTER_COMMANDS = {
    "i": "init",
    "r": "run",
    "c": "check",
    "f": "fix",
    "t": "tags",
    "q": "q",
    "e": "export",
    "s": "server",
    "o": "convert",
    "w": "convert-openapi",
}


class SingleLetterCommandRegistrationTests(unittest.TestCase):
    """Verify each command is registered under its single-letter name."""

    def _get_click_app(self):
        from typer.main import get_command

        return get_command(cli.app)

    def test_all_single_letter_commands_are_registered(self) -> None:
        click_app = self._get_click_app()
        for letter in SINGLE_LETTER_COMMANDS:
            with self.subTest(letter=letter):
                self.assertIn(
                    letter,
                    click_app.commands,
                    f"Single-letter command '{letter}' is not registered",
                )

    def test_long_command_names_are_not_registered(self) -> None:
        click_app = self._get_click_app()
        for long_name in ("init", "run", "check", "fix", "tags", "convert", "server"):
            with self.subTest(long_name=long_name):
                self.assertNotIn(
                    long_name,
                    click_app.commands,
                    f"Long command name '{long_name}' should not be registered",
                )

    def test_q_is_still_registered(self) -> None:
        click_app = self._get_click_app()
        self.assertIn("q", click_app.commands)

    def test_export_group_e_is_still_a_group(self) -> None:
        """`e` is the export group, not a direct command."""
        from typer.main import get_command

        click_app = get_command(cli.app)
        e_cmd = click_app.commands["e"]
        # The export group should be a TyperGroup (has nested commands).
        self.assertTrue(hasattr(e_cmd, "commands"))


class SingleLetterCommandHelpTests(unittest.TestCase):
    """Help output should list single-letter command names."""

    def test_root_help_lists_single_letter_commands(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.app, ["--help"])
        self.assertEqual(result.exit_code, 0)
        out = result.stdout
        for letter in ("i", "r", "c", "f", "t", "q", "e", "s", "o", "w"):
            with self.subTest(letter=letter):
                self.assertIn(
                    f"\n  {letter}",
                    out,
                    f"Single-letter command '{letter}' missing from --help",
                )

    def test_root_help_does_not_list_long_command_names(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.app, ["--help"])
        self.assertEqual(result.exit_code, 0)
        out = result.stdout
        for long_name in (
            "init",
            "run",
            "check",
            "fix",
            "tags",
            "convert",
            "convert-openapi",
            "server",
            "export",
        ):
            with self.subTest(long_name=long_name):
                # The command list section should not contain the long name
                # as a standalone command.
                self.assertNotIn(
                    f"\n  {long_name} ",
                    out,
                    f"Long command name '{long_name}' should not appear in --help command list",
                )


class LongNameRejectedTests(unittest.TestCase):
    """Long command names should produce a clear migration error, not run silently."""

    def _assert_renamed_hint(self, result, long_name: str, letter: str) -> None:
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn(long_name, result.output)
        self.assertIn(letter, result.output)
        self.assertIn("single-letter form", result.output)

    def test_long_init_is_rejected(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.app, ["init", "-force"])
        self._assert_renamed_hint(result, "init", "i")

    def test_long_run_is_rejected(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.app, ["run", "tcases"])
        self._assert_renamed_hint(result, "run", "r")

    def test_long_check_is_rejected(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.app, ["check", "tcases"])
        self._assert_renamed_hint(result, "check", "c")

    def test_long_fix_is_rejected(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.app, ["fix", "tcases"])
        self._assert_renamed_hint(result, "fix", "f")

    def test_long_tags_is_rejected(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.app, ["tags", "tcases"])
        self._assert_renamed_hint(result, "tags", "t")

    def test_long_convert_is_rejected(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.app, ["convert", "sample.curl"])
        self._assert_renamed_hint(result, "convert", "o")

    def test_long_convert_openapi_is_rejected(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.app, ["convert-openapi", "spec.yaml"])
        self._assert_renamed_hint(result, "convert-openapi", "w")

    def test_long_server_is_rejected(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.app, ["server"])
        self._assert_renamed_hint(result, "server", "s")

    def test_long_export_is_rejected(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli.app, ["export", "tc_demo.yaml"])
        self._assert_renamed_hint(result, "export", "e")


class ExportDefaultToCurlTests(unittest.TestCase):
    """Q5=A: `drun e` should default to export curl."""

    def test_e_dispatches_to_curl_with_no_subcommand(self) -> None:
        """`drun e` should auto-invoke export curl."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            from typer.main import get_command
            click_app = get_command(cli.app)
            self.assertIn("e", click_app.commands)

    def test_e_with_explicit_curl_subcommand(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            from typer.main import get_command
            click_app = get_command(cli.app)
            e_group = click_app.commands["e"]
            self.assertIn("curl", e_group.commands)


class ExportGroupDispatchTests(unittest.TestCase):
    """v8.1.4: `drun e` should default to `e curl` only when bare."""

    def test_bare_e_dispatches_to_curl(self) -> None:
        """`drun e` (no other args) should invoke `e curl`, which then
        errors on the missing PATH argument. The error should mention
        `curl`, proving the dispatch happened."""
        runner = CliRunner()
        result = runner.invoke(cli.app, ["e"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("e curl", result.output)

    def test_e_with_curl_subcommand_dispatches(self) -> None:
        """`drun e curl <path>` should reach the curl subcommand."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("tc_demo.yaml").write_text(
                "config:\n  name: Demo\n  base_url: https://example.test\nsteps: []\n",
                encoding="utf-8",
            )
            with patch("drun.cli.load_yaml_file") as mock_load:
                mock_load.return_value = ([], {})
                result = runner.invoke(
                    cli.app, ["e", "curl", "tc_demo.yaml", "-outfile", "out.curl"]
                )
                # Should reach the curl handler (no "No such command" error).
                self.assertNotIn("No such command", result.output)

    def test_e_with_unknown_arg_passes_through(self) -> None:
        """`drun e foo` (foo is not a subcommand) should fail with the
        standard 'No such command' error, not silently inject curl."""
        runner = CliRunner()
        result = runner.invoke(cli.app, ["e", "foo"])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("No such command", result.output)

    def test_e_with_option_does_not_inject_curl(self) -> None:
        """v8.1.4 regression: `drun e -port` must NOT silently inject
        `curl` (which would fail with 'No such option: -p'). Instead,
        the user sees the standard export group error pointing at the
        missing subcommand."""
        runner = CliRunner()
        result = runner.invoke(cli.app, ["e", "-port", "8080"])
        self.assertNotEqual(result.exit_code, 0)
        # Should NOT mention curl being invoked.
        self.assertNotIn("e curl", result.output)


# Import patch at the top
from unittest.mock import patch

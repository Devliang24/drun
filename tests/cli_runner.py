from __future__ import annotations

import click
from click.testing import CliRunner as ClickCliRunner
from typer.main import Typer
from typer.main import get_command as get_typer_command
from typer.testing import CliRunner as TyperCliRunner


class CliRunner(TyperCliRunner):
    """Typer test runner with Click's isolated filesystem helper.

    Typer 0.26 switched to a vendored Click namespace, so Click exceptions
    raised directly by drun's custom Click group are not formatted by Typer's
    runner.  Tests should still see the user-facing error text, not an empty
    captured output.
    """

    isolated_filesystem = ClickCliRunner.isolated_filesystem

    def invoke(self, app: Typer, *args, **kwargs):  # type: ignore[override]
        result = super().invoke(app, *args, **kwargs)
        if result.output or not isinstance(result.exception, click.ClickException):
            return result

        click_command = get_typer_command(app)
        result.exception.ctx = click.Context(click_command)
        with self.isolation() as outstreams:
            result.exception.show()
            stdout = outstreams[0].getvalue()
            stderr = outstreams[1].getvalue()
            output = outstreams[2].getvalue()

        result.stdout_bytes = stdout
        result.stderr_bytes = stderr
        result.output_bytes = output
        result.exit_code = result.exception.exit_code
        return result

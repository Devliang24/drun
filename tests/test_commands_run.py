from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

import typer

from drun.commands.run import run_cases


@contextmanager
def _chdir(path: Path):
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def _run_kwargs(**overrides):
    kwargs = {
        "path": "testcases",
        "k": None,
        "vars": [],
        "failfast": False,
        "report": None,
        "html": None,
        "allure_results": None,
        "log_level": "INFO",
        "env": "dev",
        "persist_env": None,
        "log_file": None,
        "httpx_logs": False,
        "reveal_secrets": True,
        "response_headers": False,
        "notify": None,
        "notify_only": None,
        "notify_attach_html": False,
        "no_snippet": True,
        "snippet_output": None,
        "snippet_lang": "all",
    }
    kwargs.update(overrides)
    return kwargs


class RunCommandTests(unittest.TestCase):
    def test_run_requires_env(self) -> None:
        with self.assertRaises(typer.Exit) as ctx:
            run_cases(**_run_kwargs(env=None))
        self.assertEqual(ctx.exception.exit_code, 2)

    def test_run_requires_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with _chdir(Path(td)):
                with self.assertRaises(typer.Exit) as ctx:
                    run_cases(**_run_kwargs(env="dev"))
        self.assertEqual(ctx.exception.exit_code, 2)

    def test_run_exits_when_no_yaml_files_found(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".env.dev").write_text("BASE_URL=https://api.example.com\n", encoding="utf-8")
            with _chdir(root):
                with self.assertRaises(typer.Exit) as ctx:
                    run_cases(**_run_kwargs(env="dev", path="testcases"))
        self.assertEqual(ctx.exception.exit_code, 2)


if __name__ == "__main__":
    unittest.main()

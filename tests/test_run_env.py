from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import typer

from drun.commands.run import _resolve_runtime_env_file


class RunEnvResolutionTests(unittest.TestCase):
    def test_resolve_runtime_env_file_uses_dot_env_by_default(self) -> None:
        with TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            (tmpdir / ".env").write_text("BASE_URL=http://localhost:8000\n", encoding="utf-8")

            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                resolved = _resolve_runtime_env_file(None, None)
            finally:
                os.chdir(old_cwd)

            self.assertEqual(resolved, (tmpdir / ".env").resolve())

    def test_resolve_runtime_env_file_prefers_named_env(self) -> None:
        with TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            (tmpdir / ".env").write_text("BASE_URL=http://localhost:8000\n", encoding="utf-8")
            (tmpdir / ".env.dev").write_text("BASE_URL=http://dev.local\n", encoding="utf-8")

            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                resolved = _resolve_runtime_env_file("dev", None)
            finally:
                os.chdir(old_cwd)

            self.assertEqual(resolved, (tmpdir / ".env.dev").resolve())

    def test_resolve_runtime_env_file_prefers_explicit_env_file(self) -> None:
        with TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            (tmpdir / ".env").write_text("BASE_URL=http://localhost:8000\n", encoding="utf-8")
            (tmpdir / ".env.dev").write_text("BASE_URL=http://dev.local\n", encoding="utf-8")
            (tmpdir / "demo.env").write_text("BASE_URL=http://custom.local\n", encoding="utf-8")

            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                resolved = _resolve_runtime_env_file("dev", "demo.env")
            finally:
                os.chdir(old_cwd)

            self.assertEqual(resolved, (tmpdir / "demo.env").resolve())

    def test_resolve_runtime_env_file_errors_on_missing_explicit_file(self) -> None:
        with TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)

            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                with self.assertRaises(typer.Exit):
                    _resolve_runtime_env_file("dev", "missing.env")
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()

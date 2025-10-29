"""Tests for CSV parameter path resolution behaviour"""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from drun.loader.yaml_loader import _resolve_csv_path


class ResolveCsvPathTests(unittest.TestCase):
    def test_paths_can_resolve_via_project_root_hooks(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            hooks_path = project_root / "drun_hooks.py"
            hooks_path.write_text("# hooks\n")

            testcases_dir = project_root / "testcases"
            testcases_dir.mkdir()

            data_dir = project_root / "data"
            data_dir.mkdir()
            csv_file = data_dir / "users.csv"
            csv_file.write_text("username\n")

            testcase_path = testcases_dir / "demo.yaml"
            testcase_path.write_text("config: {}\n")

            resolved = _resolve_csv_path("data/users.csv", testcase_path)

            self.assertEqual(resolved, csv_file.resolve())

    def test_paths_fallback_to_cwd_when_no_hooks(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            data_dir = project_root / "data"
            data_dir.mkdir()
            csv_file = data_dir / "users.csv"
            csv_file.write_text("username\n")

            testcases_dir = project_root / "testcases"
            testcases_dir.mkdir()
            testcase_path = testcases_dir / "demo.yaml"
            testcase_path.write_text("config: {}\n")

            previous_cwd = os.getcwd()
            try:
                os.chdir(project_root)
                resolved = _resolve_csv_path("data/users.csv", testcase_path)
            finally:
                os.chdir(previous_cwd)

            self.assertEqual(resolved, csv_file.resolve())

    def test_legacy_relative_paths_resolve_outside_project(self) -> None:
        with TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            hooks_path = project_root / "drun_hooks.py"
            hooks_path.write_text("# hooks\n")

            testcases_dir = project_root / "testcases"
            testcases_dir.mkdir()
            testcase_path = testcases_dir / "demo.yaml"
            testcase_path.write_text("config: {}\n")

            resolved = _resolve_csv_path("../data/users.csv", testcase_path)

            expected = (project_root / "../data/users.csv").resolve()
            self.assertEqual(resolved, expected)


if __name__ == "__main__":
    unittest.main()

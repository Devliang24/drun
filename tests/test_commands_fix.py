from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from drun.commands.fix import run_fix


class FixCommandTests(unittest.TestCase):
    def test_fix_moves_hooks_to_config_and_rewrites_url_to_path(self) -> None:
        content = """
config:
  name: Demo
setup_hooks:
  - ${before_case()}
steps:
  - name: GET A
    request:
      method: GET
      url: /a
    validate:
      - eq: [status_code, 200]
"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            case_dir = root / "testcases"
            case_dir.mkdir(parents=True, exist_ok=True)
            case_file = case_dir / "test_demo.yaml"
            case_file.write_text(content.strip() + "\n", encoding="utf-8")

            run_fix(paths=[str(case_dir)], only_spacing=False, only_hooks=False)

            raw = case_file.read_text(encoding="utf-8")
            data = yaml.safe_load(raw)

        self.assertNotIn("setup_hooks", data)
        self.assertIn("setup_hooks", data["config"])
        self.assertEqual(data["config"]["setup_hooks"], ["${before_case()}"])
        self.assertNotIn("url:", raw)
        self.assertEqual(data["steps"][0]["request"]["path"], "/a")

    def test_fix_inserts_blank_line_between_steps(self) -> None:
        content = """
config:
  name: Demo
steps:
  - name: First
    request:
      method: GET
      path: /a
  - name: Second
    request:
      method: GET
      path: /b
"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            case_dir = root / "testcases"
            case_dir.mkdir(parents=True, exist_ok=True)
            case_file = case_dir / "test_spacing.yaml"
            case_file.write_text(content.strip() + "\n", encoding="utf-8")

            run_fix(paths=[str(case_file)], only_spacing=True, only_hooks=False)
            fixed_text = case_file.read_text(encoding="utf-8")

        self.assertIn("\n\n  - name: Second", fixed_text)


if __name__ == "__main__":
    unittest.main()

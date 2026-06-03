from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from drun.loader.hooks import find_hooks, get_functions_for


class HooksLoaderTests(unittest.TestCase):
    def tearDown(self) -> None:
        get_functions_for.cache_clear()

    def test_default_hooks_loads_lowercase_dhook(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case_dir = root / "tcases"
            case_dir.mkdir()
            case_file = case_dir / "tc_demo.yaml"
            case_file.write_text("config:\n  name: Demo\nsteps: []\n", encoding="utf-8")
            hook_file = root / "dhook.py"
            hook_file.write_text(
                "def sign():\n    return 'lowercase'\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("DRUN_HOOKS_FILE", None)
                self.assertEqual(find_hooks(case_file), hook_file)
                funcs = get_functions_for(case_file)

        self.assertIn("sign", funcs)
        self.assertEqual(funcs["sign"](), "lowercase")

    def test_default_hooks_ignore_legacy_Dhook(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case_dir = root / "tcases"
            case_dir.mkdir()
            case_file = case_dir / "tc_demo.yaml"
            case_file.write_text("config:\n  name: Demo\nsteps: []\n", encoding="utf-8")
            (root / "Dhook.py").write_text(
                "def legacy():\n    return 'legacy'\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("DRUN_HOOKS_FILE", None)
                self.assertIsNone(find_hooks(case_file))
                funcs = get_functions_for(case_file)

        self.assertEqual(funcs, {})

    def test_default_hooks_prefer_lowercase_when_both_files_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case_dir = root / "tcases"
            case_dir.mkdir()
            case_file = case_dir / "tc_demo.yaml"
            case_file.write_text("config:\n  name: Demo\nsteps: []\n", encoding="utf-8")
            hook_file = root / "dhook.py"
            hook_file.write_text(
                "def source():\n    return 'lowercase'\n",
                encoding="utf-8",
            )
            legacy_file = root / "Dhook.py"
            legacy_file.write_text(
                "def source():\n    return 'legacy'\n",
                encoding="utf-8",
            )
            cannot_create_both = (
                not hook_file.exists()
                or not legacy_file.exists()
                or hook_file.samefile(legacy_file)
            )
            if cannot_create_both:
                self.skipTest("filesystem cannot create dhook.py and Dhook.py separately")

            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("DRUN_HOOKS_FILE", None)
                self.assertEqual(find_hooks(case_file), hook_file)
                funcs = get_functions_for(case_file)

        self.assertEqual(funcs["source"](), "lowercase")

    def test_env_override_can_load_legacy_Dhook_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case_dir = root / "tcases"
            case_dir.mkdir()
            case_file = case_dir / "tc_demo.yaml"
            case_file.write_text("config:\n  name: Demo\nsteps: []\n", encoding="utf-8")
            hook_file = root / "Dhook.py"
            hook_file.write_text(
                "def legacy():\n    return 'legacy'\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"DRUN_HOOKS_FILE": "Dhook.py"}):
                self.assertEqual(find_hooks(case_file), hook_file)
                funcs = get_functions_for(case_file)

        self.assertEqual(funcs["legacy"](), "legacy")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.check_release_version import ReleaseVersionError, check_release_version


class ReleaseVersionCheckTests(unittest.TestCase):
    def _make_project(self, version: str) -> Path:
        root = Path(tempfile.mkdtemp())
        (root / "drun").mkdir()
        (root / "pyproject.toml").write_text(
            f'[project]\nname = "drun"\nversion = "{version}"\n',
            encoding="utf-8",
        )
        (root / "drun" / "__init__.py").write_text(
            f'__version__ = "{version}"\n',
            encoding="utf-8",
        )
        return root

    def test_accepts_matching_tag_and_versions(self) -> None:
        root = self._make_project("8.2.0")

        self.assertEqual(check_release_version("v8.2.0", root), "8.2.0")
        self.assertEqual(
            check_release_version("refs/tags/v8.2.0", root),
            "8.2.0",
        )

    def test_rejects_version_mismatch(self) -> None:
        root = self._make_project("8.2.0")

        with self.assertRaises(ReleaseVersionError) as ctx:
            check_release_version("v8.2.1", root)

        message = str(ctx.exception)
        self.assertIn("Release version mismatch", message)
        self.assertIn("pyproject.toml version '8.2.0' != tag '8.2.1'", message)
        self.assertIn("drun.__version__ '8.2.0' != tag '8.2.1'", message)

    def test_rejects_non_version_tag(self) -> None:
        root = self._make_project("8.2.0")

        with self.assertRaises(ReleaseVersionError) as ctx:
            check_release_version("release-8.2.0", root)

        self.assertIn("Expected release tag like vX.Y.Z", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

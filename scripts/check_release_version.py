from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


class ReleaseVersionError(ValueError):
    """Raised when the release tag does not match package metadata."""


_VERSION_PATTERN = re.compile(r"__version__\s*=\s*['\"]([^'\"]+)['\"]")
_PROJECT_VERSION_PATTERN = re.compile(r"^version\s*=\s*['\"]([^'\"]+)['\"]")


def _normalize_tag_ref(ref_name: str | None) -> str:
    raw = (ref_name or "").strip()
    if not raw:
        raise ReleaseVersionError(
            "Missing release tag. Pass TAG or set GITHUB_REF_NAME/GITHUB_REF."
        )
    if raw.startswith("refs/tags/"):
        raw = raw.removeprefix("refs/tags/")
    if not raw.startswith("v"):
        raise ReleaseVersionError(f"Expected release tag like vX.Y.Z, got {raw!r}.")
    version = raw[1:]
    if not version:
        raise ReleaseVersionError(f"Expected release tag like vX.Y.Z, got {raw!r}.")
    return version


def _read_pyproject_version(project_root: Path) -> str:
    pyproject_path = project_root / "pyproject.toml"
    try:
        in_project = False
        for line in pyproject_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("[") and stripped.endswith("]"):
                in_project = stripped == "[project]"
                continue
            if not in_project:
                continue
            match = _PROJECT_VERSION_PATTERN.match(stripped)
            if match:
                return match.group(1)
    except FileNotFoundError as exc:
        raise ReleaseVersionError(f"Missing {pyproject_path}.") from exc
    except Exception as exc:
        raise ReleaseVersionError(
            f"Could not read project.version from {pyproject_path}: {exc}"
        ) from exc

    raise ReleaseVersionError(
        f"Could not find project.version in {pyproject_path}."
    )


def _read_module_version(project_root: Path) -> str:
    init_path = project_root / "drun" / "__init__.py"
    try:
        text = init_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ReleaseVersionError(f"Missing {init_path}.") from exc

    match = _VERSION_PATTERN.search(text)
    if not match:
        raise ReleaseVersionError(f"Could not find __version__ in {init_path}.")
    return match.group(1)


def check_release_version(ref_name: str | None, project_root: Path | str = ".") -> str:
    root = Path(project_root)
    tag_version = _normalize_tag_ref(ref_name)
    pyproject_version = _read_pyproject_version(root)
    module_version = _read_module_version(root)

    errors: list[str] = []
    if pyproject_version != tag_version:
        errors.append(
            f"pyproject.toml version {pyproject_version!r} != tag {tag_version!r}"
        )
    if module_version != tag_version:
        errors.append(f"drun.__version__ {module_version!r} != tag {tag_version!r}")

    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise ReleaseVersionError(f"Release version mismatch:\n{details}")

    return tag_version


def _default_ref_name() -> str | None:
    return os.environ.get("GITHUB_REF_NAME") or os.environ.get("GITHUB_REF")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify release tag matches pyproject.toml and drun.__version__.",
    )
    parser.add_argument(
        "tag",
        nargs="?",
        help="Release tag such as v8.2.0. Defaults to GITHUB_REF_NAME/GITHUB_REF.",
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Repository root containing pyproject.toml and drun/__init__.py.",
    )
    args = parser.parse_args(argv)

    try:
        version = check_release_version(args.tag or _default_ref_name(), args.project_root)
    except ReleaseVersionError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Release version verified: {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

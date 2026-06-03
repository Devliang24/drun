from __future__ import annotations

from pathlib import Path


def exact_child_path(directory: Path, name: str) -> Path | None:
    """Return a child whose directory entry name exactly matches ``name``.

    ``Path.exists()`` may treat names case-insensitively on some file systems.
    This helper checks the actual directory entries so filename migrations can
    enforce exact casing consistently.
    """
    try:
        for child in directory.iterdir():
            if child.name == name:
                return child
    except OSError:
        return None
    return None


def has_exact_child(directory: Path, name: str) -> bool:
    return exact_child_path(directory, name) is not None

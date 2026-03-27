from __future__ import annotations

import mimetypes
from os import PathLike
from pathlib import Path
from typing import Any, BinaryIO, Iterable, List, Sequence, Tuple


DEFAULT_BINARY_CONTENT_TYPE = "application/octet-stream"


class RequestFilesError(ValueError):
    """Raised when request.files cannot be normalized for httpx."""


def validate_request_files_shape(files: Any, *, source: str = "request.files") -> None:
    """Validate YAML-friendly request.files shapes without touching the filesystem."""
    if files is None:
        return

    if isinstance(files, dict):
        for field_name, value in files.items():
            _validate_file_value_shape(value, source=f"{source}.{field_name}")
        return

    if isinstance(files, list):
        if not files:
            return
        for idx, item in enumerate(files):
            if not isinstance(item, (list, tuple)) or len(item) != 2 or not isinstance(item[0], str):
                raise RequestFilesError(
                    f"{source}[{idx}] must be [field_name, file_spec] when request.files is a list"
                )
            _validate_file_value_shape(item[1], source=f"{source}[{idx}][1]")
        return

    raise RequestFilesError(
        f"{source} must be a mapping of field -> file spec or a list of [field_name, file_spec] pairs"
    )


def normalize_request_files(
    files: Any,
    *,
    cwd: Path | None = None,
    source: str = "request.files",
) -> tuple[Any, List[BinaryIO]]:
    """Normalize YAML-friendly request.files payloads into httpx-compatible values."""
    if files is None:
        return None, []

    base_dir = (cwd or Path.cwd()).resolve()
    opened_files: List[BinaryIO] = []

    if isinstance(files, dict):
        normalized = {
            field_name: _normalize_file_value(
                value,
                opened_files=opened_files,
                base_dir=base_dir,
                source=f"{source}.{field_name}",
            )
            for field_name, value in files.items()
        }
        return normalized, opened_files

    if isinstance(files, list):
        normalized_items = []
        for idx, item in enumerate(files):
            if not isinstance(item, (list, tuple)) or len(item) != 2 or not isinstance(item[0], str):
                _close_opened_files(opened_files)
                raise RequestFilesError(
                    f"{source}[{idx}] must be [field_name, file_spec] when request.files is a list"
                )
            normalized_items.append(
                (
                    item[0],
                    _normalize_file_value(
                        item[1],
                        opened_files=opened_files,
                        base_dir=base_dir,
                        source=f"{source}[{idx}][1]",
                    ),
                )
            )
        return normalized_items, opened_files

    raise RequestFilesError(
        f"{source} must be a mapping of field -> file spec or a list of [field_name, file_spec] pairs"
    )


def _validate_file_value_shape(value: Any, *, source: str) -> None:
    if isinstance(value, (str, PathLike, bytes, bytearray, memoryview)):
        return

    if hasattr(value, "read"):
        return

    if isinstance(value, tuple):
        if 2 <= len(value) <= 4:
            return
        raise RequestFilesError(
            f"{source} tuple must match an httpx file tuple shape of (filename, content[, content_type[, headers]])"
        )

    if isinstance(value, list):
        if len(value) == 2 and isinstance(value[0], (str, PathLike)) and isinstance(value[1], str):
            return
        raise RequestFilesError(
            f"{source} list shorthand must be [path, content_type]"
        )

    raise RequestFilesError(
        f"{source} must be a path string, [path, content_type], bytes, file-like object, or httpx-compatible tuple"
    )


def _normalize_file_value(
    value: Any,
    *,
    opened_files: List[BinaryIO],
    base_dir: Path,
    source: str,
) -> Any:
    if isinstance(value, list):
        if len(value) != 2 or not isinstance(value[0], (str, PathLike)) or not isinstance(value[1], str):
            raise RequestFilesError(f"{source} list shorthand must be [path, content_type]")
        return _open_file_spec(value[0], opened_files, base_dir=base_dir, source=source, content_type=value[1])

    if isinstance(value, (str, PathLike)):
        return _open_file_spec(value, opened_files, base_dir=base_dir, source=source)

    if isinstance(value, (bytes, bytearray, memoryview)):
        return value

    if hasattr(value, "read"):
        return value

    if isinstance(value, tuple):
        if 2 <= len(value) <= 4:
            return value
        raise RequestFilesError(
            f"{source} tuple must match an httpx file tuple shape of (filename, content[, content_type[, headers]])"
        )

    raise RequestFilesError(
        f"{source} must be a path string, [path, content_type], bytes, file-like object, or httpx-compatible tuple"
    )


def _open_file_spec(
    raw_path: str | PathLike[str],
    opened_files: List[BinaryIO],
    *,
    base_dir: Path,
    source: str,
    content_type: str | None = None,
) -> tuple[str, BinaryIO, str]:
    resolved_path = _resolve_path(raw_path, base_dir=base_dir)

    if not resolved_path.exists():
        raise RequestFilesError(f"{source} path not found: {resolved_path}")
    if not resolved_path.is_file():
        raise RequestFilesError(f"{source} is not a file: {resolved_path}")

    try:
        handle = open(resolved_path, "rb")
    except PermissionError as exc:
        raise RequestFilesError(f"{source} cannot be opened: {resolved_path} ({exc})") from exc
    except OSError as exc:
        raise RequestFilesError(f"{source} cannot be opened: {resolved_path} ({exc})") from exc

    opened_files.append(handle)
    guessed_type = content_type or mimetypes.guess_type(str(resolved_path))[0] or DEFAULT_BINARY_CONTENT_TYPE
    return (resolved_path.name, handle, guessed_type)


def _resolve_path(raw_path: str | PathLike[str], *, base_dir: Path) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _close_opened_files(handles: Iterable[BinaryIO]) -> None:
    for handle in reversed(list(handles)):
        try:
            handle.close()
        except Exception:
            pass

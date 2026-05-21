from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List

from drun.utils.errors import LoadError


def expand_parameters(
    parameters: Any, *, source_path: str | Path | None = None
) -> List[Dict[str, Any]]:
    """Expand parameterization to a list of param dicts (zipped + CSV)."""
    if not parameters:
        return [{}]

    if isinstance(parameters, list):
        combos: List[Dict[str, Any]] = [{}]

        def product_append(
            base: List[Dict[str, Any]], unit: List[Dict[str, Any]]
        ) -> List[Dict[str, Any]]:
            out: List[Dict[str, Any]] = []
            for b in base:
                for u in unit:
                    out.append({**b, **u})
            return out

        for idx, item in enumerate(parameters):
            if not isinstance(item, dict) or len(item) != 1:
                raise LoadError(
                    f"Invalid parameters at index {idx}: expected single-key dict like '- a-b: [...]' or '- csv: ...'."
                )
            key, value = next(iter(item.items()))
            if key == "csv" and not isinstance(value, list):
                unit = _load_csv_parameters(value, Path(source_path) if source_path else None)
            else:
                unit = _expand_zipped_block(str(key), value)
            combos = product_append(combos, unit)

        return combos

    raise LoadError(
        "Parameters must be declared as a list of single-key dictionaries under config.parameters."
    )


def _resolve_csv_path(path_value: str, source_path: Path | None) -> Path:
    from drun.loader.hooks import find_hooks

    candidate = Path(path_value).expanduser()
    if candidate.is_absolute():
        return candidate

    base: Path | None = None
    if source_path:
        hooks_path = find_hooks(source_path)
        if hooks_path:
            base = hooks_path.parent.resolve()

    if base is None:
        base = Path.cwd().resolve()

    return (base / candidate).resolve()


def _normalize_csv_columns(columns: Any) -> List[str]:
    if columns is None:
        return []
    if not isinstance(columns, list) or not columns:
        raise LoadError("CSV parameters 'columns' must be a non-empty list of column names.")
    names: List[str] = []
    for idx, col in enumerate(columns):
        if not isinstance(col, str):
            raise LoadError(f"CSV parameters column at index {idx} must be a string; got {type(col).__name__}.")
        name = col.strip()
        if not name:
            raise LoadError(f"CSV parameters column at index {idx} cannot be empty or whitespace.")
        if name in names:
            raise LoadError(f"CSV parameters column '{name}' is duplicated; column names must be unique.")
        names.append(name)
    return names


def _auto_convert_csv_value(value: str) -> Any:
    stripped = value.strip()

    if not stripped:
        return value

    if stripped.lower() == "true":
        return True
    if stripped.lower() == "false":
        return False

    digits_part = stripped.lstrip("-")
    if digits_part.isdigit() and len(digits_part) <= 15:
        return int(stripped)

    try:
        if "." in stripped:
            parts = stripped.lstrip("-").split(".")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                return float(stripped)
    except ValueError:
        pass

    return value


def _load_csv_parameters(spec: Any, source_path: Path | None) -> List[Dict[str, Any]]:
    if isinstance(spec, str):
        cfg: Dict[str, Any] = {"path": spec}
    elif isinstance(spec, dict):
        cfg = dict(spec)
    else:
        raise LoadError(
            f"Invalid CSV parameters declaration: expected string or mapping, got {type(spec).__name__}."
        )

    raw_path = cfg.get("path") or cfg.get("file")
    if not raw_path or not isinstance(raw_path, str):
        raise LoadError("CSV parameters require a string 'path'.")

    delimiter = cfg.get("delimiter", ",")
    if not isinstance(delimiter, str) or not delimiter:
        raise LoadError("CSV parameters 'delimiter' must be a non-empty string.")
    if len(delimiter) > 1:
        raise LoadError("CSV parameters 'delimiter' must be a single character.")

    encoding = cfg.get("encoding", "utf-8")
    if not isinstance(encoding, str) or not encoding:
        raise LoadError("CSV parameters 'encoding' must be a valid encoding name.")

    header_flag = cfg.get("header")
    if header_flag is not None and not isinstance(header_flag, bool):
        raise LoadError("CSV parameters 'header' must be a boolean if provided.")

    columns = _normalize_csv_columns(cfg.get("columns"))
    header = header_flag if header_flag is not None else True

    strip_values = cfg.get("strip", False)
    if strip_values not in (True, False):
        raise LoadError("CSV parameters 'strip' must be boolean when provided.")

    auto_type = cfg.get("auto_type", True)
    if auto_type not in (True, False):
        raise LoadError("CSV parameters 'auto_type' must be boolean when provided.")

    csv_path = _resolve_csv_path(raw_path, source_path)
    if not csv_path.exists():
        raise LoadError(f"CSV parameters file not found: '{raw_path}' (resolved to '{csv_path}')")

    rows: List[Dict[str, Any]] = []
    try:
        with csv_path.open(newline="", encoding=encoding) as fp:
            reader = csv.reader(fp, delimiter=delimiter)
            if header:
                try:
                    header_row = next(reader)
                except StopIteration as exc:
                    raise LoadError(f"CSV parameters file '{csv_path}' is empty.") from exc
                header_values = [str(h).strip() for h in header_row]
                if columns:
                    if len(columns) != len(header_values):
                        raise LoadError(
                            f"CSV parameters file '{csv_path}' header has {len(header_values)} columns but 'columns' override defines {len(columns)}."
                        )
                    fieldnames = columns
                else:
                    if any(not name for name in header_values):
                        raise LoadError(
                            f"CSV parameters file '{csv_path}' has empty column names in header row."
                        )
                    seen: set[str] = set()
                    for name in header_values:
                        if name in seen:
                            raise LoadError(
                                f"CSV parameters file '{csv_path}' header contains duplicate column '{name}'."
                            )
                        seen.add(name)
                    fieldnames = header_values
                start_line = 2
            else:
                if not columns:
                    raise LoadError(
                        f"CSV parameters for '{csv_path}' require 'columns' when 'header' is false."
                    )
                fieldnames = columns
                start_line = 1

            expected_len = len(fieldnames)
            for line_no, raw_row in enumerate(reader, start=start_line):
                if not raw_row or all(not str(cell).strip() for cell in raw_row):
                    continue
                if len(raw_row) != expected_len:
                    raise LoadError(
                        f"CSV parameters file '{csv_path}' line {line_no}: expected {expected_len} columns, got {len(raw_row)}."
                    )

                def process_cell(val: str) -> Any:
                    if strip_values:
                        val = val.strip()
                    if auto_type:
                        return _auto_convert_csv_value(val)
                    return val

                rows.append(
                    {
                        fieldnames[idx]: process_cell(raw_row[idx])
                        for idx in range(expected_len)
                    }
                )
    except UnicodeDecodeError as exc:
        raise LoadError(
            f"Failed to decode CSV parameters file '{csv_path}' with encoding '{encoding}'."
        ) from exc
    except OSError as exc:
        raise LoadError(f"Failed to read CSV parameters file '{csv_path}': {exc}") from exc

    if not rows:
        raise LoadError(f"CSV parameters file '{csv_path}' produced no data rows.")

    return rows


def _expand_zipped_block(key: str, rows: Any) -> List[Dict[str, Any]]:
    if not isinstance(rows, list):
        raise LoadError(f"Zipped parameters for '{key}' must be provided as a list.")
    names = [n.strip() for n in str(key).split("-") if n.strip()]
    if not names:
        raise LoadError(f"Zipped parameter key '{key}' must contain at least one variable name.")

    unit: List[Dict[str, Any]] = []
    for row in rows:
        if len(names) == 1:
            if isinstance(row, (list, tuple)):
                if len(row) != 1:
                    raise LoadError(
                        f"Zipped parameters for '{key}' expect single values; got {row!r}."
                    )
                values = [row[0]]
            else:
                values = [row]
        else:
            if not isinstance(row, (list, tuple)):
                raise LoadError(
                    f"Zipped parameters for '{key}' expect list/tuple rows matching {names}; got {row!r}."
                )
            if len(row) != len(names):
                raise LoadError(
                    f"Row {row!r} does not match variables {names} for zipped group '{key}'."
                )
            values = list(row)
        unit.append({name: value for name, value in zip(names, values)})
    return unit

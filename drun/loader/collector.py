from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable, List, Sequence

from drun.utils.files import has_exact_child


LEGACY_TEST_DIRS = {"testcases", "testsuites"}
CASE_FILE_RE = re.compile(r"^tc_[a-z0-9_]+\.ya?ml$")
SUITE_FILE_RE = re.compile(r"^ts_[a-z0-9_]+\.ya?ml$")
MODULE_DIR_RE = re.compile(r"^[a-z0-9_]+$")


class InvalidTestPathError(ValueError):
    """Raised when a YAML test path violates the supported layout."""


class AmbiguousTestTargetError(ValueError):
    """Raised when a shorthand test target matches multiple YAML files."""


def _validate_module_dirs(path: Path, root_dir_name: str) -> None:
    parts = path.parts
    try:
        root_index = next(i for i, part in enumerate(parts) if part.lower() == root_dir_name)
    except StopIteration:
        return
    for dirname in parts[root_index + 1 : -1]:
        if dirname.startswith(".") or (dirname.startswith("__") and dirname.endswith("__")):
            continue
        if not MODULE_DIR_RE.fullmatch(dirname):
            raise InvalidTestPathError(
                f"[ERROR] Invalid test module directory: {path}\n"
                "Module directories under tcases/ or tsuites/ must use lowercase letters, digits, and underscores only."
            )


def _is_skipped_module_path(path: Path) -> bool:
    return any(
        (part.startswith(".") and part not in {".", ".."})
        or (part.startswith("__") and part.endswith("__"))
        for part in path.parts
    )


def _is_valid_name(path: Path) -> bool:
    name = path.name
    if path.suffix.lower() not in {".yaml", ".yml"}:
        return False
    parts = {p.lower() for p in path.parts}
    if _is_skipped_module_path(path):
        return False
    if LEGACY_TEST_DIRS & parts:
        raise InvalidTestPathError(
            f"[ERROR] Invalid test path: {path}\n"
            "Legacy directories are not supported. Use tcases/tc_*.yaml or tsuites/ts_*.yaml."
        )
    # Accept files under tcases/ or tsuites/ directories
    if "tcases" in parts or "tsuites" in parts:
        if "tcases" in parts and "tsuites" in parts:
            raise InvalidTestPathError(
                f"[ERROR] Invalid test path: {path}\n"
                "Do not nest tcases/ and tsuites/ inside each other."
            )
        if "tcases" in parts:
            _validate_module_dirs(path, "tcases")
            if not CASE_FILE_RE.fullmatch(name):
                raise InvalidTestPathError(
                    f"[ERROR] Invalid test file name: {path}\n"
                    "Files under tcases/ must be named tc_*.yaml or tc_*.yml."
                )
            return True
        _validate_module_dirs(path, "tsuites")
        if not SUITE_FILE_RE.fullmatch(name):
            raise InvalidTestPathError(
                f"[ERROR] Invalid test file name: {path}\n"
                "Files under tsuites/ must be named ts_*.yaml or ts_*.yml."
            )
        return True
    # Also accept prefix-based naming convention for temporary single files
    if name.startswith("tc_") or name.startswith("ts_"):
        return True
    return False


def _raise_ambiguous_target(filename: str, matches: list[Path]) -> None:
    lines = [
        f"[ERROR] Ambiguous test target: {Path(filename).stem}",
        "Matched multiple files:",
    ]
    lines.extend(f"  - {match}" for match in sorted(matches))
    lines.append("Use an explicit module path, e.g. auth/tc_login.")
    raise AmbiguousTestTargetError("\n".join(lines))


def _search_dirs_for_target(filename: str) -> list[str]:
    name = Path(filename).name
    if name.startswith("tc_"):
        return ["tcases"]
    if name.startswith("ts_"):
        return ["tsuites"]
    return ["tcases", "tsuites"]


def _search_in_test_dirs(filename: str, base_dir: Path | None = None) -> Path | None:
    """Search for a file in tcases/ and tsuites/ directories.
    
    Args:
        filename: The filename to search for (with or without .yaml/.yml extension)
    
    Returns:
        Path to the found file, or None if not found
    """
    # If no extension provided, try .yaml and .yml
    search_names = []
    if filename.endswith('.yaml') or filename.endswith('.yml'):
        search_names = [filename]
    else:
        search_names = [f"{filename}.yaml", f"{filename}.yml"]
    
    search_dirs = _search_dirs_for_target(filename)
    
    for search_name in search_names:
        for base_dir_name in search_dirs:
            base_path = (base_dir or Path.cwd()) / base_dir_name
            if not base_path.exists():
                continue
            
            # Try direct path first
            candidate = base_path / search_name
            if candidate.exists() and _is_valid_name(candidate):
                return candidate
            
            # Recursive search if not found at root level
            matches = sorted(match for match in base_path.rglob(search_name) if _is_valid_name(match))
            if len(matches) > 1:
                _raise_ambiguous_target(filename, matches)
            if matches:
                return matches[0]
    
    return None


def _is_prefixed_test_target(path_str: str) -> bool:
    name = Path(path_str).name
    return name.startswith("tc_") or name.startswith("ts_")


def find_project_root(source: str | Path | None) -> Path | None:
    if source is None:
        return None
    path = Path(source)
    current = path if path.is_dir() else path.parent
    for candidate in [current, *current.parents]:
        has_test_dirs = (candidate / "tcases").is_dir() or (candidate / "tsuites").is_dir()
        has_marker = (candidate / ".env").exists() or has_exact_child(
            candidate, "dhook.py"
        )
        if has_test_dirs and has_marker:
            return candidate
    if current.name in {"tcases", "tsuites"}:
        return current.parent
    for parent in current.parents:
        if parent.name in {"tcases", "tsuites"}:
            return parent.parent
    return current


def _is_project_root_target(directory: Path) -> bool:
    return (directory / "tcases").is_dir() and (directory / "tsuites").is_dir()


def _discover_yaml_files(directory: Path) -> list[Path]:
    files = sorted(directory.rglob("*.yaml")) + sorted(directory.rglob("*.yml"))
    return sorted(files)


def discover(paths: Sequence[str | Path]) -> List[Path]:
    found: List[Path] = []
    for p in paths:
        pp = Path(p)
        
        # If path doesn't exist, try smart search
        if not pp.exists():
            # Check if it's a simple filename (no path separators)
            path_str = str(p)
            if '/' not in path_str and '\\' not in path_str:
                # Search in tcases and tsuites directories
                found_file = _search_in_test_dirs(path_str)
                if found_file:
                    found.append(found_file)
                    continue
            
            # If path has no extension, try adding .yaml/.yml
            if not path_str.endswith('.yaml') and not path_str.endswith('.yml'):
                if not _is_prefixed_test_target(path_str):
                    raise InvalidTestPathError(
                        f"[ERROR] Invalid test target: {path_str}\n"
                        "Test targets without an extension must start with tc_ or ts_."
                    )
                for ext in ['.yaml', '.yml']:
                    pp_with_ext = Path(path_str + ext)
                    if pp_with_ext.exists() and _is_valid_name(pp_with_ext):
                        found.append(pp_with_ext)
                        break
                if found and found[-1].stem == pp.stem:
                    continue
        
        # Original logic remains unchanged
        if pp.is_dir():
            if _is_project_root_target(pp):
                raise AmbiguousTestTargetError(
                    f"[ERROR] Ambiguous test target: {pp}\n"
                    "Target contains both tcases/ and tsuites/. Use an explicit directory such as tcases or tsuites."
                )
            for f in _discover_yaml_files(pp):
                if _is_valid_name(f):
                    found.append(f)
        elif pp.is_file() and _is_valid_name(pp):
            found.append(pp)
    return found


def match_tags(tags: Iterable[str], expr: str | None) -> bool:
    if not expr:
        return True

    tagset = {t.lower() for t in tags}
    tokens = [tok.lower() for tok in re.findall(r"\(|\)|and|or|not|[^()\s]+", expr, flags=re.IGNORECASE)]
    position = 0

    def current() -> str | None:
        return tokens[position] if position < len(tokens) else None

    def consume(expected: str | None = None) -> str | None:
        nonlocal position
        tok = current()
        if tok is None:
            return None
        if expected is not None and tok != expected:
            return None
        position += 1
        return tok

    def parse_expression() -> bool:
        return parse_or()

    def parse_or() -> bool:
        value = parse_and()
        while consume("or") is not None:
            rhs = parse_and()
            value = value or rhs
        return value

    def parse_and() -> bool:
        value = parse_not()
        while consume("and") is not None:
            rhs = parse_not()
            value = value and rhs
        return value

    def parse_not() -> bool:
        if consume("not") is not None:
            return not parse_not()
        return parse_primary()

    def parse_primary() -> bool:
        tok = current()
        if tok is None:
            return False
        if tok == "(":
            consume("(")
            value = parse_expression()
            if consume(")") is None:
                return False
            return value
        consume()
        return tok in tagset

    result = parse_expression()
    if position != len(tokens):
        return False
    return result


def resolve_invoke_path(invoke_path: str, base_dir: Path | None = None) -> Path | None:
    """Resolve an invoke path to an actual tcases file path.

    Supported formats:
    - tc_login
    - auth/tc_login
    - tc_login.yaml
    - auth/tc_login.yaml
    - tcases/auth/tc_login.yaml
    """
    if base_dir is None:
        base_dir = Path.cwd()

    invoke_path = invoke_path.replace('\\', '/')
    has_extension = invoke_path.endswith('.yaml') or invoke_path.endswith('.yml')

    candidates: List[Path] = []
    normalized = invoke_path.removeprefix("tcases/")

    if has_extension:
        if invoke_path.startswith("tcases/"):
            candidates.append(base_dir / invoke_path)
        else:
            candidates.append(base_dir / "tcases" / normalized)
    else:
        for ext in ['.yaml', '.yml']:
            if invoke_path.startswith("tcases/"):
                candidates.append(base_dir / (invoke_path + ext))
            else:
                candidates.append(base_dir / "tcases" / (normalized + ext))

    for candidate in candidates:
        if candidate.exists() and candidate.is_file() and _is_valid_name(candidate):
            return candidate

    filename = Path(normalized).name
    if not has_extension:
        for ext in ['.yaml', '.yml']:
            result = _search_in_test_dirs(filename + ext, base_dir=base_dir)
            if result:
                return result
    else:
        result = _search_in_test_dirs(filename, base_dir=base_dir)
        if result:
            return result

    return None

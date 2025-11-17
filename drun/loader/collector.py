from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable, List, Sequence


def _is_valid_name(path: Path) -> bool:
    name = path.name
    if path.suffix.lower() not in {".yaml", ".yml"}:
        return False
    # Accept files under testcases/ or testsuites/ directories
    parts = {p.lower() for p in path.parts}
    if "testcases" in parts or "testsuites" in parts:
        return True
    # Also accept prefix-based naming convention
    if name.startswith("test_") or name.startswith("suite_"):
        return True
    return False


def _search_in_test_dirs(filename: str) -> Path | None:
    """Search for a file in testcases/ and testsuites/ directories.
    
    Args:
        filename: The filename to search for (must include .yaml or .yml extension)
    
    Returns:
        Path to the found file, or None if not found
    """
    # Only accept filenames with .yaml or .yml extension
    if not (filename.endswith('.yaml') or filename.endswith('.yml')):
        return None
    
    search_dirs = ['testcases', 'testsuites']
    
    for base_dir in search_dirs:
        base_path = Path(base_dir)
        if not base_path.exists():
            continue
        
        # Try direct path first
        candidate = base_path / filename
        if candidate.exists() and _is_valid_name(candidate):
            return candidate
        
        # Recursive search if not found at root level
        matches = list(base_path.rglob(filename))
        if matches and _is_valid_name(matches[0]):
            return matches[0]
    
    return None


def discover(paths: Sequence[str | Path]) -> List[Path]:
    found: List[Path] = []
    for p in paths:
        pp = Path(p)
        
        # If path doesn't exist, try smart search in testcases/testsuites directories
        if not pp.exists():
            # Check if it's a simple filename (no path separators)
            path_str = str(p)
            if '/' not in path_str and '\\' not in path_str:
                # Search in testcases and testsuites directories
                found_file = _search_in_test_dirs(path_str)
                if found_file:
                    found.append(found_file)
                    continue
        
        # Original logic remains unchanged
        if pp.is_dir():
            for f in sorted(pp.rglob("*.yml")):
                if _is_valid_name(f):
                    found.append(f)
            for f in sorted(pp.rglob("*.yaml")):
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

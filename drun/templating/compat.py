from __future__ import annotations

import re


_TEMPLATE_WITH_CALL_PATTERN = re.compile(r"\$\{[^}]*\([^)]*\)[^}]*\}")
_ESCAPED_TEMPLATE_QUOTES_PATTERN = re.compile(r'"(\$\{[^}]*\})"')
_SIMPLE_TOKEN_PATTERN = re.compile(r"\$(?!\{)([A-Za-z_][A-Za-z0-9_]*)")

# System variables that should be skipped during token normalization.
# They are handled by the runner for response assertions/extracts.
_RESERVED_SYSTEM_VARS = {
    "body",
    "headers",
    "status_code",
    "elapsed_ms",
    "url",
    "method",
    "stream_events",
    "stream_summary",
    "stream_raw_chunks",
}


def escape_template_expressions_in_yaml(raw_text: str) -> str:
    """Wrap ${func(...)} expressions so YAML parsing stays stable."""

    def replace_template(match: re.Match[str]) -> str:
        full_match = match.group(0)
        start_pos = match.start()
        if start_pos > 0 and raw_text[start_pos - 1] in ('"', "'"):
            return full_match
        return f'"{full_match}"'

    return _TEMPLATE_WITH_CALL_PATTERN.sub(replace_template, raw_text)


def strip_escaped_template_quotes(value: str) -> str:
    """Remove YAML-added quotes around template expressions."""
    return _ESCAPED_TEMPLATE_QUOTES_PATTERN.sub(r"\1", value)


def clean_escaped_template_string(value: str) -> str:
    """Normalize display-oriented escaped template strings."""
    cleaned = strip_escaped_template_quotes(value)
    if cleaned != value:
        return cleaned

    if '\\"' in value or "\\'" in value:
        result = value
        if result.startswith('"') and result.endswith('"'):
            result = result[1:-1]
        return result.replace('\\"', '"').replace("\\'", "'")

    return cleaned


def normalize_simple_tokens(text: str) -> str:
    """Expand bare $var tokens into ${var} for downstream evaluation."""

    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in _RESERVED_SYSTEM_VARS:
            return match.group(0)
        return f"${{{name}}}"

    return _SIMPLE_TOKEN_PATTERN.sub(repl, text)

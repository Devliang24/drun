from __future__ import annotations

from dataclasses import dataclass
from textwrap import indent
from typing import Optional


@dataclass(frozen=True)
class DiagnosticCode:
    code: str
    title: str
    description: str


DIAGNOSTIC_CODE_CATALOG: tuple[DiagnosticCode, ...] = (
    DiagnosticCode(
        "DRUN-YAML-001",
        "YAML parse failure",
        "The YAML parser could not read the file because the syntax is invalid.",
    ),
    DiagnosticCode(
        "DRUN-YAML-002",
        "YAML schema violation",
        "The YAML document shape or a generic schema field does not match the supported DSL.",
    ),
    DiagnosticCode(
        "DRUN-YAML-003",
        "Invalid request field",
        "A request contains an unsupported field, commonly `request.url` instead of `request.path`.",
    ),
    DiagnosticCode(
        "DRUN-YAML-004",
        "Unsupported request.json",
        "`request.json` is not part of the DSL; JSON payloads should use `request.body`.",
    ),
    DiagnosticCode(
        "DRUN-YAML-005",
        "Invalid request nesting",
        "A step field such as `check`, `extract`, or hooks is incorrectly nested under `request`.",
    ),
    DiagnosticCode(
        "DRUN-YAML-006",
        "Invalid parameter location",
        "Case parameters are declared outside the supported `config.parameters` location.",
    ),
    DiagnosticCode(
        "DRUN-YAML-007",
        "Invalid body path syntax",
        "A response body check or extraction uses legacy `body.` syntax instead of `$` syntax.",
    ),
    DiagnosticCode(
        "DRUN-YAML-008",
        "Invalid request.files usage",
        "`request.files` is malformed or combined with `request.body`.",
    ),
    DiagnosticCode(
        "DRUN-YAML-009",
        "Legacy DSL syntax",
        "The file uses removed fields such as `cases`, `loop`, or `foreach`.",
    ),
    DiagnosticCode(
        "DRUN-YAML-010",
        "Invalid caseflow syntax",
        "`caseflow` or one of its items does not match the supported list-of-mappings form.",
    ),
    DiagnosticCode(
        "DRUN-YAML-011",
        "Invalid step executable target",
        "A step defines no executable target, combines targets, or adds request-only fields to `sleep`.",
    ),
    DiagnosticCode(
        "DRUN-YAML-012",
        "Legacy validate field",
        "`validate` has been renamed to `check`.",
    ),
    DiagnosticCode(
        "DRUN-YAML-013",
        "Invalid hook declaration",
        "A hook field is in the wrong location or does not use `${func(...)}` expression syntax.",
    ),
    DiagnosticCode(
        "DRUN-YAML-014",
        "Invalid step spacing",
        "Step items are missing the blank line required by `drun c` style validation.",
    ),
    DiagnosticCode(
        "DRUN-YAML-015",
        "Invalid repeat or sleep value",
        "`repeat` or `sleep` has an unsupported value type or range.",
    ),
    DiagnosticCode(
        "DRUN-YAML-999",
        "YAML load failure",
        "A fallback YAML loading error occurred before a more specific diagnostic was available.",
    ),
)

DIAGNOSTIC_CODES: dict[str, DiagnosticCode] = {
    item.code: item for item in DIAGNOSTIC_CODE_CATALOG
}


def get_diagnostic_code(code: str) -> DiagnosticCode | None:
    return DIAGNOSTIC_CODES.get(code)


def is_known_diagnostic_code(code: str) -> bool:
    return code in DIAGNOSTIC_CODES


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    path: Optional[str] = None
    hint: Optional[str] = None
    example: Optional[str] = None
    source_line: Optional[str] = None

    @property
    def headline(self) -> str:
        return f"{self.code} {self.message}"

    def format(self) -> str:
        lines = [self.headline]
        if self.file:
            location = self.file
            if self.line is not None:
                location = f"{location}:{self.line}"
            lines.append(f"File: {location}")
        if self.path:
            lines.append(f"Path: {self.path}")
        if self.source_line:
            lines.append(f"Line: {self.source_line.strip()}")
        if self.hint:
            lines.extend(["", self.hint])
        if self.example:
            lines.extend(["", "Example:", indent(self.example.strip("\n"), "  ")])
        return "\n".join(lines)


class LoadError(Exception):
    def __init__(
        self,
        message: str | None = None,
        *,
        diagnostic: Diagnostic | None = None,
    ) -> None:
        self.diagnostic = diagnostic
        super().__init__(message if message is not None else (diagnostic.format() if diagnostic else ""))


class DiagnosticError(LoadError):
    pass


class ValidationFailure(Exception):
    pass

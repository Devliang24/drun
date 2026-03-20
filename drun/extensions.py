from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Set, Tuple


BuiltinFunc = Callable[..., Any]
AssertionFunc = Callable[[Any, Any], bool]
ImporterFunc = Callable[..., Any]


@dataclass(frozen=True)
class ExporterSpec:
    render_step: Callable[..., str]
    describe_placeholders: Optional[Callable[..., Tuple[Set[str], Set[str]]]] = None


_BUILTINS: Dict[str, BuiltinFunc] = {}
_ASSERTIONS: Dict[str, AssertionFunc] = {}
_IMPORTERS: Dict[str, ImporterFunc] = {}
_EXPORTERS: Dict[str, Any] = {}

_DEFAULT_IMPORTERS_LOADED = False
_DEFAULT_EXPORTERS_LOADED = False


def _normalize_extension_name(name: str) -> str:
    normalized = (name or "").strip().lower()
    if not normalized:
        raise ValueError("Extension name cannot be empty")
    return normalized


def builtin_registry() -> Dict[str, BuiltinFunc]:
    return _BUILTINS


def assertion_registry() -> Dict[str, AssertionFunc]:
    return _ASSERTIONS


def register_builtin(name: str, fn: BuiltinFunc) -> None:
    _BUILTINS[_normalize_extension_name(name)] = fn


def register_assertion(name: str, fn: AssertionFunc) -> None:
    _ASSERTIONS[_normalize_extension_name(name)] = fn


def register_importer(format_name: str, importer: ImporterFunc) -> None:
    _IMPORTERS[_normalize_extension_name(format_name)] = importer


def register_exporter(format_name: str, exporter: Any) -> None:
    _EXPORTERS[_normalize_extension_name(format_name)] = exporter


def get_builtins() -> Dict[str, BuiltinFunc]:
    from drun.templating import builtins as _  # noqa: F401

    return _BUILTINS


def get_assertions() -> Dict[str, AssertionFunc]:
    from drun.runner import assertions as _  # noqa: F401

    return _ASSERTIONS


def _ensure_default_importers_loaded() -> None:
    global _DEFAULT_IMPORTERS_LOADED
    if _DEFAULT_IMPORTERS_LOADED:
        return

    from drun.importers.curl import parse_curl_text
    from drun.importers.har import parse_har
    from drun.importers.openapi import parse_openapi
    from drun.importers.postman import parse_postman

    _IMPORTERS.setdefault("curl", parse_curl_text)
    _IMPORTERS.setdefault("har", parse_har)
    _IMPORTERS.setdefault("openapi", parse_openapi)
    _IMPORTERS.setdefault("postman", parse_postman)
    _DEFAULT_IMPORTERS_LOADED = True


def _ensure_default_exporters_loaded() -> None:
    global _DEFAULT_EXPORTERS_LOADED
    if _DEFAULT_EXPORTERS_LOADED:
        return

    from drun.exporters.curl import step_placeholders, step_to_curl

    _EXPORTERS.setdefault(
        "curl",
        ExporterSpec(
            render_step=step_to_curl,
            describe_placeholders=step_placeholders,
        ),
    )
    _DEFAULT_EXPORTERS_LOADED = True


def get_importer(format_name: str) -> Optional[ImporterFunc]:
    _ensure_default_importers_loaded()
    return _IMPORTERS.get(_normalize_extension_name(format_name))


def list_importers() -> Tuple[str, ...]:
    _ensure_default_importers_loaded()
    return tuple(sorted(_IMPORTERS))


def get_exporter(format_name: str) -> Optional[Any]:
    _ensure_default_exporters_loaded()
    return _EXPORTERS.get(_normalize_extension_name(format_name))


def resolve_exporter(format_name: str) -> Optional[ExporterSpec]:
    exporter = get_exporter(format_name)
    if exporter is None:
        return None
    if isinstance(exporter, ExporterSpec):
        return exporter
    return ExporterSpec(render_step=exporter)


def list_exporters() -> Tuple[str, ...]:
    _ensure_default_exporters_loaded()
    return tuple(sorted(_EXPORTERS))

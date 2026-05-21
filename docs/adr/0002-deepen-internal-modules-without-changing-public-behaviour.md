# Deepen internal Modules without changing public behaviour

Drun Module deepening is an internal architecture move, not a public contract change. Request Projection, Response Capture, Parameter Expansion, and Run Output Orchestration can absorb implementation detail behind smaller interfaces, while CLI arguments, YAML DSL semantics, report schema, and exit code conventions stay unchanged.

**Status**: accepted

**Consequences**

- Compatibility wrappers may remain when older import paths are already used by tests or callers.
- Refactors should add behaviour tests at the public seam before moving implementation.
- Documentation updates are required only when user-visible behaviour changes.

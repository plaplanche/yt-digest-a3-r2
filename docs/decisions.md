2026-10-16: ruff runs with its default rule set and a line length of 100; mypy strict is configured in `node/pyproject.toml`.
2026-10-16: the node package is built with hatchling (src layout) and pins Python to 3.12 through `requires-python` and `node/.python-version`.
2026-10-16: the worker is an ES module package linted with ESLint 9 flat config and typescript-eslint's recommended rules; `tsc` and Vitest use `worker/tsconfig.json`.
2026-10-16: the `contracts` check passes with a message while `scripts/contracts.sh` does not exist.
2026-10-16: the contracts generator is a stdlib-only Python script (`scripts/generate_contracts.py`) covering the schema subset the contracts use; `contracts.sh` formats its Python output with the project's ruff, so no extra generator dependency is added.
2026-10-16: the log schema keeps `attrs` a free object, and the loggers do not check the per-event `service` or `attrs` of the catalogue table; only the event name, level and field names are enforced.
2026-10-16: Python models use strict field types (no coercion) with `extra="forbid"`; the TypeScript tests validate against the schemas with ajv (dev dependency).
2026-10-16: a cue counts as kept for the paragraph gap (spec 5.4 step 5) when it keeps at least one line after steps 3 and 4; segments are passed as (start, end) pairs of seconds, and the gap is compared rounded to milliseconds so that 2.0 s starts a paragraph.

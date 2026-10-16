2026-10-16: ruff runs with its default rule set and a line length of 100; mypy strict is configured in `node/pyproject.toml`.
2026-10-16: the node package is built with hatchling (src layout) and pins Python to 3.12 through `requires-python` and `node/.python-version`.
2026-10-16: the worker is an ES module package linted with ESLint 9 flat config and typescript-eslint's recommended rules; `tsc` and Vitest use `worker/tsconfig.json`.
2026-10-16: the `contracts` check passes with a message while `scripts/contracts.sh` does not exist.

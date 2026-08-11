# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`cmem-plugin-pyshacl` is a CMEM (eccenca Corporate Memory) workflow plugin that performs SHACL validation on Knowledge Graphs using pySHACL. The plugin loads data graphs and SHACL shape catalogs from CMEM, runs validation, and optionally outputs results as Entities or posts a Validation graph back to CMEM.

## Key Files

- **`cmem_plugin_pyshacl/plugin_pyshacl.py`** — The entire plugin implementation (~678 lines). Single class `ShaclValidation` extending `WorkflowPlugin`, decorated with `@Plugin` that declares all parameters (data graph URI, SHACL graph URI, validation graph URI, boolean toggles for output options, etc.).
- **`cmem_plugin_pyshacl/__init__.py`** — Package init.
- **`main.py`** — Placeholder; not used.
- **`tests/test_pyshacl.py`** — Unit/integration tests using pytest + pytest-dotenv.
- **`pyproject.toml`** — Poetry config, dependencies (pyshacl, rdflib, cmem-cmempy, cmem-client, cmem-plugin-base), dev deps (ruff, mypy, pytest, deptry, trivy).
- **`Taskfile.yaml`** — Generated task runner file; customize in `TaskfileCustom.yml`.
- **`.pre-commit-config.yaml`** — Local hooks for ruff, mypy, deptry, trivy, poetry-check.

## Architecture

The plugin follows the `cmem-plugin-base` workflow plugin pattern:

1. **Parameter declaration** via `@Plugin` decorator with `PluginParameter` definitions (graph URIs, booleans, choices).
2. **`__init__`** stores parameters as instance attrs and sets up `FixedNumberOfInputs`.
3. **`execute()`** is the entry point — it:
   - Calls `check_parameters()` for validation.
   - Uses `Client.from_context(context)` to connect to CMEM.
   - Loads graphs via `get_graph()` (exports from CMEM → parses with rdflib).
   - Runs `pyshacl.validate()` on data + SHACL graphs.
   - Optionally adds PROV provenance, labels, shui:conforms flags to the validation graph.
   - Posts results back to CMEM via `post_graph()` or returns `Entities`.

Key helper functions: `get_label()`, `preferred_label()`, `e_t()` (elapsed time).

## Development Commands

All commands require `task` (Taskfile) and Poetry installed.

```bash
# Install dependencies
poetry install

# Run all checks (linters + tests)
task check

# Run just linters (ruff, mypy, deptry, trivy)
task check:linters

# Run just tests
task check:pytest

# Format code
task format:fix

# Format with unsafe fixes
task format:fix-unsafe

# Build distribution packages
task build

# Run a single test
poetry run pytest tests/test_pyshacl.py -v
```

Pre-commit runs ruff, mypy, deptry, trivy, and poetry-check on `git commit`.

## Dependencies Summary

| Category | Key packages |
|----------|-------------|
| Core | pyshacl, rdflib, cmem-cmempy, cmem-client |
| Plugin framework | cmem-plugin-base |
| Dev | ruff, mypy, pytest, deptry, trivy-py-ecc |

## Testing

Tests use `pytest` with `pytest-dotenv` for environment-based config. A `.env` file is expected for CMEM connection credentials during testing. The test suite also supports memory profiling via `pytest-memray` (non-Windows).
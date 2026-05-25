# Development Guide

## Environment Setup

This project uses a virtual environment located in `.venv`. Ensure it is activated before running commands:

```bash
source .venv/bin/activate
```

## Running Tests

All tests are run using `pytest`:

```bash
pytest
```

**Note:** The `gramps` package is not available in this environment. Tests depend on modules that would normally be provided by the Gramps installation; therefore, any code importing from `gramps.*` must be thoroughly mocked within the test file's setup.

## Linting

This project uses `ruff` for linting:

```bash
ruff check .
```

To auto-fix linting issues:

```bash
ruff check . --fix
```

## Code Modification Rules

- Preserve existing comments unless they are demonstrably incorrect after the change.
- When modifying code, review nearby comments and update them if the behavior, assumptions, constraints, or intent changed.
- Do not remove comments simply because code was refactored, renamed, reformatted, or moved.
- Retain explanatory comments, rationale, edge-case notes, TODOs, and API usage notes whenever they remain valid.
- If a comment becomes partially outdated, update it rather than deleting it.
- New non-obvious logic should include concise explanatory comments.
- Treat comments as part of the maintained codebase, not disposable text.

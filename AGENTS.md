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

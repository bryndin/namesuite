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

## Linting

This project uses `ruff` for linting:

```bash
ruff check .
```

To auto-fix linting issues:

```bash
ruff check . --fix
```

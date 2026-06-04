# Development Guide

## Environment Setup

This project uses a virtual environment located in `.venv`. Ensure it is activated before running commands:

```bash
source ~/projects/gramps/gramps-patronymic-inference/.venv/bin/activate
```

## Running Tests

All tests are run using `pytest`:

```bash
source ~/projects/gramps/gramps-patronymic-inference/.venv/bin/activate && pytest
```

**Note:** The `gramps` package is not available in this environment. Tests depend on modules that would normally be provided by the Gramps installation; therefore, any code importing from `gramps.*` must be thoroughly mocked within the test file's setup.

## Linting

This project uses `ruff` for linting:

```bash
source ~/projects/gramps/gramps-patronymic-inference/.venv/bin/activate && ruff check .
```

To auto-fix linting issues:

```bash
source ~/projects/gramps/gramps-patronymic-inference/.venv/bin/activate && ruff check . --fix
```

## Code Formatting

After modifying Python files, format them using `ruff format`:

```bash
source ~/projects/gramps/gramps-patronymic-inference/.venv/bin/activate && ruff format <file_path>
```

For multiple files:

```bash
source ~/projects/gramps/gramps-patronymic-inference/.venv/bin/activate && ruff format <file1> <file2> ...
```

## Code Modification Rules

- Preserve existing comments unless they are demonstrably incorrect after the change.
- When modifying code, review nearby comments and update them if the behavior, assumptions, constraints, or intent changed.
- Do not remove comments simply because code was refactored, renamed, reformatted, or moved.
- Retain explanatory comments, rationale, edge-case notes, TODOs, and API usage notes whenever they remain valid.
- If a comment becomes partially outdated, update it rather than deleting it.
- New non-obvious logic should include concise explanatory comments.
- Treat comments as part of the maintained codebase, not disposable text.

## Architecture

This project uses MVCS (Model-View-Controller-Service) architecture. Agents must adhere to this architectural pattern when making changes:

- **Models**: Data structures and business logic (in `models/`)
- **Views**: UI/presentation layer (in `views/`)
- **Controllers**: Orchestration between models and views (in `controllers/`)
- **Services**: Business logic and external integrations (in `services/`)
- **Repositories**: Data access layer (in `repositories/`)

Ensure that code changes respect the separation of concerns defined by this architecture.

## Type Hints

All code must include Python type hints using Python 3.10+ syntax.
Type hints are required for all function signatures, class attributes, and module-level variables.

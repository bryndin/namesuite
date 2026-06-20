# ERD-Core-Architecture

**Authors:** Senior Software Architect, Gramps Addon Specialist
**Status:** Draft / Review
**Target Release:** Addon Pack for Gramps 6.0+

**Related Documents:**

* `[[PRD-Name-Standardization-Suite]]`
* `[[ERD-Given-Name-Renamer]]`
* `[[ERD-Patronymic-Engine]]`

---

## 1. Abstract

This document outlines the shared foundational architecture for the Name Standardization Suite. To ensure data safety, UI responsiveness during massive batch operations, and highly isolated testability, the system strictly adheres to the **MVCS (Model-View-Controller-Service)** pattern combined with elements of **Clean/Hexagonal Architecture**.

The core mandate of this architecture is strict dependency isolation:

* **Gramps DB imports (`gramps.gen.db`, `gramps.gen.lib`)** are strictly isolated to the **Repositories** layer.
* **Gramps UI imports (`gi.repository.Gtk`, `gramps.gui`)** are strictly isolated to the **Views** layer.

## 2. Architectural Layers

### 2.1 The Repositories Layer (Infrastructure)

**The Golden Rule:** The Repositories layer is the *only* place in the entire codebase permitted to interact directly with database cursors or Gramps data objects.

The repository layer is split into three specialized classes to maintain strict separation of concerns:

* **`GrampsReadRepository`** - Handles all read operations from the database, including person queries, relationship traversals, and event data extraction.
* **`GrampsWriteRepository`** - Handles all write operations, transaction management, and data mutations.
* **`GrampsPersonProxy`** - A lazy adapter that wraps Gramps `Person` objects to implement domain protocols (PatronymicSubject, ChronologySubject, etc.) without exposing Gramps internals to upper layers.

**Key Responsibilities:**

* Encapsulating the Gramps `DbTxn` (Database Transaction) context manager.
* Fetching and committing `Person` and `Name` objects.
* Providing memory-safe iterators for full-database scans (yielding handles or proxies rather than loading 15,000 objects into RAM simultaneously).
* Translating Gramps data structures into domain-friendly protocol interfaces.

**Protocol Interfaces:**

```python
# protocols/gramps.py
class GrampsDatabase(Protocol):
    def get_person_from_handle(self, handle: str) -> Person | None: ...
    def commit_person(self, person: Person, trans: object) -> None: ...

# protocols/patronymic.py
class PatronymicSubject(Protocol):
    @property
    def handle(self) -> str: ...
    @property
    def gender(self) -> Gender: ...
    @property
    def has_patronymic(self) -> bool: ...
    @property
    def given_name(self) -> str | None: ...

class PatronymicRepository(Protocol):
    def get_patronymic_subject(self, handle: str) -> PatronymicSubject | None: ...
    def get_father_handle(self, person_handle: str) -> str | None: ...

# protocols/chronology.py
class ChronologySubject(Protocol):
    @property
    def handle(self) -> str: ...

class ChronologyRepository(Protocol):
    def get_chronology_subject(self, handle: str) -> ChronologySubject | None: ...
    def get_event_years(self, person_handle: str) -> list[int]: ...
    def iter_event_years(self) -> Generator[int, None, None]: ...
```

### 2.2 The Services Layer (Business Logic & Orchestration)

The Services layer contains the core business logic. It relies on the injected `GrampsReadRepository` and `GrampsWriteRepository` to fetch and mutate data, meaning it requires **zero knowledge** of Gramps' internal C/Python APIs.

The primary service handling the "Apply" step from the `[[PRD-Name-Standardization-Suite]]` is the `GrampsTransactionService`.

**Key Responsibilities:**

* **Batch Chunking:** Mutating thousands of records synchronously will cause the OS to flag Gramps as "Not Responding." This service breaks the user-approved modifications into manageable chunks.
* **Execution Delegation:** It routes specific modifications to the specialized engines (e.g., routing name shifts to the `NameCanonicalizationService`).
* **Generator Pattern:** Yields progress metrics back to the caller to maintain UI responsiveness.

**Service Interface:**

```python
class TransactionService(Protocol):
    def execute_batch(
        self, approved_changes: list, transaction_desc: str
    ) -> Generator[float, None, None]:
        """Executes batch changes, yielding progress percentages."""
        ...
```

### 2.3 The Controllers & Views Layers (GTK UI)

The Controllers manage the user interface and respond to user events, while the Views define the UI layouts. UI-specific imports (like `gi.repository.Gtk`) are completely contained within the Views layer.

**Tab-Based View Structure:**
To maintain manageable file sizes and clear separation of concerns, the main `ToolWindow` view delegates to tab-specific view classes:
- **`RenameTab`** - Manages the "Rename Given Names" tab UI, including search/replace options, results treeview, and event handlers
- **`AuditTab`** - Manages the "Audit Patronymics" tab UI, including audit settings, results treeview, and event handlers

The `ToolWindow` acts as a shell that:
- Instantiates the tab classes with references to the parent window and controller
- Adds tab widgets to a GTK Notebook
- Provides delegation methods that forward calls to the appropriate tab instance
- Maintains shared window lifecycle (destroy handler, callback)

**Anti-Freeze Mechanism:**
When the user clicks the global `[Apply]` button, the Controller invokes the `execute_batch` generator. Instead of a blocking loop, it uses the GTK main loop iterator to consume the progress updates while keeping the UI responsive.

## 3. Reversibility & Rollback Strategy

All batch modifications are strictly funneled through the native Gramps database transaction manager (`DbTxn`). Because of this, Gramps natively handles all undo and redo operations. Users can simply use the standard `Edit -> Undo` menu in the Gramps UI to safely and completely roll back any batch operation executed by the suite.

## 4. Testing & Verification

The primary benefit of this architecture is testability. Upstream Gramps relies heavily on `PyGObject` (the `gi` package), which binds to native OS GTK libraries. These are notoriously difficult to load in standard CI/CD virtual environments.

Because our Services layer is completely decoupled from both Gramps database internals and GTK:

1. We construct mock implementations of `GrampsReadRepository` and `GrampsWriteRepository` using standard Python data structures.
2. We can run $100\%$ of our linguistic heuristics, query canonicalizations, and chunking algorithms in a pure, headless Python environment using `pytest` and `hypothesis`.
3. We avoid the overhead of mocking `DbTxn` objects or GTK widgets in our core logic tests.

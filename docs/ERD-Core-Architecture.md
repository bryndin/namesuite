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

The `GrampsDbRepository` acts as our data access adapter. It contains zero business logic, linguistic rules, or GTK UI references. It strictly translates internal operations into Gramps database operations.

**Key Responsibilities:**

* Encapsulating the Gramps `DbTxn` (Database Transaction) context manager.
* Fetching and committing `Person` and `Name` objects.
* Providing memory-safe iterators for full-database scans (yielding handles rather than loading 15,000 objects into RAM simultaneously).

**Conceptual Interface:**

```python
# repositories/gramps_db_repository.py
from gramps.gen.db import DbTxn
from gramps.gen.lib import Person, Name, NameType

class GrampsDbRepository:
    def __init__(self, dbstate):
        self.db = dbstate.db

    def get_person(self, handle: str) -> Person:
        return self.db.get_person_from_handle(handle)

    def iter_all_person_handles(self):
        for handle in self.db.iter_person_handles():
            yield handle

    def open_transaction(self, description: str) -> DbTxn:
        return DbTxn(description, self.db)

    def commit_person(self, person: Person, txn: DbTxn):
        self.db.commit_person(person, txn)

```

### 2.2 The Services Layer (Business Logic & Orchestration)

The Services layer contains the core business logic. It relies on the injected `GrampsDbRepository` to fetch data, meaning it requires **zero knowledge** of Gramps' internal C/Python APIs.

The primary service handling the "Apply" step from the `[[PRD-Name-Standardization-Suite]]` is the `GrampsTransactionService`.

**Key Responsibilities:**

* **Batch Chunking:** Mutating thousands of records synchronously will cause the OS to flag Gramps as "Not Responding." This service breaks the user-approved modifications into manageable chunks.
* **Execution Delegation:** It routes specific modifications to the specialized engines (e.g., routing name shifts to the `NameCanonicalizationService`).
* **Generator Pattern:** Yields progress metrics back to the caller to maintain UI responsiveness.

**Conceptual Interface:**

```python
# services/transaction_service.py

class GrampsTransactionService:
    def __init__(self, repository: 'GrampsDbRepository'):
        self.repository = repository
        self.chunk_size = 100 # Process N records per UI tick

    def execute_batch(self, approved_changes: list, transaction_desc: str):
        """
        Executes a batch of structural changes, yielding progress percentages.
        """
        total = len(approved_changes)
        
        with self.repository.open_transaction(transaction_desc) as txn:
            for index, change in enumerate(approved_changes):
                person = self.repository.get_person(change.person_id)
                
                # Apply the specific engine mutation (e.g., Patronymic vs Renaming)
                change.apply_mutation(person) 
                
                self.repository.commit_person(person, txn)
                
                # Yield progress back to the Controllers every chunk
                if index % self.chunk_size == 0:
                    yield (index / total) * 100
                    
        yield 100.0 # Final completion signal

```

### 2.3 The Controllers & Views Layers (GTK UI)

The Controllers manage the user interface and respond to user events, while the Views define the UI layouts. UI-specific imports (like `gi.repository.Gtk`) are completely contained within the Views layer.

**Anti-Freeze Mechanism:**
When the user clicks the global `[Apply]` button, the Controller invokes the `execute_batch` generator. Instead of a blocking loop, it uses the GTK main loop iterator to consume the progress updates while keeping the UI responsive.

```python
# controllers/main_controller.py

def on_apply_clicked(self, widget):
    approved_changes = self.view.get_checked_rows_from_treeview()
    
    # Consume the generator yielded by the Services
    for progress_pct in self.transaction_service.execute_batch(approved_changes, "Batch Name Update"):
        self.view.progress_bar.set_fraction(progress_pct / 100.0)
        
        # Flush the GTK event queue (keeps the UI from freezing)
        while self.view.events_pending():
            self.view.main_iteration()
            
    self.view.show_success_dialog()

```

## 3. Reversibility & Rollback Strategy

All batch modifications are strictly funneled through the native Gramps database transaction manager (`DbTxn`). Because of this, Gramps natively handles all undo and redo operations. Users can simply use the standard `Edit -> Undo` menu in the Gramps UI to safely and completely roll back any batch operation executed by the suite.

## 4. Testing & Verification

The primary benefit of this architecture is testability. Upstream Gramps relies heavily on `PyGObject` (the `gi` package), which binds to native OS GTK libraries. These are notoriously difficult to load in standard CI/CD virtual environments.

Because our Services layer is completely decoupled from both Gramps database internals and GTK:

1. We construct an `InMemoryMockRepository` that implements the `GrampsDbRepository` interface using standard Python dicts.
2. We can run $100\%$ of our linguistic heuristics, query canonicalizations, and chunking algorithms in a pure, headless Python environment using `pytest` and `hypothesis`.
3. We avoid the overhead of mocking `DbTxn` objects or GTK widgets in our core logic tests.

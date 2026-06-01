# ERD-Patronymic-Engine

**Authors:** Senior Software Architect, Lead Genealogist, Localization Expert
**Status:** Draft / Review
**Target Release:** Addon Pack for Gramps 6.0+

**Related Documents:**

* `[[PRD-Name-Standardization-Suite]]`
* `[[ERD-Core-Architecture]]`
* `[[ERD-Given-Name-Renamer]]`

---

## 1. Abstract

This document details the architecture and algorithmic logic for the **Patronymic Inference and Auditing Engine**. This engine is responsible for algorithmically reconstructing missing East Slavic patronymics and linting existing database entries for linguistic or chronological anomalies.

Unlike the Renamer, which uses deterministic string matching, this engine relies on a pipeline of historical chronologies, generational graph traversal, and complex morphological stemming.

## 2. Service Architecture

In accordance with the `[[ERD-Core-Architecture]]`, this module defines three distinct, stateless services that interface with the `GrampsDbRepository`.

### 2.1 `ChronologyService`

Calculates the historical Reference Year ($Y_{ref}$) to ensure generated strings respect historical naming conventions (e.g., Pre-1918 vs. Post-1918 eras).

* **Responsibilities:**
* Evaluates explicit temporal anchors (birth, marriage, death events attached to the person).
* Executes a Breadth-First Search (BFS) graph traversal through the database using the `GrampsDbRepository` if explicit events are missing.
* Applies a Generational Distance modifier ($\Delta G \times 25$ years) to estimate the era based on parents, siblings, or children.

### 2.2 `MorphologyService` (Adapter)

This service acts as an adapter between the Gramps dataset and our isolated linguistic engine.

* **Responsibilities:**
* Extracts raw string data from Gramps objects.
* Passes the strings to the internal `lib.morphology` package.
* Wraps the generated linguistic results into structured `ProposedChange` DTOs for the UI.

### 2.3 `AuditService`

The Linter component that reuses the logic from the `ChronologyService` and `MorphologyService` to evaluate existing records rather than inferring new ones.

* **Responsibilities:**
* Evaluates the target person's current patronymic against a suite of rules.
* Identifies Category A (Biological/Lineage Mismatches, e.g., male person with a female suffix).
* Identifies Category B (Temporal Anachronisms, e.g., a modern suffix appearing in 1850).
* Identifies Category C (Orthographic Anomalies, e.g., mixed Cyrillic/Latin scripts).
* Yields categorized warnings and suggested morphological fixes to the UI.

## 3. The Isolated Morphology Engine (`lib/morphology`)

To maximize testability and future-proof the codebase, the actual linguistic logic is entirely decoupled from the Gramps plugin architecture. It resides in an internal, dependency-free module (`lib/morphology/`). This allows it to be rigorously tested using `hypothesis` without booting GTK or Gramps.

### 3.1 Era Detection Pipeline

1. **Tier 1 (Direct Record):** Scan target person's events. Take the maximum valid year.
2. **Tier 2 (Graph Traversal):** Search outward (depth limit = 4). Calculate $Y_{ref} = \text{median}(Y_{relative} + (\Delta G \times 25))$.
3. **Tier 3 (Database Fallback):** Calculate the median year of the entire Gramps database. Assign a low confidence score to the result.

### 3.2 Suffix Generation Matrices (v1.0 Russian)

**Pre-1918 Epoch Strategy (Pre-Revolutionary):**
Generates direct possessive genitives without appending formal relationship terms.

* **Male:** `-ov` / `-ev` / `-in` (e.g., *Ивановъ*)
* **Female:** `-ova` / `-eva` / `-ina` (e.g., *Иванова*)
* Enforces terminal hard signs (`ъ`) where applicable.

**Modern Epoch Strategy (Post-1918):**
Generates standardized formal patronymics. Pre-reform orthography is strictly prohibited.

* **Male:** `-ovich` / `-evich` / `-ich` (e.g., *Иванович*)
* **Female:** `-ovna` / `-evna` / `-ichna` (e.g., *Ивановна*)

## 4. Execution Workflow

1. **Initialization:** The user configures the scope (e.g., filter by a specific Gramps tag) and clicks "Analyze".
2. **Batch Iteration:** The Controller requests the filtered list of person handles from the `GrampsDbRepository`.
3. **Inference Loop:**
    * The engine checks if the person already has a patronymic (if yes, skip).
    * The engine requests the linked father via the `GrampsDbRepository`. If no father exists, skip.
    * `ChronologyService` computes the $Y_{ref}$.
    * `MorphologyService` delegates to `lib/morphology` to generate the strings and confidence scores.
    * The Controller receives the `ProposedChange` DTO and displays it in the GTK View.

4. **Commit Phase:**
    * The Controller passes the user-approved DTOs to the `GrampsTransactionService`.
    * The `GrampsTransactionService` injects the strings into the Gramps database objects.
    * The `GrampsDbRepository` commits the batch within a native `DbTxn`.

## 5. System Safeguards

* **Property-Based Testing:** The `lib/morphology` module must be tested using property-based random generation (`hypothesis`) to ensure malformed Cyrillic strings, unicode anomalies, and unexpected inputs yield safe `None` returns rather than crashing the batch processor.
* **Silent Degradation:** If the morphology engine encounters a string it cannot confidently stem (e.g., an unmapped foreign name like "Karl-Heinz"), it silently skips the record. It does not guess.

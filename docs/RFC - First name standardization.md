# RFC: First Name Standardization and Canonicalization Framework for Gramps

**Authors:** Senior Software Architect, Lead Genealogist, Gramps Addon Specialist, Localization Expert, Data Modeling Specialist
**Status:** Approved for Integration
**Target Release:** Addon Pack for Gramps 5.2 / 6.0+

## 1. Abstract

This Request for Comments (RFC) details the architecture for a First Name Standardization module. Rather than introducing a new standalone addon, this framework will be integrated directly into the existing East Slavic Patronymic Inference and Reversibility project as a dedicated tab. It provides users with a conservative, user-controlled interface to efficiently execute bulk given-name renaming operations, standardize historical Church Slavonic variants to modern civil forms, and correct widespread transcription misspellings without compromising archival fidelity.

## 2. Motivation

Historical East Slavic genealogical records frequently mix church naming conventions, regional orthography, and informal civil variants. In large databases, these inconsistencies fragment lineage matching and degrade automated record searching. Furthermore, the existing patronymic inference and auditing tools rely heavily on normalized root names; inconsistent given names can trigger false-positive morphology errors or propagate incorrect data during patronymic audits. A dedicated cleaning module is required to standardize the foundational given-name dataset before advanced inference algorithms are applied.

## 3. Problem Statement

Genealogical datasets typically suffer from three categories of naming inconsistency:

1. **Church vs. Civil Forms:** Users often transcribe names exactly as written in parish registers (e.g., *Иоанн*, *Иаков*), which clash with modern civil forms (*Иван*, *Яков*).
2. **Orthographic Variations:** Pre-reform spellings, regional dialects, and interchangeable characters (e.g., *Федор* vs. *Фёдор*) create duplicate linguistic spaces.
3. **Transcription Errors:** Rapid digitization introduces typos (e.g., *Иоаннн*, *Иоан*).

When an automated patronymic auditor encounters these discrepancies, it may incorrectly flag valid names or generate linguistically inaccurate patronymic suggestions. Normalizing these names one-by-one using the native Gramps editing workflow is too slow for databases containing thousands of individuals.

## 4. Design Goals

* **Unified Tooling:** Avoid UI clutter by integrating seamlessly into the existing Patronymic Inference tool's tabbed interface.
* **User-Controlled Execution:** The tool must never perform aggressive, automated rewrites of the database without explicit user review.
* **Flexible Matching:** Provide Exact, Substring, and Regular Expression matching to handle diverse bulk renaming scenarios.
* **Conservative Scope:** Focus strictly on high-probability standardizations rather than speculative equivalence mapping.
* **Total Reversibility:** Utilize the established offline JSON transaction logging system to ensure all batch operations can be safely rolled back.

## 5. Non-Goals

To maintain focus and data integrity, this system is explicitly **NOT**:

* A universal linguistic normalization engine.
* An automatic person-merging utility or fuzzy identity matcher.
* An OCR correction or transliteration tool.
* An automated AI renaming system.
* **Complex Alternate Name Deduplication:** The tool will not attempt to merge, prune, or evaluate existing alternate names against the new target name. Existing alternate names are strictly ignored to prevent accidental data loss (e.g., deleting maiden names).

## 6. Terminology

* **Church Slavonic Name:** The formal, canonical name recorded in orthodox parish registers (e.g., *Иоанн*).
* **Civil Name:** The secular, commonly used adaptation of the canonical name (e.g., *Иван*).
* **Primary Name:** The default name string assigned to an individual in the Gramps database structure.
* **Archival Fidelity:** The principle of preserving the exact historical spelling of a record as transcribed from the source document.

## 7. Architecture Overview

The feature will be integrated into the existing **Batch Tool Addon** (`TOOL` plugin type). It will run alongside the existing inference and linter engines, sharing the same session cache and reversibility framework.

The architecture consists of three primary modules:

1. **The Dictionary Engine:** A deterministic, read-only mapping of canonical relationships (e.g., Church $\rightarrow$ Civil) and known typographical errors.
2. **The Query Controller:** Processes user-defined search parameters (Exact, Substring, RegEx) and evaluates the database against the Dictionary Engine to generate structured `ProposedChange` objects.
3. **The Shared Mutator & Logger:** Receives user-approved modifications, updates the Gramps database directly, and writes the state changes to the shared `DbTxn` offline JSON log.

## 8. Data Flow

1. **Scope Selection:** The user defines the target population via standard Gramps filters.
2. **Rule Definition:** The user inputs a source/target rule and selects the match type.
3. **Scan & Propose:** The Query Controller scans primary names, matching against user rules and the Dictionary Engine.
4. **UI Population:** The `Gtk.TreeView` grid is populated with current names, proposed standardizations, and contextual warnings (e.g., pre-existing alternate names).
5. **User Arbitration:** The user reviews suggestions and selectively confirms rows.
6. **Commit Phase:** The Shared Mutator locks the database, executes the approved primary name changes, and appends the transaction block to the user's private JSON log.

## 9. Canonicalization Strategy

The default strategy prioritizes **modern common civil names** as the canonical target, bounded by a strict adherence to archival fidelity and regional conventions.

* **Church-to-Civil Standardization:** Canonical mappings will strongly suggest civil forms for searchability (e.g., *Иаков* $\rightarrow$ *Яков*).
* **Regional Preservation:** Historical names with valid regional or dialectical roots will **not** be universally modernized. For example, *Михайло* (a standard Ukrainian/Southern form) will not be blindly converted to the Russian *Михаил* unless explicitly requested by the user.

## 10. Suggestion Engine Design

The engine avoids probabilistic or speculative NLP models, relying instead on deterministic lookups and user-defined rules.

| Detection Type | Mechanism | Example (Source $\rightarrow$ Target) |
| --- | --- | --- |
| **Direct Church Mapping** | Exact Dictionary Match | *Иоанн* $\rightarrow$ *Иван* |
| **Orthographic Correction** | Exact Dictionary Match | *Федор* $\rightarrow$ *Фёдор* |
| **Deterministic Typo** | Built-in RegEx | *Иоаннн* $\rightarrow$ *Иоанн* |
| **User Rule (Substring)** | User Input | *Иоан* $\rightarrow$ *Иван* (within *Анна-Иоанновна*) |

## 11. Batch Rename Workflow

The workflow relies on a rigid "Review Before Commit" methodology that guarantees existing metadata is never overwritten.

1. **Rule Configuration:** The user enters a `Source Name` and `Target Name`.
2. **Match Type Selection:** The user selects from a dropdown:
    * `Exact Match`: Replaces only if the given name string matches entirely.
    * `Substring`: Replaces occurrences within compound names.
    * `Regular Expression`: For advanced pattern matching.
3. **Grid Population:** Clicking "Scan Database" populates the results grid. No database modifications occur at this stage.
4. **Alternate Name Preservation (Optional):** Upon commit, if the user has checked "Preserve original Primary Names as Alternate Names":
    * The system checks if the *Original Primary Name* already exists in the individual's Alternate Names list.
    * **If Yes:** The preservation step is skipped (preventing duplicates and protecting the Revert log).
    * **If No:** The system deep-copies the Primary Name (preserving surnames/citations), changes its type to "Also Known As," and appends it to the Alternate Names list.
5. **Commit:** The user clicks "Apply Selected Corrections." The Primary Name strings are updated in place, and the transaction is logged.

## 12. UI/UX Design Principles

The tool integrates into the existing `Gtk.Notebook` layout. A new tab will be inserted, resulting in a 4-tab interface using target-explicit naming: `Given Names` | `Infer Patronymics` | `Audit Patronymics` | `Rollback`.

**Given Names Tab Layout:**

* **Top Bar:** Match Type Dropdown, Source Input, Target Input, "Scan Database" button.
* **Global Options:** Checkbox for "Preserve original Primary Names as Alternate Names" (Default: True).
* **Main Grid (`Gtk.TreeView`):**
  * `Use` (Checkbox)
  * `ID`
  * `Individual`
  * `Current Name`
  * `Proposed Name` (Uses Pango markup for diff highlights)
* **Footer:** Global "Select All" checkbox and an `[Apply Selected Corrections]` button.

## 13. Logging and Rollback

To ensure the Gramps database remains clean, this module fully reuses the existing reversibility framework established by the patronymic project.

* **Log Location:** Changes are serialized to the offline JSON log located at `~/.gramps/reversibility_logs/<database_id>.json`.
* **Unified Revert Tab:** Renaming transactions will appear in the existing `Revert` tab alongside inference and linting executions.
* **State Verification:** During a rollback, if the current primary name in the database differs from the previously `inferred_value` (indicating manual user modification after the batch run), the engine skips the rollback to preserve data integrity.

## 14. Safety Constraints

* **No Auto-Commit:** The system will never write to the database automatically.
* **Strict Target Scope:** The tool modifies the Gramps Primary Name field exclusively.
* **Graceful Failures:** Unrecognized or malformed strings are silently bypassed during the initial scan rather than triggering exceptions.

## 15. Extensibility Model

The Dictionary Engine utilizes a pluggable, JSON-based registry. This allows community contributors to submit new regional baselines (e.g., Ukrainian or Belarusian mappings) without modifying Python logic.

## 16. Future Work

* **Contextual Inference (P3):** Utilizing sibling consistency or patronymic evidence to resolve ambiguous names.
* **Dialect Mapping (P4):** Providing cautious, opt-in baseline support for cross-border dialect normalization.

## 17. Expert Review Commentary

* **Lead Software Architect (S.A.):** "For dataset-wide substring and RegEx searches, we must ensure the query engine yields cleanly to the GTK main loop. Scanning 15,000 records with a poorly written user regex could freeze the UI if not batched correctly."
* **Senior Genealogist (S.G.):** "Giving users the choice of exact vs. substring is excellent. It prevents compound names from being accidentally mangled, but allows advanced users to fix widespread hyphenated errors. Highlighting existing alternate names in the grid perfectly handles the duplication risk."
* **Gramps Addon Specialist (G.S.):** "Adding this as a 4th tab (`Standardize`) to the existing `Gtk.Notebook` is the right call. It prevents tool proliferation in the Gramps menu. Reusing the exact same `DbTxn` logging class means our Revert tab instantly supports these new renaming transactions with zero extra code."
* **Localization Expert (L.E.):** "The exact match dictionary is vital for Church-to-Civil conversions. RegEx is too blunt for historical morphology. The dual approach (Dictionary + User Rules) covers all bases."
* **Data Modeling Specialist (D.M.):** "Because this module shares the rollback state verification, a user can infer patronymics, standardize first names, and audit the database, then cleanly roll back *any* of those steps independently from the Revert tab."

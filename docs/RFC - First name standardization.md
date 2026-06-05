# RFC: First Name Standardization and Canonicalization Framework for Gramps

**Authors:** Senior Software Architect, Lead Genealogist, Gramps Addon Specialist, Localization Expert, Data Modeling Specialist
**Status:** Approved for Integration
**Target Release:** Addon Pack for Gramps 6.0+

## 1. Abstract

This Request for Comments (RFC) details the architecture for a general First Name Standardization module. Rather than introducing a new standalone addon, this framework will be integrated directly into the existing Patronymic Inference project as a dedicated tab. It provides users with a conservative, user-controlled interface to efficiently execute bulk given-name renaming operations. While highly effective for standardizing historical East Slavic Church Slavonic variants to modern civil forms, the framework is generalized to handle typographical corrections and canonicalizations for any language or naming convention without compromising archival fidelity.

## 2. Motivation

Genealogical datasets often contain inconsistencies in given names due to evolving orthography, varied transcription standards, and simple data-entry errors. These variations fragment lineage matching and hinder automated tools like the patronymic engine. A dedicated, bulk-cleaning module is needed to standardize primary names before executing advanced data analysis.

## 3. Problem Statement

Genealogical datasets across various cultures typically suffer from these categories of naming inconsistency:

1. **Church vs. Civil Forms / Formal vs. Informal:** Transcriptions often mix canonical register names (e.g., *Иоанн*, *Johannes*) with civil or common forms (*Иван*, *Johann*).
2. **Anglicization and Assimilation:** Immigrant names frequently shift across borders and census records (e.g., *Giuseppe* to *Joseph*, *Heinrich* to *Henry*).
3. **Orthographic Variations:** Pre-reform spellings, regional dialects, and interchangeable characters (e.g., *Федор* vs. *Фёдор*, *Olof* vs *Olav*) create duplicate linguistic spaces.
4. **Transcription Errors:** Rapid digitization introduces typos (e.g., *Иоаннн*, *Иоан*).

When automated auditors or matching algorithms encounter these discrepancies, they may incorrectly flag valid names. Normalizing these names one-by-one using the native Gramps editing workflow is too slow for databases containing thousands of individuals.

## 4. Design Goals

* **Unified Tooling:** Avoid UI clutter by integrating seamlessly into the existing Patronymic Inference tool's tabbed interface.
* **User-Controlled Execution:** The tool must never perform aggressive, automated rewrites of the database without explicit user review.
* **Flexible Matching:** Provide Exact, Substring, and Regular Expression matching to handle diverse bulk renaming scenarios.
* **Conservative Scope:** Focus strictly on high-probability standardizations rather than speculative equivalence mapping.

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

The feature will be integrated into the existing **Batch Tool Addon** (`TOOL` plugin type). It will run alongside the existing inference and linter engines, sharing the same session cache.

The architecture consists of two primary modules:

1. **The Query Controller:** Processes user-defined search parameters (Exact, Substring, RegEx) and evaluates the database to generate structured `ProposedChange` objects.
2. **The Shared Mutator:** Receives user-approved modifications and updates the Gramps database directly.

## 8. Canonicalization Strategy

The default strategy prioritizes modern common or civil names as the canonical target, bounded by a strict adherence to archival fidelity and regional conventions.

* **Church-to-Civil / Formal-to-Informal Standardization:** Canonical mappings will strongly suggest standardized forms for searchability (e.g., *Иаков* $\rightarrow$ *Яков*, *Johannes* $\rightarrow$ *Johann*).
* **Regional Preservation:** Historical names with valid regional or dialectical roots will **not** be universally modernized. For example, *Михайло* (a standard Ukrainian/Southern form) will not be blindly converted to the Russian *Михаил* unless explicitly requested by the user.

## 9. Suggestion Engine Design

The engine avoids probabilistic or speculative NLP models, relying instead on direct user-defined rules.

| Detection Type | Mechanism | Example (Source $\rightarrow$ Target) |
| --- | --- | --- |
| **User Rule (Exact)** | Exact Match | *Иоанн* $\rightarrow$ *Иван* |
| **User Rule (Substring)** | Substring Match | *Иоан* $\rightarrow$ *Иван* (within *Анна-Иоанновна*) |
| **User Rule (RegEx)** | Built-in RegEx | `^Иоаннн+$` $\rightarrow$ *Иоанн* |

## 10. Batch Rename Workflow

The workflow relies on a rigid "Review Before Commit" methodology that guarantees existing metadata is never overwritten.

1. **Rule Configuration:** The user enters a `Source Name` and `Target Name`.
2. **Match Type Selection:** The user selects from a dropdown:
   * `Exact Match`: Replaces only if the given name string matches entirely.
   * `Substring`: Replaces occurrences within compound names.
   * `Regular Expression`: For advanced pattern matching.

3. **Grid Population:** Clicking "Scan Database" populates the results grid. No database modifications occur at this stage.
4. **Alternate Name Preservation (Optional):** Upon commit, if the user has checked "Preserve original Primary Names as Alternate Names":
   * The system checks if the *Original Primary Name* already exists in the individual's Alternate Names list.
   * **If Yes:** The preservation step is skipped (preventing duplicates).
   * **If No:** The system deep-copies the Primary Name (preserving surnames/citations), changes its type to "Also Known As," and appends it to the Alternate Names list.

5. **Commit Phase:** The user clicks "Apply Selected Corrections." The Primary Name strings are updated in place via a Gramps transaction (that supports native Gramps undo).

## 11. UI/UX Design Principles

The tool integrates into the existing `Gtk.Notebook` layout. A new tab will be inserted, resulting in a 2-tab interface using target-explicit naming: `Given Names` | `Audit Patronymics`.

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

## 12. Safety Constraints

* **No Auto-Commit:** The system will never write to the database automatically.
* **Strict Target Scope:** The tool modifies the Gramps Primary Name field, and may also store the original name as an alternative name.
* **Graceful Failures:** The system validates user inputs (like regular expressions) before execution to prevent UI freezes or crashes. Valid but unrecognized strings are silently bypassed during the initial scan rather than triggering exceptions.

## 13. Future Work

* **The Dictionary Engine (P2):** Implementing a deterministic, read-only mapping of canonical relationships (e.g., Church $\rightarrow$ Civil) and known typographical errors utilizing a pluggable, JSON-based registry. This will allow community contributors to submit new regional baselines without modifying Python logic.
* **Contextual Inference (P3):** Utilizing sibling consistency or patronymic evidence to resolve ambiguous names.
* **Dialect Mapping (P4):** Providing cautious, opt-in baseline support for cross-border dialect normalization.

## 14. Expert Review Commentary

* **Lead Software Architect (S.A.):** "For dataset-wide substring and RegEx searches, we must ensure the query engine yields cleanly to the GTK main loop. Scanning 15,000 records with a poorly written user regex could freeze the UI if not batched correctly."
* **Senior Genealogist (S.G.):** "Giving users the choice of exact vs. substring is excellent. It prevents compound names from being accidentally mangled, but allows advanced users to fix widespread hyphenated errors. Highlighting existing alternate names in the grid perfectly handles the duplication risk."
* **Localization Expert (L.E.):** "Moving the exact match dictionary to P2 keeps the initial release agile, while the User Rules still cover all bases for manual data cleaning."
* **Gramps Addon Specialist (G.S.):** "Adding this as a 2nd tab (`Rename Given Names`) to the existing `Gtk.Notebook` is the right call. It prevents tool proliferation in the Gramps menu."

# ERD-Given-Name-Renamer

**Authors:** Senior Software Architect, Data Modeling Specialist
**Status:** Draft / Review
**Target Release:** Addon Pack for Gramps 6.0+

**Related Documents:**

* `[[PRD-Name-Standardization-Suite]]`
* `[[ERD-Core-Architecture]]`
* `[[ERD-Patronymic-Engine]]`

---

## 1. Abstract

This document outlines the technical design for the **Given Name Renamer** engine. Unlike the patronymic engine, which relies on complex morphological generation, this module operates as a deterministic, rule-based string matching system.

It is designed to be completely language-agnostic, allowing users to apply rule-based substitutions (e.g., historical Church Slavonic to modern civil forms, or localized spelling standardizations) and pattern-based corrections (via RegEx) across a massive dataset, while strictly preserving historical source data through Gramps' Alternative Name structures.

## 2. Service Architecture

In alignment with the `[[ERD-Core-Architecture]]`, this engine introduces two specialized services that sit between the GTK UI Controllers and the `GrampsDbRepository`.

### 2.1 `RenamerService`

This is the core execution engine for string matching and replacement.

* **Responsibilities:**
* Evaluates database `Name` objects against user-defined replacement rules.
* Generates the structured `ProposedChange` objects used to populate the UI grid.

* **Safety Constraints:**
* It strictly targets the "Given Name" field of the primary `Name` object.
* It validates all user-provided Regular Expressions during initialization to prevent infinite backtracking loops (ReDoS) or runtime compilation crashes.

### 2.2 `AltNamesService`

Genealogical best practices dictate that original transcriptions must never be destroyed. This service manages the safe demotion of old names before they are overwritten.

* **Responsibilities:**
* Checks a `Person` object's existing `Alternative Names` to ensure the target historical name is not already preserved (preventing duplicate entries).
* Performs a deep copy of the original Gramps `Name` object.
* Re-assigns the copied object's `NameType` to "Also Known As" (or a localized equivalent).
* Appends the preserved name to the `Person` object before the `RenamerService` overwrites the Primary Name's string.

* **Data Integrity:** By deep-copying the Gramps `Name` object, all attached source citations, dates, and notes linked to the original transcription remain perfectly intact.

## 3. Matching Strategies

The `RenamerService` supports three distinct modes of operation, selected by the user in the UI:

* **Exact Match:** The safest and most common operation. The replacement only occurs if the entire Given Name string matches the source rule exactly. *(Prevents "John" from being mutated inside "Johnathan".)*
* **Substring Match:** Performs a standard string replacement. Useful for correcting widespread typographical errors or standardizing hyphenated compound names.
* **Regular Expression (RegEx):** Exposes Python's `re` module for advanced pattern matching. **Note:** Python regex syntax uses `\1`, `\2`, etc. for capture group backreferences in replacement patterns (not `$1`, `$2`).

## 4. Execution Workflow

1. **Initialization:** The user configures a rule (e.g., Exact Match: *Федор* $\rightarrow$ *Фёдор*) and clicks "Scan".
2. **Batch Iteration:** The Controller requests all person handles via `GrampsDbRepository.iter_all_person_handles()`.
3. **Evaluation:** For each handle, the `RenamerService` checks the Primary Name. If a match is found, it yields a `ProposedChange` data transfer object (DTO) to the UI.
4. **User Arbitration:** The user reviews the grid and selects rows to apply.
5. **Commit Phase:** - The Controller passes the approved DTOs to the `GrampsTransactionService`.
    * The `GrampsTransactionService` delegates to the `AltNamesService` to safely copy the original name to the Alternative Names array.
    * The `RenamerService` applies the string mutation to the Primary Name.
    * The `GrampsDbRepository` commits the updated `Person` object within the active `DbTxn`.

## 5. Edge Cases & Error Handling

* **Existing Alternative Names:** The system will completely ignore strings found in the `Alternative Names` list during the scan phase. This prevents the tool from accidentally modifying maiden names, historical aliases, or nicknames that the user has explicitly recorded.
* **Empty Name Fields:** Individuals with blank Given Name fields are silently skipped during the scan phase.
* **Malformed Gramps Data:** If a `Person` object lacks a Primary Name object entirely (a rare database corruption scenario), the service logs a silent warning and skips the record to prevent `NoneType` errors.

## 6. Future Work

* **External Dictionary Provider Service:** As the tool matures, we plan to decouple hardcoded typographic corrections or common mappings into an external JSON-based registry. This will allow the community to easily contribute new regional standardizations (e.g., Swedish naming normalizations or regional dialect mappings) without altering the core Python application code.

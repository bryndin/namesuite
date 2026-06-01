# PRD-Name-Standardization-Suite

**Authors:** Senior Software Architect, Lead Genealogist, Gramps Addon Specialist, Localization Expert, Data Modeling Specialist
**Status:** Approved for Implementation
**Target Release:** Addon Pack for Gramps 6.0+

**Related Engineering Documents:**

* `[[ERD-Core-Architecture]]`
* `[[ERD-Given-Name-Renamer]]`
* `[[ERD-Patronymic-Engine]]`

---

## 1. Executive Summary

The **Name Standardization Suite** is a unified batch-processing Gramps Addon designed to clean, standardize, and infer naming data across large genealogical databases.

The suite provides a generalized Given Name renamer that is applicable to any language or region. Additionally, it includes powerful inference and auditing tools for patronymic names. While the initial v1.0 release of the patronymic engine is heavily tailored to East Slavic naming conventions, the architecture is designed to be extensible to other patronymic systems in the future.

The product enforces a strict **"Review Before Commit"** workflow, guaranteeing archival fidelity by ensuring that algorithmic suggestions and bulk renaming operations are heavily scrutinized by the user before any database changes occur.

## 2. User Personas

### P1: Natalia (Professional East Slavic Researcher)

Natalia manages a massive database of 18th- and 19th-century *Revision Lists* and parish registers. Her data suffers from mixed Church Slavonic/Civil orthography, transcription typos, and omitted patronymic names.

* **Needs:** A single batch utility that can filter her database, propose renaming based on linguistic rules, and allow her to selectively approve rows before safely committing the batch.

### P2: Birger (Swedish-American Hobbyist)

Birger has a family tree crossing from Sweden to Minnesota in 1891. He wants to reconstruct historical patronymics (*Sven* $\rightarrow$ *Svensson* / *Svensdotter*) for generations that lived in Sweden, but needs the engine to halt when families migrated to the US.

* **Needs:** A flexible suite where non-Slavic patronymic modules (like Nordic systems) can eventually be loaded into the exact same UI workflow without changing how he interacts with Gramps.

## 3. UI/UX Architecture

The main suite operates as a standard Gramps **Tool Addon**, accessible via `Tools -> Name Standardization Suite...`.

The primary interface utilizes a tabbed layout containing three distinct workspaces. The addon pack also includes a companion Gramplet for inline use.

### 3.1 Tab 1: Rename Given Names

Focused on deterministic dictionary mapping and typo correction for primary names across any language.

* **Configuration Header:**
* `Match Type` Dropdown (Exact, Substring, Regular Expression).
* `Source String` Input & `Target String` Input.

* **Global Toggles:**
* `[x] Preserve original Primary Names as Alternative Names` (Default: True). Guarantees archival fidelity by copying the original spelling to the "Also Known As" list.

* **Action:** `[Scan]` Button.

### 3.2 Tab 2: Infer Patronymics

Focused on generating missing patronymics using historical morphological rules and familial graph traversal.

* **Configuration Header:**
* `Scope Filter` Dropdown (Entire Database, Filter by Tag, Selected Individuals).
* `Orthography Era` Override Dropdown (Auto-Detect, Force Pre-1918, Force Post-1918).

* **Action:** `[Analyze]` Button.

### 3.3 Tab 3: Audit Patronymics

Focused on linting existing data for temporal anachronisms, gender mismatches, and lineage errors.

* **Configuration Header:**
* `Scope Filter` Dropdown.
* `Configure Rules` Button (Opens a dialog to selectively toggle specific linguistic rules).

* **Action:** `[Audit]` Button.

### 3.4 Contextual Sidebar Gramplet

Delivered as a sidebar/bottombar Gramplet active in both the *People* and *Relationships* views.

* **Behavior:** Checks if the active person lacks a patronymic but has a linked father.
* **Visuals:** Displays the inferred patronymic, a confidence score, and a single-click `[Apply]` button for rapid, one-by-one additions outside the batch Tool.

## 4. Core Workflow: "Review Before Commit"

Regardless of which tab the user operates in, the execution flow strictly adheres to the following sequence to guarantee data safety.

1. **Parameter Definition:** The user sets the scope and rules in the configuration header.
2. **Read-Only Scan:** The engine scans the database and evaluates records.
3. **Interactive Results Grid:** The UI populates a grid with the findings. The columns adapt based on the active tab:
   * *Rename Tab:* `Use (Checkbox)` | `Gramps ID` | `Person Name` | `Current Name` | `Proposed Name`
   * *Infer Tab:* `Use (Checkbox)` | `Gramps ID` | `Person Name` | `Father's Name` | `Proposed Patronymic` | `Confidence`
   * *Audit Tab:* `Use (Checkbox)` | `Gramps ID` | `Person Name` | `Current Patronymic` | `Proposed Fix` | `Triggered Rule`

4. **Human Arbitration:** The user reviews the grid. They can select/deselect individual rows, or use a global "Select All Suggestions" checkbox.
5. **Batch Execution:** The user clicks the global `[Apply]` button at the bottom of the window.
6. **Reversibility:** The system commits the batch in a way that is fully compatible with the standard `Edit -> Undo` Gramps menu if the user realizes they made a mistake.

## 5. Feature Requirements & Constraints

### 5.1 Archival Fidelity Protections

* The suite must **never** perform an auto-commit or silent background mutation.
* When renaming Given Names, the system must retain the original string, attached citations, and notes. The tool shifts the original object to the `Alternative Names` array to prevent data loss.
* The tool must ignore existing alternative names when evaluating records for renaming to avoid mutating maiden names or recorded aliases.

### 5.2 Graceful Failures and Validation

* **Regex Safety:** The Given Names query controller must validate Regular Expressions before executing the scan to prevent catastrophic UI freezes on malformed user input.
* **Morphology Fallbacks:** If the Inference engine encounters a string it cannot confidently parse, it must silently bypass the individual during the batch scan rather than throwing an error.

### 5.3 Progress Visibility

* Batch operations involving thousands of records take time. All scanning and committing operations must display a visual progress bar indicating the percentage of completion so the user knows the application is still actively working.

## 6. Acceptance Criteria

* **AC1:** The suite successfully registers as a single menu item in Gramps and launches a tabbed interface. The Gramplet is also available in the Views menu.
* **AC2:** The Rename Given Names tab successfully shifts a modified Primary Name to an Alternative Name without losing attached source citations.
* **AC3:** The Patronymic Inference tab successfully parses standard East Slavic stems and suggests historically accurate suffixes based on lineage data.
* **AC4:** The Audit tab accurately flags an intentionally mangled patronymic (e.g., an incorrect gender suffix) and suggests the correct morphological fix.
* **AC5:** Modifying 5,000 records simultaneously updates the progress bar smoothly without causing the OS to report the application as frozen.
* **AC6:** All applied modifications can be entirely reverted using the native Gramps `Undo` command.

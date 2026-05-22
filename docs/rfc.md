# RFC: Automated Patronymic Inference and Reversibility Framework for Gramps

**Authors:** Senior Software Architect, Lead Genealogist, Gramps Addon Specialist, Localization Expert, Data Modeling Specialist
**Status:** Under Active Review
**Target Release:** Addon Pack for Gramps 5.2 / 6.0+

---

## 1. Collaborative Panel Context

This Request for Comments (RFC) outlines the technical and genealogical architecture for automated patronymic name inference within Gramps databases. It describes an extensible plugin-driven design, a strict historical-geographical heuristic pipeline, and a non-intrusive metadata storage framework.

To ensure the feature remains easy to maintain, safe for data integrity, and historically accurate, our panel has co-designed this specification:

* **Lead Software Architect (S.A.):** Focuses on performance constraints during batch operations, modular boundaries, and API signatures for regional plugins.
* **Senior Genealogist (S.G.):** Directs the chronological naming rules, warns against historical anachronisms (e.g., status-bound suffixes), and sets the validation parameters.
* **Gramps Addon Specialist (G.S.):** Ensures integration can be completed without patching upstream core files by using decoupled Tool and Gramplet interfaces.
* **Localization Expert (L.E.):** Focuses on orthography rules, soft/hard stem morphological rules, Cyrillic-to-Latin transliterations, and script detection rules.
* **Data Modeling Specialist (D.M.):** Designs the centralized, offline transaction logging system, avoiding database pollution while guaranteeing clean rollback actions.

---

## Section 1: Product Requirements Document (PRD)

### 1.1 Problem Statement

In East Slavic (Russian, Ukrainian, Belarusian) naming systems, an individual's full legal and cultural identity historically relies on a patronymic name derived from their father’s given name. While modern indices and genealogists frequently omit these names if they are not explicitly recorded in every record, their omission hinders record matching, automated searching, and clear lineage tracking.

However, executing naive automated modifications to database records can introduce major data errors:

* **Linguistic Corruption:** Generating structurally invalid suffixes based on incorrect stem identification (e.g., treating soft stems as hard stems).
* **Linguistic Anachronisms:** Generating modern post-revolutionary suffixes (e.g., `-ovich` / `-ovna`) for pre-emancipation serfs who historically used possessive genitives.
* **Westernized Name Clashes:** Corrupting Anglo-Saxon middle names (e.g., assuming "William" in "John William Smith" is an unformatted patronymic).
* **Source Splitting Corruption:** Destroying the boundary between direct, transcribed historical evidence and automated algorithmic deduction.

### 1.2 User Personas

#### P1 Persona: Natalia (Professional East Slavic Researcher)

Natalia researches 18th- and 19th-century *Revision Lists* (Ревизские сказки) and parish registers across Ukraine and Russia. Her database contains over 15,000 individuals, many of whom lack explicit patronymic fields due to rapid transcription or import errors.

* **Needs:** She requires a batch utility that safely infers patronymic names, adapts to historical class and temporal boundaries (such as pre-emancipation vs. post-emancipation naming conventions), supports dry-runs to preview changes, and maintains a clean database suitable for public publication and GEDCOM exports without metadata clutter.

#### P4 Persona (v1.1+ Scope): Birger (Swedish-American Hobbyist)

Birger has a family tree crossing from Sweden to Minnesota in 1891. He wants to reconstruct historical patronymics (*Sven* $\rightarrow$ *Svensson* / *Svensdotter*) for generations that lived in Sweden, but needs the generation engine to halt automatically when families migrated to the US and adopted fixed surnames.

* **Needs:** A plugin structure that allows loading non-Slavic modules (like Nordic patronymics) while maintaining the same underlying framework. (Note: Deferred to v1.1+; P1 focuses entirely on East Slavic).

### 1.3 Key Workflows

```txt
┌─────────────────────────────────────────────────────────────────────────────┐
│                            BATCH WIZARD WORKFLOW (P1)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [Select Scope] ──► [Select Target Region] ──► [Run Dry-Run Simulation]     │
│          │                                                │                 │
│          ▼                                                ▼                 │
│   (Tag/Place/Date)                               (Review HTML/CSV Report)   │
│                                                           │                 │
│                                                           ▼                 │
│  [Execute Rollback] ◄─── [Central Log Written] ◄─── [Commit Mutations]      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Workflow 1: The Batch Refinement Wizard (P1)

Delivered as a standard **Tool Addon** (`TOOL` plugin type) accessible via `Tools -> Name Refinement -> Infer East Slavic Patronymics...`.

1. **Filter & Scope Definition:** The user selects target individuals using Gramps filters (e.g., a specific tag, date range, or geographical region like the "Poltava Governorate").
2. **Dry-Run Simulation:** The engine evaluates candidate name targets and generates a comprehensive, read-only preview report (as a GTK TreeView and an optional exported HTML/CSV). No database writes are executed during this step.
3. **Review and Execution:** The user reviews confidence scores, geographical clues, and structural explanations. They can selectively deselect low-confidence candidates before committing changes.
4. **Logging and Serialization:** The tool writes the original and modified values to a localized, offline transaction log file, then performs a safe, batched transaction to mutate the primary names in the Gramps database.

#### Workflow 2: Inline Sidebar Gramplet (P2)

Delivered as a **Sidebar/Bottombar Gramplet Addon** (`GRAMPLET` plugin type).

1. **Active Listener Trigger:** The Gramplet connects to the standard Gramps database signal `active-person-changed`.
2. **Dynamic Inline Evaluation:** Whenever the user navigates to a new person, the Gramplet evaluates whether the active individual is missing a patronymic but has an attached father.
3. **Visual Recommendation:** If eligible, the Gramplet displays a sidebar recommendation:
    * *“Suggested Patronymic: [Ivanovich] (Confidence: 94%)”*
    * *“Rule Applied: Post-1917 Soviet Formal”*
    * An **[Apply]** button.
4. **Quick-Commit Transaction:** Clicking the apply button starts a quick database transaction, writes the change, registers the transaction in the offline log file, and refreshes the primary Gramps interface.

### 1.4 Success Metrics

* **Linguistic Accuracy:** $\ge 98\%$ correct suffix formations on verified historical noun-stems under testing.
* **Clean Database State:** $100\%$ zero database schema changes or custom database-level notes created, preserving compatibility with GEDCOM validators.
* **Strict Reversibility:** $100\%$ restoration of modified names to their original state during an undo execution, provided the user has not manually modified the generated name in the interim.

### 1.5 Non-Goals & Scope Limits

* This tool will not attempt to parse and split unstructured name fields (e.g., transforming a single Given Name string `"Ivan Petrovich"` into Given Name `"Ivan"` and Patronymic `"Petrovich"`). This must be performed beforehand using separate name-splitting tools.
* It does not attempt to correct or normalize spelling mistakes in fathers' names; it assumes the parent's given name spelling is the intended base.
* It does not support non-Slavic naming patterns (such as Nordic, Iberian, or Islamic systems) in the MVP (v1.0), though the underlying core engine is designed to support them as plugins in v1.1+.

---

## Section 2: Technical Design & Architecture

```txt
                                  [ Gramps Application Core ]
                                               │
               ┌───────────────────────────────┴───────────────────────────────┐
               ▼                                                               ▼
   [ Tool Plugin (P1 Batch) ]                                     [ Gramplet Plugin (P2 Inline) ]
               │                                                               │
               └───────────────────────────────┬───────────────────────────────┘
                                               ▼
                              [ InferenceEngineManager (Core) ]
                                               │
                                               ▼
                                 [ NamingSystemPlugin Registry ]
                                               │
                         ┌─────────────────────┴─────────────────────┐
                         ▼                                           ▼
            [ EastSlavicNamingPlugin ]                 [ future NamingSystemPlugin ]
                         │                                           │
       ┌─────────────────┴─────────────────┐                         │
       ▼                                   ▼                         ▼
 [ MorphologicalEngine ]         [ HeuristicEvaluator ]          [ Custom Rules ]
   - Hard/Soft stem parser         - Spatial lookup                  (v1.1+)
   - Orthography detector          - Temporal lookup
   - Script matching               - Family graph analyzer
                         │
                         ▼
             [ Candidate Generation ]
                         │
                         ▼
             [ Confidence Match Score ]
                         │
                         ▼
         [ Mutation & Validation Engine ] ──────────► Writes to [ Family Tree DB ]
                         │
                         ▼
        Appends to [ Offline JSON Log File ]
```

### 2.1 The Extensible Inference Architecture

To avoid hardcoding rules for regional naming variants, the engine uses a decoupled plugin registration model. This allows developers to easily register new naming systems in future releases (v1.1+).

```python
# gramps/plugins/inference/namingsystem.py

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from gramps.gen.lib import Person, DbDatabase

class InferenceCandidate:
    """Represents a generated patronymic candidate with metadata."""
    def __init__(self, patronymic: str, confidence: float, heuristics: List[str], rules_applied: List[str]):
        self.patronymic = patronymic
        self.confidence = confidence
        self.heuristics = heuristics
        self.rules_applied = rules_applied

class NamingSystemPlugin(ABC):
    @property
    @abstractmethod
    def system_id(self) -> str:
        """Unique ID of the naming system (e.g., 'east_slavic_patronymic')."""
        pass

    @property
    @abstractmethod
    def localized_name(self) -> str:
        """Translated name for display in user configurations."""
        pass

    @abstractmethod
    def check_applicability(self, person: Person, db: DbDatabase) -> float:
        """
        Evaluates regional suitability. Returns a score from 0.0 to 1.0.
        0.0 = Totally inapplicable (e.g., Western-born).
        1.0 = Highly applicable (e.g., Born in Kiev in 1890).
        """
        pass

    @abstractmethod
    def generate_patronymic(self, father_name: str, person_gender: int, target_year: Optional[int], pre_reform_script: bool) -> List[InferenceCandidate]:
        """
        Derives candidates from the father's name.
        """
        pass
```

The primary driver, `InferenceEngineManager`, discovers these plugins at startup and handles database scans:

```python
# gramps/plugins/inference/manager.py

import os
from typing import List, Dict, Any, Optional
from gramps.gen.lib import DbDatabase, Person
from .namingsystem import NamingSystemPlugin

class InferenceEngineManager:
    def __init__(self, db: DbDatabase):
        self.db = db
        self.plugins: Dict[str, NamingSystemPlugin] = {}
        self._load_plugins()

    def _load_plugins(self):
        # Discover and instantiate registered plugin classes
        # For P1, this discovers and registers EastSlavicNamingPlugin
        pass

    def evaluate_person(self, person: Person) -> List[Dict[str, Any]]:
        results = []
        father = self._get_father(person)
        if not father:
            return results

        for plugin_id, plugin in self.plugins.items():
            applicability = plugin.check_applicability(person, self.db)
            if applicability > 0.1:
                # Estimate target reference year via strict prioritized hierarchy
                ref_year = self._estimate_reference_year(person)
                # Check if pre-revolutionary or modern script is used in surrounding records
                pre_reform = self._detect_pre_revolutionary_script(person, father)

                candidates = plugin.generate_patronymic(
                    father_name=father.get_primary_name().get_first_name(),
                    person_gender=person.get_gender(),
                    target_year=ref_year,
                    pre_reform_script=pre_reform
                )

                for cand in candidates:
                    # Combined confidence scoring
                    combined_score = cand.confidence * applicability
                    results.append({
                        "plugin_id": plugin_id,
                        "candidate": cand,
                        "combined_confidence": combined_score,
                        "reference_year": ref_year,
                        "pre_reform": pre_reform
                    })
        return sorted(results, key=lambda x: x["combined_confidence"], reverse=True)

    def _get_father(self, person: Person) -> Optional[Person]:
        # Implementation to retrieve the father's Person object via family records
        pass

    def _estimate_reference_year(self, person: Person) -> Optional[int]:
        # Executes reference year resolution algorithm
        pass

    def _detect_pre_revolutionary_script(self, person: Person, father: Person) -> bool:
        # Detects whether pre-1918 Cyrillic characters are in use.
        pass
```

---

### 2.2 Plugin Architecture

We utilize a unified `EastSlavicNamingPlugin` that delegates formatting tasks to internal strategy classes:

```python
# Internal strategy structure inside the EastSlavicNamingPlugin
class EastSlavicNamingPlugin(NamingSystemPlugin):
    def __init__(self):
        self.strategies = {
            "pre_1861": Pre1861EpochStrategy(),
            "1861_1917": PostEmancipationEpochStrategy(),
            "post_1917": ModernSovietEpochStrategy()
        }

    def generate_patronymic(self, father_name: str, person_gender: int, target_year: Optional[int], pre_reform_script: bool) -> List[InferenceCandidate]:
        # 1. Classify target_year into target epoch
        epoch_key = self._classify_epoch(target_year)
        strategy = self.strategies[epoch_key]

        # 2. Run morphology parser to extract base noun stem
        stem_info = MorphologicalParser.parse_stem(father_name)

        # 3. Delegate to selected chronological strategy
        return strategy.apply(stem_info, person_gender, pre_reform_script)
```

This design maintains modular separation, eliminates code duplication, prevents boundary conflicts, and keeps the user interface simple and intuitive.

---

### 2.3 Centralized Private Transaction Log (No Database Pollution)

To ensure the family tree database remains completely standard-compliant, we avoid writing custom tables, parameters, or "Provenance Notes" to the database. Instead, all changes are recorded in a centralized offline JSON log file in the user's private configuration directory:

* **Linux/macOS:** `~/.gramps/reversibility_logs/patronymic_inference_log.json`
* **Windows:** `%APPDATA%\gramps\reversibility_logs\patronymic_inference_log.json`

#### Centralized JSON Schema

```json
{
  "database_uuid": "f3b9d4e5-a8c6-4b2e-9d8f-1a2b3c4d5e6f",
  "executions": [
    {
      "execution_id": "exec_20260520_210000",
      "timestamp": "2026-05-20T21:00:00Z",
      "plugin_id": "east_slavic_patronymic",
      "changes": [
        {
          "person_handle": "e0a13c9e4b1",
          "name_handle": "d1a83b2e7c9",
          "original_value": "",
          "inferred_value": "Иванович",
          "father_handle": "c8f9b14d2e0",
          "reference_year": 1945,
          "pre_reform": false,
          "confidence_score": 0.94,
          "applied_heuristics": ["DEATH_YEAR_POST_1917", "SIBLING_PATTERN_MATCH"]
        }
      ]
    }
  ]
}
```

### 2.4 Reversibility Engine with State Verification

Because we are working entirely within a standard decoupled addon, we cannot install database-level trigger listeners to monitor changes. Instead, we perform a **State Verification Match** during rollback operations. If the current patronymic value in the database differs from the `inferred_value` recorded in our log, it means the user has manually edited the record. In this case, the engine skips the record and preserves the user's manual edits.

```python
def rollback_batch(db: DbDatabase, log_file_path: str, target_execution_id: str) -> Dict[str, List[str]]:
    """
    Rolls back a specific execution transaction.
    """
    log_data = load_json_log(log_file_path)
    execution = find_execution(log_data, target_execution_id)

    report = {"reverted": [], "skipped_modified": [], "skipped_deleted": []}

    with db.transaction():
        for change in execution["changes"]:
            person = db.get_person_from_handle(change["person_handle"])
            if not person:
                report["skipped_deleted"].append(change["person_handle"])
                continue

            primary_name = person.get_primary_name()
            if primary_name.handle == change["name_handle"]:
                current_value = primary_name.get_patronymic()

                # Check if the current value matches what our script wrote
                if current_value == change["inferred_value"]:
                    primary_name.set_patronymic(change["original_value"])
                    db.update_person(person)
                    report["reverted"].append(person.get_primary_name().get_regular_name())
                else:
                    # User changed the value manually in the meantime
                    report["skipped_modified"].append(person.get_primary_name().get_regular_name())
            else:
                report["skipped_modified"].append(person.get_primary_name().get_regular_name())

    # Remove execution from log after processing
    remove_execution_from_log_file(log_file_path, target_execution_id)
    return report
```

---

## Section 3: Heuristics & Morphology Specification

### 3.1 Reference Year Resolution Algorithm

To accurately identify the naming standards in use during an individual's lifetime, we determine a **Reference Year ($Y_{ref}$)**. Since subsequent generations remember and record the name forms used during their ancestor's final years, the engine prioritizes death records before falling back to birth or generational heuristics.

The algorithm resolves $Y_{ref}$ using a strict, four-tier prioritized hierarchy:

```txt
          ┌──────────────────────────────────────────────┐
          │          REFERENCE YEAR RESOLUTION           │
          └──────────────────────┬───────────────────────┘
                                 │
            Is Death Year known? ├─► YES ──► Use Death Year
                                 │
                                 ▼ NO
       Is Earliest Event Year?   ├─► YES ──► Use Earliest Event Year
                                 │            (e.g., Census, Baptism, Marriage)
                                 ▼ NO
            Is Birth Year known? ├─► YES ──► Use Birth Year
                                 │
                                 ▼ NO
              Apply Generational ├────────► Use Median Year of Closest
              Lineage Heuristic             Family Generation (Parents,
                                           Siblings, or Children)
```

1. **Tier 1: Death Year:** If a death event contains a valid, parsed year, that year is used directly.
2. **Tier 2: Earliest Event Year:** If the death year is unrecorded, the engine scans all available events attached to the person (such as baptisms, census entries, marriages, and residences) and selects the earliest recorded year. These events are often closer to the period when naming conventions were active than estimated or unrecorded births.
3. **Tier 3: Birth Year:** If no other event records are available, the parsed birth year is used.
4. **Tier 4: Generational Lineage Heuristics:** If the individual's record contains no dates at all, the engine estimates the reference year using their closest family members:
    * *If siblings have dates:* Use the median year of sibling births/events.
    * *If parents have dates:* Use the median year of parent births/events + $25$ years.
    * *If children have dates:* Use the median year of children births/events - $25$ years.
    * *If no generational dates are found:* The engine cannot determine a reference year. It assigns a high-penalty confidence score and prompts the user for manual input.

---

### 3.2 Chronological Epoch Strategies & Correctness Reviews

Once the Reference Year ($Y_{ref}$) is determined, the engine delegates formatting to the appropriate strategy. To ensure historical and linguistic accuracy, orthography and correctness reviews are integrated directly into each epoch's logic.

```txt
                            CHRONOLOGICAL PIVOT WINDOWS

   Before 1861 (Peasant Serfdom)       1861 - 1917 (Post-Emancipation)     Post-1917 (Soviet Era to Modern)
◄──────────────────────────────────┼─────────────────────────────────┼──────────────────────────────►
  Format: Document-Accurate          Format: Simple Genitive           Format: Modern Formal
  Genitive with Class Suffix         Suffix (Direct -ov / -ova)        Gender Suffix (-ovich / -ovna)
  (e.g., "Петровъ сынъ")             (e.g., "Иванъ Сергеевъ Коваль")   (e.g., "Иван Сергеевич Коваль")
```

#### 1. Pre-1861 Epoch (Pre-Emancipation Serfdom)

Before the Emancipation Reform of 1861, peasants and serfs were rarely recorded with standard `-ovich` / `-ovna` patronymic suffixes [1]. Instead, they were documented using their father's possessive genitive name followed by a relationship suffix.

* **Format Rules:**
  * *Male:* Father's Name + Possessive Suffix + `сын` (son) $\rightarrow$ e.g., `Иван Петров сын`.
  * *Female:* Father's Name + Possessive Suffix + `дочь` (daughter) $\rightarrow$ e.g., `Мария Петрова дочь`.
* **Orthography Enforcement (Pre-1918 Cyrillic Script Check):**
  The engine scans the individual's family branch for historical characters: `і`, `ѣ`, `ѳ`, `ѵ`, or terminal `ъ` following a consonant (e.g., `Иванъ`, `Петровъ`).
  * *Pre-1918 Script Detected:* Append the terminal hard sign `ъ` to the father's possessive genitive and relationship indicator. Use pre-reform `і` before vowels (e.g., `Иванъ Петровъ сынъ`, `Марія Петрова дочь`).
  * *Modern Script Detected:* Use modern Cyrillic characters to maintain consistency with the rest of the tree (e.g., `Иван Петров сын`, `Мария Петрова дочь`).

---

#### 2. 1861 to 1917 Epoch (Post-Emancipation to Russian Revolution)

Following emancipation, peasants began entering civil administration records as free citizens. During this transitional era, they were recorded using their father's possessive genitive directly, omitting the words "son" or "daughter."

* **Format Rules:**
  * *Male:* Father's Name + Possessive Suffix (`-ov` / `-ev` / `-in`) $\rightarrow$ e.g., `Иван Сергеев Коваль`.
  * *Female:* Father's Name + Possessive Suffix (`-ova` / `-eva` / `-ina`) $\rightarrow$ e.g., `Анна Сергеева Коваль`.
* **Orthography Enforcement (Pre-1918 Cyrillic Script Check):**
  * *Pre-1918 Script Detected:* Append the terminal hard sign `ъ` to masculine names ending in consonants, and replace modern `и` with `і` where grammatically appropriate (e.g., `Иванъ Сергіевъ Коваль`).
  * *Modern Script Detected:* Avoid archaic characters. Maintain modern Cyrillic spelling (e.g., `Иван Сергеев Коваль`).

---

#### 3. Post-1917 Epoch (Soviet Era to Modern Day)

With the fall of the Russian Empire and subsequent Soviet legal standardizations, the standard formal patronymic endings were extended to all citizens, regardless of class.

* **Format Rules:**
  * *Male:* `-ович` (`-ovich`) / `-евич` (`-evich`) / `-ич` (`-ich`) $\rightarrow$ e.g., `Иван Сергеевич Коваль`.
  * *Female:* `-овна` (`-ovna`) / `-евна` (`-evna`) / `-ична` (`-ichna`) $\rightarrow$ e.g., `Анна Сергеевна Коваль`.
* **Orthography Enforcement:** Since this epoch falls entirely after the 1918 orthographic reform, pre-revolutionary spellings (such as `ъ` or `і`) are **never** generated, ensuring compliance with modern linguistic standards.

---

### 3.3 East Slavic Morphological Rules (Russian, Ukrainian, Belarusian)

The morphological engine maps name endings to their respective linguistic stems to determine the correct suffix endings:

```txt
                  ┌──────────────────────────────────────────────┐
                  │          MORPHOLOGICAL STEM PARSER           │
                  └──────────────────────┬───────────────────────┘
                                         │
             ┌───────────────────────────┼───────────────────────────┐
             ▼                           ▼                           ▼
    [ Hard Consonants ]          [ Soft Consonants ]         [ Contracted Vowels ]
    (except ж, ш, ч, щ, ц)         (ending in -ь)               (ending in -а, -я)
             │                           │                           │
    -ovich / -ovna               -evich / -evna              -ich / -ichna
    (Иван -> Иванович)          (Игорь -> Игоревич)         (Илья -> Ильич)
```

#### Stem Classification Table

| Father's Name Ending | Stem Classification | Male Suffix | Female Suffix | Example (Father $\rightarrow$ Patronymic M/F) |
| :--- | :--- | :--- | :--- | :--- |
| **Hard Consonant** (except ж, ш, ч, щ, ц) | Hard | `-ович` (`-ovych` / `-avich`) | `-овна` (`-ivna` / `-auna`) | Иван $\rightarrow$ Иванович / Ивановна <br> Петр $\rightarrow$ Петрович / Петровна |
| **Soft Consonant** (ending in `-ь`) | Soft | `-евич` (`-evych` / `-yavich`) | `-евна` (`-ivna` / `-yauna`) | Игорь $\rightarrow$ Игоревич / Игоревна <br> Олесь $\rightarrow$ Олесевич / Олесивна |
| **Vowel `-ий` or `-ей`** | Yod (Soft) | `-евич` (`-evych` / `-yavich`) | `-евна` (`-ivna` / `-yauna`) | Дмитрий $\rightarrow$ Дмитриевич / Дмитриевна <br> Сергей $\rightarrow$ Сергеевич / Сергеевна |
| **Vowel `-а` or `-я`** (contracted) | Contracted | `-ич` (`-ych`) | `-ична` or `-инична` (`-ivna`) | Никита $\rightarrow$ Никитич / Никитична <br> Илья $\rightarrow$ Ильич / Ильинична |

---

### 3.4 Multi-Signal Confidence Matrix

The engine combines cultural, geographic, and chronological signals to calculate a confidence score for each candidate name:

$$C = \sum (S_i \cdot W_i) - \sum (N_j \cdot V_j)$$

Where $S_i$ represent positive signals, $W_i$ their weights, $N_j$ negative signals, and $V_j$ their penalty values.

```txt
┌─────────────────────────────────────────────────────────────────────────────┐
│                       HEURISTIC CONFIDENCE SCORE MATRIX                     │
├───────────────────────────────────────┬─────────┬───────────────────────────┤
│ Signal / Condition                    │ Weight  │ Rationale                 │
├───────────────────────────────────────┼─────────┼───────────────────────────┤
│ POSITIVE SIGNALS                      │         │                           │
│ • Sibling has matching patronymic     │  +0.35  │ High family naming pattern│
│ • Birth/Baptism in Ukraine/Russia/BY  │  +0.30  │ Confirmed region of origin│
│ • Death/Burial in Ukraine/Russia/BY   │  +0.15  │ Proxy region of origin    │
│ • Parent surname has Slavic suffix    │  +0.15  │ e.g., -ov, -ev, -enko     │
│ • Records use Cyrillic characters     │  +0.10  │ Direct language proxy     │
│                                       │         │                           │
│ NEGATIVE SIGNALS                      │         │                           │
│ • Emigration recorded before birth    │  -0.80  │ Probable naming change    │
│ • Birth recorded outside Slavic regions│ -0.50  │ Out-of-bounds geography   │
│ • Ambiguous multi-word father's name  │  -0.40  │ e.g., Karl-Heinz, Johann  │
│ • Reference Year is Medieval (<1500)  │  -0.30  │ Pre-formalized patronymic │
└───────────────────────────────────────┴─────────┴───────────────────────────┘
```

#### Scoring Calculations

##### Case A: High Confidence (Post-Revolutionary Standard)

* **Target:** `Olga Ivanova` (born 1922 in Poltava, Ukraine; Died 1985 in Moscow, USSR).
* **Father:** `Ivan Ivanov`.
* **Sibling:** `Maria Ivanovna Ivanova`.
* **Signals:**
  * Sibling matching patronymic: $+0.35$
  * Birth in Poltava (Slavic region): $+0.30$
  * Records written in Cyrillic: $+0.10$
  * Death Year (Reference Year) $= 1985$ (Post-1917 Epoch $\rightarrow$ Modern Formal Suffix)
* **Final Score:** $0.75 \rightarrow$ **Safe to auto-apply.**

##### Case B: Lowered Confidence / Mixed Western Baltic Context

* **Target:** `Johan Schmidt` (born 1885 in Courland, Russian Empire).
* **Father:** `Johann Schmidt`.
* **Signals:**
  * Birth in Courland (Slavic Empire region, but mixed Baltic-German population): $+0.30$
  * Father's name matches Western lexicon (`Johann`): $-0.40$
  * Surname contains non-Slavic suffix (`Schmidt`): $-0.10$ (No positive Slavic surname signal)
  * Death Year unknown, Birth Year $= 1885$ (1861–1917 Epoch $\rightarrow$ Simple Genitive format `Johannov`)
* **Final Score:** $0.00 \rightarrow$ **Aborted. Prevents generating the inaccurate name "Johan Johannov Schmidt."**

---

## Section 4: Testing Strategy

We employ a comprehensive testing suite to verify morphological generation, edge cases, and database safety.

```txt
                        ┌────────────────────────────────┐
                        │      TEST SUITE PARADIGM       │
                        └────────────────┬───────────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              ▼                          ▼                          ▼
   ┌────────────────────┐     ┌────────────────────┐     ┌────────────────────┐
   │ Morphological      │     │ Property-Based     │     │ Real-World Mock    │
   │ Unit Tests         │     │ Generation Tests   │     │ Dataset Reversion  │
   ├────────────────────┤     ├────────────────────┤     ├────────────────────┤
   │ Validates soft and │     │ Feeds randomized   │     │ Simulates runs over│
   │ hard stem mutations│     │ characters to make │     │ 10,000 mock records│
   │ on Russian,        │     │ sure the system    │     │ to verify 100%     │
   │ Ukrainian, and     │     │ gracefully rejects │     │ clean rollback     │
   │ Belarusian bases.  │     │ invalid names.     │     │ capability.        │
   └────────────────────┘     └────────────────────┘     └────────────────────┘
```

### 4.1 Dry-Run Simulation Tests

The plugin includes a dedicated validation suite to ensure that running the engine in dry-run mode never modifies the active database:

```python
import unittest
from gramps.gen.db import DbDatabase
from gramps.plugins.inference.manager import InferenceEngineManager

class TestInferenceDryRun(unittest.TestCase):
    def setUp(self):
        # Initialize a temporary, in-memory mock database
        self.db = DbDatabase()
        self._populate_test_tree(self.db)

    def test_dry_run_immutability(self):
        """Ensures dry-run calculations make zero writes to the database."""
        initial_checksum = self.db.get_checksum() if hasattr(self.db, "get_checksum") else hash(str(self.db))

        manager = InferenceEngineManager(self.db)
        # Execute run in dry-run simulation mode
        results = manager.evaluate_all_persons(dry_run=True)

        current_checksum = self.db.get_checksum() if hasattr(self.db, "get_checksum") else hash(str(self.db))
        self.assertEqual(initial_checksum, current_checksum, "Dry-run execution modified the database!")
```

### 4.2 Property-Based Testing (Hypothesis Framework)

We use property-based testing to ensure the morphological parser handles unusual or malformed inputs without crashing:

```python
from hypothesis import given, strategies as st
from EastSlavicMorphology import generate_east_slavic_patronymic

@given(st.text())
def test_fuzz_morphology_generator(input_string):
    """
    Ensures the morphological engine handles any text input
    without raising unhandled runtime exceptions.
    """
    try:
        # Generate with standard parameters
        res = generate_east_slavic_patronymic(input_string, gender=1, year=1950, pre_reform=False)
        assert res is None or isinstance(res, str)
    except ValueError:
        # Acceptable validation rejection for unparseable input
        pass
```

---

## Section 5: Phased Implementation Roadmap

```txt
                                  PHASED ROADMAP TIMELINE

   Phase 1: Engine & Dry-Run           Phase 2: The Batch Tool (P1)       Phase 3: The Gramplet (P2)
◄──────────────────────────────────┼─────────────────────────────────┼──────────────────────────────►
  - Suffix generation engines.       - Full GTK Wizard UI.             - Sidebar/Bottombar Gramplet.
  - Centralized JSON logging.        - Multi-signal calculations.      - Active navigation listeners
  - Immutability dry-run tests.      - Real-time previews.             - Quick-apply controls.
```

### Phase 1: Engine Core, Dry-Run Simulation, & Local Logging (v0.1)

* **Deliverables:** Suffix generation engines, the centralized JSON log engine, the chronological pivot rules, and a command-line wrapper script.
* **Validation:** $100\%$ test coverage on morphological edge cases. No GUI integration is introduced.

### Phase 2: GTK Batch Refinement Tool (P1) (v1.0)

* **Deliverables:** A standard Gramps Tool Addon (`TOOL` type) accessible via the application menu.
* **UI Components:** A GTK wizard window providing database filtering, a preview screen showing confidence scores with historical rules, a dry-run report exporter, and a rollback interface.

### Phase 3: Sidebar Suggestion Gramplet (P2) (v2.0)

* **Deliverables:** A Gramplet Addon (`GRAMPLET` type) for the sidebar or bottombar.
* **Behavior:** Monitors active person signals in Gramps, displaying a suggested patronymic and a one-click apply button for quick inline workflow.

---

## Future Work (review and incorporate into the rfc)

1. Support Ukrainian and Belarusian patronymic systems. Current system only supports Russian.


## References

[1] Elson, M. J. (2020). *The Development of the East Slavic Patronymic System: Social and Orthographic Dimensions*. Journal of Slavic Linguistics, 28(2), 189-214.

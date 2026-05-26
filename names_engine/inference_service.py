# -*- coding: utf-8 -*-
"""
engine/inference_service.py

Headless service for patronymic inference logic.
"""

import os
from typing import List, Generator, Tuple, Optional

from gramps.gen.lib import Person
from gramps.gen.db import DbTxn
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.const import GRAMPS_LOCALE as glocale

from names_engine.entities import InferenceCandidate
from names_engine.utils import (
    has_patronymic_surname,
    has_cyrillic,
    update_or_add_patronymic,
)
from names_engine.morphology import (
    SLAVIC_SURNAME_PATTERN,
    generate_east_slavic_patronymic,
)
from names_engine.logging import InferenceLogManager

_ = glocale.translation.gettext


class PatronymicInferenceService:
    """Headless service for patronymic candidate scanning and resolution."""

    # Reference source constants
    REF_SOURCE_LATEST_EVENT = "LATEST_EVENT"
    REF_SOURCE_GRAPH_BFS = "GRAPH_BFS"
    REF_SOURCE_DB_MEDIAN_FALLBACK = "DB_MEDIAN"

    def __init__(self, db):
        self.db = db
        # Extract unique DB directory name to isolate the logs
        db_path = self.db.get_dbname()
        self.db_id = os.path.basename(os.path.normpath(db_path))
        self.log_manager = InferenceLogManager(self.db_id)

        # Initialize DB stats
        self.given_names_set = set()
        self.db_median_year = 1920
        self._initialize_db_defaults()

    def _initialize_db_defaults(self):
        """
        Scans the database once, extracts all given names from persons,
        and builds a set for autocompletion. Also calculates the median year
        from all valid events for fallback reference year resolution.
        """
        given_names = set()
        years = []

        for handle in self.db.get_person_handles():
            person = self.db.get_person_from_handle(handle)
            if not person:
                continue

            # Extract given name
            primary_name = person.get_primary_name()
            if primary_name:
                given_name = primary_name.get_first_name()
                if given_name:
                    given_names.add(given_name)

            # Extract years from person's event references
            for event_ref in person.get_event_ref_list():
                event = self.db.get_event_from_handle(event_ref.ref)
                if event and event.get_date_object():
                    date_obj = event.get_date_object()
                    if date_obj.get_year():
                        year = date_obj.get_year()
                        if year > 0:
                            years.append(year)

        self.given_names_set = given_names

        if years:
            years.sort()
            self.db_median_year = years[len(years) // 2]

    def get_father_handle(self, person) -> Optional[str]:
        """Returns the father's handle for a given person."""
        for fam_handle in person.get_parent_family_handle_list():
            fam = self.db.get_family_from_handle(fam_handle)
            if fam and fam.get_father_handle() != "":
                return fam.get_father_handle()
        return None

    def evaluate_confidence(self, person, primary_name, father_first_name) -> float:
        """
        Multi-Signal Applicability Engine.
        Calculates a score between 0.0 and 1.0.
        """
        score = 0.0
        full_name_str = primary_name.get_regular_name()
        if has_cyrillic(full_name_str):
            score += 0.50
        for surname_obj in primary_name.get_surname_list():
            sur_str = surname_obj.get_surname()
            if sur_str and SLAVIC_SURNAME_PATTERN.search(sur_str):
                score += 0.20
        for fam_handle in person.get_parent_family_handle_list():
            fam = self.db.get_family_from_handle(fam_handle)
            if fam:
                for child_ref in fam.get_child_ref_list():
                    if child_ref.ref != person.handle:
                        sib = self.db.get_person_from_handle(child_ref.ref)
                        if sib and has_patronymic_surname(sib.get_primary_name()):
                            score += 0.30
                            break
        return min(score, 1.0)

    def resolve_reference_year(self, person) -> Tuple[int, str]:
        """Generational graph traversal to find the most likely reference year."""
        event_years = []
        for event_ref in person.get_event_ref_list():
            event = self.db.get_event_from_handle(event_ref.ref)
            if event and event.get_date_object() and event.get_date_object().get_year():
                event_years.append(event.get_date_object().get_year())
        if event_years:
            return max(event_years), self.REF_SOURCE_LATEST_EVENT

        max_depth = 4
        visited = {person.handle}
        current_level = [(person.handle, 0)]
        for depth in range(1, max_depth + 1):
            next_level = []
            level_estimates = []
            for handle, delta_g in current_level:
                p = self.db.get_person_from_handle(handle)
                if not p:
                    continue
                for fam_handle in p.get_parent_family_handle_list():
                    fam = self.db.get_family_from_handle(fam_handle)
                    if not fam:
                        continue
                    for parent_handle in (
                        fam.get_father_handle(),
                        fam.get_mother_handle(),
                    ):
                        if parent_handle and parent_handle not in visited:
                            visited.add(parent_handle)
                            next_level.append((parent_handle, delta_g + 1))
                    for child_ref in fam.get_child_ref_list():
                        if child_ref.ref not in visited:
                            visited.add(child_ref.ref)
                            next_level.append((child_ref.ref, delta_g))
                for fam_handle in p.get_family_handle_list():
                    fam = self.db.get_family_from_handle(fam_handle)
                    if not fam:
                        continue
                    for spouse_handle in (
                        fam.get_father_handle(),
                        fam.get_mother_handle(),
                    ):
                        if (
                            spouse_handle
                            and spouse_handle != handle
                            and spouse_handle not in visited
                        ):
                            visited.add(spouse_handle)
                            next_level.append((spouse_handle, delta_g))
                    for child_ref in fam.get_child_ref_list():
                        if child_ref.ref not in visited:
                            visited.add(child_ref.ref)
                            next_level.append((child_ref.ref, delta_g - 1))
            for handle, d_g in next_level:
                rel_p = self.db.get_person_from_handle(handle)
                if not rel_p:
                    continue
                for event_ref in rel_p.get_event_ref_list():
                    event = self.db.get_event_from_handle(event_ref.ref)
                    if (
                        event
                        and event.get_date_object()
                        and event.get_date_object().get_year()
                    ):
                        level_estimates.append(
                            event.get_date_object().get_year() + (d_g * 25)
                        )
            if level_estimates:
                median_year = sorted(level_estimates)[len(level_estimates) // 2]
                return median_year, self.REF_SOURCE_GRAPH_BFS
            current_level = next_level
            if not current_level:
                break
        return self.db_median_year, self.REF_SOURCE_DB_MEDIAN_FALLBACK

    def scan_candidates_generator(
        self, pre_reform=False
    ) -> Generator[InferenceCandidate, None, None]:
        """Queries database for eligible records and yields InferenceCandidate instances."""
        for handle in self.db.get_person_handles():
            person = self.db.get_person_from_handle(handle)
            if not person:
                continue
            primary_name = person.get_primary_name()
            if has_patronymic_surname(primary_name):
                continue
            father_handle = self.get_father_handle(person)
            if not father_handle:
                continue
            father = self.db.get_person_from_handle(father_handle)
            if not father:
                continue
            father_first_name = father.get_primary_name().get_first_name()
            if not father_first_name:
                continue
            confidence = self.evaluate_confidence(
                person, primary_name, father_first_name
            )
            if confidence < 0.60:
                continue
            ref_year, rule_source = self.resolve_reference_year(person)
            if rule_source == self.REF_SOURCE_DB_MEDIAN_FALLBACK:
                confidence = 0.20
            if confidence < 0.20:
                continue
            gender_val = person.get_gender()
            if gender_val not in (Person.MALE, Person.FEMALE):
                continue
            patronymic = generate_east_slavic_patronymic(
                father_name=father_first_name,
                is_male=(gender_val == Person.MALE),
                year=ref_year,
                pre_reform_script=pre_reform,
            )
            if patronymic:
                yield InferenceCandidate(
                    person_handle=handle,
                    gramps_id=person.gramps_id,
                    display_name=name_displayer.display_formal(person),
                    father_name=father_first_name,
                    reference_year=ref_year,
                    inferred_patronymic=patronymic,
                    confidence=confidence,
                    rule_source=rule_source,
                )

    def apply_patronymics_batch(
        self, candidates: List[InferenceCandidate], exec_id: str, pre_reform: bool
    ):
        """Commits patronymics safely inside a transaction."""
        logged_changes = []
        with DbTxn(_("Apply Patronymics"), self.db) as txn:
            for cand in candidates:
                person = self.db.get_person_from_handle(cand.person_handle)
                if not person:
                    continue
                primary_name = person.get_primary_name()
                orig_pat = update_or_add_patronymic(
                    primary_name, cand.inferred_patronymic
                )

                self.db.commit_person(person, txn)

                logged_changes.append(
                    {
                        "person_handle": cand.person_handle,
                        "original_value": orig_pat,
                        "inferred_value": cand.inferred_patronymic,
                        "father_handle": self.get_father_handle(person),
                        "reference_year": cand.reference_year,
                        "pre_reform": pre_reform,
                        "confidence_score": cand.confidence,
                        "is_temporal_fallback": (
                            cand.rule_source == self.REF_SOURCE_DB_MEDIAN_FALLBACK
                        ),
                        "applied_heuristics": ["DEATH_OR_BIRTH_PIVOT"],
                    }
                )
        self.log_manager.log_execution(
            exec_id, "east_slavic_patronymic", logged_changes
        )

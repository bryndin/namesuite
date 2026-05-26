# -*- coding: utf-8 -*-
"""
engine/audit_service.py

Headless service for patronymic auditing logic using the linter engine.
"""

from typing import Iterable, Set

from gramps.gen.lib import Person
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.const import GRAMPS_LOCALE as glocale

from pat_engine.entities import AuditIssue
from pat_engine.linter import RuleEngine, RuleContext, PlaceCache
from pat_engine.utils import get_patronymic_value
from pat_engine.constants import LOCALE_RU

_ = glocale.translation.gettext


class PatronymicAuditService:
    """Headless service for database-wide patronymic consistency auditing."""

    def __init__(self, db, inference_service):
        self.db = db
        self.inference_service = inference_service
        self.linter_engine = RuleEngine()

    def audit_generator(
        self, scope_idx: int, enabled_rules: Set[str], use_pre_reform: bool
    ) -> Iterable[AuditIssue]:
        """
        Runs the audit engine across the database based on filters.
        scope_idx: 0: All, 1: Males Only, 2: Females Only
        """
        place_cache = PlaceCache(self.db)

        for handle in self.db.get_person_handles():
            person = self.db.get_person_from_handle(handle)
            if not person:
                continue

            gender_val = person.get_gender()

            # Filter gender scope
            if scope_idx == 1 and gender_val != Person.MALE:
                continue
            if scope_idx == 2 and gender_val != Person.FEMALE:
                continue

            primary_name = person.get_primary_name()
            current_pat = get_patronymic_value(primary_name)

            # We only audit individuals with existing patronymic Surnames
            if not current_pat:
                continue

            father_handle = self.inference_service.get_father_handle(person)
            father_name = ""
            if father_handle:
                father = self.db.get_person_from_handle(father_handle)
                if father:
                    father_name = father.get_primary_name().get_first_name() or ""

            ref_year, rule_source = self.inference_service.resolve_reference_year(
                person
            )
            if ref_year is None:
                continue

            locale = LOCALE_RU  # V1.0 focuses on Russian locale rulesets

            ctx = RuleContext(
                person_id=person.handle,
                current_patronymic=current_pat,
                father_given_name=father_name,
                gramps_gender=gender_val,
                reference_year=ref_year,
                locale=locale,
                use_pre_reform=use_pre_reform,
                _place_resolver=place_cache.get_places,
            )

            # Run dispatcher engine
            triggered = self.linter_engine.evaluate_person(
                ctx, enabled_rules=enabled_rules
            )

            for rule, change in triggered:
                yield AuditIssue(
                    person_handle=handle,
                    gramps_id=person.gramps_id,
                    display_name=name_displayer.display_formal(person),
                    current_value=current_pat,
                    reference_year=ref_year,
                    rule_id=rule.rule_id,
                    rule_source=rule_source,
                    suggested_fix=change.suggested_string,
                )

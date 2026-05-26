# -*- coding: utf-8 -*-
"""
engine/rules/gender_mismatch.py

Rule: ErrGenderMismatch
Flags if the grammatical gender of the patronymic suffix conflicts with person's gender.
"""

from typing import Optional, Set, Tuple

from gramps.gen.lib import Person
from engine.rule import BaseRule, RuleContext, ProposedChange
from engine.constants import (
    SEVERITY_ERROR,
    LOCALE_EAST_SLAVIC,
)
from engine.utils import is_pre_reform
from engine.morphology import generate_east_slavic_patronymic
from engine.rule_utils import generate_pango_diff, swap_patronymic_gender


class ErrGenderMismatch(BaseRule):
    """Flags if the grammatical gender of the patronymic suffix conflicts with person's gender."""

    RULE_ID = "ERR_GENDER_MISMATCH"

    @property
    def severity(self) -> str:
        return SEVERITY_ERROR

    @property
    def supported_locales(self) -> Set[str]:
        return LOCALE_EAST_SLAVIC

    @property
    def active_era(self) -> Tuple[Optional[int], Optional[int]]:
        return (None, None)

    def evaluate(self, ctx: RuleContext) -> Optional[ProposedChange]:
        if (
            ctx.gramps_gender not in (Person.MALE, Person.FEMALE)
            or not ctx.current_patronymic
        ):
            return None

        is_male = ctx.gramps_gender == Person.MALE

        # 1. Evaluate with father's name if present
        if ctx.father_given_name:
            pre_reform = is_pre_reform(ctx)
            expected = generate_east_slavic_patronymic(
                ctx.father_given_name,
                is_male=is_male,
                year=ctx.reference_year,
                pre_reform_script=pre_reform,
            )
            opposite = generate_east_slavic_patronymic(
                ctx.father_given_name,
                is_male=not is_male,
                year=ctx.reference_year,
                pre_reform_script=pre_reform,
            )
            if ctx.current_patronymic == opposite and opposite != expected:
                return ProposedChange(
                    explanation=f"Linguistic gender mismatch: Patronymic is grammatically {'female' if is_male else 'male'} for a {'male' if is_male else 'female'} individual.",
                    suggested_string=expected,
                    diff_markup=generate_pango_diff(ctx.current_patronymic, expected),
                )

        # 2. Universal fallback using suffix endings
        female_endings = ("овна", "евна", "ична", "инична", "ова", "ева", "ина")
        male_endings = ("ович", "евич", "ич", "ов", "ев", "ин", "овъ", "евъ", "инъ")

        if is_male:
            if ctx.current_patronymic.endswith(female_endings):
                pre_reform = is_pre_reform(ctx)
                suggested = swap_patronymic_gender(
                    ctx.current_patronymic, to_male=True, pre_reform=pre_reform
                )
                return ProposedChange(
                    explanation="Linguistic gender mismatch: Suffix is grammatically female for a male individual.",
                    suggested_string=suggested,
                    diff_markup=generate_pango_diff(ctx.current_patronymic, suggested),
                )
        else:
            if ctx.current_patronymic.endswith(male_endings):
                suggested = swap_patronymic_gender(
                    ctx.current_patronymic, to_male=False
                )
                return ProposedChange(
                    explanation="Linguistic gender mismatch: Suffix is grammatically male for a female individual.",
                    suggested_string=suggested,
                    diff_markup=generate_pango_diff(ctx.current_patronymic, suggested),
                )

        return None

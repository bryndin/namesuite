# -*- coding: utf-8 -*-
"""
engine/rules/lineage_mismatch.py

Rule: ErrLineageMismatch
Flags if the patronymic base/root does not match the linked biological father's name.
"""

from typing import Optional, Set, Tuple

from engine.compat import Person
from engine.rule import BaseRule, RuleContext, ProposedChange
from engine.constants import (
    SEVERITY_ERROR,
    LOCALE_EAST_SLAVIC,
    LOCALE_RU,
)
from engine.utils import is_pre_reform
from engine.morphology import generate_east_slavic_patronymic
from engine.rule_utils import generate_pango_diff


class ErrLineageMismatch(BaseRule):
    """Flags if the patronymic base/root does not match the linked biological father's name."""

    RULE_ID = "ERR_LINEAGE_MISMATCH"

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
        if not ctx.father_given_name or not ctx.current_patronymic:
            return None

        is_male = ctx.gramps_gender == Person.MALE
        pre_reform = is_pre_reform(ctx)

        # Resolve target expected patronymic for active context
        expected = generate_east_slavic_patronymic(
            ctx.father_given_name,
            is_male=is_male,
            year=ctx.reference_year,
            pre_reform_script=pre_reform,
        )

        if not expected or ctx.current_patronymic == expected:
            return None

        # Cross-reference pre-1918 and post-1918 variant states to avoid flagging anachronisms as lineage mismatch
        expected_modern = generate_east_slavic_patronymic(
            ctx.father_given_name, is_male=is_male, year=1950, pre_reform_script=False
        )
        expected_archaic = generate_east_slavic_patronymic(
            ctx.father_given_name,
            is_male=is_male,
            year=1850,
            pre_reform_script=(ctx.locale == LOCALE_RU),
        )

        opposite_modern = generate_east_slavic_patronymic(
            ctx.father_given_name,
            is_male=not is_male,
            year=1950,
            pre_reform_script=False,
        )
        opposite_archaic = generate_east_slavic_patronymic(
            ctx.father_given_name,
            is_male=not is_male,
            year=1850,
            pre_reform_script=(ctx.locale == LOCALE_RU),
        )

        # If it matches the opposite gender expected base, route it to ErrGenderMismatch.RULE_ID instead
        if ctx.current_patronymic in (opposite_modern, opposite_archaic):
            return None

        # If the patronymic is already matches one of our expected era variants, skip (let the era warning handle it)
        if ctx.current_patronymic in (expected_modern, expected_archaic):
            return None

        return ProposedChange(
            explanation=f"Lineage mismatch: The patronymic does not match father's given name '{ctx.father_given_name}'.",
            suggested_string=expected,
            diff_markup=generate_pango_diff(ctx.current_patronymic, expected),
        )

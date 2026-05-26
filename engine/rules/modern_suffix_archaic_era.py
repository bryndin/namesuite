# -*- coding: utf-8 -*-
"""
engine/rules/modern_suffix_archaic_era.py

Rule: WarnModernSuffixArchaicEra
Flags pre-1918 records using modern formal endings and suggests possessive genitives.
"""

from typing import Optional, Set, Tuple

from gramps.gen.lib import Person
from engine.rule import BaseRule, RuleContext, ProposedChange
from engine.constants import (
    SEVERITY_WARNING,
    LOCALE_EAST_SLAVIC,
    LOCALE_RU,
    REFORM_YEAR_1918,
)
from engine.utils import is_pre_reform
from engine.morphology import generate_east_slavic_patronymic
from engine.rule_utils import generate_pango_diff, modern_to_archaic


class WarnModernSuffixArchaicEra(BaseRule):
    """Flags pre-1918 records using modern formal endings and suggests possessive genitives."""

    RULE_ID = "WARN_MODERN_SUFFIX_ARCHAIC_ERA"

    @property
    def severity(self) -> str:
        return SEVERITY_WARNING

    @property
    def supported_locales(self) -> Set[str]:
        return LOCALE_EAST_SLAVIC

    @property
    def active_era(self) -> Tuple[Optional[int], Optional[int]]:
        return (None, 1917)

    def evaluate(self, ctx: RuleContext) -> Optional[ProposedChange]:
        if not ctx.current_patronymic or (
            ctx.reference_year is not None and ctx.reference_year >= REFORM_YEAR_1918
        ):
            return None

        modern_suffixes = ("ович", "евич", "ич", "овна", "евна", "ична", "инична")

        if any(ctx.current_patronymic.endswith(s) for s in modern_suffixes):
            is_male = ctx.gramps_gender == Person.MALE
            # Adjust condition to respect the user toggle
            pre_reform = is_pre_reform(ctx)

            if ctx.father_given_name:
                suggested = generate_east_slavic_patronymic(
                    ctx.father_given_name,
                    is_male=is_male,
                    year=1850,
                    pre_reform_script=pre_reform,
                )
            else:
                suggested = modern_to_archaic(
                    ctx.current_patronymic, is_male=is_male, pre_reform=pre_reform
                )

            if suggested and suggested != ctx.current_patronymic:
                return ProposedChange(
                    explanation=f"Historical anachronism: Modern patronymic suffix in pre-{REFORM_YEAR_1918} era ({ctx.reference_year}).",
                    suggested_string=suggested,
                    diff_markup=generate_pango_diff(ctx.current_patronymic, suggested),
                )

        return None

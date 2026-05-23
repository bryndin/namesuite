# -*- coding: utf-8 -*-
"""
engine/rules/archaic_suffix_modern_era.py

Rule: WarnArchaicSuffixModernEra
Flags post-1918 records using archaic/informal possessive endings.
"""

from typing import Optional, Set, Tuple

from engine.compat import Person
from engine.rule import BaseRule, RuleContext, ProposedChange
from engine.constants import SEVERITY_WARNING, LOCALE_EAST_SLAVIC, REFORM_YEAR_1918
from engine.morphology import generate_east_slavic_patronymic
from engine.rule_utils import generate_pango_diff, archaic_to_modern


class WarnArchaicSuffixModernEra(BaseRule):
    """Flags post-1918 records using archaic/informal possessive endings."""
    
    @property
    def rule_id(self) -> str:
        return "WARN_ARCHAIC_SUFFIX_MODERN_ERA"

    @property
    def severity(self) -> str:
        return SEVERITY_WARNING

    @property
    def supported_locales(self) -> Set[str]:
        return LOCALE_EAST_SLAVIC

    @property
    def active_era(self) -> Tuple[Optional[int], Optional[int]]:
        return (REFORM_YEAR_1918, None)

    def evaluate(self, ctx: RuleContext) -> Optional[ProposedChange]:
        if not ctx.current_patronymic or (ctx.reference_year is not None and ctx.reference_year < REFORM_YEAR_1918):
            return None

        # Archaic endings (including pre-reform orthographic variants)
        archaic_suffixes = ("ов", "ев", "ин", "ова", "ева", "ина", "овъ", "евъ", "инъ")
        
        if any(ctx.current_patronymic.endswith(s) for s in archaic_suffixes):
            is_male = (ctx.gramps_gender == Person.MALE)
            
            if ctx.father_given_name:
                suggested = generate_east_slavic_patronymic(
                    ctx.father_given_name, is_male=is_male, year=1950, pre_reform_script=False
                )
            else:
                suggested = archaic_to_modern(ctx.current_patronymic, is_male=is_male)

            if suggested and suggested != ctx.current_patronymic:
                return ProposedChange(
                    explanation=f"Historical anachronism: Archaic genitive suffix in post-{REFORM_YEAR_1918} era ({ctx.reference_year}).",
                    suggested_string=suggested,
                    diff_markup=generate_pango_diff(ctx.current_patronymic, suggested)
                )

        return None

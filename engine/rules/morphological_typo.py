# -*- coding: utf-8 -*-
"""
engine/rules/morphological_typo.py

Rule: WarnMorphologicalTypo
Detects invalid consecutive duplicate characters at joint boundaries (e.g. Андрееевич).
"""

import re
from typing import Optional, Set, Tuple

try:
    from gramps.gen.lib import Person
except ImportError:
    class Person:
        MALE = 0
        FEMALE = 1
        UNKNOWN = 2

from engine.rule import BaseRule, RuleContext, ProposedChange
from engine.morphology import generate_east_slavic_patronymic
from engine.rule_utils import generate_pango_diff


class WarnMorphologicalTypo(BaseRule):
    """Detects invalid consecutive duplicate characters at joint boundaries (e.g. Андрееевич)."""
    
    @property
    def rule_id(self) -> str:
        return "WARN_MORPHOLOGICAL_TYPO"

    @property
    def severity(self) -> str:
        return "WARNING"

    @property
    def supported_locales(self) -> Set[str]:
        return {"ru", "uk", "be", "*"}

    @property
    def active_era(self) -> Tuple[Optional[int], Optional[int]]:
        return (None, None)

    def evaluate(self, ctx: RuleContext) -> Optional[ProposedChange]:
        if not ctx.current_patronymic:
            return None

        # 1. Typo checks on raw string (e.g. 3 consecutive identical letters like "еее")
        if re.search(r"(.)\1\1+", ctx.current_patronymic):
            # Compress consecutive duplicates to help suggest correction
            suggested = re.sub(r"(.)\1\1+", r"\1", ctx.current_patronymic)
            # Re-generate from father's name if present for maximum accuracy
            if ctx.father_given_name:
                is_male = (ctx.gramps_gender == Person.MALE)
                pre_reform = (ctx.locale == 'ru' and ctx.reference_year < 1918)
                gen_expected = generate_east_slavic_patronymic(
                    ctx.father_given_name, is_male=is_male, year=ctx.reference_year, pre_reform_script=pre_reform
                )
                if gen_expected:
                    suggested = gen_expected

            if suggested != ctx.current_patronymic:
                return ProposedChange(
                    explanation="Spelling anomaly: Contains invalid duplicate letter repetitions at morphological boundaries.",
                    suggested_string=suggested,
                    diff_markup=generate_pango_diff(ctx.current_patronymic, suggested)
                )

        # 2. Check if a duplicate letter differs only from morphological standard
        if ctx.father_given_name:
            is_male = (ctx.gramps_gender == Person.MALE)
            pre_reform = (ctx.locale == 'ru' and ctx.reference_year < 1918)
            expected = generate_east_slavic_patronymic(
                ctx.father_given_name, is_male=is_male, year=ctx.reference_year, pre_reform_script=pre_reform
            )
            if expected and ctx.current_patronymic != expected:
                # Check if they are identical after stripping consecutive repeats
                def compress(s: str) -> str:
                    return re.sub(r"(.)\1+", r"\1", s)
                
                if compress(ctx.current_patronymic) == compress(expected):
                    return ProposedChange(
                        explanation="Spelling anomaly: Joint spelling differs from standard naming morphology.",
                        suggested_string=expected,
                        diff_markup=generate_pango_diff(ctx.current_patronymic, expected)
                    )

        return None

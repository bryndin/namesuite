# -*- coding: utf-8 -*-
"""
engine/rules/missing_hard_sign.py

Rule: WarnMissingHardSign
Flags pre-1918 Russian names missing a terminal orthographic hard sign 'ъ'.
"""

from typing import Optional, Set, Tuple

from engine.rule import BaseRule, RuleContext, ProposedChange, SEVERITY_WARNING, LOCALE_RU
from engine.morphology import apply_pre_reform_orthography
from engine.rule_utils import generate_pango_diff


class WarnMissingHardSign(BaseRule):
    """Flags pre-1918 Russian names missing a terminal orthographic hard sign 'ъ'."""
    
    @property
    def rule_id(self) -> str:
        return "WARN_MISSING_HARD_SIGN"

    @property
    def severity(self) -> str:
        return SEVERITY_WARNING

    @property
    def supported_locales(self) -> Set[str]:
        return {LOCALE_RU}

    @property
    def active_era(self) -> Tuple[Optional[int], Optional[int]]:
        return (None, 1917)

    def evaluate(self, ctx: RuleContext) -> Optional[ProposedChange]:
        if not ctx.current_patronymic or ctx.reference_year >= 1918 or ctx.locale != 'ru':
            return None

        # Re-apply pre-reform orthography mapping on the current value
        reformed = apply_pre_reform_orthography(ctx.current_patronymic)
        
        if reformed != ctx.current_patronymic:
            return ProposedChange(
                explanation="Orthographical anomaly: Missing historical pre-revolutionary terminal hard signs (ъ) or decimal (і).",
                suggested_string=reformed,
                diff_markup=generate_pango_diff(ctx.current_patronymic, reformed)
            )

        return None

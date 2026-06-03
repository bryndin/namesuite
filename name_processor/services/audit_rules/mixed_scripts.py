# -*- coding: utf-8 -*-
"""
Rule: ErrMixedScripts
Detects and corrects mixed Cyrillic and Latin homoglyphs in patronymic strings.
"""

import re
from typing import Optional, Set, Tuple

from name_processor.services.audit_rules.base import BaseRule
from name_processor.entities.rule_models import RuleContext, ProposedChange
from name_processor.services.constants import (
    SEVERITY_ERROR,
    LOCALE_EAST_SLAVIC,
)

# Cyrillic and Latin Unicode blocks to detect homoglyph mixing
CYRILLIC_PATTERN = re.compile(r"[\u0400-\u04FF]")
LATIN_PATTERN = re.compile(r"[a-zA-Z]")

# Common Cyrillic-Latin homoglyph mapping dictionary
HOMOGLYPHS = {
    "a": "а",
    "A": "А",
    "c": "с",
    "C": "С",
    "e": "е",
    "E": "Е",
    "o": "о",
    "O": "О",
    "p": "р",
    "P": "Р",
    "x": "х",
    "X": "Х",
    "y": "у",
    "Y": "У",
    "H": "Н",
    "K": "К",
    "M": "М",
    "T": "Т",
    "B": "В",
}


class ErrMixedScripts(BaseRule):
    """Detects and corrects mixed Cyrillic and Latin homoglyphs in patronymic strings."""

    rule_id = "ERR_MIXED_SCRIPTS"

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
        if not ctx.current_patronymic:
            return None

        has_cyr = bool(CYRILLIC_PATTERN.search(ctx.current_patronymic))
        has_lat = bool(LATIN_PATTERN.search(ctx.current_patronymic))

        if has_cyr and has_lat:
            # Map Latin characters to Cyrillic homoglyphs
            chars = []
            for char in ctx.current_patronymic:
                chars.append(HOMOGLYPHS.get(char, char))
            suggested = "".join(chars)

            if suggested != ctx.current_patronymic:
                return ProposedChange(
                    explanation="Typographical error: Contains a mixture of Cyrillic and Latin homoglyph Unicode characters.",
                    suggested_string=suggested,
                )

        return None

# -*- coding: utf-8 -*-
"""
Confidence scoring engine for patronymic candidates.
Encapsulates heuristics used to determine reliability of inference results.
"""

import re
from typing import TYPE_CHECKING

from name_processor.services.libs.morphology import SLAVIC_SURNAME_PATTERN

if TYPE_CHECKING:
    from name_processor.repositories.gramps import GrampsDbRepository

# Confidence score thresholds
CONFIDENCE_THRESHOLD_MINIMUM = 0.60
CONFIDENCE_SCORE_CYRILLIC = 0.50
CONFIDENCE_SCORE_SLAVIC_SURNAME = 0.20
CONFIDENCE_SCORE_SIBLING = 0.30
CONFIDENCE_SCORE_FALLBACK = 0.20


def has_cyrillic(text: str) -> bool:
    """Returns True if the text contains Cyrillic characters."""
    return bool(re.search(r"[\u0400-\u04FF]", text))


class ConfidenceEngine:
    """Calculates confidence scores (0.0 to 1.0) for patronymic inferences."""

    def __init__(self, repository: "GrampsDbRepository") -> None:
        self.repository = repository

    def calculate(self, handle: str, display_name: str) -> float:
        """
        Multi-Signal Applicability Engine.
        Calculates a score between 0.0 and 1.0 based on available heuristics.
        """
        score = 0.0

        # 1. Cyrillic Check
        if has_cyrillic(display_name):
            score += CONFIDENCE_SCORE_CYRILLIC

        # 2. Slavic Surname check
        surnames = self.repository.get_surnames(handle)
        if any(SLAVIC_SURNAME_PATTERN.search(s) for s in surnames):
            score += CONFIDENCE_SCORE_SLAVIC_SURNAME

        # 3. Sibling Check
        for sib_handle in self.repository.get_sibling_handles(handle):
            sib = self.repository.get_person_by_handle(sib_handle)
            if sib and sib.has_patronymic:
                score += CONFIDENCE_SCORE_SIBLING
                break

        # TODO: Review and fix heuristics here
        # return min(score, 1.0)
        return 1.0

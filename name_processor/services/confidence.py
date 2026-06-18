"""
Confidence scoring engine for patronymic candidates.
Encapsulates heuristics used to determine reliability of inference results.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from name_processor.models.constants import MEDIEVAL_YEAR_THRESHOLD
from name_processor.services.morphology import SLAVIC_SURNAME_PATTERN

if TYPE_CHECKING:
    from name_processor.protocols.confidence import ConfidenceRepository


def has_cyrillic(text: str) -> bool:
    """Returns True if the text contains Cyrillic characters."""
    return bool(re.search(r"[\u0400-\u04FF]", text))


class ConfidenceService:
    """Calculates confidence scores (0.0 to 1.0) for patronymic inferences."""

    # Confidence score thresholds
    CONFIDENCE_BASE_SCORE = 0.40
    CONFIDENCE_SCORE_SIBLING = 0.40
    CONFIDENCE_SCORE_SLAVIC_SURNAME = 0.20
    PENALTY_MULTI_WORD_FATHER = -0.40
    PENALTY_MEDIEVAL_YEAR = -0.30
    PENALTY_NON_CYRILLIC = -0.20
    PENALTY_UNCERTAIN_FATHER = -0.50

    def __init__(self, repository: ConfidenceRepository) -> None:
        self._repository = repository

    def calculate(
        self,
        person_handle: str,
        father_handle: str | None,
        ref_year: int | None,
    ) -> float:
        """
        Multi-Signal Applicability Engine.
        Calculates a score between 0.0 and 1.0 based on available heuristics.
        """
        person = self._repository.get_person(person_handle)
        if not person:
            return 0.0

        father = None
        if father_handle:
            father = self._repository.get_person(father_handle)

        # Starting from a non-zero baseline because a successful morphological inference
        # is already a strong positive indicator.
        score = self.CONFIDENCE_BASE_SCORE

        # Positive Signals
        # 1. Sibling has matching patronymic (+0.40)
        for sibling_handle in self._repository.get_siblings_handles(person_handle):
            sibling = self._repository.get_person(sibling_handle)
            if sibling and sibling.has_patronymic:
                score += self.CONFIDENCE_SCORE_SIBLING
                break

        # 2. Parent surname has Slavic suffix (+0.20)
        surnames_to_check = father.surnames if father else person.surnames
        if any(SLAVIC_SURNAME_PATTERN.search(s) for s in surnames_to_check):
            score += self.CONFIDENCE_SCORE_SLAVIC_SURNAME

        # Negative Signals
        # 1. Absence of Cyrillic Characters (-0.20)
        if not has_cyrillic(person.display_name):
            score += self.PENALTY_NON_CYRILLIC

        if father and father.given_name:
            # 2. Ambiguous multi-word father's name (-0.40)
            if re.search(r"[\s\-]", father.given_name.strip()):
                score += self.PENALTY_MULTI_WORD_FATHER

            # 3. Uncertain father's name (e.g. contains brackets or question marks) (-0.50)
            if re.search(r"[\?\[\]\(\)]", father.given_name):
                score += self.PENALTY_UNCERTAIN_FATHER

        # 4. Reference Year is Medieval (-0.30)
        if ref_year is not None and ref_year < MEDIEVAL_YEAR_THRESHOLD:
            score += self.PENALTY_MEDIEVAL_YEAR

        return max(0.0, min(score, 1.0))

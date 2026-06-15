from __future__ import annotations

from typing import TYPE_CHECKING

from name_processor.models.infer import (
    PatronymicInferenceStatus,
    ProposedPatronymic,
)
from name_processor.models.person import Gender
from name_processor.services.morphology import MorphologyService

if TYPE_CHECKING:
    from name_processor.protocols.patronymic import PatronymicRepository
    from name_processor.services.confidence import ConfidenceService
    from name_processor.services.chronology import ChronologyService


class PatronymicInferenceService:
    def __init__(
        self,
        read_repo: PatronymicRepository,
        confidence: ConfidenceService,
        chronology_service: ChronologyService,
    ):
        self._read_repo = read_repo
        self._confidence_service = confidence
        self._chronology_service = chronology_service

    def infer_patronymic(self, handle: str) -> ProposedPatronymic:
        """
        Generate a patronymic candidate for a single person.
        Handles DB lookups, validation, and morphology generation.
        """
        person = self._read_repo.get_patronymic_subject(handle)
        if not person:
            return ProposedPatronymic(status=PatronymicInferenceStatus.NO_ACTIVE_PERSON)

        if person.gender not in (Gender.MALE, Gender.FEMALE):
            return ProposedPatronymic(status=PatronymicInferenceStatus.NON_BINARY)

        if person.has_patronymic:
            return ProposedPatronymic(
                status=PatronymicInferenceStatus.ALREADY_HAS_PATRONYMIC
            )

        father_handle = self._read_repo.get_father_handle(person.handle)
        father = (
            self._read_repo.get_patronymic_subject(father_handle)
            if father_handle
            else None
        )
        if not father:
            return ProposedPatronymic(status=PatronymicInferenceStatus.NO_FATHER)

        if not father.given_name:
            return ProposedPatronymic(status=PatronymicInferenceStatus.FATHER_NO_NAME)

        ref_year = self._chronology_service.estimate_reference_year(person.handle)

        patronymic = MorphologyService.generate_east_slavic_patronymic(
            father_name=father.given_name,
            is_male=(person.gender == Gender.MALE),
            year=ref_year,
            pre_reform_script=False,
        )

        if patronymic:
            confidence = self._confidence_service.calculate(
                person.handle,
                father.handle,
                ref_year,
            )

            return ProposedPatronymic(
                status=PatronymicInferenceStatus.SUCCESS,
                patronymic=patronymic,
                father_name=father.given_name,
                confidence=confidence,
            )
        else:
            return ProposedPatronymic(status=PatronymicInferenceStatus.MORPHOLOGY_FAIL)

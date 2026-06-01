from typing import TYPE_CHECKING, Optional

from name_processor.models.result import (
    PatronymicInferenceStatus,
    Result,
    Context,
)
from name_processor.models.person import Gender
from name_processor.protocols.patronymic import PatronymicSubject
from name_processor.services.morphology import MorphologyService

if TYPE_CHECKING:
    from name_processor.repositories.gramps_read import GrampsReadRepository
    from name_processor.services.confidence_engine import ConfidenceEngine
    from name_processor.services.chronology import ChronologyService


class PatronymicInferenceService:
    def __init__(
        self,
        read_repo: "GrampsReadRepository",
        confidence_engine: "ConfidenceEngine",
        chronology_service: "ChronologyService",
    ):
        self.read_repo = read_repo
        self.confidence_engine = confidence_engine
        self.chronology_service = chronology_service

    def infer_patronymic(
        self, person: PatronymicSubject, father: Optional[PatronymicSubject]
    ) -> Result:
        """
        Generate a patronymic candidate for a single person.
        Handles DB lookups, validation, and morphology generation.
        """
        if not person:
            return Result(status=PatronymicInferenceStatus.NO_ACTIVE_PERSON)

        if person.gender not in (Gender.MALE, Gender.FEMALE):
            return Result(status=PatronymicInferenceStatus.NON_BINARY)

        if person.has_patronymic:
            return Result(status=PatronymicInferenceStatus.ALREADY_HAS_PATRONYMIC)

        if not father:
            return Result(status=PatronymicInferenceStatus.NO_FATHER)

        if not father.given_name:
            return Result(status=PatronymicInferenceStatus.FATHER_NO_NAME)

        ref_year = self.chronology_service.estimate_reference_year(person.handle)
        # confidence = self.confidence_engine.calculate(
        #     person.handle, person.display_name
        # )

        patronymic = MorphologyService.generate_east_slavic_patronymic(
            father_name=father.given_name,
            is_male=(person.gender == Gender.MALE),
            year=ref_year,
            pre_reform_script=False,
        )

        if patronymic:
            ctx = Context(
                father_name=father.given_name,
            )
            return Result(
                value=patronymic,
                context=ctx,
                status=PatronymicInferenceStatus.SUCCESS,
            )
        else:
            return Result(
                value="",
                context=None,
                status=PatronymicInferenceStatus.MORPHOLOGY_FAIL,
            )

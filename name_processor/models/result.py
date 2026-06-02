from enum import Enum
from dataclasses import dataclass


class PatronymicInferenceStatus(Enum):
    """Status codes for patronymic inference."""

    SUCCESS = "SUCCESS"
    NO_ACTIVE_PERSON = "NO_ACTIVE_PERSON"
    NO_FATHER = "NO_FATHER"
    FATHER_NO_NAME = "FATHER_NO_NAME"
    NON_BINARY = "NON_BINARY"
    ALREADY_HAS_PATRONYMIC = "ALREADY_HAS_PATRONYMIC"
    MORPHOLOGY_FAIL = "MORPHOLOGY_FAIL"


@dataclass(frozen=True)
class Context:
    gramps_id: str | None = None
    display_name: str | None = None
    father_name: str | None = None
    reference_year: int | None = None
    inferred_patronymic: str | None = None
    confidence: float | None = None
    rule_source: str | None = None


@dataclass
class Result:
    """Result of inferring a patronymic for a single person."""

    value: str | None = None
    context: Context | None = None
    status: PatronymicInferenceStatus | None = None

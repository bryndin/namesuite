from enum import Enum
from dataclasses import dataclass
from typing import Optional


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
    gramps_id: Optional[str] = None
    display_name: Optional[str] = None
    father_name: Optional[str] = None
    reference_year: Optional[int] = None
    inferred_patronymic: Optional[str] = None
    confidence: Optional[float] = None
    rule_source: Optional[str] = None


@dataclass
class Result:
    """Result of inferring a patronymic for a single person."""

    value: Optional[str] = None
    context: Optional[Context] = None
    status: Optional[PatronymicInferenceStatus] = None

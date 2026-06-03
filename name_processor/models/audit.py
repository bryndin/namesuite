from dataclasses import dataclass
from typing import Optional
from name_processor.models.person import Gender


@dataclass
class RuleContext:
    """A flattened, read-only snapshot of a person for rule evaluation."""

    person_handle: str
    gramps_id: str
    display_name: str
    gender: Gender
    current_patronymic: str
    father_given_name: Optional[str]
    reference_year: Optional[int]
    locale: str


@dataclass
class ProposedChange:
    """The internal result from an individual rule."""

    explanation: str
    suggested_string: str


@dataclass
class AuditIssue:
    """The DTO sent back to the Controller and displayed in the View."""

    person_handle: str
    gramps_id: str
    display_name: str
    current_value: str
    reference_year: str
    rule_id: str
    suggested_fix: str
    rule_source: str
    explanation: str

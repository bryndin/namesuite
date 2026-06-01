from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


class Gender(Enum):
    """Domain enum for gender values, decoupled from Gramps integer constants."""

    MALE = "MALE"
    FEMALE = "FEMALE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=False)
class Person:
    handle: str
    gramps_id: str
    given_name: str
    gender: Gender
    has_patronymic: bool
    display_name: str
    father_handle: Optional[str] = None
    alternate_first_names: List[str] = field(default_factory=list)

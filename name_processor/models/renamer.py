from dataclasses import dataclass
from enum import Enum
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import re


class MatchMode(Enum):
    EXACT = "exact"
    SUBSTRING = "substring"
    REGEX = "regex"


@dataclass
class RuleConfig:
    """Stores and validates user-defined replacement rules."""

    mode: MatchMode
    source: str
    target: str
    pattern: Optional["re.Pattern"] = None
    is_valid: bool = True
    error_msg: str = ""


@dataclass
class ProposedRename:
    """DTO representing a single proposed name change for the UI grid."""

    handle: str
    gramps_id: str
    display_name: str
    original_given_name: str
    proposed_given_name: str

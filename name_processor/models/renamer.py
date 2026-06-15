from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


class MatchMode(Enum):
    EXACT = "exact"
    SUBSTRING = "substring"
    REGEX = "regex"


class AltAction(Enum):
    PRESERVE = "preserve"
    OVERWRITE = "overwrite"


@dataclass
class RenameConfig:
    """Stores user-defined replacement rules."""

    mode: MatchMode
    source: str
    target: str
    pattern: re.Pattern | None = None

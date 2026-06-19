from __future__ import annotations

from enum import Enum


class Gender(Enum):
    """Domain enum for gender values, decoupled from Gramps integer constants."""

    MALE = "MALE"
    FEMALE = "FEMALE"
    UNKNOWN = "UNKNOWN"

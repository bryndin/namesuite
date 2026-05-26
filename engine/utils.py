# -*- coding: utf-8 -*-
"""
engine/utils.py

Utility functions for the linter validation engine.
"""
import re
from engine.constants import LOCALE_RU, REFORM_YEAR_1918

try:
    from gramps.gen.lib import NameOriginType
except ImportError:
    class NameOriginType:
        UNKNOWN = 0
        CUSTOM = 1
        PATRONYMIC = 5

def is_pre_reform(ctx) -> bool:
    """Check if the context satisfies the pre-reform conditions."""
    return (
        ctx.locale == LOCALE_RU
        and ctx.reference_year is not None
        and ctx.reference_year < REFORM_YEAR_1918
        and ctx.use_pre_reform
    )

def is_patronymic_origin(orig) -> bool:
    """
    Checks if a surname origin type indicates a patronymic.
    Handles multiple representations of the PATRONYMIC type for compatibility.
    """
    return (
        orig == NameOriginType.PATRONYMIC
        or orig == 5
        or getattr(orig, "value", None) == NameOriginType.PATRONYMIC
        or getattr(orig, "value", None) == 5
        or str(orig).strip() == "Patronymic"
    )

def has_patronymic_surname(name_obj) -> bool:
    """Returns True if the Name object contains any Surname marked as a PATRONYMIC."""
    for surname in name_obj.get_surname_list():
        if is_patronymic_origin(surname.get_origintype()):
            return True
    return False

def has_cyrillic(text):
    """Returns True if the text contains Cyrillic characters."""
    return bool(re.search(r"[\u0400-\u04FF]", text))

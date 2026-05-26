# -*- coding: utf-8 -*-
"""
engine/utils.py

Utility functions for the linter validation engine.
"""
import re
from engine.constants import LOCALE_RU, REFORM_YEAR_1918
from gramps.gen.lib import NameOriginType, Surname

def update_or_add_patronymic(primary_name, new_patronymic_value) -> str:
    """
    Updates an existing patronymic Surname object in the list, or adds a new one.
    Returns the original patronymic value (or empty string).
    """
    surnames = primary_name.get_surname_list()
    orig_pat = ""
    found = False

    for s in surnames:
        if is_patronymic_origin(s.get_origintype()):
            orig_pat = s.get_surname()
            s.set_surname(new_patronymic_value)
            found = True
            break

    if not found:
        surn_obj = Surname()
        surn_obj.set_surname(new_patronymic_value)
        surn_obj.set_origintype(NameOriginType.PATRONYMIC)
        surn_obj.set_primary(False)
        primary_name.add_surname(surn_obj)

    return orig_pat

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

def get_patronymic_value(name_obj) -> str:
    """Finds and returns the string value of the patronymic Surname object."""
    for surname in name_obj.get_surname_list():
        if is_patronymic_origin(surname.get_origintype()):
            return surname.get_surname()
    return ""

def has_cyrillic(text):
    """Returns True if the text contains Cyrillic characters."""
    return bool(re.search(r"[\u0400-\u04FF]", text))

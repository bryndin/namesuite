# -*- coding: utf-8 -*-
"""
utils.py

Shared utility functions and mixins for patronymic inference and validation.
Extracted from patronymics_tool.py and patronymics_gramplet.py to eliminate code duplication.
"""

# Gramps dependency with safe fallback for testing
try:
    from gramps.gen.lib import NameOriginType
except ImportError:

    class NameOriginType:
        UNKNOWN = 0
        CUSTOM = 1
        PATRONYMIC = 5


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


class PatronymicMixin:
    """
    Mixin class providing shared patronymic-related methods.
    Can be used by both Tool and Gramplet classes.
    """

    def get_father_handle(self, person):
        """
        Returns the father's handle for a given person, or None if not found.
        """
        if not self.dbstate or not self.dbstate.db:
            return None

        for fam_handle in person.get_parent_family_handle_list():
            fam = self.dbstate.db.get_family_from_handle(fam_handle)
            if fam and fam.get_father_handle() != "":
                return fam.get_father_handle()
        return None

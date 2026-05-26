# -*- coding: utf-8 -*-
"""
utils.py

Shared utility functions and mixins for patronymic inference and validation.
Extracted from patronymics_tool.py and patronymics_gramplet.py to eliminate code duplication.
"""


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

# -*- coding: utf-8 -*-
"""
utils.py

Shared utility functions and mixins for patronymic inference and validation.
"""


class SharedMixin:
    """
    Mixin class providing shared patronymic-related methods.
    Can be used by both Tool and Gramplet classes.
    """

    def get_father_handle(self, person):
        """
        Returns the father's handle for a given person, or None if not found.
        """
        # Mixin expects self.db to be available via the host class
        db = getattr(self, "db", None)
        if not db:
            # Fallback for older code using self.dbstate.db
            dbstate = getattr(self, "dbstate", None)
            if dbstate:
                db = dbstate.db

        if not db:
            return None

        for fam_handle in person.get_parent_family_handle_list():
            fam = db.get_family_from_handle(fam_handle)
            if fam and fam.get_father_handle() != "":
                return fam.get_father_handle()
        return None

# -*- coding: utf-8 -*-
"""
engine/standardizer_service.py

Headless service for given name standardization logic.
"""

import os
import re
from typing import List

from gramps.gen.lib import Name, NameType
from gramps.gen.db import DbTxn
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.const import GRAMPS_LOCALE as glocale

from pat_engine.entities import RenameProposal
from pat_engine.logging import InferenceLogManager

_ = glocale.translation.gettext


class GivenNameStandardizerService:
    """Headless service for given name scanning and renaming."""

    def __init__(self, db):
        self.db = db
        # Extract unique DB directory name to isolate the logs
        db_path = self.db.get_dbname()
        self.db_id = os.path.basename(os.path.normpath(db_path))
        self.log_manager = InferenceLogManager(self.db_id)

    def scan_given_names(
        self, source_input: str, target_input: str, match_type: int
    ) -> List[RenameProposal]:
        """
        Scans the database for given names matching the source_input.
        match_type: 0 for Exact, 1 for Substring, 2 for Regex.
        """
        proposals = []
        pattern = None
        if match_type == 2:
            try:
                pattern = re.compile(source_input)
            except re.error:
                return []

        for handle in self.db.get_person_handles():
            person = self.db.get_person_from_handle(handle)
            if not person:
                continue

            primary_name = person.get_primary_name()
            if not primary_name:
                continue

            current_name = primary_name.get_first_name()
            if not current_name:
                continue

            matched = False
            proposed_name = ""

            if match_type == 0:  # Exact Match
                if current_name == source_input:
                    matched = True
                    proposed_name = target_input
            elif match_type == 1:  # Substring
                if source_input in current_name:
                    matched = True
                    proposed_name = current_name.replace(source_input, target_input)
            elif match_type == 2 and pattern:  # Regular Expression
                if pattern.search(current_name):
                    matched = True
                    proposed_name = pattern.sub(target_input, current_name)

            if matched and proposed_name != current_name:
                alt_action = "None"
                for alt_name in person.get_alternate_names():
                    if alt_name and alt_name.get_first_name() == proposed_name:
                        alt_action = "Merge Existing Alt Name"
                        break

                proposals.append(
                    RenameProposal(
                        person_handle=handle,
                        gramps_id=person.gramps_id,
                        display_name=name_displayer.display_formal(person),
                        current_name=current_name,
                        proposed_name=proposed_name,
                        alt_action=alt_action,
                    )
                )

        return proposals

    def apply_standardizations(
        self, proposals: List[RenameProposal], exec_id: str, preserve_alt_name: bool
    ):
        """Commits standardizations safely inside a transaction."""
        logged_changes = []
        with DbTxn(_("Standardize Given Names"), self.db) as txn:
            for prop in proposals:
                person = self.db.get_person_from_handle(prop.person_handle)
                if not person:
                    continue

                primary_name = person.get_primary_name()
                old_first = primary_name.get_first_name()
                new_first = prop.proposed_name

                # 1. Safe Preservation of Original Name
                if preserve_alt_name:
                    current_alts = person.get_alternate_names()
                    already_exists = any(
                        alt.get_first_name() == old_first for alt in current_alts
                    )

                    if not already_exists:
                        preserved_alt = Name()
                        # Use serialize/unserialize for a deep copy-like behavior in Gramps
                        preserved_alt.unserialize(primary_name.serialize())
                        preserved_alt.get_type().set(NameType.AKA)
                        current_alts.append(preserved_alt)
                        person.set_alternate_names(current_alts)

                # 2. Safely update the Primary Name
                primary_name.set_first_name(new_first)
                self.db.commit_person(person, txn)

                logged_changes.append(
                    {
                        "handle": prop.person_handle,
                        "original_value": old_first,
                        "inferred_value": new_first,
                    }
                )

        self.log_manager.log_execution(exec_id, "Standardize", logged_changes)

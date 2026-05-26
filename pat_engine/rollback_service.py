# -*- coding: utf-8 -*-
"""
engine/rollback_service.py

Headless service for database transaction reversals and history tracking.
"""

import json

from gramps.gen.db import DbTxn
from gramps.gen.const import GRAMPS_LOCALE as glocale

from pat_engine.utils import get_patronymic_value, is_patronymic_origin

_ = glocale.translation.gettext


class RollbackService:
    """Headless service for reverting past execution runs."""

    def __init__(self, db, log_manager):
        self.db = db
        self.log_manager = log_manager

    def get_history(self):
        """Returns the list of prior execution profiles."""
        return self.log_manager.get_executions()

    def rollback_execution(self, target_execution_id: str):
        """
        Reverts a specific execution run by ID.
        Ensures atomic database reversal and updates logs upon success.
        """
        log_file_path = self.log_manager.log_filepath
        with open(log_file_path, "r", encoding="utf-8") as f:
            log_data = json.load(f)

        execution = None
        for run in log_data.get("executions", []):
            if run.get("execution_id") == target_execution_id:
                execution = run
                break

        if not execution:
            raise ValueError(
                f"Execution ID {target_execution_id} not found in transaction logs."
            )

        report = {"reverted": [], "skipped_modified": []}

        with DbTxn(_("Rollback Executions"), self.db) as txn:
            for change in execution["changes"]:
                handle = change.get("handle", change.get("person_handle"))
                person = self.db.get_person_from_handle(handle)
                if not person:
                    continue

                primary_name = person.get_primary_name()

                if execution.get("plugin_id") == "Standardize":
                    # --- STANDARDIZATION REVERT LOGIC ---
                    current_first = primary_name.get_first_name()

                    # Skip if the user manually edited the name after the batch run
                    if current_first != change["inferred_value"]:
                        report["skipped_modified"].append(handle)
                        continue

                    # Revert Primary Name
                    primary_name.set_first_name(change["original_value"])

                    # Revert Alternate Names (remove generated backup)
                    current_alts = person.get_alternate_names()
                    reverted_alts = []
                    for alt in current_alts:
                        if alt.get_first_name() == change["original_value"]:
                            # Heuristic check: do surnames match the primary name?
                            alt_surname_strs = sorted(
                                [s.get_surname() for s in alt.get_surname_list()]
                            )
                            primary_surname_strs = sorted(
                                [
                                    s.get_surname()
                                    for s in primary_name.get_surname_list()
                                ]
                            )
                            if alt_surname_strs == primary_surname_strs:
                                # This is our backup - remove it
                                continue
                        reverted_alts.append(alt)

                    person.set_alternate_names(reverted_alts)
                    self.db.commit_person(person, txn)
                    report["reverted"].append(handle)

                else:
                    # --- PATRONYMIC REVERT LOGIC ---
                    current_value = get_patronymic_value(primary_name)
                    if current_value == change["inferred_value"]:
                        surnames = primary_name.get_surname_list()
                        new_surnames = []
                        for s in surnames:
                            if (
                                is_patronymic_origin(s.get_origintype())
                                and s.get_surname() == change["inferred_value"]
                            ):
                                if change["original_value"]:
                                    s.set_surname(change["original_value"])
                                    new_surnames.append(s)
                            else:
                                new_surnames.append(s)

                        primary_name.set_surname_list(new_surnames)
                        self.db.commit_person(person, txn)
                        report["reverted"].append(handle)
                    else:
                        report["skipped_modified"].append(handle)

        # Update JSON log file only after DB transaction success
        updated_executions = [
            run
            for run in log_data["executions"]
            if run.get("execution_id") != target_execution_id
        ]
        log_data["executions"] = updated_executions

        with open(log_file_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

        return report

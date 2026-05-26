# -*- coding: utf-8 -*-
"""
tests/test_standardize.py

Unit test suite for the Given Names batch standardization module.
"""

import unittest
import tempfile
import os
import json
from unittest.mock import MagicMock

# -------------------------------------------------------------------------
# Headless Decoupling Mocks
# -------------------------------------------------------------------------
from tests.compat_mocks import mock_gramps, Name, NameType

# Initialize mocks
mock_gramps()

# Now safely import standardizer tool rollback function
from engine.rollback_service import RollbackService


class MockLogManager:
    def __init__(self, log_filepath):
        self.log_filepath = log_filepath
    def get_executions(self):
        return []


class MockPerson:
    def __init__(self, handle, gramps_id, first_name, alts=None):
        self.handle = handle
        self.gramps_id = gramps_id
        self._primary_name = Name()
        self._primary_name.set_first_name(first_name)
        self._alts = []
        if alts:
            for a_first in alts:
                an = Name()
                an.set_first_name(a_first)
                an.set_type(NameType.AKA)
                self._alts.append(an)

    def get_primary_name(self):
        return self._primary_name

    def get_alternate_names(self):
        return self._alts

    def set_alternate_names(self, list_):
        self._alts = list_


class TestGivenNameStandardization(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_id = "test_db_98a7bc"

        # Setup mock database
        self.people = {
            "h1": MockPerson("h1", "I0001", "Иоанн"),
            "h2": MockPerson("h2", "I0002", "Иаков", ["Яков"]),
            "h3": MockPerson("h3", "I0003", "Иван-Иоанн"),
        }
        self.db = MagicMock()
        self.db.get_person_from_handle = lambda h: self.people.get(h)
        self.db.commit_person = MagicMock()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_revert_standardize_basic(self):
        """Verifies that standard rollback on 'Standardize' plugin restores names and removes backup alts."""
        # 1. Prepare simulated execution log data
        exec_id = "exec_20260525_161500"
        log_file = os.path.join(self.temp_dir.name, f"{self.db_id}.json")

        log_data = {
            "database_id": self.db_id,
            "executions": [
                {
                    "execution_id": exec_id,
                    "timestamp": "2026-05-25T16:15:00Z",
                    "plugin_id": "Standardize",
                    "changes": [
                        {
                            "person_handle": "h1",
                            "original_value": "Иоанн",
                            "inferred_value": "Иван",
                        },
                        {
                            "person_handle": "h2",
                            "original_value": "Иаков",
                            "inferred_value": "Яков",
                        },
                    ],
                }
            ],
        }
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

        # Apply mock current state (after standardization)
        # Person 1 was standardized to 'Иван', and had alternate name 'Иоанн' added as backup
        self.people["h1"].get_primary_name().set_first_name("Иван")
        alt_name = Name()
        alt_name.set_first_name("Иоанн")
        alt_name.set_type(NameType.AKA)
        self.people["h1"].set_alternate_names([alt_name])

        # Person 2 was standardized to 'Яков', no backup alt was added (preserve option was off)
        self.people["h2"].get_primary_name().set_first_name("Яков")
        self.people["h2"].set_alternate_names([])

        # 2. Run Rollback
        log_manager = MockLogManager(log_file)
        rollback_service = RollbackService(self.db, log_manager)
        report = rollback_service.rollback_execution(exec_id)


        # 3. Assertions
        self.assertEqual(len(report["reverted"]), 2)
        self.assertEqual(len(report["skipped_modified"]), 0)

        # Person 1 reverted primary to 'Иоанн', backup alt 'Иоанн' removed
        self.assertEqual(self.people["h1"].get_primary_name().get_first_name(), "Иоанн")
        self.assertEqual(len(self.people["h1"].get_alternate_names()), 0)

        # Person 2 reverted primary to 'Иаков', no alts to restore
        self.assertEqual(self.people["h2"].get_primary_name().get_first_name(), "Иаков")
        self.assertEqual(len(self.people["h2"].get_alternate_names()), 0)

    def test_revert_state_verification(self):
        """Verifies that rollback is skipped if the current primary name has changed in the interim."""
        exec_id = "exec_20260525_161500"
        log_file = os.path.join(self.temp_dir.name, f"{self.db_id}.json")

        log_data = {
            "database_id": self.db_id,
            "executions": [
                {
                    "execution_id": exec_id,
                    "timestamp": "2026-05-25T16:15:00Z",
                    "plugin_id": "Standardize",
                    "changes": [
                        {
                            "person_handle": "h1",
                            "original_value": "Иоанн",
                            "inferred_value": "Иван",
                        }
                    ],
                }
            ],
        }
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

        # Set interim state where person primary name was manually modified to 'Ваня' instead of 'Иван'
        self.people["h1"].get_primary_name().set_first_name("Ваня")
        alt_name = Name()
        alt_name.set_first_name("Иоанн")
        alt_name.set_type(NameType.AKA)
        self.people["h1"].set_alternate_names([alt_name])

        # Run Rollback
        log_manager = MockLogManager(log_file)
        rollback_service = RollbackService(self.db, log_manager)
        report = rollback_service.rollback_execution(exec_id)

        # Assertions
        self.assertEqual(len(report["reverted"]), 0)
        self.assertEqual(len(report["skipped_modified"]), 1)
        self.assertEqual(self.people["h1"].get_primary_name().get_first_name(), "Ваня")
        self.assertEqual(len(self.people["h1"].get_alternate_names()), 1)


if __name__ == "__main__":
    unittest.main()

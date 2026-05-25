# -*- coding: utf-8 -*-
"""
tests/test_standardize.py

Unit test suite for the Given Names batch standardization module.
"""

import sys
import unittest
import tempfile
import os
import json
from unittest.mock import MagicMock

# -------------------------------------------------------------------------
# Headless Decoupling Mocks
# -------------------------------------------------------------------------
gi_mock = MagicMock()
gi_repository_mock = MagicMock()
gtk_mock = MagicMock()
glib_mock = MagicMock()

gi_repository_mock.Gtk = gtk_mock
gi_repository_mock.GLib = glib_mock

sys.modules["gi"] = gi_mock
sys.modules["gi.repository"] = gi_repository_mock
sys.modules["gi.repository.Gtk"] = gtk_mock
sys.modules["gi.repository.GLib"] = glib_mock

gramps_mock = MagicMock()
gramps_gen_mock = MagicMock()
gramps_gen_db_mock = MagicMock()
gramps_gui_mock = MagicMock()
gramps_gui_plug_mock = MagicMock()
gramps_gui_dialog_mock = MagicMock()


class DbTxn:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


gramps_gen_db_mock.DbTxn = DbTxn


class MockToolBase:
    def __init__(self, *args, **kwargs):
        pass


class MockToolOptionsBase:
    def __init__(self, *args, **kwargs):
        pass


tool_module = MagicMock()
tool_module.Tool = MockToolBase
tool_module.ToolOptions = MockToolOptionsBase
gramps_gui_plug_mock.tool = tool_module

gen_const = MagicMock()
gen_const.GRAMPS_LOCALE.translation.gettext = lambda x: x


class NameOriginType:
    UNKNOWN = 0
    CUSTOM = 1
    PATRONYMIC = 5


class Surname:
    def __init__(self, surname_str="", origin=NameOriginType.UNKNOWN):
        self._surname = surname_str
        self._origin = origin

    def get_surname(self) -> str:
        return self._surname

    def get_origintype(self):
        return self._origin


class Name:
    def __init__(self):
        self._first_name = ""
        self._type = None
        self._surnames = []

    def get_first_name(self):
        return self._first_name

    def set_first_name(self, name_str):
        self._first_name = name_str

    def set_type(self, val):
        self._type = val

    def get_surname_list(self):
        return self._surnames

    def add_surname(self, surname):
        self._surnames.append(surname)

    def set_surname_list(self, list_):
        self._surnames = list_


class NameType:
    CUSTOM = 1
    ALSO_KNOWN_AS = 3


gen_lib = MagicMock()
gen_lib.NameOriginType = NameOriginType
gen_lib.Surname = Surname
gen_lib.Name = Name
gen_lib.NameType = NameType

gen_display_mock = MagicMock()
gen_display_name_mock = MagicMock()
gen_display_mock.name = gen_display_name_mock

gen_errors_mock = MagicMock()
gen_errors_mock.WindowActiveError = Exception

gui_editors_mock = MagicMock()
gui_editors_mock.EditPerson = MagicMock

sys.modules["gramps"] = gramps_mock
sys.modules["gramps.gen"] = gramps_gen_mock
sys.modules["gramps.gen.const"] = gen_const
sys.modules["gramps.gen.db"] = gramps_gen_db_mock
sys.modules["gramps.gen.lib"] = gen_lib
sys.modules["gramps.gen.display"] = gen_display_mock
sys.modules["gramps.gen.display.name"] = gen_display_name_mock
sys.modules["gramps.gen.errors"] = gen_errors_mock
sys.modules["gramps.gui"] = gramps_gui_mock
sys.modules["gramps.gui.plug"] = gramps_gui_plug_mock
sys.modules["gramps.gui.dialog"] = gramps_gui_dialog_mock
sys.modules["gramps.gui.editors"] = gui_editors_mock

# Now safely import standardizer tool rollback function
from patronymics_tool import rollback_batch_execution  # noqa: E402


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
                an.set_type(NameType.ALSO_KNOWN_AS)
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
        """Verifies that standard rollback on 'Standardize' plugin restores names and alts correctly."""
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
                            "alts_added": ["Иоанн"],
                            "alts_removed": [],
                        },
                        {
                            "person_handle": "h2",
                            "original_value": "Иаков",
                            "inferred_value": "Яков",
                            "alts_added": [],
                            "alts_removed": ["Яков"],
                        },
                    ],
                }
            ],
        }
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

        # Apply mock current state (after standardization)
        # Person 1 was standardized to 'Иван', and had alternate name 'Иоанн' added
        self.people["h1"].get_primary_name().set_first_name("Иван")
        alt_name = Name()
        alt_name.set_first_name("Иоанн")
        alt_name.set_type(NameType.ALSO_KNOWN_AS)
        self.people["h1"].set_alternate_names([alt_name])

        # Person 2 was standardized to 'Яков', and had alternate 'Яков' removed
        self.people["h2"].get_primary_name().set_first_name("Яков")
        self.people["h2"].set_alternate_names([])

        # 2. Run Rollback
        report = rollback_batch_execution(self.db, log_file, exec_id)

        # 3. Assertions
        self.assertEqual(len(report["reverted"]), 2)
        self.assertEqual(len(report["skipped_modified"]), 0)

        # Person 1 reverted primary to 'Иоанн', alt 'Иоанн' removed
        self.assertEqual(self.people["h1"].get_primary_name().get_first_name(), "Иоанн")
        self.assertEqual(len(self.people["h1"].get_alternate_names()), 0)

        # Person 2 reverted primary to 'Иаков', alt 'Яков' restored
        self.assertEqual(self.people["h2"].get_primary_name().get_first_name(), "Иаков")
        self.assertEqual(len(self.people["h2"].get_alternate_names()), 1)
        self.assertEqual(
            self.people["h2"].get_alternate_names()[0].get_first_name(), "Яков"
        )

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
                            "alts_added": ["Иоанн"],
                            "alts_removed": [],
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
        alt_name.set_type(NameType.ALSO_KNOWN_AS)
        self.people["h1"].set_alternate_names([alt_name])

        # Run Rollback
        report = rollback_batch_execution(self.db, log_file, exec_id)

        # Assertions
        self.assertEqual(len(report["reverted"]), 0)
        self.assertEqual(len(report["skipped_modified"]), 1)
        self.assertEqual(self.people["h1"].get_primary_name().get_first_name(), "Ваня")
        self.assertEqual(len(self.people["h1"].get_alternate_names()), 1)


if __name__ == "__main__":
    unittest.main()

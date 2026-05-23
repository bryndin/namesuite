# -*- coding: utf-8 -*-
"""
tests/test_ref_year.py

Verifies the Reference Year resolution algorithm, specifically the Tier 2
Generational Lineage Heuristic and the newly added Tier 3 Spouse/Family heuristic.
"""

import sys
import unittest
from unittest.mock import MagicMock

# -*- coding: utf-8 -*-
"""
tests/test_ref_year.py

Verifies the Reference Year resolution algorithm.
"""


# -------------------------------------------------------------------------
# Headless Decoupling Mocks
# -------------------------------------------------------------------------

# GTK & GLib mocks
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

# Create parent package mocks
gramps_mock = MagicMock()
gramps_gen_mock = MagicMock()
gramps_gen_const_mock = MagicMock()
gramps_gen_db_mock = MagicMock()
gramps_gen_lib_mock = MagicMock()
gramps_gui_mock = MagicMock()
gramps_gui_plug_mock = MagicMock()
gramps_gui_dialog_mock = MagicMock()

# Mock gramps.gen.lib
class NameOriginType:
    UNKNOWN = 0
    CUSTOM = 1
    PATRONYMIC = 5

class Surname:
    def __init__(self, surname_str="", origin=NameOriginType.UNKNOWN):
        self._surname = surname_str
        self._origin = origin
    def get_surname(self) -> str: return self._surname
    def set_surname(self, val): self._surname = val
    def get_origintype(self): return self._origin
    def set_origintype(self, val): self._origin = val
    def set_primary(self, val): pass

gramps_gen_lib_mock.NameOriginType = NameOriginType
gramps_gen_lib_mock.Surname = Surname
gramps_gen_lib_mock.Person = MagicMock()

# Gramps localization mock
gramps_gen_const_mock.GRAMPS_LOCALE.translation.gettext = lambda x: x

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

sys.modules["gramps"] = gramps_mock
sys.modules["gramps.gen"] = gramps_gen_mock
sys.modules["gramps.gen.const"] = gramps_gen_const_mock
sys.modules["gramps.gen.db"] = gramps_gen_db_mock
sys.modules["gramps.gen.lib"] = gramps_gen_lib_mock
sys.modules["gramps.gui"] = gramps_gui_mock
sys.modules["gramps.gui.plug"] = gramps_gui_plug_mock
sys.modules["gramps.gui.dialog"] = gramps_gui_dialog_mock



# Now import the tool
from patronymics_tool import InferPatronymicsTool
from gramps.gen.lib import Person




class MockEvent:
    def __init__(self, year):
        self.year = year
    def get_date_object(self):
        date_obj = MagicMock()
        date_obj.get_year.return_value = self.year
        return date_obj

class TestReferenceYearResolution(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        # Create a tool instance without full GTK init
        self.tool = MagicMock(spec=InferPatronymicsTool)
        self.tool.db = self.mock_db
        # Re-bind the method we want to test
        self.tool.resolve_reference_year = InferPatronymicsTool.resolve_reference_year.__get__(self.tool, InferPatronymicsTool)

    def test_tier1_latest_event_year(self):
        person = MagicMock()
        event1 = MockEvent(1850)
        event2 = MockEvent(1880)
        person.get_event_ref_list.return_value = [MagicMock(ref="E1"), MagicMock(ref="E2")]
        
        self.mock_db.get_event_from_handle.side_effect = lambda h: event1 if h == "E1" else event2
        
        year, source = self.tool.resolve_reference_year(person)
        self.assertEqual(year, 1880)
        self.assertIn("Latest Event Year", source)

    def test_tier3_spouse_marriage_heuristic(self):
        """
        Scenario: Person has no events, but married in 1836 and wife born in 1814.
        Ref year should be median of [1836, 1814] -> 1836? 
        """
        person = MagicMock()
        person.get_event_ref_list.return_value = []
        person.get_parent_family_handle_list.return_value = [] # No parents
        person.get_family_handle_list.return_value = ["F1"]
        person.get_gender.return_value = Person.MALE

        family = MagicMock()
        family.get_event_ref_list.return_value = [MagicMock(ref="E_MARR")]
        family.get_mother_handle.return_value = "WIFE_H"
        
        wife = MagicMock()
        wife.get_event_ref_list.return_value = [MagicMock(ref="E_WIFE_BIRTH")]
        
        marr_event = MockEvent(1836)
        wife_birth = MockEvent(1814)

        def db_get_event(h):
            if h == "E_MARR": return marr_event
            if h == "E_WIFE_BIRTH": return wife_birth
            return None

        self.mock_db.get_family_from_handle.return_value = family
        self.mock_db.get_person_from_handle.return_value = wife
        self.mock_db.get_event_from_handle.side_effect = db_get_event

        year, source = self.tool.resolve_reference_year(person)
        self.assertEqual(year, 1836)
        self.assertIn("Spouse/Family", source)

    def test_tier4_fallback_default(self):
        person = MagicMock()
        person.get_event_ref_list.return_value = []
        person.get_parent_family_handle_list.return_value = []
        person.get_family_handle_list.return_value = []
        
        year, source = self.tool.resolve_reference_year(person)
        self.assertIsNone(year)
        self.assertIsNone(source)

if __name__ == "__main__":
    unittest.main()

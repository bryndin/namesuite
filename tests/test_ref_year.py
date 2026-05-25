# -*- coding: utf-8 -*-
"""
tests/test_ref_year.py

Verifies the Reference Year resolution algorithm.
"""

import sys
import unittest
from unittest.mock import MagicMock

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
gramps_gen_display_name_mock = MagicMock()
gramps_gen_errors_mock = MagicMock()
gramps_gui_mock = MagicMock()
gramps_gui_plug_mock = MagicMock()
gramps_gui_dialog_mock = MagicMock()
gramps_gui_editors_mock = MagicMock()

# Mock EditPerson
class MockEditPerson:
    def __init__(self, *args, **kwargs):
        pass

gramps_gui_editors_mock.EditPerson = MockEditPerson

# Mock WindowActiveError
class MockWindowActiveError(Exception):
    pass

gramps_gen_errors_mock.WindowActiveError = MockWindowActiveError

# Mock displayer
gramps_gen_display_name_mock.displayer.display_formal.return_value = "Mock Name"

# Gramps localization mock
gramps_gen_const_mock.GRAMPS_LOCALE.translation.gettext = lambda x: x


# Mock gramps.gen.lib
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

    def set_primary(self, val):
        pass


gramps_gen_lib_mock.NameOriginType = NameOriginType
gramps_gen_lib_mock.Surname = Surname
gramps_gen_lib_mock.Person = MagicMock()


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
sys.modules["gramps.gen.display.name"] = gramps_gen_display_name_mock
sys.modules["gramps.gen.errors"] = gramps_gen_errors_mock
sys.modules["gramps.gui"] = gramps_gui_mock
sys.modules["gramps.gui.plug"] = gramps_gui_plug_mock
sys.modules["gramps.gui.dialog"] = gramps_gui_dialog_mock
sys.modules["gramps.gui.editors"] = gramps_gui_editors_mock

# Import after mock setup (intentionally not at top of file)
from patronymics_tool import InferPatronymicsTool  # noqa: E402


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
        self.tool = MagicMock(spec=InferPatronymicsTool)
        self.tool.db = self.mock_db
        self.tool.db_median_year = 1921
        # Copy the REF_SOURCE constants from the actual class
        self.tool.REF_SOURCE_LATEST_EVENT = InferPatronymicsTool.REF_SOURCE_LATEST_EVENT
        self.tool.REF_SOURCE_GENERATIONAL_PARENTS = InferPatronymicsTool.REF_SOURCE_GENERATIONAL_PARENTS
        self.tool.REF_SOURCE_GENERATIONAL_SPOUSE_FAMILY = InferPatronymicsTool.REF_SOURCE_GENERATIONAL_SPOUSE_FAMILY
        self.tool.REF_SOURCE_DB_MEDIAN_FALLBACK = InferPatronymicsTool.REF_SOURCE_DB_MEDIAN_FALLBACK
        self.tool.resolve_reference_year = (
            InferPatronymicsTool.resolve_reference_year.__get__(
                self.tool, InferPatronymicsTool
            )
        )

    def test_tier1_latest_event_year(self):
        person = MagicMock()
        person.get_event_ref_list.return_value = [
            MagicMock(ref="E1"),
            MagicMock(ref="E2"),
        ]
        self.mock_db.get_event_from_handle.side_effect = lambda h: (
            MockEvent(1850) if h == "E1" else MockEvent(1880)
        )
        year, source = self.tool.resolve_reference_year(person)
        self.assertEqual(year, 1880)
        self.assertEqual(source, InferPatronymicsTool.REF_SOURCE_LATEST_EVENT)

    def test_tier2_parents_heuristic(self):
        person = MagicMock()
        person.get_parent_family_handle_list.return_value = ["F1"]
        family = MagicMock()
        family.get_father_handle.return_value = "FATHER"
        self.mock_db.get_family_from_handle.return_value = family
        father = MagicMock()
        father.get_event_ref_list.return_value = [MagicMock(ref="E1")]
        self.mock_db.get_person_from_handle.return_value = father
        self.mock_db.get_event_from_handle.return_value = MockEvent(1900)
        year, source = self.tool.resolve_reference_year(person)
        self.assertEqual(year, 1925)
        self.assertIn("Parents", source)

    def test_tier3_spouse_family_heuristic(self):
        person = MagicMock()
        person.get_event_ref_list.return_value = []
        person.get_family_handle_list.return_value = ["F1"]
        family = MagicMock()
        family.get_event_ref_list.return_value = [MagicMock(ref="E1")]
        self.mock_db.get_family_from_handle.return_value = family
        self.mock_db.get_event_from_handle.return_value = MockEvent(1900)
        year, source = self.tool.resolve_reference_year(person)
        self.assertEqual(year, 1900)
        self.assertIn("Spouse/Family", source)

    def test_tier4_fallback_default(self):
        person = MagicMock()
        person.get_event_ref_list.return_value = []
        person.get_parent_family_handle_list.return_value = []
        person.get_family_handle_list.return_value = []
        year, source = self.tool.resolve_reference_year(person)
        self.assertEqual(year, 1921)
        self.assertEqual(source, InferPatronymicsTool.REF_SOURCE_DB_MEDIAN_FALLBACK)


if __name__ == "__main__":
    unittest.main()

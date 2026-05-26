# -*- coding: utf-8 -*-
"""
tests/test_ref_year.py

Verifies the tiered reference year resolution logic (Events -> BFS Graph -> Median).
"""

import unittest
from unittest.mock import MagicMock

# -------------------------------------------------------------------------
# Headless Decoupling Mocks
# -------------------------------------------------------------------------
from tests.compat_mocks import mock_gramps

# Initialize mocks
mock_gramps()

# Import after mock setup
from names_engine.inference_service import PatronymicInferenceService


class MockEvent:
    def __init__(self, year):
        self.year = year

    def get_date_object(self):
        return self

    def get_year(self):
        return self.year


class TestReferenceYearResolution(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.mock_db.get_dbname.return_value = "/tmp/mock.db"
        self.service = PatronymicInferenceService(self.mock_db)
        self.service.db_median_year = 1921

        # Keep 'tool' name for minimal changes in test cases below
        self.tool = self.service

        # Source constants are now on the service
        self.REF_SOURCE_LATEST_EVENT = self.service.REF_SOURCE_LATEST_EVENT
        self.REF_SOURCE_GRAPH_BFS = self.service.REF_SOURCE_GRAPH_BFS
        self.REF_SOURCE_DB_MEDIAN_FALLBACK = self.service.REF_SOURCE_DB_MEDIAN_FALLBACK

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
        self.assertEqual(source, self.REF_SOURCE_LATEST_EVENT)

    def test_tier2_graph_bfs_parents(self):
        person = MagicMock(handle="P1")
        person.get_event_ref_list.return_value = []
        person.get_parent_family_handle_list.return_value = ["F1"]

        family = MagicMock()
        family.get_father_handle.return_value = "F_DAD"
        family.get_mother_handle.return_value = ""
        family.get_child_ref_list.return_value = []
        self.mock_db.get_family_from_handle.return_value = family

        father = MagicMock()
        father.get_event_ref_list.return_value = [MagicMock(ref="E_DAD")]
        self.mock_db.get_person_from_handle.side_effect = lambda h: (
            person if h == "P1" else father if h == "F_DAD" else None
        )

        self.mock_db.get_event_from_handle.return_value = MockEvent(1840)

        # BFS should find father's event at depth 1 (delta_g = +1)
        # Expected year: 1840 + (1 * 25) = 1865
        year, source = self.tool.resolve_reference_year(person)
        self.assertEqual(year, 1865)
        self.assertEqual(source, self.REF_SOURCE_GRAPH_BFS)

    def test_tier2_graph_bfs_children(self):
        person = MagicMock(handle="P1")
        person.get_event_ref_list.return_value = []
        person.get_parent_family_handle_list.return_value = []
        person.get_family_handle_list.return_value = ["F1"]

        family = MagicMock()
        family.get_father_handle.return_value = "P1"
        family.get_mother_handle.return_value = ""
        child_ref = MagicMock(ref="C1")
        family.get_child_ref_list.return_value = [child_ref]
        self.mock_db.get_family_from_handle.return_value = family

        child = MagicMock()
        child.get_event_ref_list.return_value = [MagicMock(ref="E_CHILD")]
        self.mock_db.get_person_from_handle.side_effect = lambda h: (
            person if h == "P1" else child if h == "C1" else None
        )

        self.mock_db.get_event_from_handle.return_value = MockEvent(1900)

        # BFS should find child's event at depth 1 (delta_g = -1)
        # Expected year: 1900 + (-1 * 25) = 1875
        year, source = self.tool.resolve_reference_year(person)
        self.assertEqual(year, 1875)
        self.assertEqual(source, self.REF_SOURCE_GRAPH_BFS)

    def test_tier3_database_fallback(self):
        person = MagicMock(handle="P1")
        person.get_event_ref_list.return_value = []
        person.get_parent_family_handle_list.return_value = []
        person.get_family_handle_list.return_value = []
        self.mock_db.get_person_from_handle.return_value = person

        year, source = self.tool.resolve_reference_year(person)
        self.assertEqual(year, 1921)
        self.assertEqual(source, self.REF_SOURCE_DB_MEDIAN_FALLBACK)


if __name__ == "__main__":
    unittest.main()

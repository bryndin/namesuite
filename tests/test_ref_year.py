# -*- coding: utf-8 -*-
"""
tests/test_ref_year.py

Verifies the Reference Year resolution algorithm.
"""

import unittest
from unittest.mock import MagicMock

# Import common test mocks
from tests.compat_mocks import mock_gramps

# Initialize mocks
mock_gramps()

# Import after mock setup
from patronymics_tool import EastSlavicNameTools


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
        self.tool = MagicMock(spec=EastSlavicNameTools)
        self.tool.db = self.mock_db
        self.tool.db_median_year = 1921
        # Copy the REF_SOURCE constants from the actual class
        self.tool.REF_SOURCE_LATEST_EVENT = EastSlavicNameTools.REF_SOURCE_LATEST_EVENT
        self.tool.REF_SOURCE_GRAPH_BFS = EastSlavicNameTools.REF_SOURCE_GRAPH_BFS
        self.tool.REF_SOURCE_DB_MEDIAN_FALLBACK = (
            EastSlavicNameTools.REF_SOURCE_DB_MEDIAN_FALLBACK
        )
        self.tool.resolve_reference_year = (
            EastSlavicNameTools.resolve_reference_year.__get__(
                self.tool, EastSlavicNameTools
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
        self.assertEqual(source, EastSlavicNameTools.REF_SOURCE_LATEST_EVENT)

    def test_tier2_generational_graph_bfs(self):
        """Test Tier 2: BFS traversal finds father event and normalizes by generation."""
        person = MagicMock()
        person.handle = "PERSON"
        person.get_event_ref_list.return_value = []  # No own events
        person.get_parent_family_handle_list.return_value = ["F1"]
        person.get_family_handle_list.return_value = []

        family = MagicMock()
        family.get_father_handle.return_value = "FATHER"
        family.get_mother_handle.return_value = None
        family.get_child_ref_list.return_value = []
        self.mock_db.get_family_from_handle.return_value = family

        father = MagicMock()
        father.handle = "FATHER"
        father.get_event_ref_list.return_value = [MagicMock(ref="E1")]
        father.get_parent_family_handle_list.return_value = []
        father.get_family_handle_list.return_value = []

        # Mock get_person_from_handle to return the correct person for each handle
        def mock_get_person(handle):
            if handle == "PERSON":
                return person
            elif handle == "FATHER":
                return father
            return None

        self.mock_db.get_person_from_handle.side_effect = mock_get_person
        self.mock_db.get_event_from_handle.return_value = MockEvent(1900)

        year, source = self.tool.resolve_reference_year(person)
        # Father is at delta_g = +1, so 1900 + (1 * 25) = 1925
        self.assertEqual(year, 1925)
        self.assertEqual(source, self.tool.REF_SOURCE_GRAPH_BFS)

    def test_tier2_generational_graph_multiple_relatives(self):
        """Test Tier 2: BFS with multiple relatives uses median of normalized years."""
        person = MagicMock()
        person.handle = "PERSON"
        person.get_event_ref_list.return_value = []  # No own events
        person.get_parent_family_handle_list.return_value = ["F1"]
        person.get_family_handle_list.return_value = []

        family = MagicMock()
        family.get_father_handle.return_value = "FATHER"
        family.get_mother_handle.return_value = "MOTHER"
        family.get_child_ref_list.return_value = []
        self.mock_db.get_family_from_handle.return_value = family

        father = MagicMock()
        father.handle = "FATHER"
        father.get_event_ref_list.return_value = [MagicMock(ref="E1")]
        father.get_parent_family_handle_list.return_value = []
        father.get_family_handle_list.return_value = []

        mother = MagicMock()
        mother.handle = "MOTHER"
        mother.get_event_ref_list.return_value = [MagicMock(ref="E2")]
        mother.get_parent_family_handle_list.return_value = []
        mother.get_family_handle_list.return_value = []

        def mock_get_person(handle):
            if handle == "PERSON":
                return person
            elif handle == "FATHER":
                return father
            elif handle == "MOTHER":
                return mother
            return None

        self.mock_db.get_person_from_handle.side_effect = mock_get_person

        def mock_get_event(handle):
            if handle == "E1":
                return MockEvent(1900)
            elif handle == "E2":
                return MockEvent(1910)
            return None

        self.mock_db.get_event_from_handle.side_effect = mock_get_event

        year, source = self.tool.resolve_reference_year(person)
        # Both parents at delta_g = +1: [1900+25, 1910+25] = [1925, 1935]
        # Implementation uses sorted()[len//2] which for 2 elements picks index 1 (upper value)
        self.assertEqual(year, 1935)
        self.assertEqual(source, self.tool.REF_SOURCE_GRAPH_BFS)

    def test_tier3_database_fallback(self):
        person = MagicMock()
        person.get_event_ref_list.return_value = []
        person.get_parent_family_handle_list.return_value = []
        person.get_family_handle_list.return_value = []
        year, source = self.tool.resolve_reference_year(person)
        self.assertEqual(year, 1921)
        self.assertEqual(source, EastSlavicNameTools.REF_SOURCE_DB_MEDIAN_FALLBACK)


if __name__ == "__main__":
    unittest.main()

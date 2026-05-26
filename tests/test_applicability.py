# -*- coding: utf-8 -*-
"""
tests/test_applicability.py

Implements TestFamilyGraphLineageScanner and TestMultiSignalApplicability
using clean mock-driven environments to bypass Gramps core database
and GTK GUI requirements.
"""

import unittest
from unittest.mock import MagicMock

# Import common test mocks
from tests.compat_mocks import mock_gramps, NameOriginType, Surname

# Initialize mocks
mock_gramps()

# Now safely import components
from utils import PatronymicMixin
from patronymics_tool import EastSlavicNameTools

# -------------------------------------------------------------------------
# Test Helper Class
# -------------------------------------------------------------------------
class MockPatronymicsTool(PatronymicMixin):
    """
    Decoupled tool proxy mapping target inference methods to allow testing
    the core business logic without triggering GTK UI initializations.
    """

    def __init__(self, db):
        self.db = db
        self.dbstate = MagicMock()
        self.dbstate.db = db

    evaluate_confidence = EastSlavicNameTools.evaluate_confidence


# -------------------------------------------------------------------------
# Test Cases
# -------------------------------------------------------------------------
class TestFamilyGraphLineageScanner(unittest.TestCase):
    """
    Verifies that family traversal correctly resolves biological fathers
    without introducing self-referential lineage loops.
    """

    def setUp(self):
        self.mock_db = MagicMock()
        self.tool = MockPatronymicsTool(self.mock_db)

    def test_no_self_ancestry_logic_loop(self):
        """
        Dmitry (I1) is a father in family F1. He does not have a parent
        family record. Traversal must return None instead of looping.
        """
        # Dmitry (I1)
        father = MagicMock()
        father.handle = "I1"
        father.get_parent_family_handle_list.return_value = []

        father_handle = self.tool.get_father_handle(father)
        self.assertIsNone(father_handle, "A father with no parents must return None.")

    def test_correct_lineage_resolution(self):
        """
        Masha (I2) is a child in family F1, where Dmitry (I1) is the father.
        Traversal on Masha must return Dmitry's handle.
        """
        # Masha (I2)
        child = MagicMock()
        child.handle = "I2"
        child.get_parent_family_handle_list.return_value = ["F1"]

        # Family F1
        family = MagicMock()
        family.handle = "F1"
        family.get_father_handle.return_value = "I1"

        # Map DB mock responses
        self.mock_db.get_family_from_handle.return_value = family

        father_handle = self.tool.get_father_handle(child)
        self.assertEqual(
            father_handle,
            "I1",
            "Lineage engine must return the correct biological father handle.",
        )


class TestMultiSignalApplicability(unittest.TestCase):
    """
    Verifies the multi-signal confidence matrix correctly classifies regional,
    orthographical, and lineage context signals to isolate East Slavic trees
    from other ethnic backgrounds.
    """

    def setUp(self):
        self.mock_db = MagicMock()
        self.tool = MockPatronymicsTool(self.mock_db)

    def test_valid_east_slavic_context_cyrillic(self):
        """
        A person named 'Аня Козявкина' with father 'Дмитрий' matches both
        Cyrillic script checks and Slavic surname rules, scoring above the
        automatic inference threshold (>= 0.60).
        """
        person = MagicMock()
        person.handle = "I3"
        person.get_parent_family_handle_list.return_value = []

        primary_name = MagicMock()
        primary_name.get_regular_name.return_value = "Аня Козявкина"

        # Mock Surname object ending in Cyrillic '-ина'
        surname = Surname("Козявкина", NameOriginType.UNKNOWN)
        primary_name.get_surname_list.return_value = [surname]

        confidence = self.tool.evaluate_confidence(person, primary_name, "Дмитрий")

        # Cyrillic (+0.50) + Suffix Match (+0.20) = 0.70
        self.assertGreaterEqual(
            confidence,
            0.60,
            f"East Slavic name context should score >= 0.60 (got {confidence})",
        )

    def test_polish_westernized_exclusion(self):
        """
        A Polish person named 'Maria Skłodowska' uses the Latin script and a
        surnaming convention ending in '-ska'. The engine must classify this
        as non-Slavic/excluded, yielding a score under the threshold (< 0.60).
        """
        person = MagicMock()
        person.handle = "I4"
        person.get_parent_family_handle_list.return_value = []

        primary_name = MagicMock()
        primary_name.get_regular_name.return_value = "Maria Skłodowska"

        # Surname does not match SLAVIC_SURNAME_PATTERN (excludes Polish "-ska")
        surname = Surname("Skłodowska", NameOriginType.UNKNOWN)
        primary_name.get_surname_list.return_value = [surname]

        confidence = self.tool.evaluate_confidence(person, primary_name, "Władysław")

        # Latin script (0.0) + Excluded Polish Suffix (0.0) = 0.0
        self.assertLess(
            confidence,
            0.60,
            f"Polish name context should score < 0.60 (got {confidence})",
        )

    def test_slavic_surnames_written_in_latin(self):
        """
        An individual with a Slavic surname written in Latin characters (e.g. 'Fyodor Dostoevsky')
        receives a positive signal for the surname suffix (+0.20) but 0 for Cyrillic script.
        Without family tree confirmations, they score under the threshold (< 0.60).
        """
        person = MagicMock()
        person.handle = "I5"
        person.get_parent_family_handle_list.return_value = []

        primary_name = MagicMock()
        primary_name.get_regular_name.return_value = "Fyodor Dostoevsky"

        # 'Dostoevsky' matches Latin 'sky' suffix (+0.20)
        surname = Surname("Dostoevsky", NameOriginType.UNKNOWN)
        primary_name.get_surname_list.return_value = [surname]

        confidence = self.tool.evaluate_confidence(person, primary_name, "Dmitry")

        # Latin script (0.0) + Surname suffix match (+0.20) = 0.20
        self.assertLess(
            confidence,
            0.60,
            f"Latinized Slavic names without sibling patterns must score < 0.60 (got {confidence})",
        )


if __name__ == "__main__":
    unittest.main()

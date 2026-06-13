from __future__ import annotations

import unittest
from unittest.mock import Mock

from name_processor.repositories.person import GrampsPersonProxy
from name_processor.models.person import Gender


# Mocking Gramps constants used in the proxy
class MockGrampsPerson:
    MALE = 0
    FEMALE = 1


class MockNameOriginType:
    PATRONYMIC = 2
    GIVEN = 0


class TestGrampsPersonProxy(unittest.TestCase):
    def setUp(self):
        self.mock_db = Mock()
        self.mock_gramps_person = Mock()
        self.mock_gramps_person.get_handle.return_value = "p123"

        # Patch the GrampsPerson reference in the module to use our mock constants
        import name_processor.repositories.person as repo_module

        repo_module.GrampsPerson = MockGrampsPerson
        repo_module.NameOriginType = MockNameOriginType

        self.proxy = GrampsPersonProxy(self.mock_gramps_person, self.mock_db)

    def test_handle(self):
        self.assertEqual(self.proxy.handle, "p123")

    def test_gender_male(self):
        self.mock_gramps_person.get_gender.return_value = MockGrampsPerson.MALE
        self.assertEqual(self.proxy.gender, Gender.MALE)

    def test_gender_female_or_other(self):
        self.mock_gramps_person.get_gender.return_value = MockGrampsPerson.FEMALE
        self.assertEqual(self.proxy.gender, Gender.FEMALE)

    def test_has_patronymic_true(self):
        mock_primary_name = Mock()
        mock_surname1 = Mock()
        mock_surname1.get_origintype.return_value = MockNameOriginType.GIVEN
        mock_surname2 = Mock()
        mock_surname2.get_origintype.return_value = MockNameOriginType.PATRONYMIC

        mock_primary_name.get_surname_list.return_value = [mock_surname1, mock_surname2]
        self.mock_gramps_person.get_primary_name.return_value = mock_primary_name

        self.assertTrue(self.proxy.has_patronymic)

    def test_has_patronymic_false(self):
        mock_primary_name = Mock()
        mock_surname = Mock()
        mock_surname.get_origintype.return_value = MockNameOriginType.GIVEN

        mock_primary_name.get_surname_list.return_value = [mock_surname]
        self.mock_gramps_person.get_primary_name.return_value = mock_primary_name

        self.assertFalse(self.proxy.has_patronymic)

    def test_father_handle_found(self):
        self.mock_gramps_person.get_parent_family_handle_list.return_value = ["fam1"]
        mock_family = Mock()
        mock_family.get_father_handle.return_value = "father123"
        self.mock_db.get_family_from_handle.return_value = mock_family

        self.assertEqual(self.proxy.father_handle, "father123")

    def test_mother_handle_not_found(self):
        self.mock_gramps_person.get_parent_family_handle_list.return_value = []
        self.assertIsNone(self.proxy.mother_handle)

    def test_children_handles(self):
        self.mock_gramps_person.get_family_handle_list.return_value = ["fam1", "fam2"]

        mock_fam1 = Mock()
        mock_child1 = Mock(ref="child1")
        mock_child2 = Mock(ref="child2")
        mock_fam1.get_child_ref_list.return_value = [mock_child1, mock_child2]

        mock_fam2 = Mock()
        mock_child3 = Mock(ref="child3")
        mock_fam2.get_child_ref_list.return_value = [mock_child3]

        self.mock_db.get_family_from_handle.side_effect = [mock_fam1, mock_fam2]

        self.assertEqual(self.proxy.children_handles, ["child1", "child2", "child3"])

    def test_siblings_handles_excludes_self(self):
        # Proxy's own handle is "p123"
        self.mock_gramps_person.get_parent_family_handle_list.return_value = [
            "parent_fam"
        ]

        mock_fam = Mock()
        mock_self = Mock(ref="p123")
        mock_sibling = Mock(ref="sib456")
        mock_fam.get_child_ref_list.return_value = [mock_self, mock_sibling]

        self.mock_db.get_family_from_handle.return_value = mock_fam

        self.assertEqual(self.proxy.siblings_handles, ["sib456"])

    def test_event_years(self):
        mock_ref1 = Mock(ref="e1")
        mock_ref2 = Mock(ref="e2")
        self.mock_gramps_person.get_event_ref_list.return_value = [mock_ref1, mock_ref2]

        mock_event1 = Mock()
        mock_date1 = Mock()
        mock_date1.is_empty.return_value = False
        mock_date1.get_year.return_value = 1850
        mock_event1.get_date_object.return_value = mock_date1

        mock_event2 = Mock()
        mock_date2 = Mock()
        mock_date2.is_empty.return_value = True  # Empty date should be skipped
        mock_event2.get_date_object.return_value = mock_date2

        self.mock_db.get_event_from_handle.side_effect = [mock_event1, mock_event2]

        self.assertEqual(self.proxy.event_years, [1850])

    def test_given_name(self):
        mock_primary_name = Mock()
        mock_primary_name.get_first_name.return_value = "Ivan"
        self.mock_gramps_person.get_primary_name.return_value = mock_primary_name

        self.assertEqual(self.proxy.given_name, "Ivan")

    def test_siblings_returns_generator(self):
        """Test that siblings property returns a generator (lazy evaluation)."""
        self.mock_gramps_person.get_parent_family_handle_list.return_value = [
            "parent_fam"
        ]

        mock_fam = Mock()
        mock_self = Mock(ref="p123")
        mock_sibling = Mock(ref="sib456")
        mock_fam.get_child_ref_list.return_value = [mock_self, mock_sibling]

        self.mock_db.get_family_from_handle.return_value = mock_fam

        # siblings should return a generator, not a list
        siblings_gen = self.proxy.siblings
        self.assertNotIsInstance(siblings_gen, list)

        # Converting to list should work
        siblings_list = list(siblings_gen)
        self.assertEqual(len(siblings_list), 1)

    def test_siblings_yields_proxies(self):
        """Test that siblings yields GrampsPersonProxy objects."""
        self.mock_gramps_person.get_parent_family_handle_list.return_value = [
            "parent_fam"
        ]

        mock_fam = Mock()
        mock_self = Mock(ref="p123")
        mock_sibling1 = Mock(ref="sib1")
        mock_sibling2 = Mock(ref="sib2")
        mock_fam.get_child_ref_list.return_value = [
            mock_self,
            mock_sibling1,
            mock_sibling2,
        ]

        self.mock_db.get_family_from_handle.return_value = mock_fam

        # Mock the sibling persons
        mock_sibling_person1 = Mock()
        mock_sibling_person1.get_handle.return_value = "sib1"
        mock_sibling_person2 = Mock()
        mock_sibling_person2.get_handle.return_value = "sib2"

        self.mock_db.get_person_from_handle.side_effect = [
            mock_sibling_person1,
            mock_sibling_person2,
        ]

        siblings = list(self.proxy.siblings)
        self.assertEqual(len(siblings), 2)
        self.assertIsInstance(siblings[0], GrampsPersonProxy)
        self.assertIsInstance(siblings[1], GrampsPersonProxy)
        self.assertEqual(siblings[0].handle, "sib1")
        self.assertEqual(siblings[1].handle, "sib2")

    def test_siblings_handles_none_person(self):
        """Test that siblings handles None from get_person_from_handle gracefully."""
        self.mock_gramps_person.get_parent_family_handle_list.return_value = [
            "parent_fam"
        ]

        mock_fam = Mock()
        mock_self = Mock(ref="p123")
        mock_sibling = Mock(ref="sib456")
        mock_fam.get_child_ref_list.return_value = [mock_self, mock_sibling]

        self.mock_db.get_family_from_handle.return_value = mock_fam
        self.mock_db.get_person_from_handle.return_value = None  # Person not found

        siblings = list(self.proxy.siblings)
        self.assertEqual(len(siblings), 0)  # Should skip None values

    def test_siblings_empty(self):
        """Test that siblings returns empty generator when no siblings."""
        self.mock_gramps_person.get_parent_family_handle_list.return_value = []

        siblings = list(self.proxy.siblings)
        self.assertEqual(len(siblings), 0)


if __name__ == "__main__":
    unittest.main()

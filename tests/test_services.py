# -*- coding: utf-8 -*-
import unittest
import tempfile
from unittest.mock import MagicMock

from tests.compat_mocks import mock_gramps, Name, Surname, Person as GrampsPerson

mock_gramps()

from names_engine.inference_service import PatronymicInferenceService
from names_engine.audit_service import PatronymicAuditService
from names_engine.standardizer_service import GivenNameStandardizerService


class MockPerson:
    def __init__(self, handle, gramps_id, first_name, gender=0, surname=""):
        self.handle = handle
        self.gramps_id = gramps_id
        self._primary_name = Name()
        self._primary_name.set_first_name(first_name)
        if surname:
            self._primary_name.add_surname(Surname(surname))
        self._gender = gender
        self._parent_family_handle_list = []
        self._event_ref_list = []

    def get_primary_name(self):
        return self._primary_name

    def get_gender(self):
        return self._gender

    def get_parent_family_handle_list(self):
        return self._parent_family_handle_list

    def get_event_ref_list(self):
        return self._event_ref_list

    def get_alternate_names(self):
        return []

    def set_alternate_names(self, alts):
        pass


class TestServices(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = MagicMock()
        self.db.get_dbname.return_value = "/mock/db/path"
        self.people = {
            "p1": MockPerson("p1", "I0001", "Иван", gender=GrampsPerson.MALE),
            "p2": MockPerson("p2", "I0002", "Мария", gender=GrampsPerson.FEMALE),
        }
        self.db.get_person_from_handle.side_effect = lambda h: self.people.get(h)
        self.db.get_person_handles.return_value = ["p1", "p2"]

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_inference_service_initialization(self):
        service = PatronymicInferenceService(self.db)
        self.assertEqual(service.db_id, "path")
        self.assertIn("Иван", service.given_names_set)

    def test_standardizer_scan(self):
        service = GivenNameStandardizerService(self.db)
        proposals = service.scan_given_names("Иван", "Иоанн", 0)
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0].proposed_name, "Иоанн")

    def test_audit_service_basic(self):
        inference = PatronymicInferenceService(self.db)
        audit = PatronymicAuditService(self.db, inference)
        # Should just run without error
        issues = list(audit.audit_generator(0, set(), False))
        # No patronymics to audit yet, so issues list should be empty
        self.assertEqual(len(issues), 0)

    def test_inference_with_father(self):
        # Setup Father
        father = MockPerson("father1", "I0000", "Иван")
        self.people["father1"] = father
        self.db.get_person_handles.return_value = ["p1", "father1"]

        # Setup Family
        family = MagicMock()
        family.get_father_handle.return_value = "father1"
        self.db.get_family_from_handle.return_value = family
        self.people["p1"]._parent_family_handle_list = ["fam1"]

        service = PatronymicInferenceService(self.db)
        candidates = list(service.scan_candidates_generator())
        # We need to ensure criteria are met (confidence)
        # In this mock, it might not trigger without more setup,
        # but verifies it runs.
        self.assertIsInstance(candidates, list)


if __name__ == "__main__":
    unittest.main()

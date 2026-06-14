from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from name_processor.models.renamer import MatchMode
from name_processor.services.renamer import RenamerService


class TestRenamerService(unittest.TestCase):
    def test_regex_capture_group_single(self):
        """Test regex with single capture group using Python \1 syntax."""
        service = RenamerService()
        rule = service.create_config(MatchMode.REGEX, "А(.*)", r"О\1")

        person = MagicMock()
        person.handle = "handle1"
        person.gramps_id = "I0001"
        person.display_name = "Test Person"
        person.given_name = "Анна"

        result = service.evaluate_person(person, rule)

        self.assertIsNotNone(result)
        self.assertEqual(result.proposed_given_name, "Онна")

    def test_regex_capture_group_single_arkady(self):
        """Test regex with single capture group using Python \1 syntax for Аркадий."""
        service = RenamerService()
        rule = service.create_config(MatchMode.REGEX, "А(.*)", r"О\1")

        person = MagicMock()
        person.handle = "handle2"
        person.gramps_id = "I0002"
        person.display_name = "Test Person"
        person.given_name = "Аркадий"

        result = service.evaluate_person(person, rule)

        self.assertIsNotNone(result)
        self.assertEqual(result.proposed_given_name, "Оркадий")

    def test_regex_capture_group_multiple(self):
        """Test regex with multiple capture groups using Python \1, \2 syntax."""
        service = RenamerService()
        rule = service.create_config(MatchMode.REGEX, "(А)(.*)", r"О\2")

        person = MagicMock()
        person.handle = "handle3"
        person.gramps_id = "I0003"
        person.display_name = "Test Person"
        person.given_name = "Анна"

        result = service.evaluate_person(person, rule)

        self.assertIsNotNone(result)
        self.assertEqual(result.proposed_given_name, "Онна")

    def test_regex_no_capture_group(self):
        """Test regex without capture groups still works."""
        service = RenamerService()
        rule = service.create_config(MatchMode.REGEX, "Анна", "Анна Мария")

        person = MagicMock()
        person.handle = "handle4"
        person.gramps_id = "I0004"
        person.display_name = "Test Person"
        person.given_name = "Анна"

        result = service.evaluate_person(person, rule)

        self.assertIsNotNone(result)
        self.assertEqual(result.proposed_given_name, "Анна Мария")

    def test_regex_no_match(self):
        """Test regex that doesn't match returns None."""
        service = RenamerService()
        rule = service.create_config(MatchMode.REGEX, "Б(.*)", "О$1")

        person = MagicMock()
        person.handle = "handle5"
        person.gramps_id = "I0005"
        person.display_name = "Test Person"
        person.given_name = "Анна"

        result = service.evaluate_person(person, rule)

        self.assertIsNone(result)

    def test_exact_match(self):
        """Test exact match mode."""
        service = RenamerService()
        rule = service.create_config(MatchMode.EXACT, "Анна", "Анна Мария")

        person = MagicMock()
        person.handle = "handle6"
        person.gramps_id = "I0006"
        person.display_name = "Test Person"
        person.given_name = "Анна"

        result = service.evaluate_person(person, rule)

        self.assertIsNotNone(result)
        self.assertEqual(result.proposed_given_name, "Анна Мария")

    def test_substring_match(self):
        """Test substring match mode."""
        service = RenamerService()
        rule = service.create_config(MatchMode.SUBSTRING, "Анна", "Анна Мария")

        person = MagicMock()
        person.handle = "handle7"
        person.gramps_id = "I0007"
        person.display_name = "Test Person"
        person.given_name = "Анна Иванова"

        result = service.evaluate_person(person, rule)

        self.assertIsNotNone(result)
        self.assertEqual(result.proposed_given_name, "Анна Мария Иванова")

    def test_invalid_regex(self):
        """Test invalid regex is caught during config creation."""
        service = RenamerService()
        rule = service.create_config(MatchMode.REGEX, "[invalid", "replacement")

        self.assertFalse(rule.is_valid)
        self.assertIn("Invalid Regular Expression", rule.error_msg)

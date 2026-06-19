from __future__ import annotations

import unittest

from name_processor.models.person import Gender


class TestGenderEnum(unittest.TestCase):
    def test_gender_enum(self):
        self.assertEqual(Gender.MALE.value, "MALE")
        self.assertEqual(Gender.FEMALE.value, "FEMALE")
        self.assertEqual(Gender.UNKNOWN.value, "UNKNOWN")


if __name__ == "__main__":
    unittest.main()

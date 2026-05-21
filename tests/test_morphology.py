# -*- coding: utf-8 -*-

import unittest

from engine.morphology import generate_east_slavic_patronymic, SLAVIC_SURNAME_PATTERN

class TestEastSlavicMorphology(unittest.TestCase):

    def test_modern_formal_post_1917(self):
        year = 1950
        f = generate_east_slavic_patronymic

        # Hard stem
        self.assertEqual(f("Иван", "male", year), "Иванович")
        self.assertEqual(f("Иван", "female", year), "Ивановна")

        # Soft stem
        self.assertEqual(f("Игорь", "male", year), "Игоревич")
        self.assertEqual(f("Игорь", "female", year), "Игоревна")

        # Yod -ий ending
        self.assertEqual(f("Дмитрий", "male", year), "Дмитриевич")
        self.assertEqual(f("Василий", "male", year), "Васильевич")
        self.assertEqual(f("Василий", "female", year), "Васильевна")

        # Yod -ей ending
        self.assertEqual(f("Сергей", "male", year), "Сергеевич")
        self.assertEqual(f("Сергей", "female", year), "Сергеевна")

        # Contracted endings
        self.assertEqual(f("Илья", "male", year), "Ильич")
        self.assertEqual(f("Илья", "female", year), "Ильинична")
        self.assertEqual(f("Никита", "male", year), "Никитич")
        self.assertEqual(f("Никита", "female", year), "Никитична")

    def test_transitional_genitives_1861_1917(self):
        year = 1890
        f = generate_east_slavic_patronymic

        # Direct genitive suffix, no "сын/дочь"
        self.assertEqual(f("Сергей", "male", year), "Сергеев")
        self.assertEqual(f("Сергей", "female", year), "Сергеева")
        self.assertEqual(f("Никита", "male", year), "Никитин")
        self.assertEqual(f("Никита", "female", year), "Никитина")

    def test_pre_emancipation_pre_1861(self):
        year = 1830
        f = generate_east_slavic_patronymic

        # Genitive base + relational noun
        self.assertEqual(f("Иван", "male", year), "Иванов сын")
        self.assertEqual(f("Иван", "female", year), "Иванова дочь")

    def test_pre_reform_orthography_pre_1918(self):
        year = 1830
        f = generate_east_slavic_patronymic

        # Suffix with terminal 'ъ' and decimal 'і' before vowels
        self.assertEqual(f("Иванъ", "male", year, pre_reform_script=True), "Ивановъ сынъ")
        self.assertEqual(f("Дмитрій", "male", year, pre_reform_script=True), "Дмитріевъ сынъ")

    def test_gender_integer_mapping(self):
        year = 1950
        f = generate_east_slavic_patronymic

        # Support Gramps integer constants (1=male, 0=female)
        self.assertEqual(f("Иван", 1, year), "Иванович")
        self.assertEqual(f("Иван", 0, year), "Ивановна")

    def test_empty_and_invalid_inputs(self):
        f = generate_east_slavic_patronymic
        self.assertIsNone(f("", "male", 1950))
        self.assertIsNone(f("   ", "male", 1950))
        self.assertIsNone(f("Иван", "unknown", 1950))
        self.assertIsNone(f("Иван", 3, 1950))  # Invalid integer gender

    def test_western_names_handling(self):
        f = generate_east_slavic_patronymic
        # Verify robust handling of Latin names without crashing
        self.assertEqual(f("John", "male", 1950), "Johnович")
        self.assertEqual(f("John", "female", 1950), "Johnовна")
        self.assertEqual(f("William", "male", 1950), "Williamович")

    def test_slavic_surname_pattern_regex(self):
        # Surnames that MUST match (East Slavic patterns)
        matching_surnames = [
            "Иванов", "Ivanov",
            "Иванова", "Ivanova",
            "Сергеев", "Sergeev",
            "Сергеева", "Sergeeva",
            "Никитин", "Nikitin",
            "Никитина", "Nikitina",
            "Шевченко", "Shevchenko",
            "Клименко", "Klimenko",
            "Достоевский", "Dostoevsky",
            "Достоевская", "Dostoevskaya",
            "Корнейчук", "Korneychuk",
            "Гриценко"
        ]

        # Surnames that MUST NOT match (Polish, German, Western or non-Slavic)
        non_matching_surnames = [
            "Skladowska",      # Polish (avoiding "ska" false match bugs)
            "Kowalski",        # Polish (avoiding "ski" false match bugs)
            "Smith",           # English
            "Schmidt",         # German
            "Müller",          # German
            "John",            # Given name
            "Skladowski"       # Polish masculine
        ]

        for s in matching_surnames:
            self.assertTrue(
                SLAVIC_SURNAME_PATTERN.search(s) is not None,
                f"Expected surname '{s}' to match SLAVIC_SURNAME_PATTERN, but it did not."
            )

        for s in non_matching_surnames:
            self.assertFalse(
                SLAVIC_SURNAME_PATTERN.search(s) is not None,
                f"Expected surname '{s}' NOT to match SLAVIC_SURNAME_PATTERN, but it did."
            )


if __name__ == "__main__":
    unittest.main()
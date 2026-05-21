# -*- coding: utf-8 -*-

import unittest

from engine.morphology import generate_east_slavic_patronymic, SLAVIC_SURNAME_PATTERN

class TestEastSlavicMorphology(unittest.TestCase):

    def test_modern_formal_post_1917(self):
        year = 1950
        f = generate_east_slavic_patronymic

        # Hard stem
        self.assertEqual(f("Иван", True, year), "Иванович")
        self.assertEqual(f("Иван", False, year), "Ивановна")

        # Soft stem
        self.assertEqual(f("Игорь", True, year), "Игоревич")
        self.assertEqual(f("Игорь", False, year), "Игоревна")

        # Yod -ий ending
        self.assertEqual(f("Дмитрий", True, year), "Дмитриевич")
        self.assertEqual(f("Василий", True, year), "Васильевич")
        self.assertEqual(f("Василий", False, year), "Васильевна")

        # Yod -ей ending
        self.assertEqual(f("Сергей", True, year), "Сергеевич")
        self.assertEqual(f("Сергей", False, year), "Сергеевна")

        # Contracted endings
        self.assertEqual(f("Илья", True, year), "Ильич")
        self.assertEqual(f("Илья", False, year), "Ильинична")
        self.assertEqual(f("Никита", True, year), "Никитич")
        self.assertEqual(f("Никита", False, year), "Никитична")

    def test_transitional_genitives_1861_1917(self):
        year = 1890
        f = generate_east_slavic_patronymic

        # Direct genitive suffix, no "сын/дочь"
        self.assertEqual(f("Сергей", True, year), "Сергеев")
        self.assertEqual(f("Сергей", False, year), "Сергеева")
        self.assertEqual(f("Никита", True, year), "Никитин")
        self.assertEqual(f("Никита", False, year), "Никитина")

    def test_pre_emancipation_pre_1861(self):
        year = 1830
        f = generate_east_slavic_patronymic

        # Genitive base + relational noun
        self.assertEqual(f("Иван", True, year), "Иванов сын")
        self.assertEqual(f("Иван", False, year), "Иванова дочь")

    def test_pre_reform_orthography_pre_1918(self):
        year = 1830
        f = generate_east_slavic_patronymic

        # Suffix with terminal 'ъ' and decimal 'і' before vowels
        self.assertEqual(f("Иванъ", True, year, pre_reform_script=True), "Ивановъ сынъ")
        self.assertEqual(f("Дмитрій", True, year, pre_reform_script=True), "Дмитріевъ сынъ")

    def test_gender_integer_mapping(self):
        year = 1950
        f = generate_east_slavic_patronymic

        # Support Gramps integer constants (True=male, False=female)
        self.assertEqual(f("Иван", True, year), "Иванович")
        self.assertEqual(f("Иван", False, year), "Ивановна")

    def test_western_names_handling(self):
        year = 1950
        f = generate_east_slavic_patronymic

        # Verify robust handling of Latin names without crashing
        self.assertEqual(f("John", True, year), "Johnович")
        self.assertEqual(f("John", False, year), "Johnовна")
        self.assertEqual(f("William", True, year), "Williamович")

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
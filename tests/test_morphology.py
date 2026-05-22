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

    def test_pre_1917_possessives(self):
        year = 1890
        f = generate_east_slavic_patronymic

        # Direct genitive suffix, no "сын/дочь" text
        self.assertEqual(f("Сергей", True, year), "Сергеев")
        self.assertEqual(f("Сергей", False, year), "Сергеева")
        self.assertEqual(f("Никита", True, year), "Никитин")
        self.assertEqual(f("Никита", False, year), "Никитина")

    def test_pre_reform_orthography_pre_1918(self):
        year = 1890
        f = generate_east_slavic_patronymic

        # Suffix with terminal 'ъ' and decimal 'і' before vowels
        self.assertEqual(f("Иванъ", True, year, pre_reform_script=True), "Ивановъ")
        self.assertEqual(f("Дмитрій", True, year, pre_reform_script=True), "Дмитріевъ")

    def test_empty_and_invalid_inputs(self):
        f = generate_east_slavic_patronymic
        self.assertIsNone(f("", True, 1950))
        self.assertIsNone(f("   ", True, 1950))

    def test_western_names_handling(self):
        f = generate_east_slavic_patronymic
        # Verify robust handling of Latin names without crashing
        self.assertEqual(f("John", True, 1950), "Johnович")
        self.assertEqual(f("John", False, 1950), "Johnовна")
        self.assertEqual(f("William", True, 1950), "Williamович")

    def test_irregular_historical_names(self):
        f = generate_east_slavic_patronymic

        # 1. Fleet vowel dropped in "Павел"
        self.assertEqual(f("Павел", True, 1821), "Павлов")
        self.assertEqual(f("Павел", False, 1821), "Павлова")
        self.assertEqual(f("Павел", True, 1960), "Павлович")
        self.assertEqual(f("Павел", False, 1960), "Павловна")

        # 2. Fleet vowel dropped in "Лев"
        self.assertEqual(f("Лев", True, 1812), "Львов")
        self.assertEqual(f("Лев", False, 1812), "Львова")
        self.assertEqual(f("Лев", True, 1950), "Львович")
        self.assertEqual(f("Лев", False, 1950), "Львовна")

        # 3. Intrusive 'л' in "Яков" / "Иаков"
        self.assertEqual(f("Яков", True, 1803), "Яковлев")
        self.assertEqual(f("Яков", False, 1803), "Яковлева")
        self.assertEqual(f("Яков", True, 1920), "Яковлевич")
        self.assertEqual(f("Яков", False, 1920), "Яковлевна")
        self.assertEqual(f("Иаков", True, 1826), "Иаковлев")
        self.assertEqual(f("Иаков", False, 1826), "Иаковлева")

        # 4. Contraction in "Михаил"
        self.assertEqual(f("Михаил", True, 1812), "Михайлов")
        self.assertEqual(f("Михаил", False, 1812), "Михайлова")
        self.assertEqual(f("Михаил", True, 1950), "Михайлович")
        self.assertEqual(f("Михаил", False, 1950), "Михайловна")

        # 5. Spelling preservation in "Димитрий" vs. "Дмитрий"
        self.assertEqual(f("Димитрий", True, 1850), "Димитриев")
        self.assertEqual(f("Димитрий", True, 1950), "Димитриевич")
        self.assertEqual(f("Дмитрий", True, 1850), "Дмитриев")
        self.assertEqual(f("Дмитрий", True, 1950), "Дмитриевич")

    def test_slavic_surname_pattern_regex(self):
        # Surnames that MUST match (East Slavic patterns)
        matching_surnames = [
            "Иванов",
            "Ivanov",
            "Иванова",
            "Ivanova",
            "Сергеев",
            "Sergeev",
            "Сергеева",
            "Sergeeva",
            "Никитин",
            "Nikitin",
            "Никитина",
            "Nikitina",
            "Шевченко",
            "Shevchenko",
            "Клименко",
            "Klimenko",
            "Достоевский",
            "Dostoevsky",
            "Достоевская",
            "Dostoevskaya",
            "Корнейчук",
            "Korneychuk",
            "Гриценко",
        ]

        # Surnames that MUST NOT match (Polish, German, Western or non-Slavic)
        non_matching_surnames = [
            "Skladowska",  # Polish (avoiding "ska" false match bugs)
            "Kowalski",  # Polish (avoiding "ski" false match bugs)
            "Smith",  # English
            "Schmidt",  # German
            "Müller",  # German
            "John",  # Given name
            "Skladowski",  # Polish masculine
        ]

        for s in matching_surnames:
            self.assertTrue(
                SLAVIC_SURNAME_PATTERN.search(s) is not None,
                f"Expected surname '{s}' to match SLAVIC_SURNAME_PATTERN, but it did not.",
            )

        for s in non_matching_surnames:
            self.assertFalse(
                SLAVIC_SURNAME_PATTERN.search(s) is not None,
                f"Expected surname '{s}' NOT to match SLAVIC_SURNAME_PATTERN, but it did.",
            )


if __name__ == "__main__":
    unittest.main()

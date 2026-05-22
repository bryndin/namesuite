# -*- coding: utf-8 -*-

import unittest

from engine.morphology import generate_east_slavic_patronymic, SLAVIC_SURNAME_PATTERN


class TestEastSlavicMorphology(unittest.TestCase):
    def test_modern_formal_post_1917(self):
        year = 1950
        f = generate_east_slavic_patronymic

        test_cases = [
            # Hard stem
            ("Иван (male)", ("Иван", True, year), "Иванович"),
            ("Иван (female)", ("Иван", False, year), "Ивановна"),

            # Soft stem
            ("Игорь (male)", ("Игорь", True, year), "Игоревич"),
            ("Игорь (female)", ("Игорь", False, year), "Игоревна"),

            # Yod -ий ending
            ("Дмитрий (male)", ("Дмитрий", True, year), "Дмитриевич"),
            ("Василий (male)", ("Василий", True, year), "Васильевич"),
            ("Василий (female)", ("Василий", False, year), "Васильевна"),

            # Yod -ей ending
            ("Сергей (male)", ("Сергей", True, year), "Сергеевич"),
            ("Сергей (female)", ("Сергей", False, year), "Сергеевна"),

            # Contracted endings
            ("Илья (male)", ("Илья", True, year), "Ильич"),
            ("Илья (female)", ("Илья", False, year), "Ильинична"),
            ("Никита (male)", ("Никита", True, year), "Никитич"),
            ("Никита (female)", ("Никита", False, year), "Никитична"),
        ]

        failures = []
        for name, args, expected in test_cases:
            result = f(*args)
            if result != expected:
                failures.append(f"{name}: expected '{expected}', got '{result}'")

        if failures:
            self.fail("\n" + "\n".join(failures))

    def test_pre_1917_possessives(self):
        year = 1890
        f = generate_east_slavic_patronymic

        test_cases = [
            # Direct genitive suffix, no "сын/дочь" text
            ("Сергей (male)", ("Сергей", True, year), "Сергеев"),
            ("Сергей (female)", ("Сергей", False, year), "Сергеева"),
            ("Никита (male)", ("Никита", True, year), "Никитин"),
            ("Никита (female)", ("Никита", False, year), "Никитина"),
        ]

        failures = []
        for name, args, expected in test_cases:
            result = f(*args)
            if result != expected:
                failures.append(f"{name}: expected '{expected}', got '{result}'")

        if failures:
            self.fail("\n" + "\n".join(failures))

    def test_pre_reform_orthography_pre_1918(self):
        year = 1890
        f = generate_east_slavic_patronymic

        test_cases = [
            # Suffix with terminal 'ъ' and decimal 'і' before vowels
            ("Иванъ", ("Иванъ", True, year), "Ивановъ", {"pre_reform_script": True}),
            ("Дмитрій", ("Дмитрій", True, year), "Дмитріевъ", {"pre_reform_script": True}),
        ]

        failures = []
        for name, args, expected, kwargs in test_cases:
            result = f(*args, **kwargs)
            if result != expected:
                failures.append(f"{name}: expected '{expected}', got '{result}'")

        if failures:
            self.fail("\n" + "\n".join(failures))

    def test_empty_and_invalid_inputs(self):
        f = generate_east_slavic_patronymic

        test_cases = [
            ("empty string", ("", True, 1950), None),
            ("whitespace only", ("   ", True, 1950), None),
        ]

        failures = []
        for name, args, expected in test_cases:
            result = f(*args)
            if result != expected:
                failures.append(f"{name}: expected '{expected}', got '{result}'")

        if failures:
            self.fail("\n" + "\n".join(failures))

    def test_western_names_handling(self):
        f = generate_east_slavic_patronymic

        test_cases = [
            # Verify robust handling of Latin names without crashing
            ("John (male)", ("John", True, 1950), "Johnович"),
            ("John (female)", ("John", False, 1950), "Johnовна"),
            ("William (male)", ("William", True, 1950), "Williamович"),
        ]

        failures = []
        for name, args, expected in test_cases:
            result = f(*args)
            if result != expected:
                failures.append(f"{name}: expected '{expected}', got '{result}'")

        if failures:
            self.fail("\n" + "\n".join(failures))

    def test_irregular_historical_names(self):
        f = generate_east_slavic_patronymic

        test_cases = [
            # 1. Fleet vowel dropped in "Павел"
            ("Павел (male, 1821)", ("Павел", True, 1821), "Павлов"),
            ("Павел (female, 1821)", ("Павел", False, 1821), "Павлова"),
            ("Павел (male, 1960)", ("Павел", True, 1960), "Павлович"),
            ("Павел (female, 1960)", ("Павел", False, 1960), "Павловна"),

            # 2. Fleet vowel dropped in "Лев"
            ("Лев (male, 1812)", ("Лев", True, 1812), "Львов"),
            ("Лев (female, 1812)", ("Лев", False, 1812), "Львова"),
            ("Лев (male, 1950)", ("Лев", True, 1950), "Львович"),
            ("Лев (female, 1950)", ("Лев", False, 1950), "Львовна"),

            # 3. Intrusive 'л' in "Яков" / "Иаков"
            ("Яков (male, 1803)", ("Яков", True, 1803), "Яковлев"),
            ("Яков (female, 1803)", ("Яков", False, 1803), "Яковлева"),
            ("Яков (male, 1920)", ("Яков", True, 1920), "Яковлевич"),
            ("Яков (female, 1920)", ("Яков", False, 1920), "Яковлевна"),
            ("Иаков (male, 1826)", ("Иаков", True, 1826), "Иаковлев"),
            ("Иаков (female, 1826)", ("Иаков", False, 1826), "Иаковлева"),

            # 4. Contraction in "Михаил"
            ("Михаил (male, 1812)", ("Михаил", True, 1812), "Михайлов"),
            ("Михаил (female, 1812)", ("Михаил", False, 1812), "Михайлова"),
            ("Михаил (male, 1950)", ("Михаил", True, 1950), "Михайлович"),
            ("Михаил (female, 1950)", ("Михаил", False, 1950), "Михайловна"),

            # 5. Spelling preservation in "Димитрий" vs. "Дмитрий"
            ("Димитрий (male, 1850)", ("Димитрий", True, 1850), "Димитриев"),
            ("Димитрий (male, 1950)", ("Димитрий", True, 1950), "Димитриевич"),
            ("Дмитрий (male, 1850)", ("Дмитрий", True, 1850), "Дмитриев"),
            ("Дмитрий (male, 1950)", ("Дмитрий", True, 1950), "Дмитриевич"),
        ]

        failures = []
        for name, args, expected in test_cases:
            result = f(*args)
            if result != expected:
                failures.append(f"{name}: expected '{expected}', got '{result}'")

        if failures:
            self.fail("\n" + "\n".join(failures))

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

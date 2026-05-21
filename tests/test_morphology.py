# -*- coding: utf-8 -*-
"""
tests/test_morphology.py
"""

import unittest
from engine.morphology import generate_east_slavic_patronymic

class TestEastSlavicMorphology(unittest.TestCase):

    def test_modern_formal_post_1917(self):
        # Hard stem
        self.assertEqual(generate_east_slavic_patronymic("Иван", "male", 1950), "Иванович")
        self.assertEqual(generate_east_slavic_patronymic("Иван", "female", 1950), "Ивановна")

        # Soft stem
        self.assertEqual(generate_east_slavic_patronymic("Игорь", "male", 1950), "Игоревич")
        self.assertEqual(generate_east_slavic_patronymic("Игорь", "female", 1950), "Игоревна")

        # Yod -ий ending
        self.assertEqual(generate_east_slavic_patronymic("Дмитрий", "male", 1950), "Дмитриевич")
        self.assertEqual(generate_east_slavic_patronymic("Василий", "male", 1950), "Васильевич")
        self.assertEqual(generate_east_slavic_patronymic("Василий", "female", 1950), "Васильевна")

        # Yod -ей ending
        self.assertEqual(generate_east_slavic_patronymic("Сергей", "male", 1950), "Сергеевич")
        self.assertEqual(generate_east_slavic_patronymic("Сергей", "female", 1950), "Сергеевна")

        # Contracted endings
        self.assertEqual(generate_east_slavic_patronymic("Илья", "male", 1950), "Ильич")
        self.assertEqual(generate_east_slavic_patronymic("Илья", "female", 1950), "Ильинична")
        self.assertEqual(generate_east_slavic_patronymic("Никита", "male", 1950), "Никитич")
        self.assertEqual(generate_east_slavic_patronymic("Никита", "female", 1950), "Никитична")

    def test_transitional_genitives_1861_1917(self):
        # Direct genitive suffix, no "сын/дочь"
        self.assertEqual(generate_east_slavic_patronymic("Сергей", "male", 1890), "Сергеев")
        self.assertEqual(generate_east_slavic_patronymic("Сергей", "female", 1890), "Сергеева")
        self.assertEqual(generate_east_slavic_patronymic("Никита", "male", 1890), "Никитин")
        self.assertEqual(generate_east_slavic_patronymic("Никита", "female", 1890), "Никитина")

    def test_pre_emancipation_pre_1861(self):
        # Genitive base + relational noun
        self.assertEqual(generate_east_slavic_patronymic("Иван", "male", 1830), "Иванов сын")
        self.assertEqual(generate_east_slavic_patronymic("Иван", "female", 1830), "Иванова дочь")

    def test_pre_reform_orthography_pre_1918(self):
        # Suffix with terminal 'ъ' and decimal 'і' before vowels
        self.assertEqual(
            generate_east_slavic_patronymic("Иван", "male", 1830, pre_reform_script=True),
            "Ивановъ сынъ"
        )
        self.assertEqual(
            generate_east_slavic_patronymic("Дмитрий", "male", 1890, pre_reform_script=True),
            "Дмитріевъ"
        )

    def test_gender_integer_mapping(self):
        # Support Gramps integer constants (1=male, 0=female)
        self.assertEqual(generate_east_slavic_patronymic("Иван", 1, 1950), "Иванович")
        self.assertEqual(generate_east_slavic_patronymic("Иван", 0, 1950), "Ивановна")


if __name__ == "__main__":
    unittest.main()
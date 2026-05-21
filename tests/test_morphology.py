# -*- coding: utf-8 -*-

import unittest

from engine.morphology import generate_east_slavic_patronymic

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


if __name__ == "__main__":
    unittest.main()
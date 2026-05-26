# -*- coding: utf-8 -*-
"""
tests/test_rules.py

Headless logic tests for the individual validation rules.
"""

import unittest
from tests.compat_mocks import mock_gramps, Person

# Initialize mocks before importing engine modules
mock_gramps()

from names_engine.rule import RuleContext
from names_engine.constants import LOCALE_RU

# Import the rules
from names_engine.rules.gender_mismatch import ErrGenderMismatch
from names_engine.rules.lineage_mismatch import ErrLineageMismatch
from names_engine.rules.mixed_scripts import ErrMixedScripts
from names_engine.rules.modern_suffix_archaic_era import WarnModernSuffixArchaicEra
from names_engine.rules.archaic_suffix_modern_era import WarnArchaicSuffixModernEra
from names_engine.rules.missing_hard_sign import WarnMissingHardSign
from names_engine.rules.morphological_typo import WarnMorphologicalTypo


class TestLinterRules(unittest.TestCase):
    def test_err_gender_mismatch(self):
        rule = ErrGenderMismatch()

        # Test 1: Male person with Female suffix
        ctx_male_error = RuleContext(
            "p1", "Ивановна", "Иван", Person.MALE, 1950, LOCALE_RU
        )
        res_male = rule.evaluate(ctx_male_error)
        self.assertIsNotNone(res_male)
        self.assertEqual(res_male.suggested_string, "Иванович")

        # Test 2: Female person with Male suffix
        ctx_female_error = RuleContext(
            "p2", "Иванович", "Иван", Person.FEMALE, 1950, LOCALE_RU
        )
        res_female = rule.evaluate(ctx_female_error)
        self.assertIsNotNone(res_female)
        self.assertEqual(res_female.suggested_string, "Ивановна")

        # Test 3: Correct gender (Should pass/return None)
        ctx_pass = RuleContext("p3", "Иванович", "Иван", Person.MALE, 1950, LOCALE_RU)
        self.assertIsNone(rule.evaluate(ctx_pass))

        # Test 4: Correct female gender (Should pass/return None)
        ctx_pass = RuleContext("p4", "Ивановна", "Иван", Person.FEMALE, 1950, LOCALE_RU)
        self.assertIsNone(rule.evaluate(ctx_pass))

    def test_err_lineage_mismatch(self):
        rule = ErrLineageMismatch()

        # Test 1: Root doesn't match father's name
        ctx_mismatch = RuleContext(
            "p1", "Петрович", "Иван", Person.MALE, 1950, LOCALE_RU
        )
        res = rule.evaluate(ctx_mismatch)
        self.assertIsNotNone(res)
        self.assertEqual(res.suggested_string, "Иванович")

        # Test 2: Root matches
        ctx_match = RuleContext("p2", "Иванович", "Иван", Person.MALE, 1950, LOCALE_RU)
        self.assertIsNone(rule.evaluate(ctx_match))

    def test_err_mixed_scripts(self):
        rule = ErrMixedScripts()

        # Test 1: String containing Latin homoglyphs (Latin 'a' and 'o')
        latin_a = "\u0061"
        latin_o = "\u006f"
        mixed_string = f"Ив{latin_a}н{latin_o}вич"

        ctx = RuleContext("p1", mixed_string, "Иван", Person.MALE, 1950, LOCALE_RU)
        res = rule.evaluate(ctx)
        self.assertIsNotNone(res)
        # Should correct to pure Cyrillic
        self.assertEqual(res.suggested_string, "Иванович")

        # Test 2: Pure Cyrillic string
        ctx_pure = RuleContext("p2", "Иванович", "Иван", Person.MALE, 1950, LOCALE_RU)
        self.assertIsNone(rule.evaluate(ctx_pure))

    def test_warn_modern_suffix_archaic_era(self):
        rule = WarnModernSuffixArchaicEra()

        # Test 1: Pre-1918 record using modern "-ович"
        ctx = RuleContext("p1", "Иванович", "Иван", Person.MALE, 1850, LOCALE_RU)
        res = rule.evaluate(ctx)
        self.assertIsNotNone(res)
        # Should suggest pre-reform archaic genitive
        self.assertEqual(res.suggested_string, "Ивановъ")

        # Test 2: Post-1918 record (Rule should ignore)
        ctx_ignore = RuleContext("p2", "Иванович", "Иван", Person.MALE, 1950, LOCALE_RU)
        self.assertIsNone(rule.evaluate(ctx_ignore))

    def test_warn_archaic_suffix_modern_era(self):
        rule = WarnArchaicSuffixModernEra()

        # Test 1: Post-1918 record using archaic/informal "-ов"
        ctx = RuleContext("p1", "Иванов", "Иван", Person.MALE, 1950, LOCALE_RU)
        res = rule.evaluate(ctx)
        self.assertIsNotNone(res)
        # Should suggest modern formal
        self.assertEqual(res.suggested_string, "Иванович")

        # Test 2: Pre-1918 record (Rule should ignore)
        ctx_ignore = RuleContext("p2", "Иванов", "Иван", Person.MALE, 1850, LOCALE_RU)
        self.assertIsNone(rule.evaluate(ctx_ignore))

    def test_warn_missing_hard_sign(self):
        rule = WarnMissingHardSign()

        # Test 1: Pre-1918 RU record missing terminal hard sign
        ctx = RuleContext("p1", "Иванов", "Иван", Person.MALE, 1850, LOCALE_RU)
        res = rule.evaluate(ctx)
        self.assertIsNotNone(res)
        self.assertEqual(res.suggested_string, "Ивановъ")

        # Test 2: Post-1918 RU record missing hard sign (Should pass, as it's modern)
        ctx_modern = RuleContext("p2", "Иванов", "Иван", Person.MALE, 1950, LOCALE_RU)
        self.assertIsNone(rule.evaluate(ctx_modern))

    def test_warn_morphological_typo(self):
        rule = WarnMorphologicalTypo()

        # Test 1: Obvious typo with 3 duplicate letters
        ctx = RuleContext("p1", "Андрееевич", "Андрей", Person.MALE, 1950, LOCALE_RU)
        res = rule.evaluate(ctx)
        self.assertIsNotNone(res)
        self.assertEqual(res.suggested_string, "Андреевич")


if __name__ == "__main__":
    unittest.main()

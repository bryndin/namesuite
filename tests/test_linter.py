# -*- coding: utf-8 -*-
"""
tests/test_linter.py

Unit test suite for Phase 3 Quality & Consistency Auditing (The Linter)
for Gramps Patronymic Inference and Consistency checks.
"""

# ruff: noqa: E402

import sys
import unittest
from unittest.mock import MagicMock

# -------------------------------------------------------------------------
# Headless Decoupling Mocks
# Mock Gramps and GTK dependencies to ensure tests run 100% headlessly.
# -------------------------------------------------------------------------

# GTK & GLib mocks
gi_mock = MagicMock()
gi_repository_mock = MagicMock()
gtk_mock = MagicMock()
glib_mock = MagicMock()

gi_repository_mock.Gtk = gtk_mock
gi_repository_mock.GLib = glib_mock

sys.modules["gi"] = gi_mock
sys.modules["gi.repository"] = gi_repository_mock
sys.modules["gi.repository.Gtk"] = gtk_mock
sys.modules["gi.repository.GLib"] = glib_mock

# Create parent package mocks
gramps_mock = MagicMock()
gramps_gen_mock = MagicMock()
gramps_gen_db_mock = MagicMock()
gramps_gui_mock = MagicMock()
gramps_gui_plug_mock = MagicMock()
gramps_gui_dialog_mock = MagicMock()


class DbTxn:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


gramps_gen_db_mock.DbTxn = DbTxn


class MockToolBase:
    def __init__(self, *args, **kwargs):
        pass


class MockToolOptionsBase:
    def __init__(self, *args, **kwargs):
        pass


tool_module = MagicMock()
tool_module.Tool = MockToolBase
tool_module.ToolOptions = MockToolOptionsBase
gramps_gui_plug_mock.tool = tool_module

# Gramps localization mock
gen_const = MagicMock()
gen_const.GRAMPS_LOCALE.translation.gettext = lambda x: x


class NameOriginType:
    UNKNOWN = 0
    CUSTOM = 1
    PATRONYMIC = 5


class Surname:
    def __init__(self, surname_str="", origin=NameOriginType.UNKNOWN):
        self._surname = surname_str
        self._origin = origin

    def get_surname(self) -> str:
        return self._surname

    def get_origintype(self):
        return self._origin


gen_lib = MagicMock()
gen_lib.NameOriginType = NameOriginType
gen_lib.Surname = Surname

# Populate sys.modules for all required levels
sys.modules["gramps"] = gramps_mock
sys.modules["gramps.gen"] = gramps_gen_mock
sys.modules["gramps.gen.const"] = gen_const
sys.modules["gramps.gen.db"] = gramps_gen_db_mock
sys.modules["gramps.gen.lib"] = gen_lib
sys.modules["gramps.gui"] = gramps_gui_mock
sys.modules["gramps.gui.plug"] = gramps_gui_plug_mock
sys.modules["gramps.gui.dialog"] = gramps_gui_dialog_mock

# Now we can safely import components
from gramps.gen.lib import Surname, NameOriginType

from engine.compat import Person
from engine.linter import (
    PlaceCache,
    RuleEngine,
    BaseRule,
    ProposedChange,
)
from engine.rule import RuleContext
from engine.constants import LOCALE_RU, LOCALE_UK, LOCALE_UNIVERSAL
from engine.rule_utils import generate_pango_diff, swap_patronymic_gender
from engine.rules import (
    ErrGenderMismatch,
    ErrLineageMismatch,
    WarnModernSuffixArchaicEra,
    WarnArchaicSuffixModernEra,
    ErrMixedScripts,
    WarnMorphologicalTypo,
    WarnMissingHardSign,
)


class TestLinterEngineAndRules(unittest.TestCase):
    """Verifies core linter abstractions, context caching, and the default ruleset."""

    def test_pango_diff_generation(self):
        """Checks additions, deletions, replacements, and HTML safety in diffs."""
        # Simple swap
        diff1 = generate_pango_diff("Иванович", "Ивановна")
        self.assertIn("<span foreground='red'><s>ич</s></span>", diff1)
        self.assertIn("<span foreground='green'>на</span>", diff1)

        # XML escape safety check
        diff2 = generate_pango_diff("Иван <&>", "Иван <&>ович")
        self.assertIn("&amp;", diff2)
        self.assertIn("&lt;", diff2)
        self.assertIn("&gt;", diff2)

    def test_swap_patronymic_gender(self):
        """Verifies suffix-based swapping of grammatical genders."""
        # Modern: Female to Male
        self.assertEqual(swap_patronymic_gender("Ивановна", to_male=True), "Иванович")
        self.assertEqual(swap_patronymic_gender("Ильинична", to_male=True), "Ильич")

        # Modern: Male to Female
        self.assertEqual(swap_patronymic_gender("Иванович", to_male=False), "Ивановна")
        self.assertEqual(swap_patronymic_gender("Ильич", to_male=False), "Ильинична")

        # Archaic: Female to Male
        self.assertEqual(
            swap_patronymic_gender("Иванова", to_male=True, pre_reform=False), "Иванов"
        )
        self.assertEqual(
            swap_patronymic_gender("Иванова", to_male=True, pre_reform=True), "Ивановъ"
        )

    def test_place_session_lru_cache(self):
        """Verifies lazy place resolution and session-scoped LRU caching logic."""
        mock_db = MagicMock()
        mock_person = MagicMock()
        mock_event_ref = MagicMock()
        mock_event_ref.ref = "evt_01"
        mock_person.get_event_ref_list.return_value = [mock_event_ref]

        mock_event = MagicMock()
        mock_event.get_place_handle.return_value = "plc_01"

        mock_place = MagicMock()
        mock_place.get_title.return_value = "Sankt-Peterburg"

        mock_db.get_person_from_handle.return_value = mock_person
        mock_db.get_event_from_handle.return_value = mock_event
        mock_db.get_place_from_handle.return_value = mock_place

        # Create PlaceCache
        cache = PlaceCache(mock_db)

        # First call: triggers DB retrieval
        places1 = cache.get_places("p001")
        self.assertEqual(places1, ["Sankt-Peterburg"])
        self.assertEqual(mock_db.get_person_from_handle.call_count, 1)

        # Second call: fetches from cache directly, DB call count stays 1
        places2 = cache.get_places("p001")
        self.assertEqual(places2, ["Sankt-Peterburg"])
        self.assertEqual(mock_db.get_person_from_handle.call_count, 1)

        # Different person: triggers DB retrieval
        cache.get_places("p002")
        self.assertEqual(mock_db.get_person_from_handle.call_count, 2)

    def test_rule_err_gender_mismatch(self):
        """Checks ERR_GENDER_MISMATCH flags suffix conflicts correctly."""
        rule = ErrGenderMismatch()

        # 1. Male with female suffix (modern)
        ctx1 = RuleContext("p1", "Ивановна", "Иван", Person.MALE, 1950, LOCALE_RU)
        change1 = rule.evaluate(ctx1)
        self.assertIsNotNone(change1)
        self.assertEqual(change1.suggested_string, "Иванович")

        # 2. Female with male suffix (modern)
        ctx2 = RuleContext("p2", "Иванович", "Иван", Person.FEMALE, 1950, LOCALE_RU)
        change2 = rule.evaluate(ctx2)
        self.assertIsNotNone(change2)
        self.assertEqual(change2.suggested_string, "Ивановна")

        # 3. No mismatch
        ctx3 = RuleContext("p3", "Иванович", "Иван", Person.MALE, 1950, LOCALE_RU)
        self.assertIsNone(rule.evaluate(ctx3))

    def test_rule_err_lineage_mismatch(self):
        """Checks ERR_LINEAGE_MISMATCH flags base root mismatches correctly."""
        rule = ErrLineageMismatch()

        # 1. Father is Petr, patronymic is Ivanovich -> Mismatch
        ctx1 = RuleContext("p1", "Иванович", "Петр", Person.MALE, 1950, LOCALE_RU)
        change1 = rule.evaluate(ctx1)
        self.assertIsNotNone(change1)
        self.assertEqual(change1.suggested_string, "Петрович")

        # 2. Gender mismatch but same root -> Handled by gender rule, not lineage
        ctx2 = RuleContext("p2", "Петровна", "Петр", Person.MALE, 1950, LOCALE_RU)
        self.assertIsNone(rule.evaluate(ctx2))

        # 3. Correct lineage
        ctx3 = RuleContext("p3", "Петрович", "Петр", Person.MALE, 1950, LOCALE_RU)
        self.assertIsNone(rule.evaluate(ctx3))

    def test_rule_warn_modern_suffix_archaic_era(self):
        """Checks WARN_MODERN_SUFFIX_ARCHAIC_ERA detects modern suffix in pre-1918 records."""
        rule = WarnModernSuffixArchaicEra()

        # Pre-1918 (1850) and modern suffix
        ctx1 = RuleContext("p1", "Иванович", "Иван", Person.MALE, 1850, LOCALE_RU)
        change1 = rule.evaluate(ctx1)
        self.assertIsNotNone(change1)
        self.assertEqual(change1.suggested_string, "Ивановъ")

        # Post-1918 (1950) with modern suffix -> OK
        ctx2 = RuleContext("p2", "Иванович", "Иван", Person.MALE, 1950, LOCALE_RU)
        self.assertIsNone(rule.evaluate(ctx2))

    def test_rule_warn_archaic_suffix_modern_era(self):
        """Checks WARN_ARCHAIC_SUFFIX_MODERN_ERA detects archaic suffix in post-1918 records."""
        rule = WarnArchaicSuffixModernEra()

        # Post-1918 (1950) and archaic suffix
        ctx1 = RuleContext("p1", "Иванов", "Иван", Person.MALE, 1950, LOCALE_RU)
        change1 = rule.evaluate(ctx1)
        self.assertIsNotNone(change1)
        self.assertEqual(change1.suggested_string, "Иванович")

        # Pre-1918 (1850) with archaic suffix -> OK
        ctx2 = RuleContext("p2", "Ивановъ", "Иван", Person.MALE, 1850, LOCALE_RU)
        self.assertIsNone(rule.evaluate(ctx2))

    def test_rule_err_mixed_scripts(self):
        """Checks ERR_MIXED_SCRIPTS detects and normalizes mixed Latin/Cyrillic homoglyphs."""
        rule = ErrMixedScripts()

        # Latin 'o' (U+006F) inside Cyrillic "Петрович"
        mixed_str = "Петр" + "o" + "вич"
        ctx1 = RuleContext("p1", mixed_str, "", Person.MALE, 1950, LOCALE_RU)
        change1 = rule.evaluate(ctx1)
        self.assertIsNotNone(change1)
        self.assertEqual(change1.suggested_string, "Петрович")

        # Ensure 'o' is indeed Cyrillic (not Latin U+006F)
        self.assertNotIn("o", change1.suggested_string)

    def test_rule_warn_morphological_typo(self):
        """Checks WARN_MORPHOLOGICAL_TYPO catches repetitive character boundary typos."""
        rule = WarnMorphologicalTypo()

        # Extra repeats
        ctx1 = RuleContext("p1", "Андрееевич", "Андрей", Person.MALE, 1950, LOCALE_RU)
        change1 = rule.evaluate(ctx1)
        self.assertIsNotNone(change1)
        self.assertEqual(change1.suggested_string, "Андреевич")

    def test_rule_warn_missing_hard_sign(self):
        """Checks WARN_MISSING_HARD_SIGN flags missing terminal hard sign in pre-reform Russian."""
        rule = WarnMissingHardSign()

        # Pre-1918 (1850) missing 'ъ'
        ctx1 = RuleContext("p1", "Иванов", "", Person.MALE, 1850, LOCALE_RU)
        change1 = rule.evaluate(ctx1)
        self.assertIsNotNone(change1)
        self.assertEqual(change1.suggested_string, "Ивановъ")

    def test_rule_engine_dispatcher_and_routing(self):
        """Checks RuleEngine dynamic indexing and targeted locale/era execution routing."""
        engine = RuleEngine()

        # Verify 7 rules loaded dynamically
        self.assertEqual(len(engine.rules), 7)

        # Context for a Russian pre-reform individual
        ctx = RuleContext("p1", "Иванович", "Иван", Person.MALE, 1850, LOCALE_RU)

        # Evaluating this should trigger multiple rules: WarnModernSuffixArchaicEra, WarnMissingHardSign
        results = engine.evaluate_person(ctx)
        rule_ids = [r.rule_id for r, _ in results]

        self.assertIn("WARN_MODERN_SUFFIX_ARCHAIC_ERA", rule_ids)

    def test_engine_graceful_degradation(self):
        class MockCrashRule(BaseRule):
            @property
            def rule_id(self):
                return "CRASH_RULE"

            @property
            def severity(self):
                return "ERROR"

            @property
            def supported_locales(self):
                return {LOCALE_UNIVERSAL}

            @property
            def active_era(self):
                return (None, None)

            def evaluate(self, ctx):
                raise ValueError("Intentional crash for testing")

        class MockSafeRule(BaseRule):
            @property
            def rule_id(self):
                return "SAFE_RULE"

            @property
            def severity(self):
                return "INFO"

            @property
            def supported_locales(self):
                return {LOCALE_UNIVERSAL}

            @property
            def active_era(self):
                return (None, None)

            def evaluate(self, ctx):
                return ProposedChange("Safe", "SafeString", "SafeDiff")

        engine = RuleEngine(rules=[MockCrashRule(), MockSafeRule()])
        ctx = RuleContext("p1", "Test", "Test", Person.MALE, 1900, LOCALE_RU)

        # Should not raise an exception, and should return the result of the SafeRule
        results = engine.evaluate_person(ctx)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0].rule_id, "SAFE_RULE")

    def test_engine_routing_filters(self):
        class MockEraRule(BaseRule):
            @property
            def rule_id(self):
                return "ERA_RULE"

            @property
            def severity(self):
                return "ERROR"

            @property
            def supported_locales(self):
                return {LOCALE_UNIVERSAL}

            @property
            def active_era(self):
                return (1800, 1900)

            def evaluate(self, ctx):
                return ProposedChange("Hit", "Hit", "Hit")

        class MockLocaleRule(BaseRule):
            @property
            def rule_id(self):
                return "LOCALE_RULE"

            @property
            def severity(self):
                return "ERROR"

            @property
            def supported_locales(self):
                return {LOCALE_UK}

            @property
            def active_era(self):
                return (None, None)

            def evaluate(self, ctx):
                return ProposedChange("Hit", "Hit", "Hit")

        engine = RuleEngine(rules=[MockEraRule(), MockLocaleRule()])

        # Context: Year 1950 (Fails Era), Locale 'ru' (Fails Locale)
        ctx_miss = RuleContext("p1", "Test", "Test", Person.MALE, 1950, LOCALE_RU)
        self.assertEqual(len(engine.evaluate_person(ctx_miss)), 0)

        # Context: Year 1850 (Passes Era), Locale 'uk' (Passes Locale)
        ctx_hit = RuleContext("p2", "Test", "Test", Person.MALE, 1850, LOCALE_UK)
        self.assertEqual(len(engine.evaluate_person(ctx_hit)), 2)

    def test_engine_enabled_rules_toggle(self):
        engine = RuleEngine()  # Loads default 7 rules
        ctx = RuleContext(
            "p1", "Иванович", "Иван", Person.FEMALE, 1950, LOCALE_RU
        )  # Will trigger ErrGenderMismatch

        # Run with all rules
        all_results = engine.evaluate_person(ctx, enabled_rules=None)
        self.assertTrue(any(r[0].rule_id == "ERR_GENDER_MISMATCH" for r in all_results))

        # Run with gender rule explicitly disabled
        restricted_results = engine.evaluate_person(
            ctx, enabled_rules={"ERR_LINEAGE_MISMATCH"}
        )
        self.assertFalse(
            any(r[0].rule_id == "ERR_GENDER_MISMATCH" for r in restricted_results)
        )


# class TestLinterUIIntegration(unittest.TestCase):
#     """Verifies linter integration within the GTK Tool window and its event loops."""

#     def test_ui_audit_flow(self):
#         """Mocks GTK's GLib.idle_add event loop to execute and assert the database audit workflow."""
#         # Setup clean mocks
#         mock_db = MagicMock()
#         mock_db.get_dbname.return_value = "/mock/db/path"

#         mock_dbstate = MagicMock()
#         mock_dbstate.db = mock_db

#         # Mock Person with a gender mismatch
#         person = MagicMock()
#         person.handle = "p_001"
#         person.gramps_id = "I0001"
#         person.get_gender.return_value = Person.MALE
#         person.get_event_ref_list.return_value = []

#         primary_name = MagicMock()
#         primary_name.get_regular_name.return_value = "Иван Ивановна"

#         # Existing patronymic Surname object
#         patronymic_surname = Surname("Ивановна", NameOriginType.PATRONYMIC)
#         primary_name.get_surname_list.return_value = [patronymic_surname]
#         person.get_primary_name.return_value = primary_name

#         # Father link
#         person.get_parent_family_handle_list.return_value = ["f_001"]
#         family = MagicMock()
#         family.get_father_handle.return_value = "father_001"

#         father = MagicMock()
#         father.get_primary_name().get_first_name.return_value = "Иван"
#         father.get_event_ref_list.return_value = []

#         # Mock DB returns
#         mock_db.get_person_handles.return_value = ["p_001"]
#         mock_db.get_person_from_handle.side_effect = lambda h: {
#             "p_001": person,
#             "father_001": father,
#         }.get(h)
#         mock_db.get_family_from_handle.return_value = family

#         # Instantiate Tool
#         tool = InferPatronymicsTool(mock_dbstate, MagicMock(), MagicMock(), "TestTool")
#         tool.audit_scope_combo.get_active.return_value = 0

#         # Trigger the audit click event
#         tool.on_audit_clicked(None)

#         # Since GLib.idle_add is mocked in headless, manually capture and run the callback!
#         import patronymics_tool

#         glib_ref = getattr(patronymics_tool, "GLib", None)
#         self.assertTrue(glib_ref is not None)
#         self.assertTrue(glib_ref.idle_add.called)
#         idle_callback = glib_ref.idle_add.call_args[0][0]

#         # Run loop to completion
#         keep_going = True
#         while keep_going:
#             keep_going = idle_callback()

#         print("MOCK DEBUG - audit_store len:", len(tool.audit_store))
#         print(
#             "MOCK DEBUG - person primary_name regular name:",
#             person.get_primary_name().get_regular_name(),
#         )
#         print(
#             "MOCK DEBUG - get_patronymic_value:",
#             repr(get_patronymic_value(person.get_primary_name())),
#         )
#         print(
#             "MOCK DEBUG - has_patronymic_surname:",
#             has_patronymic_surname(person.get_primary_name()),
#         )
#         for row in tool.audit_store:
#             print("MOCK DEBUG - row:", row)

#         self.fail("Dummy fail to inspect stdout")


    def test_linter_handles_none_reference_year(self):
        """Verifies that all linter rules handle None reference year without crashing."""
        engine = RuleEngine()
        # Context with reference_year = None
        ctx = RuleContext("p1", "Иванович", "Иван", Person.MALE, None, LOCALE_RU)

        # This should not raise TypeError
        try:
            engine.evaluate_person(ctx)
        except TypeError as e:
            self.fail(f"evaluate_person raised TypeError with reference_year=None: {e}")

if __name__ == "__main__":
    unittest.main()

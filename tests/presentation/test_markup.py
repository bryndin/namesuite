import unittest
from name_processor.presentation.markup import (
    pango_escape,
    generate_pango_diff,
    format_confidence,
)


class TestPangoEscape(unittest.TestCase):
    def test_escapes_ampersand(self):
        self.assertEqual(pango_escape("AT&T"), "AT&amp;T")

    def test_escapes_less_than(self):
        self.assertEqual(pango_escape("a<b"), "a&lt;b")

    def test_escapes_greater_than(self):
        self.assertEqual(pango_escape("a>b"), "a&gt;b")

    def test_escapes_all_special_chars(self):
        self.assertEqual(pango_escape("<a&b>"), "&lt;a&amp;b&gt;")


class TestGeneratePangoDiff(unittest.TestCase):
    def test_old_to_new_diff(self):
        self.assertEqual(
            generate_pango_diff("Иванович", "Ивановна"),
            "Иванович → <span weight='bold'>Ивановна</span>",
        )

    def test_empty_old_bold_new(self):
        self.assertEqual(
            generate_pango_diff("", "Ивановна"),
            "<span weight='bold'>Ивановна</span>",
        )

    def test_empty_new_old_only(self):
        self.assertEqual(generate_pango_diff("Иванович", ""), "Иванович")

    def test_both_empty(self):
        self.assertEqual(generate_pango_diff("", ""), "")

    def test_xml_escaping_in_diff(self):
        self.assertEqual(
            generate_pango_diff("<old>", "<new>"),
            "&lt;old&gt; → <span weight='bold'>&lt;new&gt;</span>",
        )


class TestFormatConfidence(unittest.TestCase):
    def test_zero_confidence(self):
        self.assertEqual(format_confidence(0.0), "0%")

    def test_half_confidence(self):
        self.assertEqual(format_confidence(0.5), "50%")

    def test_full_confidence(self):
        self.assertEqual(format_confidence(1.0), "100%")

    def test_fractional_confidence(self):
        self.assertEqual(format_confidence(0.75), "75%")

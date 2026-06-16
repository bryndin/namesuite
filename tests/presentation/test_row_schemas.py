import unittest
from name_processor.presentation.row_schemas import GivenRowData, AuditRowData


class TestGivenRowData(unittest.TestCase):
    def test_instantiation(self):
        row = GivenRowData(
            checkbox=True,
            gramps_id="I001",
            display_name="John Doe",
            current="John",
            proposed="Jane",
            alt_action="PRESERVE",
            handle="handle1",
        )
        self.assertEqual(row.gramps_id, "I001")

    def test_field_order(self):
        fields = GivenRowData._fields
        self.assertEqual(fields[0], "checkbox")
        self.assertEqual(fields[1], "gramps_id")
        self.assertEqual(fields[2], "display_name")
        self.assertEqual(fields[3], "current")
        self.assertEqual(fields[4], "proposed")
        self.assertEqual(fields[5], "alt_action")
        self.assertEqual(fields[6], "handle")

    def test_immutability(self):
        row = GivenRowData(
            checkbox=True,
            gramps_id="I001",
            display_name="John Doe",
            current="John",
            proposed="Jane",
            alt_action="PRESERVE",
            handle="handle1",
        )
        with self.assertRaises(AttributeError):
            row.gramps_id = "I002"

    def test_replace_method(self):
        row = GivenRowData(
            checkbox=True,
            gramps_id="I001",
            display_name="John Doe",
            current="John",
            proposed="Jane",
            alt_action="PRESERVE",
            handle="handle1",
        )
        new_row = row._replace(checkbox=False)
        self.assertEqual(new_row.checkbox, False)
        self.assertEqual(new_row.gramps_id, "I001")


class TestAuditRowData(unittest.TestCase):
    def test_instantiation(self):
        row = AuditRowData(
            checkbox=True,
            display_name="John Doe",
            gramps_id="I001",
            father_name="Father",
            current_patronymic="ovich",
            diff_markup="old → new",
            confidence="75%",
            ref_year="1900",
            rule_id="RULE1",
            handle="handle1",
            suggested_string="new",
            explanation="test",
        )
        self.assertEqual(row.gramps_id, "I001")

    def test_field_order(self):
        fields = AuditRowData._fields
        self.assertEqual(fields[0], "checkbox")
        self.assertEqual(fields[1], "display_name")
        self.assertEqual(fields[2], "gramps_id")
        self.assertEqual(fields[3], "father_name")
        self.assertEqual(fields[4], "current_patronymic")
        self.assertEqual(fields[5], "diff_markup")
        self.assertEqual(fields[6], "confidence")
        self.assertEqual(fields[7], "ref_year")
        self.assertEqual(fields[8], "rule_id")
        self.assertEqual(fields[9], "handle")
        self.assertEqual(fields[10], "suggested_string")
        self.assertEqual(fields[11], "explanation")

    def test_immutability(self):
        row = AuditRowData(
            checkbox=True,
            display_name="John Doe",
            gramps_id="I001",
            father_name="Father",
            current_patronymic="ovich",
            diff_markup="old → new",
            confidence="75%",
            ref_year="1900",
            rule_id="RULE1",
            handle="handle1",
            suggested_string="new",
            explanation="test",
        )
        with self.assertRaises(AttributeError):
            row.gramps_id = "I002"

    def test_replace_method(self):
        row = AuditRowData(
            checkbox=True,
            display_name="John Doe",
            gramps_id="I001",
            father_name="Father",
            current_patronymic="ovich",
            diff_markup="old → new",
            confidence="75%",
            ref_year="1900",
            rule_id="RULE1",
            handle="handle1",
            suggested_string="new",
            explanation="test",
        )
        new_row = row._replace(checkbox=False)
        self.assertEqual(new_row.checkbox, False)
        self.assertEqual(new_row.gramps_id, "I001")

# -*- coding: utf-8 -*-
"""
tests/test_logging.py
"""

import os
import unittest
import tempfile
from pat_engine.logging import InferenceLogManager, generate_execution_id


class TestInferenceLogging(unittest.TestCase):
    def setUp(self):
        # Create a isolated temporary directory for testing filesystem operations
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_id = "test_db_60a5d9"
        self.manager = InferenceLogManager(self.db_id, log_dir=self.temp_dir.name)

    def tearDown(self):
        # Clean up directory resources
        self.temp_dir.cleanup()

    def test_log_file_path(self):
        expected_path = os.path.join(self.temp_dir.name, f"{self.db_id}.json")
        self.assertEqual(self.manager.log_filepath, expected_path)

    def test_empty_log_initialization(self):
        # File should not exist initially
        self.assertFalse(os.path.exists(self.manager.log_filepath))

        log_data = self.manager.load_log()
        self.assertEqual(log_data["database_id"], self.db_id)
        self.assertEqual(log_data["executions"], [])

    def test_log_execution_and_retrieval(self):
        exec_id = generate_execution_id()
        plugin_id = "east_slavic_patronymic"

        changes = [
            {
                "person_handle": "p1",
                "name_handle": "n1",
                "original_value": "",
                "inferred_value": "Иванович",
                "father_handle": "f1",
                "reference_year": 1920,
                "pre_reform": False,
                "confidence_score": 0.95,
                "applied_heuristics": ["DEATH_YEAR_POST_1918"],
            }
        ]

        self.manager.log_execution(exec_id, plugin_id, changes)

        # File should now exist
        self.assertTrue(os.path.exists(self.manager.log_filepath))

        # Retrieve runs
        runs = self.manager.get_executions()
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["execution_id"], exec_id)
        self.assertEqual(runs[0]["plugin_id"], plugin_id)
        self.assertEqual(runs[0]["changes"], changes)

        # Retrieve specific run
        run_details = self.manager.get_execution(exec_id)
        self.assertIsNotNone(run_details)
        self.assertEqual(run_details["execution_id"], exec_id)

    def test_multiple_executions_ordering(self):
        exec_1 = "exec_1_first"
        exec_2 = "exec_2_second"

        self.manager.log_execution(exec_1, "p_id", [])
        self.manager.log_execution(exec_2, "p_id", [])

        runs = self.manager.get_executions()
        self.assertEqual(len(runs), 2)
        # Latest runs must be prepended at index 0
        self.assertEqual(runs[0]["execution_id"], exec_2)
        self.assertEqual(runs[1]["execution_id"], exec_1)

    def test_remove_execution(self):
        exec_1 = "exec_to_keep"
        exec_2 = "exec_to_remove"

        self.manager.log_execution(exec_1, "p_id", [])
        self.manager.log_execution(exec_2, "p_id", [])

        self.assertTrue(self.manager.remove_execution(exec_2))

        runs = self.manager.get_executions()
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["execution_id"], exec_1)
        self.assertFalse(self.manager.remove_execution("invalid_id"))


if __name__ == "__main__":
    unittest.main()

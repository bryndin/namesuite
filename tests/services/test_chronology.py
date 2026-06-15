from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from name_processor.services.chronology import ChronologyService
from name_processor.protocols.chronology import ChronologyRepository, ChronologySubject


class TestChronologyService(unittest.TestCase):
    def setUp(self):
        self.mock_repo = MagicMock(spec=ChronologyRepository)
        self.service = ChronologyService(self.mock_repo)

    def test_update_median_year_with_valid_years(self):
        """Test update_median_year calculates median correctly."""
        years = [1800, 1850, 1900, 1950, 2000]
        result = self.service.update_median_year(years)

        self.assertEqual(result, 1900)
        self.assertEqual(self.service._db_median_year, 1900)

    def test_update_median_year_with_even_number_of_years(self):
        """Test update_median_year with even number of years (upper median)."""
        years = [1800, 1850, 1900, 1950]
        result = self.service.update_median_year(years)

        # For even length, returns upper middle element (index 2)
        self.assertEqual(result, 1900)
        self.assertEqual(self.service._db_median_year, 1900)

    def test_update_median_year_with_unsorted_years(self):
        """Test update_median_year sorts years before calculating median."""
        years = [1950, 1800, 2000, 1850, 1900]
        result = self.service.update_median_year(years)

        self.assertEqual(result, 1900)
        self.assertEqual(self.service._db_median_year, 1900)

    def test_update_median_year_with_empty_list(self):
        """Test update_median_year returns None for empty list."""
        result = self.service.update_median_year([])

        self.assertIsNone(result)
        self.assertIsNone(self.service._db_median_year)

    def test_update_median_year_with_none(self):
        """Test update_median_year returns None when years is None."""
        result = self.service.update_median_year(None)

        self.assertIsNone(result)
        self.assertIsNone(self.service._db_median_year)

    def test_update_median_year_resets_previous_value(self):
        """Test update_median_year resets previous median before calculating new one."""
        # Set an initial median
        self.service._db_median_year = 1900

        # Update with new years
        years = [2000, 2010, 2020]
        result = self.service.update_median_year(years)

        self.assertEqual(result, 2010)
        self.assertEqual(self.service._db_median_year, 2010)

    def test_set_db_median_year(self):
        """Test set_db_median_year sets the median year directly."""
        self.service.set_db_median_year(1950)

        self.assertEqual(self.service._db_median_year, 1950)

    def test_estimate_reference_year_with_no_person(self):
        """Test estimate_reference_year returns None when person not found."""
        self.mock_repo.get_chronology_subject.return_value = None

        result = self.service.estimate_reference_year("person1")

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()

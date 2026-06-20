from __future__ import annotations

import unittest

from name_processor.repositories.entity_cache import EntityCache, _MISSING


class TestEntityCache(unittest.TestCase):
    def setUp(self):
        self.cache = EntityCache()

    def test_get_returns_missing_for_uncached_handle(self):
        """Verify sentinel returned for never-queried handle."""
        result = self.cache.get_person("uncached_handle")
        self.assertIs(result, _MISSING)

    def test_put_and_get_returns_cached_object(self):
        """Store → retrieve round-trip."""
        mock_person = object()
        self.cache.put_person("handle1", mock_person)
        result = self.cache.get_person("handle1")
        self.assertIs(result, mock_person)

    def test_put_none_caches_negative_lookup(self):
        """Store None → retrieve returns None, not sentinel."""
        self.cache.put_person("handle1", None)
        result = self.cache.get_person("handle1")
        self.assertIsNone(result)
        self.assertIsNot(result, _MISSING)

    def test_invalidate_removes_entry(self):
        """Invalidate → subsequent get returns sentinel."""
        mock_person = object()
        self.cache.put_person("handle1", mock_person)
        self.cache.invalidate_person("handle1")
        result = self.cache.get_person("handle1")
        self.assertIs(result, _MISSING)

    def test_invalidate_nonexistent_is_noop(self):
        """Invalidating uncached handle does not raise."""
        # Should not raise an exception
        self.cache.invalidate_person("nonexistent_handle")

    def test_clear_persons_only_clears_persons(self):
        """Family and event caches unaffected."""
        mock_person = object()
        mock_family = object()
        mock_event = object()

        self.cache.put_person("p1", mock_person)
        self.cache.put_family("f1", mock_family)
        self.cache.put_event("e1", mock_event)

        self.cache.clear_persons()

        self.assertIs(self.cache.get_person("p1"), _MISSING)
        self.assertIs(self.cache.get_family("f1"), mock_family)
        self.assertIs(self.cache.get_event("e1"), mock_event)

    def test_clear_all_clears_everything(self):
        """All three caches emptied."""
        mock_person = object()
        mock_family = object()
        mock_event = object()

        self.cache.put_person("p1", mock_person)
        self.cache.put_family("f1", mock_family)
        self.cache.put_event("e1", mock_event)

        self.cache.clear_all()

        self.assertIs(self.cache.get_person("p1"), _MISSING)
        self.assertIs(self.cache.get_family("f1"), _MISSING)
        self.assertIs(self.cache.get_event("e1"), _MISSING)

    def test_person_count_reflects_cache_state(self):
        """Count tracks puts and invalidations."""
        self.assertEqual(self.cache.person_count, 0)

        self.cache.put_person("p1", object())
        self.assertEqual(self.cache.person_count, 1)

        self.cache.put_person("p2", object())
        self.assertEqual(self.cache.person_count, 2)

        self.cache.invalidate_person("p1")
        self.assertEqual(self.cache.person_count, 1)

    def test_family_operations(self):
        """Family cache operations work identically to person."""
        mock_family = object()
        self.cache.put_family("f1", mock_family)
        result = self.cache.get_family("f1")
        self.assertIs(result, mock_family)

        self.cache.invalidate_family("f1")
        result = self.cache.get_family("f1")
        self.assertIs(result, _MISSING)

    def test_event_operations(self):
        """Event cache operations work identically to person."""
        mock_event = object()
        self.cache.put_event("e1", mock_event)
        result = self.cache.get_event("e1")
        self.assertIs(result, mock_event)

        self.cache.invalidate_event("e1")
        result = self.cache.get_event("e1")
        self.assertIs(result, _MISSING)

    def test_family_count_reflects_cache_state(self):
        """Family count tracks puts and invalidations."""
        self.assertEqual(self.cache.family_count, 0)

        self.cache.put_family("f1", object())
        self.assertEqual(self.cache.family_count, 1)

        self.cache.put_family("f2", object())
        self.assertEqual(self.cache.family_count, 2)

        self.cache.invalidate_family("f1")
        self.assertEqual(self.cache.family_count, 1)

    def test_event_count_reflects_cache_state(self):
        """Event count tracks puts and invalidations."""
        self.assertEqual(self.cache.event_count, 0)

        self.cache.put_event("e1", object())
        self.assertEqual(self.cache.event_count, 1)

        self.cache.put_event("e2", object())
        self.assertEqual(self.cache.event_count, 2)

        self.cache.invalidate_event("e1")
        self.assertEqual(self.cache.event_count, 1)

    def test_clear_families_only_clears_families(self):
        """Person and event caches unaffected."""
        mock_person = object()
        mock_family = object()
        mock_event = object()

        self.cache.put_person("p1", mock_person)
        self.cache.put_family("f1", mock_family)
        self.cache.put_event("e1", mock_event)

        self.cache.clear_families()

        self.assertIs(self.cache.get_person("p1"), mock_person)
        self.assertIs(self.cache.get_family("f1"), _MISSING)
        self.assertIs(self.cache.get_event("e1"), mock_event)

    def test_clear_events_only_clears_events(self):
        """Person and family caches unaffected."""
        mock_person = object()
        mock_family = object()
        mock_event = object()

        self.cache.put_person("p1", mock_person)
        self.cache.put_family("f1", mock_family)
        self.cache.put_event("e1", mock_event)

        self.cache.clear_events()

        self.assertIs(self.cache.get_person("p1"), mock_person)
        self.assertIs(self.cache.get_family("f1"), mock_family)
        self.assertIs(self.cache.get_event("e1"), _MISSING)


if __name__ == "__main__":
    unittest.main()

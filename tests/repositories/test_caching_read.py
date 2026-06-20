from __future__ import annotations

import unittest
from unittest.mock import Mock

from name_processor.repositories.entity_cache import EntityCache
from name_processor.repositories.caching_read import CachingReadRepository


class TestCachingReadRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_inner = Mock()
        self.cache = EntityCache()
        self.repo = CachingReadRepository(self.mock_inner, self.cache)

    def test_get_person_cache_miss_delegates_to_inner(self) -> None:
        """First call delegates to inner repo and caches the result."""
        mock_raw_person = Mock()
        self.mock_inner._get_person_from_handle.return_value = mock_raw_person

        # Miss
        result = self.repo.get_person("handle1")
        self.assertIsNotNone(result)
        self.mock_inner._get_person_from_handle.assert_called_once_with("handle1")
        self.assertEqual(self.cache.person_count, 1)

    def test_get_person_cache_hit_does_not_delegate(self) -> None:
        """Second call returns cached; inner not called again."""
        mock_raw_person = Mock()
        self.mock_inner._get_person_from_handle.return_value = mock_raw_person

        # First call (miss)
        self.repo.get_person("handle1")
        self.mock_inner._get_person_from_handle.reset_mock()

        # Second call (hit)
        result = self.repo.get_person("handle1")
        self.assertIsNotNone(result)
        self.mock_inner._get_person_from_handle.assert_not_called()

    def test_get_person_none_is_cached(self) -> None:
        """Invalid handle is cached as None; inner called only once."""
        self.mock_inner._get_person_from_handle.return_value = None

        # First call (miss)
        result1 = self.repo.get_person("bad_handle")
        self.assertIsNone(result1)
        self.mock_inner._get_person_from_handle.assert_called_once_with("bad_handle")
        self.mock_inner._get_person_from_handle.reset_mock()

        # Second call (hit None)
        result2 = self.repo.get_person("bad_handle")
        self.assertIsNone(result2)
        self.mock_inner._get_person_from_handle.assert_not_called()

    def test_get_raw_person_uses_cache(self) -> None:
        """get_raw_person shares cache with get_person."""
        mock_raw_person = Mock()
        self.mock_inner._get_person_from_handle.return_value = mock_raw_person

        # First call via get_raw_person (miss)
        raw_result = self.repo.get_raw_person("handle1")
        self.assertEqual(raw_result, mock_raw_person)
        self.mock_inner._get_person_from_handle.assert_called_once_with("handle1")
        self.mock_inner._get_person_from_handle.reset_mock()

        # Second call via get_person (hit)
        proxy_result = self.repo.get_person("handle1")
        self.assertIsNotNone(proxy_result)
        self.mock_inner._get_person_from_handle.assert_not_called()

    def test_get_family_cache_through(self) -> None:
        """Family caching works cache-through."""
        mock_family = Mock()
        self.mock_inner._get_family_from_handle.return_value = mock_family

        # Miss
        res1 = self.repo.get_family("fam1")
        self.assertEqual(res1, mock_family)
        self.mock_inner._get_family_from_handle.assert_called_once_with("fam1")
        self.mock_inner._get_family_from_handle.reset_mock()

        # Hit
        res2 = self.repo.get_family("fam1")
        self.assertEqual(res2, mock_family)
        self.mock_inner._get_family_from_handle.assert_not_called()

    def test_get_event_cache_through(self) -> None:
        """Event caching works cache-through."""
        mock_event = Mock()
        self.mock_inner._get_event_from_handle.return_value = mock_event

        # Miss
        res1 = self.repo.get_event("evt1")
        self.assertEqual(res1, mock_event)
        self.mock_inner._get_event_from_handle.assert_called_once_with("evt1")
        self.mock_inner._get_event_from_handle.reset_mock()

        # Hit
        res2 = self.repo.get_event("evt1")
        self.assertEqual(res2, mock_event)
        self.mock_inner._get_event_from_handle.assert_not_called()

    def test_get_father_handle_caches_person_and_family(self) -> None:
        """Relationship method populates both caches."""
        mock_person = Mock()
        mock_person.get_parent_family_handle_list.return_value = ["fam1"]
        mock_family = Mock()
        mock_family.get_father_handle.return_value = "father1"

        self.mock_inner._get_person_from_handle.return_value = mock_person
        self.mock_inner._get_family_from_handle.return_value = mock_family

        # Get father handle
        father_h = self.repo.get_father_handle("child1")
        self.assertEqual(father_h, "father1")

        # Verify person and family cached
        self.assertEqual(self.cache.person_count, 1)
        self.assertEqual(self.cache.family_count, 1)

    def test_get_siblings_handles_populates_cache(self) -> None:
        """Multiple entities cached during traversal."""
        mock_person = Mock()
        mock_person.get_parent_family_handle_list.return_value = ["fam1"]
        mock_family = Mock()
        mock_ref1 = Mock()
        mock_ref1.ref = "person1"
        mock_ref2 = Mock()
        mock_ref2.ref = "sibling1"
        mock_family.get_child_ref_list.return_value = [mock_ref1, mock_ref2]

        self.mock_inner._get_person_from_handle.return_value = mock_person
        self.mock_inner._get_family_from_handle.return_value = mock_family

        siblings = self.repo.get_siblings_handles("person1")
        self.assertEqual(siblings, ["sibling1"])

        # Check caches: self (person1) and family (fam1) should be cached
        # sibling1's handle list lookup is done via family child refs, sibling1 person is NOT fetched yet
        self.assertEqual(self.cache.person_count, 1)
        self.assertEqual(self.cache.family_count, 1)

    def test_iter_all_persons_populates_cache(self) -> None:
        """Full iteration fills cache."""
        self.mock_inner.get_all_person_handles.return_value = ["p1", "p2"]
        mock_p1 = Mock()
        mock_p2 = Mock()
        self.mock_inner._get_person_from_handle.side_effect = [mock_p1, mock_p2]

        proxies = list(self.repo.iter_all_persons())
        self.assertEqual(len(proxies), 2)
        self.assertEqual(self.cache.person_count, 2)

    def test_get_person_count_delegates_directly(self) -> None:
        """Not cached; always delegates."""
        self.mock_inner.get_person_count.return_value = 42
        count = self.repo.get_person_count()
        self.assertEqual(count, 42)
        self.mock_inner.get_person_count.assert_called_once()

    def test_get_all_person_handles_delegates_directly(self) -> None:
        """Not cached; always delegates."""
        self.mock_inner.get_all_person_handles.return_value = ["h1", "h2"]
        handles = self.repo.get_all_person_handles()
        self.assertEqual(handles, ["h1", "h2"])
        self.mock_inner.get_all_person_handles.assert_called_once()

    def test_invalidation_causes_refetch(self) -> None:
        """After invalidation, next read delegates to inner."""
        mock_raw_person = Mock()
        self.mock_inner._get_person_from_handle.return_value = mock_raw_person

        # Fetch and cache
        self.repo.get_person("handle1")
        self.mock_inner._get_person_from_handle.reset_mock()

        # Invalidate
        self.cache.invalidate_person("handle1")

        # Refetch (should delegate again)
        self.repo.get_person("handle1")
        self.mock_inner._get_person_from_handle.assert_called_once_with("handle1")


if __name__ == "__main__":
    unittest.main()

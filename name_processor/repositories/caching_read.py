from __future__ import annotations

from typing import TYPE_CHECKING, Generator

from name_processor.protocols.gramps import Person, Family, Event
from name_processor.repositories.person import GrampsPersonProxy
from name_processor.repositories.entity_cache import EntityCache, _MISSING

if TYPE_CHECKING:
    from name_processor.repositories.gramps_read import GrampsReadRepository


class CachingReadRepository:
    """Decorator around GrampsReadRepository that adds transparent caching.

        Implements the same public interface as GrampsReadRepository.
        All entity fetch methods check the cache first, then delegate to
        the inner repository on cache miss.

        Non-cacheable methods (iterators, handle lists, person counts)
        are delegated directly to the inner repository.
    ```
    NOTE: The relationship methods duplicate logic from GrampsReadRepository.
    This is intentional because the decorator needs to intercept at the
    entity-fetch level (i.e. using cached versions of get_person, get_family,
    and get_event) rather than delegating the high-level method which would
    bypass the cache for internal lookups.
    ```
    """

    def __init__(
        self,
        inner: GrampsReadRepository,
        cache: EntityCache,
    ) -> None:
        self._inner = inner
        self._cache = cache

    # ==========================================
    # Public Entity Access Methods (Cached)
    # ==========================================
    def get_person(self, handle: str) -> GrampsPersonProxy | None:
        """Returns a GrampsPersonProxy for the person, using cache, or None if not found."""
        raw = self._get_cached_person(handle)
        if not raw:
            return None
        return GrampsPersonProxy(raw)

    def get_raw_person(self, handle: str) -> Person | None:
        """Returns a raw Gramps Person object using cache, or None if not found."""
        return self._get_cached_person(handle)

    def get_family(self, handle: str) -> Family | None:
        """Returns a Family object from cache, or None if not found."""
        return self._get_cached_family(handle)

    def get_event(self, handle: str) -> Event | None:
        """Returns an Event object from cache, or None if not found."""
        return self._get_cached_event(handle)

    # ==========================================
    # Private Cache-Through Helpers
    # ==========================================
    def _get_cached_person(self, handle: str) -> Person | None:
        cached = self._cache.get_person(handle)
        if cached is not _MISSING:
            return cached
        person = self._inner._get_person_from_handle(handle)
        self._cache.put_person(handle, person)
        return person

    def _get_cached_family(self, handle: str) -> Family | None:
        cached = self._cache.get_family(handle)
        if cached is not _MISSING:
            return cached
        family = self._inner._get_family_from_handle(handle)
        self._cache.put_family(handle, family)
        return family

    def _get_cached_event(self, handle: str) -> Event | None:
        cached = self._cache.get_event(handle)
        if cached is not _MISSING:
            return cached
        event = self._inner._get_event_from_handle(handle)
        self._cache.put_event(handle, event)
        return event

    # ==========================================
    # Delegated Methods (Not Cached)
    # ==========================================
    def is_protected_by_alias(self, person: Person, search_str: str) -> bool:
        """Checks if a specific string exists within the alternative names (delegated)."""
        return self._inner.is_protected_by_alias(person, search_str)

    def get_person_count(self) -> int:
        """Returns the total number of individuals (delegated)."""
        return self._inner.get_person_count()

    def get_all_person_handles(self) -> list[str]:
        """Returns a list of all person handles (delegated)."""
        return self._inner.get_all_person_handles()

    def get_all_event_handles(self) -> list[str]:
        """Returns a list of all event handles (delegated)."""
        return self._inner.get_all_event_handles()

    # ==========================================
    # Relationship Handle Methods (Cached)
    # ==========================================
    def get_father_handle(self, person_handle: str) -> str | None:
        """Returns the father's handle for a person, or None if not found (using cache)."""
        person = self._get_cached_person(person_handle)
        if not person:
            return None
        families = person.get_parent_family_handle_list()
        if not families:
            return None
        family = self._get_cached_family(families[0])
        return family.get_father_handle() if family else None

    def get_mother_handle(self, person_handle: str) -> str | None:
        """Returns the mother's handle for a person, or None if not found (using cache)."""
        person = self._get_cached_person(person_handle)
        if not person:
            return None
        families = person.get_parent_family_handle_list()
        if not families:
            return None
        family = self._get_cached_family(families[0])
        return family.get_mother_handle() if family else None

    def get_children_handles(self, person_handle: str) -> list[str]:
        """Returns a list of children handles for a person (using cache)."""
        person = self._get_cached_person(person_handle)
        if not person:
            return []
        children: list[str] = []
        for family_handle in person.get_family_handle_list():
            family = self._get_cached_family(family_handle)
            if family:
                for child_ref in family.get_child_ref_list():
                    if child_ref.ref:
                        children.append(child_ref.ref)
        return children

    def get_siblings_handles(self, person_handle: str) -> list[str]:
        """Returns a list of siblings handles for a person (using cache)."""
        person = self._get_cached_person(person_handle)
        if not person:
            return []
        siblings: list[str] = []
        for family_handle in person.get_parent_family_handle_list():
            family = self._get_cached_family(family_handle)
            if family:
                for child_ref in family.get_child_ref_list():
                    child_handle = child_ref.ref
                    if child_handle and child_handle != person_handle:
                        siblings.append(child_handle)
        return siblings

    # ==========================================
    # Relationship Proxy Methods (Cached)
    # ==========================================
    def get_father(self, person_handle: str) -> GrampsPersonProxy | None:
        """Returns a GrampsPersonProxy for the father of the given person (using cache)."""
        father_handle = self.get_father_handle(person_handle)
        if not father_handle:
            return None
        return self.get_person(father_handle)

    def get_siblings(self, person_handle: str) -> list[GrampsPersonProxy]:
        """Returns all siblings of the given person as GrampsPersonProxies (using cache)."""
        sibling_handles = self.get_siblings_handles(person_handle)
        proxies: list[GrampsPersonProxy] = []
        for handle in sibling_handles:
            proxy = self.get_person(handle)
            if proxy:
                proxies.append(proxy)
        return proxies

    # ==========================================
    # Event/Chronology Methods (Cached)
    # ==========================================
    def get_event_years(self, person_handle: str) -> list[int]:
        """Returns a list of years from a person's events (using cache)."""
        person = self._get_cached_person(person_handle)
        if not person:
            return []
        years: list[int] = []
        for ref in person.get_event_ref_list():
            if ref.ref is None:
                continue
            event = self._get_cached_event(ref.ref)
            if event:
                date_obj = event.get_date_object()
                if date_obj and not date_obj.is_empty():
                    year = date_obj.get_year()
                    if year and year > 0:
                        years.append(year)
        return years

    # ==========================================
    # Iterator Methods (Cached)
    # ==========================================
    def iter_all_persons(self) -> Generator[GrampsPersonProxy, None, None]:
        """Yields person proxies, populating cache for each entity accessed."""
        for handle in self.get_all_person_handles():
            proxy = self.get_person(handle)
            if proxy:
                yield proxy

    def iter_all_events_years(self) -> Generator[int, None, None]:
        """Yields years, populating event cache for each entity accessed."""
        for handle in self.get_all_event_handles():
            event = self.get_event(handle)
            if event:
                date_obj = event.get_date_object()
                if date_obj and not date_obj.is_empty():
                    year = date_obj.get_year()
                    if year and year > 0:
                        yield year

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, Generator

from name_processor.protocols.audit import AuditSubject
from name_processor.protocols.chronology import ChronologySubject
from name_processor.protocols.confidence import ConfidenceSubject
from name_processor.protocols.gramps import DateObject, GrampsDatabase
from name_processor.protocols.patronymic import PatronymicSubject

if TYPE_CHECKING:
    from name_processor.repositories.person import GrampsPersonProxy


class GrampsReadRepository:
    def __init__(self, db: GrampsDatabase) -> None:
        self._db = db

    # ==========================================
    # System Operations
    # ==========================================
    def get_person_count(self) -> int:
        """Returns the total number of individuals to power UI progress bars."""
        return self.get_total_person_count()

    def get_total_person_count(self) -> int:
        """Returns the total number of individuals in the database."""
        return self._db.get_number_of_people()

    # ==========================================
    # Database Query Methods
    # ==========================================
    def get_family_from_handle(self, handle: str) -> object | None:
        """Returns a Family object from its handle, or None if not found."""
        return self._db.get_family_from_handle(handle)

    def get_person_from_handle(self, handle: str) -> object | None:
        """Returns a Person object from its handle, or None if not found."""
        return self._db.get_person_from_handle(handle)

    def get_event_from_handle(self, handle: str) -> object | None:
        """Returns an Event object from its handle, or None if not found."""
        return self._db.get_event_from_handle(handle)

    def get_all_person_handles(self) -> list[str]:
        """Returns a list of all person handles."""
        return self._db.get_person_handles()

    def get_all_event_handles(self) -> list[str]:
        """Returns a list of all event handles."""
        return self._db.get_event_handles()

    # ==========================================
    # Relationship Query Methods
    # ==========================================
    def get_father_handle(self, person_handle: str) -> str | None:
        """Returns the father's handle for a person, or None if not found."""
        person = self.get_person_from_handle(person_handle)
        if not person:
            return None
        families = person.get_parent_family_handle_list()
        if not families:
            return None
        family = self.get_family_from_handle(families[0])
        return family.get_father_handle() if family else None

    def get_mother_handle(self, person_handle: str) -> str | None:
        """Returns the mother's handle for a person, or None if not found."""
        person = self.get_person_from_handle(person_handle)
        if not person:
            return None
        families = person.get_parent_family_handle_list()
        if not families:
            return None
        family = self.get_family_from_handle(families[0])
        return family.get_mother_handle() if family else None

    def get_children_handles(self, person_handle: str) -> list[str]:
        """Returns a list of children handles for a person."""
        person = self.get_person_from_handle(person_handle)
        if not person:
            return []
        children = []
        for family_handle in person.get_family_handle_list():
            family = self.get_family_from_handle(family_handle)
            if family:
                for child_ref in family.get_child_ref_list():
                    if child_ref.ref:
                        children.append(child_ref.ref)
        return children

    def get_siblings_handles(self, person_handle: str) -> list[str]:
        """Returns a list of siblings handles for a person."""
        person = self.get_person_from_handle(person_handle)
        if not person:
            return []
        siblings = []
        for family_handle in person.get_parent_family_handle_list():
            family = self.get_family_from_handle(family_handle)
            if family:
                for child_ref in family.get_child_ref_list():
                    child_handle = child_ref.ref
                    if child_handle and child_handle != person_handle:
                        siblings.append(child_handle)
        return siblings

    def get_event_years(self, person_handle: str) -> list[int]:
        """Returns a list of years from a person's events."""
        person = self.get_person_from_handle(person_handle)
        if not person:
            return []
        years = []
        for ref in person.get_event_ref_list():
            event = self.get_event_from_handle(ref.ref)
            if event:
                date_obj = event.get_date_object()
                if date_obj and not date_obj.is_empty():
                    year = date_obj.get_year()
                    if year and year > 0:
                        years.append(year)
        return years

    # ==========================================
    # Proxy Access & Iterators
    # ==========================================
    def get_person_proxy(self, handle: str) -> GrampsPersonProxy | None:
        from name_processor.repositories.person import GrampsPersonProxy

        gramps_person = self.get_person_from_handle(handle)
        if not gramps_person:
            return None
        return GrampsPersonProxy(gramps_person)

    def get_chronology_subject(self, handle: str) -> ChronologySubject | None:
        return self.get_person_proxy(handle)

    def get_confidence_subject(self, handle: str) -> ConfidenceSubject | None:
        return self.get_person_proxy(handle)

    def get_audit_subject(self, handle: str) -> AuditSubject | None:
        return self.get_person_proxy(handle)

    def get_patronymic_subject(self, handle: str) -> PatronymicSubject | None:
        return self.get_person_proxy(handle)

    def get_person_proxies_chunked(
        self, chunk_size: int = 250
    ) -> Generator[list[GrampsPersonProxy], None, None]:
        """
        Yields batches of person proxies to hide handle iteration
        and support GTK idle loop chunking.
        """
        handles = self.get_all_person_handles()
        for i in range(0, len(handles), chunk_size):
            chunk = []
            for handle in handles[i : i + chunk_size]:
                proxy = self.get_person_proxy(handle)
                if proxy:
                    chunk.append(proxy)
            yield chunk

    def iter_all_person_proxies(self) -> Generator[GrampsPersonProxy, None, None]:
        """Yields person proxies one by one for direct iteration."""
        for handle in self.get_all_person_handles():
            proxy = self.get_person_proxy(handle)
            if proxy:
                yield proxy

    def iter_event_years(self) -> Generator[int, None, None]:
        """Yields raw years sequentially. No business logic (medians) allowed here."""
        for handle in self._db.get_event_handles():
            event = self._db.get_event_from_handle(handle)
            if event:
                date_obj = event.get_date_object()
                if date_obj and not date_obj.is_empty():
                    year = date_obj.get_year()
                    if year and year > 0:
                        yield year

    # ==========================================
    # Aggregations
    # ==========================================
    def get_database_median_year_chunked(
        self, chunk_size: int = 500
    ) -> Generator[None, None, int | None]:
        """Calculates the median year asynchronously."""
        years = []
        handles = self.get_all_event_handles()
        handle_iter = iter(handles)

        while True:
            chunk = list(itertools.islice(handle_iter, chunk_size))
            if not chunk:
                break

            for handle in chunk:
                event = self.get_event_from_handle(handle)
                if event:
                    date_obj: DateObject | None = event.get_date_object()
                    if date_obj and not date_obj.is_empty():
                        year = date_obj.get_year()
                        if year and year > 0:
                            years.append(year)
            yield None

        if years:
            years.sort()
            return years[len(years) // 2]
        return None

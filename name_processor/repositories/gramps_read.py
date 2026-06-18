from __future__ import annotations

from typing import TYPE_CHECKING, Generator

from name_processor.protocols.gramps import GrampsDatabase, Person
from name_processor.repositories.person import GrampsPersonProxy

if TYPE_CHECKING:
    from name_processor.repositories.person import GrampsPersonProxy


class GrampsReadRepository:
    def __init__(self, db: GrampsDatabase) -> None:
        self._db = db

    # ==========================================
    # Database Query Methods
    # ==========================================
    def get_person_count(self) -> int:
        """Returns the total number of individuals to power UI progress bars."""
        return self._db.get_number_of_people()

    def get_family_from_handle(self, handle: str) -> object | None:
        """Returns a Family object from its handle, or None if not found."""
        return self._db.get_family_from_handle(handle)

    def get_person_from_handle(self, handle: str) -> object | None:
        """Returns a Person object from its handle, or None if not found."""
        return self._db.get_person_from_handle(handle)

    def get_event_from_handle(self, handle: str) -> object | None:
        """Returns an Event object from its handle, or None if not found."""
        return self._db.get_event_from_handle(handle)

    def preserve_primary_name(self, person: object) -> None:
        """
        Creates a deep copy of the person's current primary name and appends it
        to their Alternative Names list. Retains all attached citations and dates.
        This is a read operation that prepares data for later write operations.
        """
        from gramps.gen.lib import Name, NameType

        primary_name = person.get_primary_name()
        if not primary_name:
            return

        # Gramps domain objects support deep copy via the 'source' kwarg
        preserved_name = Name(source=primary_name)

        # Reclassify the preserved name to distinguish it from the new primary
        preserved_name.set_type(NameType(NameType.AKA))

        person.add_alternate_name(preserved_name)

    def is_protected_by_alias(self, person: Person, search_str: str) -> bool:
        """
        Checks if a specific string exists within the alternative names.
        Used to skip renaming if the string is a known historical alias or maiden name.
        """
        for alt_name in person.get_alternate_names():
            if search_str in alt_name.get_first_name():
                return True
        return False

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

    def get_father(self, person_handle: str) -> GrampsPersonProxy | None:
        """
        Returns a GrampsPersonProxy for the father of the given person.
        Returns None if the person has no father or father not found.
        """
        father_handle = self.get_father_handle(person_handle)
        if not father_handle:
            return None
        return self.get_person(father_handle)

    def get_siblings(self, person_handle: str) -> list[GrampsPersonProxy]:
        """
        Returns a list of GrampsPersonProxy objects for all siblings of the given person.
        Returns empty list if person has no siblings.
        """
        sibling_handles = self.get_siblings_handles(person_handle)
        proxies = []
        for handle in sibling_handles:
            proxy = self.get_person(handle)
            if proxy:
                proxies.append(proxy)
        return proxies

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
    def get_person(self, handle: str) -> GrampsPersonProxy | None:
        gramps_person = self.get_person_from_handle(handle)
        if not gramps_person:
            return None
        return GrampsPersonProxy(gramps_person)

    def iter_all_persons(self) -> Generator[GrampsPersonProxy, None, None]:
        """Yields person proxies one by one for direct iteration."""
        for handle in self.get_all_person_handles():
            proxy = self.get_person(handle)
            if proxy:
                yield proxy

    def iter_all_events_years(self) -> Generator[int, None, None]:
        """Yields raw years sequentially. No business logic (medians) allowed here."""
        for handle in self._db.get_event_handles():
            event = self._db.get_event_from_handle(handle)
            if event:
                date_obj = event.get_date_object()
                if date_obj and not date_obj.is_empty():
                    year = date_obj.get_year()
                    if year and year > 0:
                        yield year

from typing import Protocol, Optional, List


class ChronologySubject(Protocol):
    """The shape of the subject data required by ChronologyService."""

    @property
    def handle(self) -> str: ...

    @property
    def event_years(self) -> List[int]:
        """A list of years extracted from the subject's birth, death, or marriage events."""
        ...

    @property
    def father_handle(self) -> Optional[str]: ...

    @property
    def mother_handle(self) -> Optional[str]: ...

    @property
    def children_handles(self) -> List[str]: ...

    @property
    def siblings_handles(self) -> List[str]: ...


class ChronologyRepository(Protocol):
    """The repository interface required by ChronologyService."""

    def get_chronology_subject(self, handle: str) -> Optional[ChronologySubject]: ...

    def get_database_median_year(self) -> Optional[int]: ...

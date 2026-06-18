from __future__ import annotations

from typing import Generator, Protocol


class ChronologySubject(Protocol):
    """The shape of the subject data required by ChronologyService."""

    @property
    def handle(self) -> str: ...


class ChronologyRepository(Protocol):
    """The repository interface required by ChronologyService."""

    def get_person(self, handle: str) -> ChronologySubject | None: ...

    def get_event_years(self, person_handle: str) -> list[int]: ...

    def iter_all_events_years(self) -> Generator[int, None, None]: ...

    def get_father_handle(self, person_handle: str) -> str | None: ...

    def get_mother_handle(self, person_handle: str) -> str | None: ...

    def get_children_handles(self, person_handle: str) -> list[str]: ...

    def get_siblings_handles(self, person_handle: str) -> list[str]: ...

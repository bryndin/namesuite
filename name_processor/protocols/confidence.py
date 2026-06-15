from __future__ import annotations

from typing import Protocol


class ConfidenceSubject(Protocol):
    """Protocol for subjects evaluated by the ConfidenceService."""

    @property
    def display_name(self) -> str: ...

    @property
    def surnames(self) -> list[str]: ...

    @property
    def given_name(self) -> str | None: ...

    @property
    def has_patronymic(self) -> bool: ...


class ConfidenceRepository(Protocol):
    """The repository interface required by ConfidenceService."""

    def get_confidence_subject(self, handle: str) -> ConfidenceSubject | None: ...

    def get_siblings_handles(self, person_handle: str) -> list[str]: ...

from __future__ import annotations

from typing import Protocol

from name_processor.models.person import Gender


class PatronymicSubject(Protocol):
    """The Service dictates the shape of the data it needs."""

    @property
    def handle(self) -> str: ...

    @property
    def gender(self) -> Gender: ...

    @property
    def has_patronymic(self) -> bool: ...

    @property
    def given_name(self) -> str | None: ...


class PatronymicRepository(Protocol):
    """The repository interface required by PatronymicInferenceService."""

    def get_patronymic_subject(self, handle: str) -> PatronymicSubject | None: ...

    def get_father_handle(self, person_handle: str) -> str | None: ...

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from name_processor.models.person import Gender

if TYPE_CHECKING:
    from name_processor.repositories.person import GrampsPersonProxy


class AuditSubject(Protocol):
    """Protocol for subjects evaluated by the AuditService."""

    @property
    def handle(self) -> str: ...

    @property
    def gramps_id(self) -> str: ...

    @property
    def display_name(self) -> str: ...

    @property
    def gender(self) -> Gender: ...

    @property
    def patronymic(self) -> str | None: ...

    @property
    def father_handle(self) -> str | None: ...

    @property
    def given_name(self) -> str | None: ...

    @property
    def surnames(self) -> list[str]: ...

    @property
    def siblings_handles(self) -> list[str]: ...


class AuditRepository(Protocol):
    """The repository interface required by AuditService."""

    def get_audit_subject(self, handle: str) -> AuditSubject | None: ...

    def get_father_proxy(self, person_handle: str) -> GrampsPersonProxy | None: ...

from __future__ import annotations

from typing import Protocol


class RenameSubject(Protocol):
    """The shape of the subject data required by RenamerService."""

    @property
    def handle(self) -> str: ...

    @property
    def gramps_id(self) -> str: ...

    @property
    def display_name(self) -> str: ...

    @property
    def given_name(self) -> str | None: ...

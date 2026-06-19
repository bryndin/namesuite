from __future__ import annotations

from typing import Protocol

from name_processor.protocols.gramps import Person


class ReadRepository(Protocol):
    """Protocol for read repository operations used by services."""

    def preserve_primary_name(self, person: Person) -> None:
        """
        Creates a deep copy of the person's current primary name and appends it
        to their Alternative Names list. Retains all attached citations and dates.
        """
        ...

    def is_protected_by_alias(self, person: Person, search_str: str) -> bool:
        """
        Checks if a specific string exists within the alternative names.
        Used to skip renaming if the string is a known historical alias or maiden name.
        """
        ...

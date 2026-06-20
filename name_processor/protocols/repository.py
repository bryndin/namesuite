from __future__ import annotations

from typing import Protocol

from name_processor.protocols.gramps import Person


class ReadRepository(Protocol):
    """Protocol for read repository operations used by services."""

    def is_protected_by_alias(self, person: Person, search_str: str) -> bool:
        """
        Checks if a specific string exists within the alternative names.
        Used to skip renaming if the string is a known historical alias or maiden name.
        """
        ...

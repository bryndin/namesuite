from __future__ import annotations

from typing import TYPE_CHECKING

from name_processor.protocols.gramps import Person

if TYPE_CHECKING:
    from name_processor.repositories.gramps_read import GrampsReadRepository


class AltNamesService:
    """Thin wrapper for alternate name operations delegated to read repository."""

    def __init__(self, read_repo: GrampsReadRepository | None = None) -> None:
        """
        Initialize with optional read repository for delegation.
        If not provided, methods will need to be called with repository explicitly.
        """
        self._read_repo = read_repo

    def preserve_primary_name(self, gramps_person: Person) -> None:
        """
        Delegates to GrampsReadRepository.preserve_primary_name.
        Creates a deep copy of the person's current primary name and appends it
        to their Alternative Names list. Retains all attached citations and dates.
        """
        if self._read_repo:
            self._read_repo.preserve_primary_name(gramps_person)
        else:
            raise RuntimeError(
                "AltNamesService not initialized with read_repo. "
                "Use GrampsReadRepository.preserve_primary_name directly."
            )

    def is_protected_by_alias(self, gramps_person: Person, search_str: str) -> bool:
        """
        Delegates to GrampsReadRepository.is_protected_by_alias.
        Checks if a specific string exists within the alternative names.
        Used to skip renaming if the string is a known historical alias or maiden name.
        """
        if self._read_repo:
            return self._read_repo.is_protected_by_alias(gramps_person, search_str)
        else:
            raise RuntimeError(
                "AltNamesService not initialized with read_repo. "
                "Use GrampsReadRepository.is_protected_by_alias directly."
            )

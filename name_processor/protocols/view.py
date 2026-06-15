# name_processor/protocols/view.py
from typing import Protocol, Iterable
from name_processor.models.view import GivenRowData


class ToolWindowProtocol(Protocol):
    """Protocol for ToolWindow UI."""

    def clear_rename_proposals(self) -> None: ...

    def append_rename_proposals(self, proposals: Iterable[GivenRowData]) -> None: ...

    def update_audit_progress(self, fraction: float, text: str) -> None: ...

    def show_error(self, title: str, message: str) -> None: ...

    def get_checked_renaming_handles(self) -> list[str]: ...

# name_processor/protocols/view.py
from typing import Protocol

from name_processor.models.audit import AuditIssue
from name_processor.models.infer import PatronymicInferenceStatus
from name_processor.models.renamer import AltAction
from name_processor.models.view import GivenRowData


class ToolViewPort(Protocol):
    """Protocol for ToolWindow UI."""

    # Read path (controller → view)
    def clear_rename_proposals(self) -> None: ...

    def clear_given_store(
        self,
    ) -> None: ...  # Note: This will replace direct widget access in Stage 2

    def append_rename_proposal(self, row: GivenRowData) -> None: ...

    def update_given_store_actions(self, action: AltAction) -> None: ...

    def update_given_apply_button(self) -> None: ...

    def clear_audit_results(self) -> None: ...

    def append_issue(self, issue: AuditIssue) -> None: ...

    def update_audit_progress(self, fraction: float, text: str) -> None: ...

    def on_audit_complete(self, total_found: int) -> None: ...

    def update_audit_apply_button(self) -> None: ...

    def setup_given_name_autocompletion(self) -> None: ...

    def show_ok_dialog(self, title: str, message: str) -> None: ...

    # Write path (view → controller queries)
    def get_checked_renaming_handles(self) -> set[str]: ...

    def get_checked_audit_keys(self) -> set[tuple[str, str]]: ...


class GrampletViewPort(Protocol):
    """Protocol for GrampletView UI."""

    def show_status_message(
        self, message_key: PatronymicInferenceStatus, apply_sensitive: bool = False
    ) -> None: ...

    def show_suggestion(self, patronymic: str, father_name: str) -> None: ...

    def display_error(self, title_key: str, message: str) -> None: ...

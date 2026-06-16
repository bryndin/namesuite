from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from name_processor.controllers.tool import ToolController
from name_processor.models.renamer import AltAction, MatchMode
from name_processor.presentation.row_schemas import GivenRowData
from tests.compat_mocks import mock_gramps
from tests.fakes.fake_tool_view import FakeToolView
from tests.fakes.sync_task_runner import SynchronousTaskRunner

mock_gramps()


class TestRenameWorkflow(unittest.TestCase):
    """End-to-end tests for rename scan and apply workflow."""

    def setUp(self) -> None:
        """Set up test fixtures with fake view and sync runner."""
        self.fake_view = FakeToolView()
        self.sync_runner = SynchronousTaskRunner()

        # Mock dependencies
        self.mock_tool = MagicMock()
        self.mock_tool.dbstate = MagicMock()
        self.mock_tool.dbstate.db = MagicMock()

        self.mock_read_repo = MagicMock()
        self.mock_write_repo = MagicMock()
        self.mock_renamer_service = MagicMock()
        self.mock_alt_names_service = MagicMock()
        self.mock_patronymic_service = MagicMock()
        self.mock_audit_service = MagicMock()
        self.mock_chronology_service = MagicMock()

        # Create controller
        self.controller = ToolController(
            tool_instance=self.mock_tool,
            view=self.fake_view,
            read_repo=self.mock_read_repo,
            write_repo=self.mock_write_repo,
            renamer_service=self.mock_renamer_service,
            alt_names_service=self.mock_alt_names_service,
            patronymic_service=self.mock_patronymic_service,
            audit_service=self.mock_audit_service,
            chronology_service=self.mock_chronology_service,
        )

    def _run_scan_synchronously(self, generator, on_complete=None):
        """Helper to run a scan generator synchronously using SynchronousTaskRunner."""
        self.sync_runner.run_chunked(generator, on_complete)

    @patch("name_processor.controllers.tool.run_in_idle_loop")
    def test_rename_scan_finds_proposals(self, mock_run_in_idle_loop) -> None:
        """Test that rename scan finds and displays proposals."""
        # Arrange: Create mock person proxies
        mock_proxy1 = MagicMock()
        mock_proxy1.given_name = "Ivan"
        mock_proxy1.gramps_id = "I0001"
        mock_proxy1.display_name = "Ivan Ivanov"
        mock_proxy1.handle = "handle1"

        mock_proxy2 = MagicMock()
        mock_proxy2.given_name = "Ivan"
        mock_proxy2.gramps_id = "I0002"
        mock_proxy2.display_name = "Ivan Petrov"
        mock_proxy2.handle = "handle2"

        self.mock_read_repo.iter_all_persons.return_value = iter(
            [mock_proxy1, mock_proxy2]
        )

        # Configure renamer service to return proposed name
        self.mock_renamer_service.create_config.return_value = MagicMock()
        self.mock_renamer_service.evaluate_person.return_value = "Ioann"

        # Configure mock to run synchronously
        mock_run_in_idle_loop.side_effect = self._run_scan_synchronously

        # Act: Run scan
        result = self.controller.run_rename_scan("Ivan", "Ioann", MatchMode.EXACT)

        # Assert: Scan started successfully
        self.assertTrue(result)

        # Assert: Two proposals appended to view
        self.assertEqual(len(self.fake_view.rename_proposals), 2)

        # Assert: Proposals have correct data
        proposal1 = self.fake_view.rename_proposals[0]
        self.assertEqual(proposal1.current, "Ivan")
        self.assertEqual(proposal1.proposed, "Ioann")
        self.assertEqual(proposal1.handle, "handle1")

        # Assert: Both proposals checked by default
        self.assertEqual(len(self.fake_view.checked_rename_handles), 2)

    def test_rename_apply_checked_proposals(self) -> None:
        """Test that applying checked renamings calls write repository correctly."""
        # Arrange: Pre-populate rename candidates
        row_data = GivenRowData(
            checkbox=True,
            gramps_id="I0001",
            display_name="Ivan Ivanov",
            current="Ivan",
            proposed="Ioann",
            alt_action=AltAction.OVERWRITE.value,
            handle="handle1",
        )
        self.controller._rename_candidates["handle1"] = row_data
        self.fake_view.rename_proposals.append(row_data)
        self.fake_view.checked_rename_handles.add("handle1")

        # Mock repository methods
        mock_person = MagicMock()
        self.mock_read_repo.get_person_from_handle.return_value = mock_person
        self.mock_write_repo.transaction.return_value.__enter__ = MagicMock()
        self.mock_write_repo.transaction.return_value.__exit__ = MagicMock()

        # Act: Apply checked renamings
        result = self.controller.apply_checked_renamings()

        # Assert: Apply succeeded
        self.assertTrue(result)

        # Assert: Write repository called with correct parameters
        self.mock_write_repo.apply_first_name_correction.assert_called_once()
        call_args = self.mock_write_repo.apply_first_name_correction.call_args
        self.assertEqual(call_args[0][2], "Ioann")  # proposed name

    def test_rename_apply_with_preserve_alt(self) -> None:
        """Test that preserve alt-names is respected during apply."""
        # Arrange: Pre-populate rename candidates
        row_data = GivenRowData(
            checkbox=True,
            gramps_id="I0001",
            display_name="Ivan Ivanov",
            current="Ivan",
            proposed="Ioann",
            alt_action=AltAction.PRESERVE.value,
            handle="handle1",
        )
        self.controller._rename_candidates["handle1"] = row_data
        self.fake_view.rename_proposals.append(row_data)
        self.fake_view.checked_rename_handles.add("handle1")
        self.fake_view.set_preserve_alt_enabled(True)

        # Mock repository methods
        mock_person = MagicMock()
        self.mock_read_repo.get_person_from_handle.return_value = mock_person
        self.mock_write_repo.transaction.return_value.__enter__ = MagicMock()
        self.mock_write_repo.transaction.return_value.__exit__ = MagicMock()

        # Act: Apply checked renamings
        result = self.controller.apply_checked_renamings()

        # Assert: Apply succeeded
        self.assertTrue(result)

        # Assert: Alt names service called to preserve primary name
        self.mock_alt_names_service.preserve_primary_name.assert_called_once_with(
            mock_person
        )

    def test_rename_apply_partial_selection(self) -> None:
        """Test that only checked proposals are applied."""
        # Arrange: Pre-populate two rename candidates
        row_data1 = GivenRowData(
            checkbox=True,
            gramps_id="I0001",
            display_name="Ivan Ivanov",
            current="Ivan",
            proposed="Ioann",
            alt_action=AltAction.OVERWRITE.value,
            handle="handle1",
        )
        row_data2 = GivenRowData(
            checkbox=True,
            gramps_id="I0002",
            display_name="Petr Petrov",
            current="Petr",
            proposed="Pyotr",
            alt_action=AltAction.OVERWRITE.value,
            handle="handle2",
        )
        self.controller._rename_candidates["handle1"] = row_data1
        self.controller._rename_candidates["handle2"] = row_data2
        self.fake_view.rename_proposals.extend([row_data1, row_data2])

        # Only check first proposal
        self.fake_view.checked_rename_handles.add("handle1")

        # Mock repository methods
        mock_person = MagicMock()
        self.mock_read_repo.get_person_from_handle.return_value = mock_person
        self.mock_write_repo.transaction.return_value.__enter__ = MagicMock()
        self.mock_write_repo.transaction.return_value.__exit__ = MagicMock()

        # Act: Apply checked renamings
        result = self.controller.apply_checked_renamings()

        # Assert: Apply succeeded
        self.assertTrue(result)

        # Assert: Write repository called only once (for handle1)
        self.mock_write_repo.apply_first_name_correction.assert_called_once()

    def test_preserve_alt_toggle_updates_all_proposals(self) -> None:
        """Test that toggling preserve alt updates all rename proposals."""
        # Arrange: Pre-populate rename candidates
        row_data1 = GivenRowData(
            checkbox=True,
            gramps_id="I0001",
            display_name="Ivan Ivanov",
            current="Ivan",
            proposed="Ioann",
            alt_action=AltAction.OVERWRITE.value,
            handle="handle1",
        )
        row_data2 = GivenRowData(
            checkbox=True,
            gramps_id="I0002",
            display_name="Petr Petrov",
            current="Petr",
            proposed="Pyotr",
            alt_action=AltAction.OVERWRITE.value,
            handle="handle2",
        )
        self.controller._rename_candidates["handle1"] = row_data1
        self.controller._rename_candidates["handle2"] = row_data2
        self.fake_view.rename_proposals.extend([row_data1, row_data2])

        # Act: Toggle preserve alt to PRESERVE
        self.controller.update_preserve_alt(AltAction.PRESERVE)

        # Assert: All proposals updated to PRESERVE action
        for proposal in self.fake_view.rename_proposals:
            self.assertEqual(proposal.alt_action, AltAction.PRESERVE.value)

        # Assert: View notified of action update
        self.assertEqual(len(self.fake_view.store_action_updates), 1)
        self.assertEqual(self.fake_view.store_action_updates[0], AltAction.PRESERVE)

        # Act: Toggle preserve alt back to OVERWRITE
        self.controller.update_preserve_alt(AltAction.OVERWRITE)

        # Assert: All proposals updated to OVERWRITE action
        for proposal in self.fake_view.rename_proposals:
            self.assertEqual(proposal.alt_action, AltAction.OVERWRITE.value)

    @patch("name_processor.controllers.tool.run_in_idle_loop")
    def test_rename_scan_no_results_shows_dialog(self, mock_run_in_idle_loop) -> None:
        """Test that scan with no results shows appropriate dialog."""
        # Arrange: Configure repository to return no persons
        self.mock_read_repo.iter_all_persons.return_value = iter([])

        self.mock_renamer_service.create_config.return_value = MagicMock()

        # Configure mock to run synchronously
        mock_run_in_idle_loop.side_effect = self._run_scan_synchronously

        # Act: Run scan
        result = self.controller.run_rename_scan("Ivan", "Ioann", MatchMode.EXACT)

        # Assert: Scan started successfully
        self.assertTrue(result)

        # Assert: No proposals appended
        self.assertEqual(len(self.fake_view.rename_proposals), 0)

        # Assert: "No Results" dialog shown
        self.assertEqual(len(self.fake_view.dialog_calls), 1)
        title, message = self.fake_view.dialog_calls[0]
        self.assertEqual(title, "No Results")
        self.assertEqual(message, "No matching given names found.")


if __name__ == "__main__":
    unittest.main()

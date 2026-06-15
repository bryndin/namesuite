from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

# Mock GTK and Gramps modules before importing
from tests.compat_mocks import mock_gramps

mock_gramps()

from name_processor.controllers.tool import ToolController
from name_processor.models.renamer import AltAction, MatchMode
from name_processor.models.view import GivenRowData


class TestToolController(unittest.TestCase):
    def test_controller_initialization(self):
        mock_dbstate = MagicMock()
        mock_tool = MagicMock(dbstate=mock_dbstate)

        # Instantiate without real DB
        controller = ToolController(
            tool_instance=mock_tool,
            view=MagicMock(),
            read_repo=MagicMock(),
            write_repo=MagicMock(),
            patronymic_service=MagicMock(),
            renamer_service=MagicMock(),
            alt_names_service=MagicMock(),
            audit_service=MagicMock(),
            chronology_service=MagicMock(),
        )
        self.assertEqual(controller.dbstate, mock_dbstate)

    def test_update_preserve_alt(self) -> None:
        mock_dbstate = MagicMock()
        mock_tool = MagicMock(dbstate=mock_dbstate)
        mock_view = MagicMock()

        controller = ToolController(
            tool_instance=mock_tool,
            view=mock_view,
            read_repo=MagicMock(),
            write_repo=MagicMock(),
            patronymic_service=MagicMock(),
            renamer_service=MagicMock(),
            alt_names_service=MagicMock(),
            audit_service=MagicMock(),
            chronology_service=MagicMock(),
        )

        row_data1 = GivenRowData(
            checkbox=True,
            gramps_id="I0001",
            display_name="Ivan Ivanov",
            current="Ivan",
            proposed="Ioann",
            alt_action=AltAction.OVERWRITE.value,
            handle="handle1",
        )
        controller._rename_candidates["handle1"] = row_data1

        # Toggle preserve on (active=True)
        controller.update_preserve_alt(AltAction.PRESERVE)

        self.assertEqual(
            controller._rename_candidates["handle1"].alt_action,
            AltAction.PRESERVE.value,
        )
        mock_view.update_given_store_actions.assert_called_once_with(AltAction.PRESERVE)

        # Toggle preserve off (active=False)
        mock_view.reset_mock()
        controller.update_preserve_alt(AltAction.OVERWRITE)

        self.assertEqual(
            controller._rename_candidates["handle1"].alt_action,
            AltAction.OVERWRITE.value,
        )
        mock_view.update_given_store_actions.assert_called_once_with(
            AltAction.OVERWRITE
        )

    @patch("name_processor.controllers.tool.run_in_idle_loop")
    def test_run_rename_scan_exact_mode_filtering(self, mock_run_in_idle_loop):
        mock_tool = MagicMock()
        mock_view = MagicMock()
        mock_read_repo = MagicMock()
        from name_processor.services.renamer import RenamerService

        renamer_service = RenamerService()

        # Mock two proxies: one matches the given_name, one doesn't
        mock_proxy_match = MagicMock()
        mock_proxy_match.given_name = "Ivan"
        mock_proxy_match.gramps_id = "I0001"
        mock_proxy_match.display_name = "Ivan Ivanov"
        mock_proxy_match.handle = "handle1"

        mock_proxy_no_match = MagicMock()
        mock_proxy_no_match.given_name = "Petr"
        mock_proxy_no_match.gramps_id = "I0002"
        mock_proxy_no_match.display_name = "Petr Petrov"
        mock_proxy_no_match.handle = "handle2"

        # Configure repository to return both proxies
        mock_read_repo.get_person_proxies_chunked.return_value = [
            [mock_proxy_match, mock_proxy_no_match]
        ]

        controller = ToolController(
            tool_instance=mock_tool,
            view=mock_view,
            read_repo=mock_read_repo,
            write_repo=MagicMock(),
            patronymic_service=MagicMock(),
            renamer_service=renamer_service,
            alt_names_service=MagicMock(),
            audit_service=MagicMock(),
            chronology_service=MagicMock(),
        )

        # Define how to handle the mocked run_in_idle_loop
        def side_effect(generator, on_complete):
            result = None
            try:
                while True:
                    next(generator)
            except StopIteration as e:
                result = e.value
            if on_complete:
                on_complete(result)

        mock_run_in_idle_loop.side_effect = side_effect

        # Run scan: Source is 'Ivan', Target is 'Ioann'
        # With buggy RenamerService, both 'Ivan' and 'Petr' will get proposed names
        controller.run_rename_scan("Ivan", "Ioann", MatchMode.EXACT)

        # Verify that _append_rename_proposal_to_store was called ONLY for 'Ivan'
        # With the bug, it will be called twice (for Ivan AND Petr)
        self.assertEqual(
            mock_view._append_rename_proposal_to_store.call_count,
            1,
            f"Expected 1 call, but got {mock_view._append_rename_proposal_to_store.call_count}",
        )

    @patch("name_processor.controllers.tool.run_in_idle_loop")
    def test_run_rename_scan_no_results(self, mock_run_in_idle_loop):
        mock_tool = MagicMock()
        mock_view = MagicMock()
        mock_read_repo = MagicMock()
        mock_renamer_service = MagicMock()

        # No results
        mock_read_repo.get_person_proxies_chunked.return_value = []

        mock_renamer_service.create_config.return_value = {}

        controller = ToolController(
            tool_instance=mock_tool,
            view=mock_view,
            read_repo=mock_read_repo,
            write_repo=MagicMock(),
            patronymic_service=MagicMock(),
            renamer_service=mock_renamer_service,
            alt_names_service=MagicMock(),
            audit_service=MagicMock(),
            chronology_service=MagicMock(),
        )

        # Define how to handle the mocked run_in_idle_loop
        def side_effect(generator, on_complete):
            result = None
            try:
                while True:
                    next(generator)
            except StopIteration as e:
                result = e.value
            if on_complete:
                on_complete(result)

        mock_run_in_idle_loop.side_effect = side_effect

        # Run scan
        controller.run_rename_scan("Ivan", "Ioann", MatchMode.EXACT)

        # Verify that "No Results" dialog WAS shown
        mock_view.show_ok_dialog.assert_called_with(
            "No Results", "No matching given names found."
        )

    @patch("name_processor.controllers.tool.run_in_idle_loop")
    def test_initialize_median_year_async(self, mock_run_in_idle_loop):
        mock_tool = MagicMock()
        mock_view = MagicMock()
        mock_read_repo = MagicMock()
        mock_chronology_service = MagicMock()

        # Mock iter_event_years to yield years
        mock_read_repo.iter_event_years.return_value = iter(
            [1800, 1850, 1900, 1950, 2000]
        )

        # Mock update_median_year to return median
        mock_chronology_service.update_median_year.return_value = 1900

        controller = ToolController(
            tool_instance=mock_tool,
            view=mock_view,
            read_repo=mock_read_repo,
            write_repo=MagicMock(),
            patronymic_service=MagicMock(),
            renamer_service=MagicMock(),
            alt_names_service=MagicMock(),
            audit_service=MagicMock(),
            chronology_service=mock_chronology_service,
        )

        # Define how to handle the mocked run_in_idle_loop
        def side_effect(generator, on_complete):
            result = None
            try:
                while True:
                    next(generator)
            except StopIteration as e:
                result = e.value
            if on_complete:
                on_complete(result)

        mock_run_in_idle_loop.side_effect = side_effect

        # Initialize median year
        controller.initialize_median_year_async()

        # Verify iter_event_years was called
        mock_read_repo.iter_event_years.assert_called_once()

        # Verify update_median_year was called with collected years
        mock_chronology_service.update_median_year.assert_called_once()
        call_args = mock_chronology_service.update_median_year.call_args[0][0]
        self.assertEqual(call_args, [1800, 1850, 1900, 1950, 2000])

    @patch("name_processor.controllers.tool.run_in_idle_loop")
    def test_initialize_median_year_async_with_empty_years(self, mock_run_in_idle_loop):
        mock_tool = MagicMock()
        mock_view = MagicMock()
        mock_read_repo = MagicMock()
        mock_chronology_service = MagicMock()

        # Mock iter_event_years to yield no years
        mock_read_repo.iter_event_years.return_value = iter([])

        controller = ToolController(
            tool_instance=mock_tool,
            view=mock_view,
            read_repo=mock_read_repo,
            write_repo=MagicMock(),
            patronymic_service=MagicMock(),
            renamer_service=MagicMock(),
            alt_names_service=MagicMock(),
            audit_service=MagicMock(),
            chronology_service=mock_chronology_service,
        )

        # Define how to handle the mocked run_in_idle_loop
        def side_effect(generator, on_complete):
            result = None
            try:
                while True:
                    next(generator)
            except StopIteration as e:
                result = e.value
            if on_complete:
                on_complete(result)

        mock_run_in_idle_loop.side_effect = side_effect

        # Initialize median year
        controller.initialize_median_year_async()

        # Verify update_median_year was called with empty list
        mock_chronology_service.update_median_year.assert_called_once_with([])


if __name__ == "__main__":
    unittest.main()

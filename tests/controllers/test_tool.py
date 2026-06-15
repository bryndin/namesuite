from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from name_processor.controllers.tool import ToolController


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

        from name_processor.models.renamer import AltAction
        from name_processor.models.view import GivenRowData

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


if __name__ == "__main__":
    unittest.main()

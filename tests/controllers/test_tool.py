from unittest.mock import MagicMock
from name_processor.controllers.tool import ToolController


def test_controller_initialization():
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
    assert controller.dbstate == mock_dbstate

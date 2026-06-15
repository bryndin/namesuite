from __future__ import annotations

import unittest
from unittest.mock import Mock, MagicMock, patch

from name_processor.controllers.gramplet import GrampletController
from name_processor.models.infer import PatronymicInferenceStatus


class TestGrampletController(unittest.TestCase):
    def setUp(self):
        """Provide fresh mocks for every test."""
        self.mocks = {
            "view": Mock(),
            "patronymic_service": Mock(),
            "chronology_service": Mock(),  # Added missing mock
            "read_repo": Mock(),
            "write_repo": Mock(),
        }
        self.controller = GrampletController(
            view=self.mocks["view"],
            patronymic_service=self.mocks["patronymic_service"],
            chronology_service=self.mocks["chronology_service"],  # Injected here
            read_repo=self.mocks["read_repo"],
            write_repo=self.mocks["write_repo"],
        )

    def test_on_active_changed_with_none_handle(self):
        # Act
        self.controller.on_active_changed(None)

        # Assert
        self.assertIsNone(self.controller._current_handle)
        self.mocks["view"].show_status_message.assert_called_once_with(
            PatronymicInferenceStatus.NO_ACTIVE_PERSON, apply_sensitive=False
        )
        self.mocks["read_repo"].get_person_proxy.assert_not_called()

    def test_on_active_changed_person_not_found(self):
        # Arrange
        mock_result = MagicMock()
        mock_result.status = PatronymicInferenceStatus.NO_ACTIVE_PERSON

        self.mocks["patronymic_service"].infer_patronymic.return_value = mock_result

        # Act
        self.controller.on_active_changed("h123")

        # Assert
        self.assertEqual(self.controller._current_handle, "h123")
        self.mocks["patronymic_service"].infer_patronymic.assert_called_once_with(
            "h123"
        )
        self.mocks["view"].show_status_message.assert_called_once_with(
            PatronymicInferenceStatus.NO_ACTIVE_PERSON, apply_sensitive=False
        )

    def test_on_active_changed_success(self):
        # Arrange
        mock_result = MagicMock()
        mock_result.status = PatronymicInferenceStatus.SUCCESS
        mock_result.patronymic = "Ivanovich"
        mock_result.father_name = "Ivan"

        self.mocks["patronymic_service"].infer_patronymic.return_value = mock_result

        # Act
        self.controller.on_active_changed("h123")

        # Assert
        self.mocks["patronymic_service"].infer_patronymic.assert_called_once_with(
            "h123"
        )
        self.assertEqual(self.controller._suggested_patronymic, "Ivanovich")
        self.mocks["view"].show_suggestion.assert_called_once_with("Ivanovich", "Ivan")

    def test_on_apply_clicked_does_nothing_if_no_suggestion(self):
        # Arrange
        self.controller._current_handle = "h123"
        self.controller._suggested_patronymic = None

        # Act
        self.controller.on_apply_clicked()

        # Assert
        self.mocks["write_repo"].update_patronymic_names.assert_not_called()

    def test_on_apply_clicked_success(self):
        # Arrange
        self.controller._current_handle = "h123"
        self.controller._suggested_patronymic = "Ivanovich"

        # Act
        self.controller.on_apply_clicked()

        # Assert
        self.mocks["write_repo"].update_patronymic_names.assert_called_once_with(
            {"h123": "Ivanovich"}
        )
        self.mocks["view"].show_status_message.assert_called_once_with(
            PatronymicInferenceStatus.SUCCESS, apply_sensitive=False
        )

    @patch("name_processor.controllers.gramplet.run_in_idle_loop")
    def test_initialize_background_tasks_calls_update_median_year(
        self, mock_run_in_idle_loop
    ):
        # Arrange
        years = [1900, 1910, 1920]

        # Act
        self.controller.initialize_background_tasks()

        # Capture the callback
        args, kwargs = mock_run_in_idle_loop.call_args
        on_complete_callback = kwargs["on_complete"]

        # Call the callback
        on_complete_callback(years)

        # Assert
        self.mocks["chronology_service"].update_median_year.assert_called_once_with(
            years
        )


if __name__ == "__main__":
    unittest.main()

from name_processor.models.result import PatronymicInferenceStatus


class GrampletController:
    def __init__(self, view, patronymic_service, read_repo, write_repo):
        self.current_handle: str | None = None

        self._view = view
        self._patronymic_service = patronymic_service
        self._read_repo = read_repo
        self._write_repo = write_repo
        self._suggested_patronymic: str | None = None

    def on_active_changed(self, handle):
        self.current_handle = handle
        self._suggested_patronymic = None

        if not handle:
            self._view.show_status_message(
                PatronymicInferenceStatus.NO_ACTIVE_PERSON, apply_sensitive=False
            )
            return

        person = self._read_repo.get_person_proxy(handle)
        if not person:
            self._view.show_status_message(
                PatronymicInferenceStatus.NO_ACTIVE_PERSON, apply_sensitive=False
            )
            return

        father = None
        if person.father_handle:
            father = self._read_repo.get_person_proxy(person.father_handle)

        res = self._patronymic_service.infer_patronymic(person, father)

        if res.status == PatronymicInferenceStatus.SUCCESS:
            self._suggested_patronymic = res.value
            self._view.show_suggestion(
                res.value,
                res.context.father_name,
            )
        else:
            self._view.show_status_message(res.status, apply_sensitive=False)

    def on_apply_clicked(self):
        if not self.current_handle or not self._suggested_patronymic:
            return

        try:
            self._write_repo.update_patronymic_names(
                {self.current_handle: self._suggested_patronymic}
            )

            self._view.show_status_message(
                PatronymicInferenceStatus.SUCCESS, apply_sensitive=False
            )
        except Exception as e:
            raise e

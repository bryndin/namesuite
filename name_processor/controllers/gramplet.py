from name_processor.models.result import PatronymicInferenceStatus


class GrampletController:
    def __init__(self, view, patronymic_service, read_repo, write_repo):
        self.view = view
        self.patronymic_service = patronymic_service
        self.read_repo = read_repo
        self.write_repo = write_repo
        self.current_handle = None
        self.suggested_patronymic = None

    def on_active_changed(self, handle):
        self.current_handle = handle
        self.suggested_patronymic = None

        if not handle:
            self.view.show_status_message(
                PatronymicInferenceStatus.NO_ACTIVE_PERSON, apply_sensitive=False
            )
            return

        person = self.read_repo.get_person_proxy(handle)
        if not person:
            self.view.show_status_message(
                PatronymicInferenceStatus.NO_ACTIVE_PERSON, apply_sensitive=False
            )
            return

        father = None
        if person.father_handle:
            father = self.read_repo.get_person_proxy(person.father_handle)

        res = self.patronymic_service.infer_patronymic(person, father)

        if res.status == PatronymicInferenceStatus.SUCCESS:
            self.suggested_patronymic = res.value
            self.view.show_suggestion(
                res.value,
                res.context.father_name,
            )
        else:
            self.view.show_status_message(res.status, apply_sensitive=False)

    def on_apply_clicked(self):
        if not self.current_handle or not self.suggested_patronymic:
            return

        try:
            self.write_repo.update_patronymic_names(
                {self.current_handle: self.suggested_patronymic}
            )

            self.view.show_status_message(
                PatronymicInferenceStatus.SUCCESS, apply_sensitive=False
            )
        except Exception as e:
            raise e

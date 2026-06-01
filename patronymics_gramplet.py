from gramps.gen.plug import Gramplet

from name_processor.drivers.db_wrapper import GrampsDbWrapper
from name_processor.services.patronymic_inference import PatronymicInferenceService
from name_processor.controllers.gramplet_controller import GrampletController
from name_processor.ui.gramplet_view import GrampletView


class PatronymicSuggestionGramplet(Gramplet):
    def __init__(self, dbstate):
        self.dbstate = dbstate
        self.db_wrapper = GrampsDbWrapper(self.dbstate)

        self.inference_service = PatronymicInferenceService(self.db_wrapper)
        self.view = GrampletView(self)
        self.controller = GrampletController(self.view, self.inference_service)
        self.view.set_controller(self.controller)

    def build_widget(self):
        self.view.init()
        return self.view.get_root_widget()

    def active_changed(self, handle):
        self.controller.on_active_changed(handle)

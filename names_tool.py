# names_tool.py
# -*- coding: utf-8 -*-

from gramps.gui.plug import tool

from name_processor.drivers.db_wrapper import GrampsDbWrapper
from name_processor.services.patronymic_inference import PatronymicInferenceService
from name_processor.services.rename import RenameService
from name_processor.services.patronymic_audit import PatronymicAuditService
from name_processor.controllers.tool_controller import ToolController
from name_processor.ui.tool_window import NamesToolWindow


class NamesTool(tool.Tool):
    def __init__(self, dbstate, user, options_class, name, callback=None):
        self.db_wrapper = GrampsDbWrapper(dbstate)

        # Initialize Services with the wrapper for persistence layer access
        self.inference_service = PatronymicInferenceService(self.db_wrapper)
        self.standardizer_service = RenameService(self.db_wrapper)
        self.audit_service = PatronymicAuditService(self.db_wrapper)

        # Instantiate View and Controller layers
        self.view = NamesToolWindow(callback)
        self.controller = ToolController(
            self.view,
            self.db_wrapper,
            user,
            self.inference_service,
            self.standardizer_service,
            self.audit_service,
        )

        self.view.set_controller(self.controller)
        tool.Tool.__init__(self, dbstate, options_class, name)

    def run(self):
        self.view.window.show_all()


class NamesToolOptions(tool.ToolOptions):
    def __init__(self, name, person_id=None):
        tool.ToolOptions.__init__(self, name, person_id)

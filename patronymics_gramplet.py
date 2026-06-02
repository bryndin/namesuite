from typing import Generator, Callable, Any, Optional

from gi.repository import GLib

from gramps.gen.plug import Gramplet
from gramps.gen.types import PersonHandle

from name_processor.repositories.gramps_read import GrampsReadRepository
from name_processor.repositories.gramps_write import GrampsWriteRepository
from name_processor.services.patronymic import PatronymicInferenceService
from name_processor.services.confidence_engine import ConfidenceEngine
from name_processor.services.chronology import ChronologyService
from name_processor.controllers.gramplet import GrampletController
from name_processor.views.gramplet import GrampletView
from name_processor.models.result import PatronymicInferenceStatus
from name_processor.utils.gtk_runner import run_in_idle_loop


class PatronymicSuggestionGramplet(Gramplet):
    def __init__(self, gui, nav_group: int = 0) -> None:
        # 1. Declare placeholders BEFORE running the parent constructor
        self.view = None
        self.controller = None
        self.read_repo = None
        self.write_repo = None
        self.confidence_engine = None
        self.chronology_service = None
        self.patronymic_service = None

        # 2. Run super constructor (which invokes init() and db_changed())
        super().__init__(gui, nav_group)

    def init(self) -> None:
        """
        Runs once when the Gramplet is registered.
        Sets up the static visual interface.
        """
        self.view = GrampletView(self)
        self.view.init()

        # Swap default textview with custom layout (runs once)
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.WIDGET = self.view.get_root_widget()
        self.gui.get_container_widget().add(self.gui.WIDGET)
        self.gui.WIDGET.show()

    def db_changed(self) -> None:
        """
        Overridden to recreate the database-dependent dependency graph
        whenever the database state changes (e.g., opened, switched, or closed).
        """
        if self.dbstate.is_open():
            # Recreate repositories tied to the new database session
            self.read_repo = GrampsReadRepository(self.dbstate)
            self.write_repo = GrampsWriteRepository(self.dbstate)

            # Recreate domain services
            self.confidence_engine = ConfidenceEngine(self.read_repo)
            self.chronology_service = ChronologyService(self.read_repo)
            self.patronymic_service = PatronymicInferenceService(
                self.read_repo, self.confidence_engine, self.chronology_service
            )

            # Recreate the controller and link it to the existing view
            self.controller = GrampletController(
                self.view,
                self.patronymic_service,
                self.read_repo,
                self.write_repo,
            )
            if self.view:
                self.view.set_controller(self.controller)

            # Start the non-blocking database scan
            self._start_background_median_calc()
        else:
            # DB has closed - cleanly tear down backend dependencies
            self._median_generator = None
            self.controller = None
            if self.view:
                self.view.set_controller(None)
                self.view.show_status_message(
                    PatronymicInferenceStatus.NO_ACTIVE_PERSON, apply_sensitive=False
                )

    def active_changed(self, handle: PersonHandle) -> None:
        """Called automatically by Gramps when the active person changes."""
        if self.dbstate.is_open() and self.controller:
            self.controller.on_active_changed(handle)

    def _start_background_median_calc(self) -> None:
        if not self.read_repo:
            return

        # 1. Get the generator from the repository
        median_generator = self.read_repo.get_database_median_year_chunked()

        # 2. Define what happens when it finishes
        def on_median_calculated(median_year: int | None) -> None:
            if median_year is not None and self.chronology_service:
                self.chronology_service.set_db_median_year(median_year)

                # Update UI if needed
                if self.controller and self.controller.current_handle:
                    self.controller.on_active_changed(self.controller.current_handle)

        # 3. Hand it to the generic runner
        run_in_idle_loop(median_generator, on_complete=on_median_calculated)

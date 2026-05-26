# patronymics_gramplet.py
# -*- coding: utf-8 -*-
"""
patronymics_gramplet.py

Real-time sidebar suggestion widget. Reacts instantly to active-person-changed
signals, evaluates eligibility, and commits quick-apply single writes.
"""

from gi.repository import Gtk

# Gramps modules
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.plug import Gramplet
from gramps.gen.lib import Person
from gramps.gui.dialog import ErrorDialog

# Local modules
from pat_engine.inference_service import PatronymicInferenceService
from pat_engine.entities import InferenceCandidate
from pat_engine.utils import has_patronymic_surname
from utils import PatronymicMixin

_ = glocale.translation.gettext


class InferPatronymicsGramplet(PatronymicMixin, Gramplet):
    """
    Gramplet sidebar component offering fast inline suggestion matches.
    """

    def init(self):
        """Sets up the GTK user interface panel."""
        self.title = _("Patronymic Suggestion")
        self.current_handle = None
        self.suggested_candidate = None
        self.inference_service = PatronymicInferenceService(self.dbstate.db)

        # Build UI Box
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.box.set_border_width(8)

        # Display Message
        self.label = Gtk.Label(
            label=_("Navigate to an individual to check patronymic status.")
        )
        self.label.set_xalign(0.0)
        self.label.set_line_wrap(True)
        self.box.pack_start(self.label, True, True, 0)

        # Action Trigger
        self.apply_btn = Gtk.Button(label=_("Apply Suggestion"))
        self.apply_btn.set_sensitive(False)
        self.apply_btn.connect("clicked", self.on_apply_clicked)
        self.box.pack_start(self.apply_btn, False, False, 0)

        # Install widget container
        self.gui.WIDGET = self.box
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add(self.gui.WIDGET)
        self.gui.WIDGET.show_all()

    def active_changed(self, handle):
        """
        Signals listener execution. Resolves candidates immediately
        when the active person changes in the primary navigator.
        """
        self.current_handle = handle
        self.suggested_candidate = None

        if not handle:
            self.label.set_text(_("No active person selected."))
            self.apply_btn.set_sensitive(False)
            return

        person = self.dbstate.db.get_person_from_handle(handle)
        if not person:
            self.label.set_text(_("No active person selected."))
            self.apply_btn.set_sensitive(False)
            return

        # 1. Reset and sanity check gender
        gender_val = person.get_gender()
        if gender_val not in (Person.MALE, Person.FEMALE):
            self.label.set_text(
                _(
                    "Patronymic inference can't be inferred for non-binary or unknown genders."
                )
            )
            self.apply_btn.set_sensitive(False)
            return

        # 2. Check if patronymic exists via schema-safe check
        primary_name = person.get_primary_name()
        if has_patronymic_surname(primary_name):
            self.label.set_text(_("Individual already has a recorded patronymic."))
            self.apply_btn.set_sensitive(False)
            return

        # 3. Call inference service
        father_handle = self.inference_service.get_father_handle(person)
        if not father_handle:
            self.label.set_text(
                _("No attached father found in database family records.")
            )
            self.apply_btn.set_sensitive(False)
            return

        father = self.dbstate.db.get_person_from_handle(father_handle)
        if not father or not father.get_primary_name().get_first_name():
            self.label.set_text(_("Father lacks a recorded first name."))
            self.apply_btn.set_sensitive(False)
            return

        father_name = father.get_primary_name().get_first_name()

        # Evaluate using service
        ref_year, rule_source = self.inference_service.resolve_reference_year(person)
        confidence = self.inference_service.evaluate_confidence(
            person, primary_name, father_name
        )

        from pat_engine.morphology import generate_east_slavic_patronymic

        patronymic = generate_east_slavic_patronymic(
            father_name=father_name,
            is_male=(gender_val == Person.MALE),
            year=ref_year,
            pre_reform_script=False,
        )

        if patronymic:
            self.suggested_candidate = InferenceCandidate(
                person_handle=handle,
                gramps_id=person.gramps_id,
                display_name=person.get_primary_name().get_regular_name(),
                father_name=father_name,
                reference_year=ref_year,
                inferred_patronymic=patronymic,
                confidence=confidence,
                rule_source=rule_source,
            )
            self.label.set_text(
                _(
                    "Missing Patronymic Detected.\nSuggested: {0}\nBased on father: {1}"
                ).format(patronymic, father_name)
            )
            self.apply_btn.set_sensitive(True)
        else:
            self.label.set_text(_("Could not generate valid morphology patterns."))
            self.apply_btn.set_sensitive(False)

    def on_apply_clicked(self, widget):
        """Commits the suggested patronymic change directly inside a secure transaction."""
        if not self.current_handle or not self.suggested_candidate:
            return

        try:
            from pat_engine.logging import generate_execution_id

            exec_id = generate_execution_id()
            self.inference_service.apply_patronymics_batch(
                [self.suggested_candidate], exec_id, pre_reform=False
            )
        except Exception as e:
            ErrorDialog(_("Transaction Failed"), str(e), self.gui.get_window())
            return

        # Clean GUI state
        self.label.set_text(_("Patronymic applied successfully!"))
        self.apply_btn.set_sensitive(False)

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
from gramps.gen.db import DbTxn
from gramps.gen.lib import Surname, NameOriginType, Person

# Local modules
from engine.morphology import generate_east_slavic_patronymic

_ = glocale.translation.gettext


# Schema compatibility check
def has_patronymic_surname(name_obj) -> bool:
    """
    Returns True if the Name object contains any Surname marked as a PATRONYMIC.
    """
    for surname in name_obj.get_surname_list():
        orig = surname.get_origintype()
        if (
            orig == NameOriginType.PATRONYMIC
            or orig == 5
            or getattr(orig, "value", None) == NameOriginType.PATRONYMIC
            or getattr(orig, "value", None) == 5
            or str(orig).strip() == "Patronymic"
        ):
            return True
    return False


class InferPatronymicsGramplet(Gramplet):
    """
    Gramplet sidebar component offering fast inline suggestion matches.
    """

    def init(self):
        """Sets up the GTK user interface panel."""
        self.title = _("Patronymic Suggestion")
        self.current_handle = None
        self.suggested_value = None

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
        self.suggested_value = None

        if not handle:
            self.label.set_text(_("No active person selected."))
            self.apply_btn.set_sensitive(False)
            return

        person = self.dbstate.db.get_person_from_handle(handle)
        if not person:
            self.label.set_text(_("No active person selected."))
            self.apply_btn.set_sensitive(False)
            return

        # Check if patronymic exists via schema-safe loop
        primary_name = person.get_primary_name()
        if has_patronymic_surname(primary_name):
            self.label.set_text(_("Individual already has a recorded patronymic."))
            self.apply_btn.set_sensitive(False)
            return

        # Navigate to father
        father_handle = self.get_father_handle(person)
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

        # Resolve binary gender translation at the boundary
        gender_val = person.get_gender()
        if gender_val not in (Person.MALE, Person.FEMALE):
            # Skip persons with OTHER or UNKNOWN genders as traditional patronymic
            # suffix grammar cannot be deterministically inferred for them.
            return

        # Run inference using standard modern standard defaults for inline matches
        patronymic = generate_east_slavic_patronymic(
            father_name=father_name,
            is_male=(gender_val == Person.MALE),
            year=1950,  # Standard default
            pre_reform_script=False,
        )

        if patronymic:
            self.suggested_value = patronymic
            self.label.set_text(
                _(
                    "Missing Patronymic Detected.\nSuggested: {0}\nBased on father: {1}"
                ).format(patronymic, father_name)
            )
            self.apply_btn.set_sensitive(True)
        else:
            self.label.set_text(_("Could not generate valid morphology patterns."))
            self.apply_btn.set_sensitive(False)

    def get_father_handle(self, person):
        for fam_handle in person.get_parent_family_handle_list():
            fam = self.dbstate.db.get_family_from_handle(fam_handle)
            if fam and fam.get_father_handle() != "":
                return fam.get_father_handle()
        return None

    def on_apply_clicked(self, widget):
        """Commits the suggested patronymic change directly inside a secure transaction."""
        if not self.current_handle or not self.suggested_value:
            return

        # Open database writing transaction context
        with DbTxn(_("Apply Single Patronymic"), self.dbstate.db) as txn:
            person = self.dbstate.db.get_person_from_handle(self.current_handle)
            if person:
                primary_name = person.get_primary_name()

                # Append standard Surname object to list
                surn_obj = Surname()
                surn_obj.set_surname(self.suggested_value)
                surn_obj.set_origintype(NameOriginType.PATRONYMIC)
                surn_obj.set_primary(False)

                primary_name.add_surname(surn_obj)

                self.dbstate.db.commit_person(person, txn)

        # Clean GUI state
        self.label.set_text(_("Patronymic applied successfully!"))
        self.apply_btn.set_sensitive(False)

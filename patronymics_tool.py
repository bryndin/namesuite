# patronymics_tool.py
# -*- coding: utf-8 -*-
"""
patronymics_tool.py

Batch Tool Addon for Gramps. Scan records, evaluate multi-signal confidence,
and batch-apply inferred patronymic name fields with clean reversibility logs.
"""

import os
import re
import logging
from gi.repository import Gtk, Gdk, GObject

# Gramps modules
from gramps.gen.const import GRAMPS_LOCALE as glocale

_ = glocale.translation.gettext

from gramps.gui.plug import tool
from gramps.gen.db import DbTxn
from gramps.gen.lib import Surname, NameOriginType
from gramps.gui.dialog import OkDialog, ErrorDialog

# Custom modular imports
from engine.morphology import generate_east_slavic_patronymic
from engine.logging import InferenceLogManager, generate_execution_id

# Slavic surname regex markers (Cyrillic and Latin transliterated)
SLAVIC_SURNAME_PATTERN = re.compile(
    r"(ов|ев|ин|ын|енко|чук|ко|ова|ева|ина|ына|ov|ev|in|enko|chuk|sky|ska)$",
    re.IGNORECASE,
)


# Helpers to navigate the Surname List schema
def has_patronymic_surname(name_obj) -> bool:
    """Returns True if the Name object contains any Surname marked as a PATRONYMIC."""
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


def get_patronymic_value(name_obj) -> str:
    """Finds and returns the string value of the patronymic Surname object."""
    for surname in name_obj.get_surname_list():
        orig = surname.get_origintype()
        if (
            orig == NameOriginType.PATRONYMIC
            or orig == 5
            or getattr(orig, "value", None) == NameOriginType.PATRONYMIC
            or getattr(orig, "value", None) == 5
            or str(orig).strip() == "Patronymic"
        ):
            return surname.get_surname()
    return ""


class InferPatronymicsTool(tool.Tool):
    """
    GTK Batch Processing Wizard to evaluate, filter, and write
    inferred patronymic records safely.
    """

    def __init__(self, dbstate, user, options_class, name, callback=None, **kwargs):
        """
        Initializes the Gramps Tool window.
        """
        self.user = user
        self.dbstate = dbstate
        self.db = dbstate.db
        self.callback = callback

        # Invoke core Tool initialization with correct signature
        tool.Tool.__init__(self, dbstate, options_class, name)

        # Extract unique DB directory name to isolate the logs
        db_path = self.db.get_dbname()
        self.db_id = os.path.basename(os.path.normpath(db_path))
        self.log_manager = InferenceLogManager(self.db_id)

        # In-memory storage of calculated candidates
        self.scanned_candidates = []

        # Build GTK Window UI
        self.build_window()

    def build_window(self):
        self.window = Gtk.Window(title=_("Infer East Slavic Patronymics"))
        self.window.set_default_size(850, 550)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.set_border_width(12)

        # Connect window destroy signal
        self.window.connect("destroy", self.on_destroy)

        # Main layout container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.window.add(main_box)

        # Notebook / Tabs
        notebook = Gtk.Notebook()
        main_box.pack_start(notebook, True, True, 0)

        # --- TAB 1: Scan & Apply ---
        scan_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        scan_box.set_border_width(8)
        notebook.append_page(scan_box, Gtk.Label(label=_("Inference Engine")))

        # Configuration Controls Panel
        config_frame = Gtk.Frame(label=_("Inference Options"))
        scan_box.pack_start(config_frame, False, False, 0)

        config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        config_box.set_border_width(8)
        config_frame.add(config_box)

        # Dry-run setting
        self.dry_run_check = Gtk.CheckButton(
            label=_("Dry-Run Simulation (Do not write changes to database)")
        )
        self.dry_run_check.set_active(True)
        self.dry_run_check.connect("toggled", self.on_dry_run_toggled)
        config_box.pack_start(self.dry_run_check, False, False, 0)

        # Script matching check
        self.script_check = Gtk.CheckButton(
            label=_("Automatically match Pre-Revolutionary Orthography (ъ/і)")
        )
        self.script_check.set_active(True)
        config_box.pack_start(self.script_check, False, False, 0)

        # Scan trigger button
        self.scan_btn = Gtk.Button(label=_("Scan Database"))
        self.scan_btn.connect("clicked", self.on_scan_clicked)
        config_box.pack_start(self.scan_btn, False, False, 0)

        # TreeView panel for scans
        scroll_win = Gtk.ScrolledWindow()
        scroll_win.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scan_box.pack_start(scroll_win, True, True, 0)

        # TreeView Model structure: [Include, PersonName, FatherName, ReferenceYear, InferredPatronymic, Confidence, RulesString, Handle]
        self.list_store = Gtk.ListStore(bool, str, str, int, str, str, str, str)
        self.tree_view = Gtk.TreeView(model=self.list_store)
        scroll_win.add(self.tree_view)
        self.setup_tree_columns()

        # Execution Controls
        self.exec_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        scan_box.pack_start(self.exec_box, False, False, 0)

        self.apply_btn = Gtk.Button(label=_("Commit Checked Inferences"))
        self.apply_btn.set_sensitive(False)
        self.apply_btn.connect("clicked", self.on_apply_clicked)
        self.exec_box.pack_end(self.apply_btn, False, False, 0)

        # --- TAB 2: Reversibility & Rollbacks ---
        rollback_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        rollback_box.set_border_width(8)
        notebook.append_page(rollback_box, Gtk.Label(label=_("Transaction Reversions")))

        rollback_label = Gtk.Label(
            label=_("Select a past execution run to revert its changes:")
        )
        rollback_label.set_xalign(0)
        rollback_box.pack_start(rollback_label, False, False, 0)

        # Scrolled window for log records
        log_scroll = Gtk.ScrolledWindow()
        log_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        rollback_box.pack_start(log_scroll, True, True, 0)

        # Log ListStore: [ExecutionID, Date/Time, InferencesCount, SuffixEngine]
        self.log_store = Gtk.ListStore(str, str, int, str)
        self.log_tree = Gtk.TreeView(model=self.log_store)
        log_scroll.add(self.log_tree)
        self.setup_log_columns()

        # Rollback actions panel
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        rollback_box.pack_start(action_box, False, False, 0)

        self.revert_btn = Gtk.Button(label=_("Revert Selected Run"))
        self.revert_btn.connect("clicked", self.on_revert_clicked)
        action_box.pack_end(self.revert_btn, False, False, 0)

        # Load any existing history
        self.refresh_log_history()

        # Show window components
        self.window.show_all()

    def on_destroy(self, widget):
        self.window.destroy()

    def setup_tree_columns(self):
        """Creates table headers and columns for scanned candidates."""
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self.on_row_toggled)
        col_toggle = Gtk.TreeViewColumn(_("Apply"), renderer_toggle, active=0)
        self.tree_view.append_column(col_toggle)

        col_person = Gtk.TreeViewColumn(_("Individual"), Gtk.CellRendererText(), text=1)
        self.tree_view.append_column(col_person)

        col_father = Gtk.TreeViewColumn(_("Father"), Gtk.CellRendererText(), text=2)
        self.tree_view.append_column(col_father)

        col_year = Gtk.TreeViewColumn(
            _("Reference Year"), Gtk.CellRendererText(), text=3
        )
        self.tree_view.append_column(col_year)

        col_pat = Gtk.TreeViewColumn(
            _("Inferred Patronymic"), Gtk.CellRendererText(), text=4
        )
        self.tree_view.append_column(col_pat)

        col_conf = Gtk.TreeViewColumn(_("Confidence"), Gtk.CellRendererText(), text=5)
        self.tree_view.append_column(col_conf)

        col_rules = Gtk.TreeViewColumn(
            _("Historical Context Rule"), Gtk.CellRendererText(), text=6
        )
        self.tree_view.append_column(col_rules)

    def setup_log_columns(self):
        """Creates table headers for rollback histories."""
        self.log_tree.append_column(
            Gtk.TreeViewColumn(_("Execution ID"), Gtk.CellRendererText(), text=0)
        )
        self.log_tree.append_column(
            Gtk.TreeViewColumn(_("Execution Timestamp"), Gtk.CellRendererText(), text=1)
        )
        self.log_tree.append_column(
            Gtk.TreeViewColumn(_("Changes Written"), Gtk.CellRendererText(), text=2)
        )
        self.log_tree.append_column(
            Gtk.TreeViewColumn(_("Plugin Applied"), Gtk.CellRendererText(), text=3)
        )

    def on_dry_run_toggled(self, widget):
        self.update_action_buttons()

    def on_row_toggled(self, widget, path):
        self.list_store[path][0] = not self.list_store[path][0]

    def update_action_buttons(self):
        """Sets sensitive states of GTK controls dynamically."""
        has_results = len(self.list_store) > 0
        is_dry_run = self.dry_run_check.get_active()

        if is_dry_run:
            self.apply_btn.set_sensitive(False)
            self.apply_btn.set_label(_("Dry-Run Active (No Commit)"))
        else:
            self.apply_btn.set_sensitive(has_results)
            self.apply_btn.set_label(_("Commit Checked Inferences"))

    def refresh_log_history(self):
        """Reloads and binds the list of prior JSON logged execution profiles."""
        self.log_store.clear()
        executions = self.log_manager.get_executions()
        for run in executions:
            self.log_store.append(
                [
                    run.get("execution_id", ""),
                    run.get("timestamp", ""),
                    len(run.get("changes", [])),
                    run.get("plugin_id", ""),
                ]
            )

    def has_cyrillic(self, text):
        return bool(re.search(r"[\u0400-\u04FF]", text))

    def evaluate_confidence(self, person, primary_name, father_first_name) -> float:
        """
        Multi-Signal Applicability Engine.
        Calculates a score between 0.0 and 1.0.
        Requires at least 0.60 to pass auto-inference checks.
        """
        score = 0.0

        # Signal 1: Cyrillic Script Check (+0.50)
        # Direct indicator of East Slavic localizations
        full_name_str = primary_name.get_regular_name()
        if self.has_cyrillic(full_name_str) or self.has_cyrillic(father_first_name):
            score += 0.50

        # Signal 2: Slavic Surname Ends (+0.20)
        for surname_obj in primary_name.get_surname_list():
            sur_str = surname_obj.get_surname()
            if sur_str and SLAVIC_SURNAME_PATTERN.search(sur_str):
                score += 0.20

        # Signal 3: Sibling Patronymic Presence (+0.30)
        for fam_handle in person.get_parent_family_handle_list():
            fam = self.db.get_family_from_handle(fam_handle)
            if fam:
                for child_ref in fam.get_child_ref_list():
                    if child_ref.ref != person.handle:
                        sib = self.db.get_person_from_handle(child_ref.ref)
                        if sib and has_patronymic_surname(sib.get_primary_name()):
                            score += 0.30
                            break

        return min(score, 1.0)

    def on_scan_clicked(self, widget):
        """Scans the database and populates our list of candidates."""
        self.list_store.clear()
        self.scanned_candidates = []

        for handle in self.db.get_person_handles():
            person = self.db.get_person_from_handle(handle)
            if not person:
                continue

            primary_name = person.get_primary_name()

            # Execute schema-compliant check for existing patronymic Surnames
            if has_patronymic_surname(primary_name):
                continue

            father_handle = self.get_father_handle(person)
            if not father_handle:
                continue
            father = self.db.get_person_from_handle(father_handle)
            if not father:
                continue

            father_first_name = father.get_primary_name().get_first_name()
            if not father_first_name:
                continue

            # Check applicability confidence scores
            confidence = self.evaluate_confidence(
                person, primary_name, father_first_name
            )
            if confidence < 0.60:
                # Silently skip individuals (such as Skłodowska or Dostoevsky written in Latin)
                # who do not meet our strict cultural applicability thresholds
                continue

            ref_year, rule_source = self.resolve_reference_year(person)
            pre_reform = (
                self.script_check.get_active()
                if self.script_check.get_active()
                else False
            )

            patronymic = generate_east_slavic_patronymic(
                father_name=father_first_name,
                gender=person.get_gender(),
                year=ref_year,
                pre_reform_script=pre_reform,
            )

            if patronymic:
                self.list_store.append(
                    [
                        True,
                        primary_name.get_regular_name(),
                        father_first_name,
                        ref_year if ref_year else 0,
                        patronymic,
                        f"{int(confidence * 100)}%",
                        rule_source,
                        handle,
                    ]
                )

        self.update_action_buttons()

    def get_father_handle(self, person):
        for fam_handle in person.get_parent_family_handle_list():
            fam = self.db.get_family_from_handle(fam_handle)
            if fam and fam.get_father_handle() != "":
                return fam.get_father_handle()
        return None

    def resolve_reference_year(self, person):
        # 1. Death Year
        for event_ref in person.get_event_ref_list():
            event = self.db.get_event_from_handle(event_ref.ref)
            if event and event.get_type() == 4:  # Death
                date_obj = event.get_date_object()
                if date_obj and date_obj.get_year():
                    return date_obj.get_year(), _("Death Year")

        # 2. Earliest Event
        earliest_year = None
        for event_ref in person.get_event_ref_list():
            event = self.db.get_event_from_handle(event_ref.ref)
            if event:
                date_obj = event.get_date_object()
                if date_obj and date_obj.get_year():
                    yr = date_obj.get_year()
                    if earliest_year is None or yr < earliest_year:
                        earliest_year = yr
        if earliest_year:
            return earliest_year, _("Earliest Event Year")

        # 3. Birth Year
        for event_ref in person.get_event_ref_list():
            event = self.db.get_event_from_handle(event_ref.ref)
            if event and event.get_type() == 2:  # Birth
                date_obj = event.get_date_object()
                if date_obj and date_obj.get_year():
                    return date_obj.get_year(), _("Birth Year")

        # 4. Generational Heuristics
        father_handle = self.get_father_handle(person)
        if father_handle:
            father = self.db.get_person_from_handle(father_handle)
            if father:
                for event_ref in father.get_event_ref_list():
                    event = self.db.get_event_from_handle(event_ref.ref)
                    if event and event.get_type() == 2:
                        date_obj = event.get_date_object()
                        if date_obj and date_obj.get_year():
                            return date_obj.get_year() + 25, _(
                                "Generational Estimation"
                            )

        return 1920, _("Default Modern Era")

    def on_apply_clicked(self, widget):
        changes_to_apply = []
        for row in self.list_store:
            if row[0]:
                changes_to_apply.append(
                    {
                        "handle": row[7],
                        "patronymic": row[4],
                        "ref_year": row[3],
                        "pre_reform": self.script_check.get_active(),
                    }
                )

        if not changes_to_apply:
            OkDialog(
                _("No Checked Records"),
                _("Please select at least one record to apply."),
                self.window,
            )
            return

        exec_id = generate_execution_id()
        logged_changes = []

        with DbTxn(_("Apply Patronymics"), self.db) as txn:
            for item in changes_to_apply:
                person = self.db.get_person_from_handle(item["handle"])
                if person:
                    primary_name = person.get_primary_name()
                    orig_pat = get_patronymic_value(primary_name)

                    # Create standard Surname object to append to list
                    surn_obj = Surname()
                    surn_obj.set_surname(item["patronymic"])
                    surn_obj.set_origintype(NameOriginType.PATRONYMIC)
                    surn_obj.set_primary(False)

                    primary_name.add_surname(surn_obj)

                    self.db.update_person(person, txn)

                    logged_changes.append(
                        {
                            "person_handle": item["handle"],
                            "name_handle": primary_name.handle,
                            "original_value": orig_pat,
                            "inferred_value": item["patronymic"],
                            "father_handle": self.get_father_handle(person),
                            "reference_year": item["ref_year"],
                            "pre_reform": item["pre_reform"],
                            "confidence_score": 0.94,
                            "applied_heuristics": ["DEATH_OR_BIRTH_PIVOT"],
                        }
                    )

        self.log_manager.log_execution(
            exec_id, "east_slavic_patronymic", logged_changes
        )

        self.list_store.clear()
        self.apply_btn.set_sensitive(False)
        self.refresh_log_history()

        OkDialog(
            _("Success"), _("Inferences applied and logged successfully."), self.window
        )

    def on_revert_clicked(self, widget):
        selection = self.log_tree.get_selection()
        model, tree_iter = selection.get_selected()
        if not tree_iter:
            OkDialog(
                _("No Selection"),
                _("Please select a transaction to revert."),
                self.window,
            )
            return

        exec_id = model.get_value(tree_iter, 0)

        try:
            log_path = self.log_manager.log_filepath
            report = rollback_batch_execution(self.db, log_path, exec_id)
            self.refresh_log_history()

            msg = _(
                "Rollback complete.\nReverted: {0}\nSkipped (Edited by User): {1}"
            ).format(len(report["reverted"]), len(report["skipped_modified"]))
            OkDialog(_("Rollback Executed"), msg, self.window)
        except Exception as e:
            ErrorDialog(_("Rollback Error"), str(e), self.window)


def rollback_batch_execution(db, log_file_path, target_execution_id):
    import json

    with open(log_file_path, "r", encoding="utf-8") as f:
        log_data = json.load(f)

    execution = None
    for run in log_data.get("executions", []):
        if run.get("execution_id") == target_execution_id:
            execution = run
            break

    if not execution:
        raise ValueError("Execution ID not found in transaction logs.")

    report = {"reverted": [], "skipped_modified": []}

    with DbTxn(_("Rollback Patronymics"), db) as txn:
        for change in execution["changes"]:
            person = db.get_person_from_handle(change["person_handle"])
            if not person:
                continue

            primary_name = person.get_primary_name()
            if primary_name.handle == change["name_handle"]:
                current_value = get_patronymic_value(primary_name)

                if current_value == change["inferred_value"]:
                    # Safely remove the added patronymic Surname object from the Surname List
                    surnames = primary_name.get_surname_list()
                    new_surnames = []
                    for s in surnames:
                        orig = s.get_origintype()
                        is_patro = (
                            orig == NameOriginType.PATRONYMIC
                            or orig == 5
                            or getattr(orig, "value", None) == NameOriginType.PATRONYMIC
                            or getattr(orig, "value", None) == 5
                            or str(orig).strip() == "Patronymic"
                        )
                        if is_patro and s.get_surname() == change["inferred_value"]:
                            # If there was a previous patronymic, restore it. Otherwise drop.
                            if change["original_value"]:
                                s.set_surname(change["original_value"])
                                new_surnames.append(s)
                        else:
                            new_surnames.append(s)

                    primary_name.set_surname_list(new_surnames)
                    db.update_person(person, txn)
                    report["reverted"].append(person.handle)
                else:
                    report["skipped_modified"].append(person.handle)

    executions = [
        run
        for run in log_data["executions"]
        if run.get("execution_id") != target_execution_id
    ]
    log_data["executions"] = executions
    with open(log_file_path, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    return report


# -------------------------------------------------------------------------
# InferPatronymicsOptions
# -------------------------------------------------------------------------
class InferPatronymicsOptions(tool.ToolOptions):
    """
    Defines options and provides a handling interface for the patronymic inference tool.
    Even when using a completely custom GTK interface, Gramps requires this class
    to satisfy its plugin runner initialization.
    """

    def __init__(self, name, person_id=None):
        """Initializes the options class."""
        tool.ToolOptions.__init__(self, name, person_id)

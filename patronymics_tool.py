# patronymics_tool.py
# -*- coding: utf-8 -*-
"""
patronymics_tool.py

Batch Tool Addon for Gramps. Scan records, evaluate multi-signal confidence,
batch-apply inferred patronymics, and run morphological consistency audits (linter)
with clean transaction logging and total reversibility.
"""

import os
import re
from gi.repository import Gtk, GLib

# Gramps modules
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gui.plug import tool
from gramps.gen.db import DbTxn
from gramps.gen.lib import Surname, NameOriginType, Person
from gramps.gui.dialog import OkDialog, ErrorDialog

# Custom modular imports
from engine.morphology import generate_east_slavic_patronymic, SLAVIC_SURNAME_PATTERN
from engine.logging import InferenceLogManager, generate_execution_id
from engine.linter import RuleEngine, RuleContext, PlaceCache
from utils import PatronymicMixin, has_patronymic_surname

_ = glocale.translation.gettext


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


def update_or_add_patronymic(primary_name, new_patronymic_value) -> str:
    """
    Updates an existing patronymic Surname object in the list, or adds a new one.
    Returns the original patronymic value (or empty string).
    """
    surnames = primary_name.get_surname_list()
    orig_pat = ""
    found = False

    for s in surnames:
        orig = s.get_origintype()
        is_patro = (
            orig == NameOriginType.PATRONYMIC
            or orig == 5
            or getattr(orig, "value", None) == NameOriginType.PATRONYMIC
            or getattr(orig, "value", None) == 5
            or str(orig).strip() == "Patronymic"
        )
        if is_patro:
            orig_pat = s.get_surname()
            s.set_surname(new_patronymic_value)
            found = True
            break

    if not found:
        surn_obj = Surname()
        surn_obj.set_surname(new_patronymic_value)
        surn_obj.set_origintype(NameOriginType.PATRONYMIC)
        surn_obj.set_primary(False)
        primary_name.add_surname(surn_obj)

    return orig_pat


class InferPatronymicsTool(PatronymicMixin, tool.Tool):
    """
    GTK Batch Processing Wizard to evaluate, filter, and write
    inferred patronymic records safely, alongside morphological linter audits.
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

        # Initialize Linter Engine and active rules list
        self.linter_engine = RuleEngine()
        self.enabled_rules = {rule.rule_id: True for rule in self.linter_engine.rules}

        # Build GTK Window UI
        self.build_window()

    def build_window(self):
        self.window = Gtk.Window(title=_("Infer East Slavic Patronymics"))
        self.window.set_default_size(900, 600)
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

        # --- TAB 1: Scan & Apply (Inference Engine) ---
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
        self.script_check.set_active(False)
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

        # --- TAB 2: Database Auditor (The Linter) ---
        audit_tab_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        audit_tab_box.set_border_width(8)
        notebook.append_page(audit_tab_box, Gtk.Label(label=_("Database Auditor")))

        # Filter and Configuration Header Frame
        audit_header_frame = Gtk.Frame(label=_("Auditing Settings"))
        audit_tab_box.pack_start(audit_header_frame, False, False, 0)

        audit_header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        audit_header_box.set_border_width(8)
        audit_header_frame.add(audit_header_box)

        # Filter Dropdown Scope
        filter_label = Gtk.Label(label=_("Target Scope:"))
        audit_header_box.pack_start(filter_label, False, False, 0)

        self.audit_scope_combo = Gtk.ComboBoxText()
        self.audit_scope_combo.append_text(_("All Records"))
        self.audit_scope_combo.append_text(_("Males Only"))
        self.audit_scope_combo.append_text(_("Females Only"))
        self.audit_scope_combo.set_active(0)
        audit_header_box.pack_start(self.audit_scope_combo, False, False, 0)

        # Rules config trigger button
        self.rules_config_btn = Gtk.Button(label=_("Configure Rules..."))
        self.rules_config_btn.connect("clicked", self.on_configure_rules_clicked)
        audit_header_box.pack_start(self.rules_config_btn, False, False, 0)

        # Create the check button
        self.audit_pre_reform_check = Gtk.CheckButton(
            label=_("Automatically match Pre-Revolutionary Orthography (ъ/і)")
        )
        self.audit_pre_reform_check.set_active(False)
        audit_header_box.pack_start(self.audit_pre_reform_check, False, False, 0)

        # Progress panel & trigger button
        audit_action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        audit_tab_box.pack_start(audit_action_box, False, False, 0)

        self.audit_run_btn = Gtk.Button(label=_("Audit Database"))
        self.audit_run_btn.connect("clicked", self.on_audit_clicked)
        audit_action_box.pack_start(self.audit_run_btn, False, False, 0)

        self.audit_progress = Gtk.ProgressBar()
        self.audit_progress.set_show_text(True)
        audit_action_box.pack_start(self.audit_progress, True, True, 0)

        # Scrolled TreeView panel for Auditor
        audit_scroll = Gtk.ScrolledWindow()
        audit_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        audit_tab_box.pack_start(audit_scroll, True, True, 0)

        # Auditor ListStore: [Include, Person ID/Name, Current Value, Triggered Rule, Suggested Fix (Markup), Handle, Rule ID, Suggested String]
        self.audit_store = Gtk.ListStore(bool, str, str, str, str, str, str, str)
        self.audit_tree = Gtk.TreeView(model=self.audit_store)
        audit_scroll.add(self.audit_tree)
        self.setup_audit_columns()

        # Action Footer
        audit_footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        audit_tab_box.pack_start(audit_footer_box, False, False, 0)

        self.audit_select_all = Gtk.CheckButton(label=_("Select All Safe Corrections"))
        self.audit_select_all.set_active(True)
        self.audit_select_all.connect("toggled", self.on_audit_select_all_toggled)
        audit_footer_box.pack_start(self.audit_select_all, False, False, 0)

        self.audit_apply_btn = Gtk.Button(label=_("Apply Selected Corrections"))
        self.audit_apply_btn.set_sensitive(False)
        self.audit_apply_btn.connect("clicked", self.on_audit_apply_clicked)
        audit_footer_box.pack_end(self.audit_apply_btn, False, False, 0)

        # --- TAB 3: Reversibility & Rollbacks ---
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
        col_toggle = Gtk.TreeViewColumn(_("Use"), renderer_toggle, active=0)
        col_toggle.set_resizable(True)
        self.tree_view.append_column(col_toggle)

        col_person = Gtk.TreeViewColumn(_("Individual"), Gtk.CellRendererText(), text=1)
        col_person.set_resizable(True)
        col_person.set_expand(True)
        self.tree_view.append_column(col_person)

        col_father = Gtk.TreeViewColumn(_("Father"), Gtk.CellRendererText(), text=2)
        col_father.set_resizable(True)
        self.tree_view.append_column(col_father)

        col_year = Gtk.TreeViewColumn(
            _("Ref Year"), Gtk.CellRendererText(), text=3
        )
        col_year.set_resizable(True)
        self.tree_view.append_column(col_year)

        col_pat = Gtk.TreeViewColumn(
            _("Inferred Patronymic"), Gtk.CellRendererText(), text=4
        )
        col_pat.set_resizable(True)
        self.tree_view.append_column(col_pat)

        col_conf = Gtk.TreeViewColumn(_("Conf"), Gtk.CellRendererText(), text=5)
        col_conf.set_resizable(True)
        self.tree_view.append_column(col_conf)

        col_rules = Gtk.TreeViewColumn(
            _("Historical Context Rule"), Gtk.CellRendererText(), text=6
        )
        col_rules.set_resizable(True)
        col_rules.set_expand(True)
        self.tree_view.append_column(col_rules)

    def setup_audit_columns(self):
        """Creates table headers and renderers for the Auditor results."""
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self.on_audit_row_toggled)
        col_toggle = Gtk.TreeViewColumn(_("Use"), renderer_toggle, active=0)
        col_toggle.set_resizable(True)
        self.audit_tree.append_column(col_toggle)

        col_person = Gtk.TreeViewColumn(
            _("Individual ID / Name"), Gtk.CellRendererText(), text=1
        )
        col_person.set_resizable(True)
        col_person.set_expand(True)
        self.audit_tree.append_column(col_person)

        col_current = Gtk.TreeViewColumn(
            _("Current Value"), Gtk.CellRendererText(), text=2
        )
        col_current.set_resizable(True)
        self.audit_tree.append_column(col_current)

        col_rule = Gtk.TreeViewColumn(
            _("Triggered Rule"), Gtk.CellRendererText(), text=3
        )
        col_rule.set_resizable(True)
        self.audit_tree.append_column(col_rule)

        # Render suggested fixes with Pango markup
        col_suggested = Gtk.TreeViewColumn(
            _("Suggested Fix"), Gtk.CellRendererText(), markup=4
        )
        col_suggested.set_resizable(True)
        col_suggested.set_expand(True)
        self.audit_tree.append_column(col_suggested)

    def setup_log_columns(self):
        """Creates table headers for rollback histories."""
        col_exec_id = Gtk.TreeViewColumn(_("Execution ID"), Gtk.CellRendererText(), text=0)
        col_exec_id.set_resizable(True)
        self.log_tree.append_column(col_exec_id)

        col_timestamp = Gtk.TreeViewColumn(_("Execution Timestamp"), Gtk.CellRendererText(), text=1)
        col_timestamp.set_resizable(True)
        col_timestamp.set_expand(True)
        self.log_tree.append_column(col_timestamp)

        col_changes = Gtk.TreeViewColumn(_("Changes Written"), Gtk.CellRendererText(), text=2)
        col_changes.set_resizable(True)
        self.log_tree.append_column(col_changes)

        col_plugin = Gtk.TreeViewColumn(_("Plugin Applied"), Gtk.CellRendererText(), text=3)
        col_plugin.set_resizable(True)
        self.log_tree.append_column(col_plugin)

    def on_dry_run_toggled(self, widget):
        self.update_action_buttons()

    def on_row_toggled(self, widget, path):
        self.list_store[path][0] = not self.list_store[path][0]

    def on_audit_row_toggled(self, widget, path):
        self.audit_store[path][0] = not self.audit_store[path][0]
        self.update_audit_apply_button()

    def on_audit_select_all_toggled(self, widget):
        is_active = self.audit_select_all.get_active()
        for row in self.audit_store:
            row[0] = is_active
        self.update_audit_apply_button()

    def update_action_buttons(self):
        """Sets sensitive states of GTK controls dynamically for Tab 1."""
        has_results = len(self.list_store) > 0
        is_dry_run = self.dry_run_check.get_active()

        if is_dry_run:
            self.apply_btn.set_sensitive(False)
            self.apply_btn.set_label(_("Dry-Run Active (No Commit)"))
        else:
            self.apply_btn.set_sensitive(has_results)
            self.apply_btn.set_label(_("Commit Checked Inferences"))

    def update_audit_apply_button(self):
        """Sets sensitive states of GTK controls dynamically for Tab 2."""
        has_checked = any(row[0] for row in self.audit_store)
        self.audit_apply_btn.set_sensitive(has_checked)

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
        full_name_str = primary_name.get_regular_name()
        if self.has_cyrillic(full_name_str):
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

    def on_configure_rules_clicked(self, widget):
        """Opens settings dialog allowing users to toggle specific rules."""
        dialog = Gtk.Dialog(
            title=_("Configure Validation Rules"),
            parent=self.window,
            flags=Gtk.DialogFlags.MODAL,
        )
        dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        dialog.set_default_size(320, 320)

        content = dialog.get_content_area()
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        content.pack_start(scroll, True, True, 10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_border_width(10)
        scroll.add(vbox)

        checks = {}
        for rule in self.linter_engine.rules:
            chk = Gtk.CheckButton(label=f"{rule.rule_id} ({rule.severity})")
            chk.set_active(self.enabled_rules[rule.rule_id])
            vbox.pack_start(chk, False, False, 0)
            checks[rule.rule_id] = chk

        dialog.show_all()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            for r_id, chk in checks.items():
                self.enabled_rules[r_id] = chk.get_active()
        dialog.destroy()

    def on_scan_clicked(self, widget):
        """Scans the database and populates our list of candidates (Tab 1)."""
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

            # Resolve binary gender translation at the boundary
            gender_val = person.get_gender()
            if gender_val not in (Person.MALE, Person.FEMALE):
                # Skip persons with OTHER or UNKNOWN genders as traditional patronymic
                # suffix grammar cannot be deterministically inferred for them.
                continue

            patronymic = generate_east_slavic_patronymic(
                father_name=father_first_name,
                is_male=(gender_val == Person.MALE),
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

    def on_audit_clicked(self, widget):
        """Performs database-wide consistency scan using GLib.idle_add for responsive chunking."""
        self.audit_store.clear()
        self.audit_run_btn.set_sensitive(False)
        self.audit_apply_btn.set_sensitive(False)

        scope_idx = (
            self.audit_scope_combo.get_active()
        )  # 0: All, 1: Males Only, 2: Females Only
        handles = list(self.db.get_person_handles())
        total = len(handles)

        if total == 0:
            self.audit_run_btn.set_sensitive(True)
            return

        # 1. Capture the configuration state at runtime execution
        use_pre_reform = self.audit_pre_reform_check.get_active()

        self.audit_progress.set_fraction(0.0)
        self.audit_progress.set_text(f"0 / {total}")

        # Instantiate dynamic session-scoped PlaceCache
        place_cache = PlaceCache(self.db)

        # Track our progress iterator in mutable box
        idx = [0]
        active_rules = {r_id for r_id, val in self.enabled_rules.items() if val}

        def audit_idle():
            if idx[0] >= total:
                self.audit_progress.set_fraction(1.0)
                self.audit_progress.set_text(_("Audit Complete!"))
                self.audit_run_btn.set_sensitive(True)
                self.update_audit_apply_button()
                return False  # Stops the idle worker

            chunk_size = 50
            end = min(idx[0] + chunk_size, total)

            for i in range(idx[0], end):
                handle = handles[i]
                person = self.db.get_person_from_handle(handle)
                if not person:
                    continue

                gender_val = person.get_gender()

                # Filter gender scope
                if scope_idx == 1 and gender_val != Person.MALE:
                    continue
                if scope_idx == 2 and gender_val != Person.FEMALE:
                    continue

                primary_name = person.get_primary_name()
                current_pat = get_patronymic_value(primary_name)

                # We only audit individuals with existing patronymic Surnames
                if not current_pat:
                    continue

                father_handle = self.get_father_handle(person)
                father_name = ""
                if father_handle:
                    father = self.db.get_person_from_handle(father_handle)
                    if father:
                        father_name = father.get_primary_name().get_first_name() or ""

                ref_year, rule_source = self.resolve_reference_year(person)
                locale = "ru"  # V1.0 focuses on Russian locale rulesets

                ctx = RuleContext(
                    person_id=person.handle,
                    current_patronymic=current_pat,
                    father_given_name=father_name,
                    gramps_gender=gender_val,
                    reference_year=ref_year,
                    locale=locale,
                    use_pre_reform=use_pre_reform,
                    _place_resolver=place_cache.get_places,
                )

                # Run dispatcher engine
                triggered = self.linter_engine.evaluate_person(
                    ctx, enabled_rules=active_rules
                )

                for rule, change in triggered:
                    self.audit_store.append(
                        [
                            True,
                            f"{primary_name.get_regular_name()} ({person.gramps_id})",
                            current_pat,
                            rule.rule_id,
                            change.diff_markup,
                            handle,
                            rule.rule_id,
                            change.suggested_string,
                        ]
                    )

            idx[0] = end
            fraction = idx[0] / total
            self.audit_progress.set_fraction(fraction)
            self.audit_progress.set_text(f"{idx[0]} / {total}")
            return True  # Continues the idle handler

        GLib.idle_add(audit_idle)

    def on_audit_apply_clicked(self, widget):
        """Commits selected auditor suggestions inside transaction & records log."""
        changes_to_apply = []
        for row in self.audit_store:
            if row[0]:
                changes_to_apply.append(
                    {"handle": row[5], "suggested_string": row[7], "rule_id": row[6]}
                )

        if not changes_to_apply:
            OkDialog(
                _("No Checked Records"),
                _("Please select at least one correction to apply."),
                self.window,
            )
            return

        exec_id = generate_execution_id()
        logged_changes = []

        with DbTxn(_("Apply Linter Corrections"), self.db) as txn:
            for item in changes_to_apply:
                person = self.db.get_person_from_handle(item["handle"])
                if person:
                    primary_name = person.get_primary_name()

                    # Update existing Surname or append new one
                    orig_pat = update_or_add_patronymic(
                        primary_name, item["suggested_string"]
                    )
                    self.db.commit_person(person, txn)

                    logged_changes.append(
                        {
                            "person_handle": item["handle"],
                            "original_value": orig_pat,
                            "inferred_value": item["suggested_string"],
                            "father_handle": self.get_father_handle(person),
                            "reference_year": 1950,  # Default proxy year
                            "pre_reform": False,
                            "confidence_score": 1.0,  # Complete linter certainty
                            "applied_heuristics": [item["rule_id"]],
                        }
                    )

        # Append to localized reversibility log
        self.log_manager.log_execution(
            exec_id, "east_slavic_patronymic_linter", logged_changes
        )

        self.audit_store.clear()
        self.audit_apply_btn.set_sensitive(False)
        self.refresh_log_history()

        OkDialog(
            _("Success"),
            _("Auditor corrections applied and logged successfully."),
            self.window,
        )

    def resolve_reference_year(self, person):
        # Tier 1: Latest Recorded Event Year
        # Scan all events (Birth, Baptism, Marriage, Census, Death, Burial)
        # and extract the maximum (latest) valid year
        event_years = []
        for event_ref in person.get_event_ref_list():
            event = self.db.get_event_from_handle(event_ref.ref)
            if event:
                date_obj = event.get_date_object()
                if date_obj and date_obj.get_year():
                    event_years.append(date_obj.get_year())

        if event_years:
            latest_year = max(event_years)
            return latest_year, _("Latest Event Year")

        # Tier 2: Generational Lineage Heuristic
        # If no dated events, estimate using immediate family members

        # Parents: Median year of parent events + 25 years
        parent_years = []
        for fam_handle in person.get_parent_family_handle_list():
            fam = self.db.get_family_from_handle(fam_handle)
            if fam:
                # Father events
                father_handle = fam.get_father_handle()
                if father_handle:
                    father = self.db.get_person_from_handle(father_handle)
                    if father:
                        for event_ref in father.get_event_ref_list():
                            event = self.db.get_event_from_handle(event_ref.ref)
                            if event:
                                date_obj = event.get_date_object()
                                if date_obj and date_obj.get_year():
                                    parent_years.append(date_obj.get_year())
                # Mother events
                mother_handle = fam.get_mother_handle()
                if mother_handle:
                    mother = self.db.get_person_from_handle(mother_handle)
                    if mother:
                        for event_ref in mother.get_event_ref_list():
                            event = self.db.get_event_from_handle(event_ref.ref)
                            if event:
                                date_obj = event.get_date_object()
                                if date_obj and date_obj.get_year():
                                    parent_years.append(date_obj.get_year())

        if parent_years:
            median_parent_year = sorted(parent_years)[len(parent_years) // 2]
            return median_parent_year + 25, _("Generational Estimation (Parents)")

        # Siblings: Median year of sibling events
        sibling_years = []
        for fam_handle in person.get_parent_family_handle_list():
            fam = self.db.get_family_from_handle(fam_handle)
            if fam:
                for child_ref in fam.get_child_ref_list():
                    if child_ref.ref != person.handle:
                        sibling = self.db.get_person_from_handle(child_ref.ref)
                        if sibling:
                            for event_ref in sibling.get_event_ref_list():
                                event = self.db.get_event_from_handle(event_ref.ref)
                                if event:
                                    date_obj = event.get_date_object()
                                    if date_obj and date_obj.get_year():
                                        sibling_years.append(date_obj.get_year())

        if sibling_years:
            median_sibling_year = sorted(sibling_years)[len(sibling_years) // 2]
            return median_sibling_year, _("Generational Estimation (Siblings)")

        # Children: Median year of children events - 25 years
        child_years = []
        for fam_handle in person.get_family_handle_list():
            fam = self.db.get_family_from_handle(fam_handle)
            if fam:
                for child_ref in fam.get_child_ref_list():
                    child = self.db.get_person_from_handle(child_ref.ref)
                    if child:
                        for event_ref in child.get_event_ref_list():
                            event = self.db.get_event_from_handle(event_ref.ref)
                            if event:
                                date_obj = event.get_date_object()
                                if date_obj and date_obj.get_year():
                                    child_years.append(date_obj.get_year())

        if child_years:
            median_child_year = sorted(child_years)[len(child_years) // 2]
            return median_child_year - 25, _("Generational Estimation (Children)")

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

                    self.db.commit_person(person, txn)

                    logged_changes.append(
                        {
                            "person_handle": item["handle"],
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
                db.commit_person(person, txn)
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

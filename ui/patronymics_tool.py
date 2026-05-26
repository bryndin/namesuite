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
from gramps.gen.lib import Surname, NameOriginType, Person, Name, NameType
from gramps.gen.display.name import displayer as name_displayer
from gramps.gui.dialog import OkDialog, ErrorDialog
from gramps.gui.editors import EditPerson
from gramps.gen.errors import WindowActiveError

# Custom modular imports
from ui.presenters import EastSlavicToolsPresenter
from engine.rule_utils import pango_escape
from utils import (
    PatronymicMixin,
)

_ = glocale.translation.gettext


class EastSlavicNameTools(PatronymicMixin, tool.Tool):
    """
    GTK Batch Processing Wizard to infer and audit patronymic names,
    and work with given names for East Slavic locales.
    """

    # Given Names store column indices (Tab 1 - Standardize)
    GIVEN_COL_CHECKBOX = 0
    GIVEN_COL_GRAMPS_ID = 1
    GIVEN_COL_DISPLAY_NAME = 2
    GIVEN_COL_CURRENT = 3
    GIVEN_COL_PROPOSED = 4
    GIVEN_COL_ALT_ACTION = 5
    GIVEN_COL_HANDLE = 6
    GIVEN_COL_PROPOSED_RAW = 7

    # Audit store column indices
    AUDIT_COL_CHECKBOX = 0
    AUDIT_COL_DISPLAY_NAME = 1
    AUDIT_COL_GRAMPS_ID = 2
    AUDIT_COL_CURRENT_PAT = 3
    AUDIT_COL_REF_YEAR = 4
    AUDIT_COL_RULE_ID = 5
    AUDIT_COL_DIFF_MARKUP = 6
    AUDIT_COL_HANDLE = 7
    AUDIT_COL_RULE_ID_DUP = 8
    AUDIT_COL_SUGGESTED_STRING = 9
    AUDIT_COL_RULE_SOURCE = 10

    # List store column indices (Tab 1 - inference results)
    LIST_COL_CHECKBOX = 0
    LIST_COL_DISPLAY_NAME = 1
    LIST_COL_FATHER_NAME = 2
    LIST_COL_REF_YEAR = 3
    LIST_COL_PATRONYMIC = 4
    LIST_COL_CONFIDENCE = 5
    LIST_COL_RULE_SOURCE = 6
    LIST_COL_GRAMPS_ID = 7
    LIST_COL_HANDLE = 8

    # Log store column indices (Tab 3 - rollback history)
    LOG_COL_EXEC_ID = 0
    LOG_COL_TIMESTAMP = 1
    LOG_COL_CHANGES_COUNT = 2
    LOG_COL_PLUGIN_ID = 3

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

        # Initialize MVP Presenter
        self.presenter = EastSlavicToolsPresenter(self, dbstate)

        # Local view state (UI specific)
        self.enabled_rules = {rule.rule_id: True for rule in self.presenter.audit_service.linter_engine.rules}
        self.given_names_set = set()
        
        # Build GTK Window UI
        self.build_window()
        self.presenter.refresh_history()

    def update_audit_progress(self, fraction, text):
        """Callback for the presenter to update UI progress."""
        self.audit_progress.set_fraction(fraction)
        self.audit_progress.set_text(text)

    def on_audit_complete(self, total_found):
        """Callback for the presenter when audit completes."""
        self.audit_progress.set_fraction(1.0)
        self.audit_progress.set_text(_("Audit Complete!"))
        self.audit_run_btn.set_sensitive(True)
        self.update_audit_apply_button()

        if total_found == 0:
            OkDialog(
                _("No Results"),
                _("No patronymic issues found in the database."),
                self.window,
            )

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

        # --- TAB 0: Given Names (Standardization) ---
        given_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        given_box.set_border_width(8)
        notebook.append_page(given_box, Gtk.Label(label=_("Standardize Names")))

        # Config Panel
        given_config_frame = Gtk.Frame(label=_("Search and Replace Options"))
        given_box.pack_start(given_config_frame, False, False, 0)

        given_config_grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        given_config_grid.set_border_width(8)
        given_config_frame.add(given_config_grid)

        # Source Name
        given_config_grid.attach(Gtk.Label(label=_("Source Name:")), 0, 0, 1, 1)
        self.given_source_entry = Gtk.Entry()
        self.given_source_entry.set_placeholder_text(_("e.g. Иоанн"))
        given_config_grid.attach(self.given_source_entry, 1, 0, 1, 1)

        # Target Name
        given_config_grid.attach(Gtk.Label(label=_("Target Name:")), 0, 1, 1, 1)
        self.given_target_entry = Gtk.Entry()
        self.given_target_entry.set_placeholder_text(_("e.g. Иван"))
        given_config_grid.attach(self.given_target_entry, 1, 1, 1, 1)

        # Match Type
        given_config_grid.attach(Gtk.Label(label=_("Match Mode:")), 2, 0, 1, 1)
        self.given_match_type_combo = Gtk.ComboBoxText()
        self.given_match_type_combo.append_text(_("Exact Match"))
        self.given_match_type_combo.append_text(_("Substring"))
        self.given_match_type_combo.append_text(_("Regular Expression"))
        self.given_match_type_combo.set_active(0)
        given_config_grid.attach(self.given_match_type_combo, 3, 0, 1, 1)

        # Scan Button
        self.given_scan_btn = Gtk.Button(label=_("Scan for Names"))
        self.given_scan_btn.connect("clicked", self.on_given_scan_clicked)
        given_config_grid.attach(self.given_scan_btn, 3, 1, 1, 1)

        # Preservation Check
        self.preserve_alt_check = Gtk.CheckButton(
            label=_("Preserve original name as 'Also Known As' (AKA) alternate name")
        )
        self.preserve_alt_check.set_active(True)
        given_box.pack_start(self.preserve_alt_check, False, False, 0)

        # TreeView for results
        given_scroll_win = Gtk.ScrolledWindow()
        given_scroll_win.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        given_box.pack_start(given_scroll_win, True, True, 0)

        self.given_store = Gtk.ListStore(bool, str, str, str, str, str, str, str)
        self.given_tree = Gtk.TreeView(model=self.given_store)
        self.given_tree.connect("row-activated", self.on_given_row_activated)
        given_scroll_win.add(self.given_tree)
        self.setup_given_names_rename_columns()

        # Action Footer
        given_footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        given_box.pack_start(given_footer_box, False, False, 0)

        self.given_select_all = Gtk.CheckButton(label=_("Select All"))
        self.given_select_all.set_active(True)
        self.given_select_all.connect("toggled", self.on_given_select_all_toggled)
        given_footer_box.pack_start(self.given_select_all, False, False, 0)

        self.given_apply_btn = Gtk.Button(label=_("Apply Selected Corrections"))
        self.given_apply_btn.set_sensitive(False)
        self.given_apply_btn.connect("clicked", self.on_given_apply_clicked)
        given_footer_box.pack_end(self.given_apply_btn, False, False, 0)

        # --- TAB 1: Scan & Apply (Inference Engine) ---
        scan_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        scan_box.set_border_width(8)
        notebook.append_page(scan_box, Gtk.Label(label=_("Infer Patronymics")))

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

        # TreeView Model structure: [Include, PersonName, FatherName, ReferenceYear, InferredPatronymic, Confidence, RulesString, GrampsID, Handle]
        self.list_store = Gtk.ListStore(bool, str, str, int, str, str, str, str, str)
        self.tree_view = Gtk.TreeView(model=self.list_store)
        self.tree_view.connect("row-activated", self.on_list_row_activated)
        scroll_win.add(self.tree_view)
        self.setup_inference_columns()

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
        notebook.append_page(audit_tab_box, Gtk.Label(label=_("Audit Patronymics")))

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

        # Auditor ListStore: [Include, Person Name, GrampsID, Current Value, Ref Year, Triggered Rule, Suggested Fix (Markup), Handle, Rule ID, Suggested String, Rule Source]
        self.audit_store = Gtk.ListStore(
            bool, str, str, str, int, str, str, str, str, str, str
        )
        self.audit_tree = Gtk.TreeView(model=self.audit_store)
        self.audit_tree.connect("row-activated", self.on_audit_row_activated)
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
        notebook.append_page(rollback_box, Gtk.Label(label=_("Revert")))

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

        # Action Footer
        revert_footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        rollback_box.pack_start(revert_footer_box, False, False, 0)

        self.revert_btn = Gtk.Button(label=_("Rollback Selected Transaction"))
        self.revert_btn.connect("clicked", self.on_revert_clicked)
        revert_footer_box.pack_end(self.revert_btn, False, False, 0)

        self.window.show_all()

    def on_destroy(self, widget):
        """Standard cleanup upon window closure."""
        if self.callback:
            self.callback()
        self.window.destroy()

    def on_dry_run_toggled(self, widget):
        """Updates UI status labels for simulation mode."""
        if widget.get_active():
            self.apply_btn.set_label(_("Simulate Checked Inferences"))
        else:
            self.apply_btn.set_label(_("Commit Checked Inferences"))

    def setup_inference_columns(self):
        """Initializes the TreeView column headers for the Inference Engine."""
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self.on_list_row_toggled)
        col_toggle = Gtk.TreeViewColumn(
            _("Apply"), renderer_toggle, active=self.LIST_COL_CHECKBOX
        )
        col_toggle.set_resizable(True)
        self.tree_view.append_column(col_toggle)

        col_id = Gtk.TreeViewColumn(
            _("ID"), Gtk.CellRendererText(), text=self.LIST_COL_GRAMPS_ID
        )
        col_id.set_sort_column_id(self.LIST_COL_GRAMPS_ID)
        col_id.set_resizable(True)
        self.tree_view.append_column(col_id)

        col_person = Gtk.TreeViewColumn(
            _("Individual"), Gtk.CellRendererText(), text=self.LIST_COL_DISPLAY_NAME
        )
        col_person.set_sort_column_id(self.LIST_COL_DISPLAY_NAME)
        col_person.set_resizable(True)
        col_person.set_expand(True)
        self.tree_view.append_column(col_person)

        col_father = Gtk.TreeViewColumn(
            _("Father's Name"), Gtk.CellRendererText(), text=self.LIST_COL_FATHER_NAME
        )
        col_father.set_sort_column_id(self.LIST_COL_FATHER_NAME)
        col_father.set_resizable(True)
        self.tree_view.append_column(col_father)

        col_year = Gtk.TreeViewColumn(
            _("Ref Year"), Gtk.CellRendererText(), text=self.LIST_COL_REF_YEAR
        )
        col_year.set_sort_column_id(self.LIST_COL_REF_YEAR)
        col_year.set_resizable(True)
        self.tree_view.append_column(col_year)

        col_pat = Gtk.TreeViewColumn(
            _("Inferred Patronymic"),
            Gtk.CellRendererText(),
            text=self.LIST_COL_PATRONYMIC,
        )
        col_pat.set_sort_column_id(self.LIST_COL_PATRONYMIC)
        col_pat.set_resizable(True)
        col_pat.set_expand(True)
        self.tree_view.append_column(col_pat)

        col_conf = Gtk.TreeViewColumn(
            _("Confidence"), Gtk.CellRendererText(), text=self.LIST_COL_CONFIDENCE
        )
        col_conf.set_sort_column_id(self.LIST_COL_CONFIDENCE)
        col_conf.set_resizable(True)
        self.tree_view.append_column(col_conf)

        col_source = Gtk.TreeViewColumn(
            _("Source"), Gtk.CellRendererText(), text=self.LIST_COL_RULE_SOURCE
        )
        col_source.set_sort_column_id(self.LIST_COL_RULE_SOURCE)
        col_source.set_resizable(True)
        self.tree_view.append_column(col_source)

    def setup_given_names_rename_columns(self):
        """Creates table headers and columns for Given Names standardization."""
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self.on_given_row_toggled)
        col_toggle = Gtk.TreeViewColumn(
            _("Use"), renderer_toggle, active=self.GIVEN_COL_CHECKBOX
        )
        col_toggle.set_resizable(True)
        self.given_tree.append_column(col_toggle)

        col_id = Gtk.TreeViewColumn(
            _("ID"), Gtk.CellRendererText(), text=self.GIVEN_COL_GRAMPS_ID
        )
        col_id.set_sort_column_id(self.GIVEN_COL_GRAMPS_ID)
        col_id.set_resizable(True)
        self.given_tree.append_column(col_id)

        col_person = Gtk.TreeViewColumn(
            _("Individual"), Gtk.CellRendererText(), text=self.GIVEN_COL_DISPLAY_NAME
        )
        col_person.set_sort_column_id(self.GIVEN_COL_DISPLAY_NAME)
        col_person.set_resizable(True)
        col_person.set_expand(True)
        self.given_tree.append_column(col_person)

        col_current = Gtk.TreeViewColumn(
            _("Current Name"), Gtk.CellRendererText(), text=self.GIVEN_COL_CURRENT
        )
        col_current.set_sort_column_id(self.GIVEN_COL_CURRENT)
        col_current.set_resizable(True)
        self.given_tree.append_column(col_current)

        col_proposed = Gtk.TreeViewColumn(
            _("Proposed Name"), Gtk.CellRendererText(), markup=self.GIVEN_COL_PROPOSED
        )
        col_proposed.set_sort_column_id(self.GIVEN_COL_PROPOSED)
        col_proposed.set_resizable(True)
        col_proposed.set_expand(True)
        self.given_tree.append_column(col_proposed)

        col_alt_action = Gtk.TreeViewColumn(
            _("Alt Name Action"), Gtk.CellRendererText(), text=self.GIVEN_COL_ALT_ACTION
        )
        col_alt_action.set_sort_column_id(self.GIVEN_COL_ALT_ACTION)
        col_alt_action.set_resizable(True)
        self.given_tree.append_column(col_alt_action)

    def setup_audit_columns(self):
        """Initializes table headers for the Database Auditor tab."""
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self.on_audit_row_toggled)
        col_toggle = Gtk.TreeViewColumn(
            _("Apply"), renderer_toggle, active=self.AUDIT_COL_CHECKBOX
        )
        col_toggle.set_resizable(True)
        self.audit_tree.append_column(col_toggle)

        col_person = Gtk.TreeViewColumn(
            _("Individual"), Gtk.CellRendererText(), text=self.AUDIT_COL_DISPLAY_NAME
        )
        col_person.set_sort_column_id(self.AUDIT_COL_DISPLAY_NAME)
        col_person.set_resizable(True)
        col_person.set_expand(True)
        self.audit_tree.append_column(col_person)

        col_id = Gtk.TreeViewColumn(
            _("ID"), Gtk.CellRendererText(), text=self.AUDIT_COL_GRAMPS_ID
        )
        col_id.set_sort_column_id(self.AUDIT_COL_GRAMPS_ID)
        col_id.set_resizable(True)
        self.audit_tree.append_column(col_id)

        col_current = Gtk.TreeViewColumn(
            _("Current Value"), Gtk.CellRendererText(), text=self.AUDIT_COL_CURRENT_PAT
        )
        col_current.set_sort_column_id(self.AUDIT_COL_CURRENT_PAT)
        col_current.set_resizable(True)
        self.audit_tree.append_column(col_current)

        col_year = Gtk.TreeViewColumn(
            _("Year"), Gtk.CellRendererText(), text=self.AUDIT_COL_REF_YEAR
        )
        col_year.set_sort_column_id(self.AUDIT_COL_REF_YEAR)
        col_year.set_resizable(True)
        self.audit_tree.append_column(col_year)

        col_rule = Gtk.TreeViewColumn(
            _("Issue / Rule"), Gtk.CellRendererText(), text=self.AUDIT_COL_RULE_ID
        )
        col_rule.set_sort_column_id(self.AUDIT_COL_RULE_ID)
        col_rule.set_resizable(True)
        self.audit_tree.append_column(col_rule)

        col_diff = Gtk.TreeViewColumn(
            _("Proposed Correction"),
            Gtk.CellRendererText(),
            markup=self.AUDIT_COL_DIFF_MARKUP,
        )
        col_diff.set_sort_column_id(self.AUDIT_COL_DIFF_MARKUP)
        col_diff.set_resizable(True)
        col_diff.set_expand(True)
        self.audit_tree.append_column(col_diff)

        col_source = Gtk.TreeViewColumn(
            _("Year Source"), Gtk.CellRendererText(), text=self.AUDIT_COL_RULE_SOURCE
        )
        col_source.set_sort_column_id(self.AUDIT_COL_RULE_SOURCE)
        col_source.set_resizable(True)
        self.audit_tree.append_column(col_source)

    def setup_log_columns(self):
        """Standardizes table headers for the JSON Rollback history view."""
        self.log_tree.append_column(
            Gtk.TreeViewColumn(_("Execution ID"), Gtk.CellRendererText(), text=0)
        )
        self.log_tree.append_column(
            Gtk.TreeViewColumn(_("Date/Time"), Gtk.CellRendererText(), text=1)
        )
        self.log_tree.append_column(
            Gtk.TreeViewColumn(_("Changes"), Gtk.CellRendererText(), text=2)
        )
        self.log_tree.append_column(
            Gtk.TreeViewColumn(_("Type"), Gtk.CellRendererText(), text=3)
        )

    def on_list_row_toggled(self, widget, path):
        self.list_store[path][self.LIST_COL_CHECKBOX] = not self.list_store[path][
            self.LIST_COL_CHECKBOX
        ]
        self.update_action_buttons()

    def on_given_row_toggled(self, widget, path):
        self.given_store[path][self.GIVEN_COL_CHECKBOX] = not self.given_store[path][
            self.GIVEN_COL_CHECKBOX
        ]
        self.update_given_apply_button()

    def on_audit_row_toggled(self, widget, path):
        self.audit_store[path][self.AUDIT_COL_CHECKBOX] = not self.audit_store[path][
            self.AUDIT_COL_CHECKBOX
        ]
        self.update_audit_apply_button()

    def on_given_select_all_toggled(self, widget):
        active = widget.get_active()
        for row in self.given_store:
            row[self.GIVEN_COL_CHECKBOX] = active
        self.update_given_apply_button()

    def on_audit_select_all_toggled(self, widget):
        active = widget.get_active()
        for row in self.audit_store:
            row[self.AUDIT_COL_CHECKBOX] = active
        self.update_audit_apply_button()

    def update_action_buttons(self):
        has_checked = any(row[self.LIST_COL_CHECKBOX] for row in self.list_store)
        self.apply_btn.set_sensitive(has_checked)

    def update_given_apply_button(self):
        has_checked = any(row[self.GIVEN_COL_CHECKBOX] for row in self.given_store)
        self.given_apply_btn.set_sensitive(has_checked)

    def update_audit_apply_button(self):
        has_checked = any(row[self.AUDIT_COL_CHECKBOX] for row in self.audit_store)
        self.audit_apply_btn.set_sensitive(has_checked)

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
        for rule in self.presenter.audit_service.linter_engine.rules:
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

    def on_given_scan_clicked(self, widget):
        """Scans the database and populates our list of given name standardization proposals."""
        source_input = self.given_source_entry.get_text().strip()
        target_input = self.given_target_entry.get_text().strip()

        if not source_input or not target_input:
            OkDialog(
                _("Empty Fields"),
                _("Please enter both Source Name and Target Name."),
                self.window,
            )
            return

        match_type = self.given_match_type_combo.get_active()
        if self.presenter.run_standardize_scan(source_input, target_input, match_type):
            self.update_given_apply_button()
        else:
            OkDialog(
                _("No Results"),
                _("No matching names found in the database."),
                self.window,
            )

    def on_scan_clicked(self, widget):
        """Scans the database and populates our list of candidates (Tab 1)."""
        pre_reform = self.script_check.get_active()
        if self.presenter.run_inference_scan(pre_reform=pre_reform):
            self.update_action_buttons()
        else:
            OkDialog(
                _("No Results"),
                _("No patronymic candidates found in the database."),
                self.window,
            )

    def on_audit_clicked(self, widget):
        """Performs database-wide consistency scan using GLib.idle_add for responsive chunking."""
        self.audit_run_btn.set_sensitive(False)
        self.audit_apply_btn.set_sensitive(False)

        scope_idx = self.audit_scope_combo.get_active()  # 0: All, 1: Males Only, 2: Females Only
        use_pre_reform = self.audit_pre_reform_check.get_active()
        active_rules = {r_id for r_id, val in self.enabled_rules.items() if val}

        self.presenter.run_audit_scan(scope_idx, active_rules, use_pre_reform)

    def on_given_apply_clicked(self, widget):
        """Commits selected given name standardizations via presenter."""
        checked_handles = set()
        for row in self.given_store:
            if row[self.GIVEN_COL_CHECKBOX]:
                checked_handles.add(row[self.GIVEN_COL_HANDLE])

        if not checked_handles:
            OkDialog(
                _("No Checked Records"),
                _("Please select at least one standardization to apply."),
                self.window,
            )
            return

        preserve_alt = self.preserve_alt_check.get_active()
        try:
            if self.presenter.apply_standardizations(checked_handles, preserve_alt):
                self.given_store.clear()
                self.given_apply_btn.set_sensitive(False)
                self.presenter.refresh_history()
                OkDialog(
                    _("Success"),
                    _("Given name standardizations applied and logged successfully."),
                    self.window,
                )
        except Exception as e:
            ErrorDialog(_("Transaction Failed"), str(e), self.window)

    def on_audit_apply_clicked(self, widget):
        """Commits selected auditor suggestions via presenter."""
        checked_indices = []
        for i, row in enumerate(self.audit_store):
            if row[self.AUDIT_COL_CHECKBOX]:
                checked_indices.append(i)

        if not checked_indices:
            OkDialog(
                _("No Checked Records"),
                _("Please select at least one correction to apply."),
                self.window,
            )
            return

        use_pre_reform = self.audit_pre_reform_check.get_active()
        try:
            if self.presenter.apply_audit_fixes(checked_indices, use_pre_reform):
                self.audit_store.clear()
                self.audit_apply_btn.set_sensitive(False)
                self.presenter.refresh_history()
                OkDialog(
                    _("Success"),
                    _("Auditor corrections applied and logged successfully."),
                    self.window,
                )
        except Exception as e:
            ErrorDialog(_("Transaction Failed"), str(e), self.window)

    def on_apply_clicked(self, widget):
        """Commits selected inferences via presenter."""
        checked_handles = set()
        for row in self.list_store:
            if row[self.LIST_COL_CHECKBOX]:
                checked_handles.add(row[self.LIST_COL_HANDLE])

        if not checked_handles:
            OkDialog(
                _("No Checked Records"),
                _("Please select at least one record to apply."),
                self.window,
            )
            return

        pre_reform = self.script_check.get_active()
        try:
            if self.presenter.apply_inferences(checked_handles, pre_reform):
                self.list_store.clear()
                self.apply_btn.set_sensitive(False)
                self.presenter.refresh_history()
                OkDialog(
                    _("Success"), _("Inferences applied and logged successfully."), self.window
                )
        except Exception as e:
            ErrorDialog(_("Transaction Failed"), str(e), self.window)

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

        exec_id = model.get_value(tree_iter, self.LOG_COL_EXEC_ID)

        try:
            report = self.presenter.rollback_run(exec_id)
            self.presenter.refresh_history()

            msg = _(
                "Rollback complete.\nReverted: {0}\nSkipped (Edited by User): {1}"
            ).format(len(report["reverted"]), len(report["skipped_modified"]))
            OkDialog(_("Rollback Executed"), msg, self.window)
        except Exception as e:
            ErrorDialog(_("Rollback Error"), str(e), self.window)

    def _open_person_edit_dialog(self, treeview, path, handle_column):
        """Opens the Gramps person edit dialog for the selected row."""
        model = treeview.get_model()
        person_handle = model[path][handle_column]

        if not person_handle:
            return

        person = self.db.get_person_from_handle(person_handle)
        if person:
            try:
                uistate = getattr(self.user, "uistate", None)
                EditPerson(self.dbstate, uistate, [], person)
            except WindowActiveError:
                pass

    def on_list_row_activated(self, treeview, path, view_column):
        """Opens the Gramps person edit dialog from the Inference Engine tab."""
        self._open_person_edit_dialog(treeview, path, self.LIST_COL_HANDLE)

    def on_audit_row_activated(self, treeview, path, view_column):
        """Opens the Gramps person edit dialog from the Database Auditor tab."""
        self._open_person_edit_dialog(treeview, path, self.AUDIT_COL_HANDLE)

    def on_given_row_activated(self, treeview, path, view_column):
        """Opens the Gramps person edit dialog from the Given Names tab."""
        self._open_person_edit_dialog(treeview, path, self.GIVEN_COL_HANDLE)


# -------------------------------------------------------------------------
# EastSlavicNameToolsOptions
# -------------------------------------------------------------------------
class EastSlavicNameToolsOptions(tool.ToolOptions):
    """
    Defines options and provides a handling interface for the East Slavic name tools.
    Even when using a completely custom GTK interface, Gramps requires this class
    to satisfy its plugin runner initialization.
    """

    def __init__(self, name, person_id=None):
        """Initializes the options class."""
        tool.ToolOptions.__init__(self, name, person_id)

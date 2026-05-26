# patronymics_tool.py
# -*- coding: utf-8 -*-
"""
patronymics_tool.py

Batch Tool Addon for Gramps. Scan records, evaluate multi-signal confidence,
batch-apply inferred patronymics, and run morphological consistency audits (linter)
with clean transaction logging and total reversibility.
"""

from gi.repository import Gtk

# Gramps modules
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gui.plug import tool
from gramps.gui.dialog import OkDialog, ErrorDialog
from gramps.gui.editors import EditPerson
from gramps.gen.errors import WindowActiveError

# Custom modular imports
from presenters import EastSlavicToolsPresenter
from utils import (
    PatronymicMixin,
)

_ = glocale.translation.gettext


class EastSlavicNameTools(PatronymicMixin, tool.Tool):
    """
    GTK Batch Processing Wizard. Acts as a Passive View in the MVP pattern.
    All business logic and long-running tasks are delegated to the presenter.
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
        """Initializes the Gramps Tool window."""
        self.user = user
        self.dbstate = dbstate
        self.db = dbstate.db
        self.callback = callback

        # Invoke core Tool initialization
        tool.Tool.__init__(self, dbstate, options_class, name)

        # Initialize MVP Presenter
        self.presenter = EastSlavicToolsPresenter(self, dbstate)

        # Local view state (UI specific)
        self.enabled_rules = {
            rule.rule_id: True
            for rule in self.presenter.audit_service.linter_engine.rules
        }

        # Build GTK Window UI
        self.build_window()

        # Start background metadata calculation
        self.presenter.initialize_async()
        self.presenter.refresh_history()

    def build_window(self):
        self.window = Gtk.Window(title=_("Infer East Slavic Patronymics"))
        self.window.set_default_size(900, 600)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.set_border_width(12)

        self.window.connect("destroy", self.on_destroy)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.window.add(main_box)

        notebook = Gtk.Notebook()
        main_box.pack_start(notebook, True, True, 0)

        # --- TAB 0: Given Names (Standardization) ---
        given_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        given_box.set_border_width(8)
        notebook.append_page(given_box, Gtk.Label(label=_("Standardize Names")))

        given_config_frame = Gtk.Frame(label=_("Search and Replace Options"))
        given_box.pack_start(given_config_frame, False, False, 0)

        given_config_grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        given_config_grid.set_border_width(8)
        given_config_frame.add(given_config_grid)

        given_config_grid.attach(Gtk.Label(label=_("Source Name:")), 0, 0, 1, 1)
        self.given_source_entry = Gtk.Entry()
        self.given_source_entry.set_placeholder_text(_("e.g. Иоанн"))

        # Set up autocompletion with given names from database
        completion = Gtk.EntryCompletion()
        given_names_list = Gtk.ListStore(str)
        for name in sorted(self.presenter.inference_service.given_names_set):
            given_names_list.append([name])
        completion.set_model(given_names_list)
        completion.set_text_column(0)
        completion.set_minimum_key_length(1)
        self.given_source_entry.set_completion(completion)

        given_config_grid.attach(self.given_source_entry, 1, 0, 1, 1)

        given_config_grid.attach(Gtk.Label(label=_("Target Name:")), 0, 1, 1, 1)
        self.given_target_entry = Gtk.Entry()
        self.given_target_entry.set_placeholder_text(_("e.g. Иван"))
        given_config_grid.attach(self.given_target_entry, 1, 1, 1, 1)

        given_config_grid.attach(Gtk.Label(label=_("Match Mode:")), 2, 0, 1, 1)
        self.given_match_type_combo = Gtk.ComboBoxText()
        self.given_match_type_combo.append_text(_("Exact Match"))
        self.given_match_type_combo.append_text(_("Substring"))
        self.given_match_type_combo.append_text(_("Regular Expression"))
        self.given_match_type_combo.set_active(0)
        given_config_grid.attach(self.given_match_type_combo, 3, 0, 1, 1)

        self.given_scan_btn = Gtk.Button(label=_("Scan for Names"))
        self.given_scan_btn.connect("clicked", self.on_given_scan_clicked)
        given_config_grid.attach(self.given_scan_btn, 3, 1, 1, 1)

        self.preserve_alt_check = Gtk.CheckButton(
            label=_("Preserve original name as alternative")
        )
        self.preserve_alt_check.set_active(True)
        given_box.pack_start(self.preserve_alt_check, False, False, 0)

        given_scroll_win = Gtk.ScrolledWindow()
        given_scroll_win.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        given_box.pack_start(given_scroll_win, True, True, 0)

        self.given_store = Gtk.ListStore(bool, str, str, str, str, str, str, str)
        self.given_tree = Gtk.TreeView(model=self.given_store)
        self.given_tree.connect("row-activated", self.on_given_row_activated)
        given_scroll_win.add(self.given_tree)
        self.setup_given_names_rename_columns()

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

        config_frame = Gtk.Frame(label=_("Inference Options"))
        scan_box.pack_start(config_frame, False, False, 0)

        config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        config_box.set_border_width(8)
        config_frame.add(config_box)

        self.script_check = Gtk.CheckButton(
            label=_("Match Pre-Revolutionary Orthography")
        )
        self.script_check.set_active(False)
        config_box.pack_start(self.script_check, False, False, 0)

        self.scan_btn = Gtk.Button(label=_("Scan Database"))
        self.scan_btn.connect("clicked", self.on_scan_clicked)
        config_box.pack_start(self.scan_btn, False, False, 0)

        scroll_win = Gtk.ScrolledWindow()
        scroll_win.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scan_box.pack_start(scroll_win, True, True, 0)

        self.list_store = Gtk.ListStore(bool, str, str, int, str, str, str, str, str)
        self.tree_view = Gtk.TreeView(model=self.list_store)
        self.tree_view.connect("row-activated", self.on_list_row_activated)
        scroll_win.add(self.tree_view)
        self.setup_inference_columns()

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

        audit_header_frame = Gtk.Frame(label=_("Auditing Settings"))
        audit_tab_box.pack_start(audit_header_frame, False, False, 0)

        audit_header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        audit_header_box.set_border_width(8)
        audit_header_frame.add(audit_header_box)

        self.audit_scope_combo = Gtk.ComboBoxText()
        self.audit_scope_combo.append_text(_("All Records"))
        self.audit_scope_combo.append_text(_("Males Only"))
        self.audit_scope_combo.append_text(_("Females Only"))
        self.audit_scope_combo.set_active(0)
        audit_header_box.pack_start(self.audit_scope_combo, False, False, 0)

        self.rules_config_btn = Gtk.Button(label=_("Configure Rules..."))
        self.rules_config_btn.connect("clicked", self.on_configure_rules_clicked)
        audit_header_box.pack_start(self.rules_config_btn, False, False, 0)

        self.audit_pre_reform_check = Gtk.CheckButton(
            label=_("Match Pre-Revolutionary Orthography")
        )
        self.audit_pre_reform_check.set_active(False)
        audit_header_box.pack_start(self.audit_pre_reform_check, False, False, 0)

        audit_action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        audit_tab_box.pack_start(audit_action_box, False, False, 0)

        self.audit_run_btn = Gtk.Button(label=_("Audit Database"))
        self.audit_run_btn.connect("clicked", self.on_audit_clicked)
        audit_action_box.pack_start(self.audit_run_btn, False, False, 0)

        self.audit_progress = Gtk.ProgressBar()
        self.audit_progress.set_show_text(True)
        audit_action_box.pack_start(self.audit_progress, True, True, 0)

        audit_scroll = Gtk.ScrolledWindow()
        audit_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        audit_tab_box.pack_start(audit_scroll, True, True, 0)

        self.audit_store = Gtk.ListStore(
            bool, str, str, str, int, str, str, str, str, str, str
        )
        self.audit_tree = Gtk.TreeView(model=self.audit_store)
        self.audit_tree.connect("row-activated", self.on_audit_row_activated)
        audit_scroll.add(self.audit_tree)
        self.setup_audit_columns()

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

        log_scroll = Gtk.ScrolledWindow()
        log_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        rollback_box.pack_start(log_scroll, True, True, 0)

        self.log_store = Gtk.ListStore(str, str, int, str)
        self.log_tree = Gtk.TreeView(model=self.log_store)
        log_scroll.add(self.log_tree)
        self.setup_log_columns()

        revert_footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        rollback_box.pack_start(revert_footer_box, False, False, 0)

        self.revert_btn = Gtk.Button(label=_("Rollback Selected Transaction"))
        self.revert_btn.connect("clicked", self.on_revert_clicked)
        revert_footer_box.pack_end(self.revert_btn, False, False, 0)

        self.window.show_all()

    def on_destroy(self, widget):
        if self.callback:
            self.callback()
        self.window.destroy()

    def update_audit_progress(self, fraction, text):
        """Presenter callback."""
        self.audit_progress.set_fraction(fraction)
        self.audit_progress.set_text(text)

    def on_audit_complete(self, total_found):
        """Presenter callback."""
        self.audit_progress.set_fraction(1.0)
        self.audit_progress.set_text(_("Audit Complete!"))
        self.audit_run_btn.set_sensitive(True)
        self.update_audit_apply_button()
        if total_found == 0:
            OkDialog(_("No Results"), _("No issues found."), self.window)

    def update_action_buttons(self):
        """Presenter callback after inference scan."""
        self.scan_btn.set_sensitive(True)
        has_checked = any(row[self.LIST_COL_CHECKBOX] for row in self.list_store)
        self.apply_btn.set_sensitive(has_checked)

    def update_given_apply_button(self):
        has_checked = any(row[self.GIVEN_COL_CHECKBOX] for row in self.given_store)
        self.given_apply_btn.set_sensitive(has_checked)

    def update_audit_apply_button(self):
        has_checked = any(row[self.AUDIT_COL_CHECKBOX] for row in self.audit_store)
        self.audit_apply_btn.set_sensitive(has_checked)

    # --- Signal Handlers (Thin delegation) ---

    def on_given_scan_clicked(self, widget):
        source = self.given_source_entry.get_text().strip()
        target = self.given_target_entry.get_text().strip()
        if not source or not target:
            OkDialog(
                _("Empty Fields"), _("Enter Source and Target names."), self.window
            )
            return
        m_type = self.given_match_type_combo.get_active()
        if self.presenter.run_standardize_scan(source, target, m_type):
            self.update_given_apply_button()
        else:
            OkDialog(_("No Results"), _("No matching names found."), self.window)

    def on_scan_complete(self, total_found):
        """Presenter callback."""
        self.scan_btn.set_sensitive(True)
        self.update_action_buttons()
        if total_found == 0:
            OkDialog(_("No Results"), _("No patronymics found."), self.window)

    def on_scan_clicked(self, widget):
        self.scan_btn.set_sensitive(False)
        self.apply_btn.set_sensitive(False)
        self.presenter.run_inference_scan(self.script_check.get_active())

    def on_audit_clicked(self, widget):
        self.audit_run_btn.set_sensitive(False)
        self.audit_apply_btn.set_sensitive(False)
        scope = self.audit_scope_combo.get_active()
        pre_reform = self.audit_pre_reform_check.get_active()
        rules = {r_id for r_id, val in self.enabled_rules.items() if val}
        self.presenter.run_audit_scan(scope, rules, pre_reform)

    def on_given_apply_clicked(self, widget):
        preserve = self.preserve_alt_check.get_active()
        try:
            if self.presenter.apply_checked_standardizations(preserve):
                self.given_store.clear()
                self.given_apply_btn.set_sensitive(False)
                self.presenter.refresh_history()
                OkDialog(_("Success"), _("Standardizations applied."), self.window)
            else:
                OkDialog(
                    _("No Selection"), _("Select at least one record."), self.window
                )
        except Exception as e:
            ErrorDialog(_("Failed"), str(e), self.window)

    def on_audit_apply_clicked(self, widget):
        pre_reform = self.audit_pre_reform_check.get_active()
        try:
            if self.presenter.apply_checked_audit_fixes(pre_reform):
                self.audit_store.clear()
                self.audit_apply_btn.set_sensitive(False)
                self.presenter.refresh_history()
                OkDialog(_("Success"), _("Corrections applied."), self.window)
            else:
                OkDialog(
                    _("No Selection"), _("Select at least one record."), self.window
                )
        except Exception as e:
            ErrorDialog(_("Failed"), str(e), self.window)

    def on_apply_clicked(self, widget):
        pre_reform = self.script_check.get_active()
        try:
            if self.presenter.apply_checked_inferences(pre_reform):
                self.list_store.clear()
                self.apply_btn.set_sensitive(False)
                self.presenter.refresh_history()
                OkDialog(_("Success"), _("Inferences applied."), self.window)
            else:
                OkDialog(
                    _("No Selection"), _("Select at least one record."), self.window
                )
        except Exception as e:
            ErrorDialog(_("Failed"), str(e), self.window)

    def on_revert_clicked(self, widget):
        selection = self.log_tree.get_selection()
        model, tree_iter = selection.get_selected()
        if not tree_iter:
            return
        exec_id = model.get_value(tree_iter, self.LOG_COL_EXEC_ID)
        try:
            report = self.presenter.rollback_run(exec_id)
            self.presenter.refresh_history()
            msg = _("Reverted: {0}, Skipped: {1}").format(
                len(report["reverted"]), len(report["skipped_modified"])
            )
            OkDialog(_("Rollback Executed"), msg, self.window)
        except Exception as e:
            ErrorDialog(_("Error"), str(e), self.window)

    # --- UI Helpers (Gtk Boilerplate) ---

    def setup_inference_columns(self):
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self.on_list_row_toggled)
        self.tree_view.append_column(
            Gtk.TreeViewColumn(
                _("Use"), renderer_toggle, active=self.LIST_COL_CHECKBOX
            )
        )
        self.tree_view.append_column(
            Gtk.TreeViewColumn(
                _("ID"), Gtk.CellRendererText(), text=self.LIST_COL_GRAMPS_ID
            )
        )
        individual_col = Gtk.TreeViewColumn(
            _("Individual"), Gtk.CellRendererText(), text=self.LIST_COL_DISPLAY_NAME
        )
        individual_col.set_expand(True)
        self.tree_view.append_column(individual_col)
        father_col = Gtk.TreeViewColumn(
            _("Father"), Gtk.CellRendererText(), text=self.LIST_COL_FATHER_NAME
        )
        father_col.set_expand(True)
        self.tree_view.append_column(father_col)
        patronymic_col = Gtk.TreeViewColumn(
            _("Patronymic"), Gtk.CellRendererText(), text=self.LIST_COL_PATRONYMIC
        )
        patronymic_col.set_expand(True)
        self.tree_view.append_column(patronymic_col)
        self.tree_view.append_column(
            Gtk.TreeViewColumn(
                _("Conf"), Gtk.CellRendererText(), text=self.LIST_COL_CONFIDENCE
            )
        )
        self.tree_view.append_column(
            Gtk.TreeViewColumn(
                _("Ref Year"), Gtk.CellRendererText(), text=self.LIST_COL_REF_YEAR
            )
        )
        self.tree_view.append_column(
            Gtk.TreeViewColumn(
                _("Ref Year Src"), Gtk.CellRendererText(), text=self.LIST_COL_RULE_SOURCE
            )
        )

    def setup_given_names_rename_columns(self):
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self.on_given_row_toggled)
        self.given_tree.append_column(
            Gtk.TreeViewColumn(
                _("Use"), renderer_toggle, active=self.GIVEN_COL_CHECKBOX
            )
        )
        self.given_tree.append_column(
            Gtk.TreeViewColumn(
                _("ID"), Gtk.CellRendererText(), text=self.GIVEN_COL_GRAMPS_ID
            )
        )
        individual_col = Gtk.TreeViewColumn(
            _("Individual"),
            Gtk.CellRendererText(),
            text=self.GIVEN_COL_DISPLAY_NAME,
        )
        individual_col.set_expand(True)
        self.given_tree.append_column(individual_col)
        current_col = Gtk.TreeViewColumn(
            _("Current"), Gtk.CellRendererText(), text=self.GIVEN_COL_CURRENT
        )
        current_col.set_expand(True)
        self.given_tree.append_column(current_col)
        proposed_col = Gtk.TreeViewColumn(
            _("Proposed"), Gtk.CellRendererText(), markup=self.GIVEN_COL_PROPOSED
        )
        proposed_col.set_expand(True)
        self.given_tree.append_column(proposed_col)
        self.given_tree.append_column(
            Gtk.TreeViewColumn(
                _("Action"), Gtk.CellRendererText(), text=self.GIVEN_COL_ALT_ACTION
            )
        )

    def setup_audit_columns(self):
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self.on_audit_row_toggled)
        self.audit_tree.append_column(
            Gtk.TreeViewColumn(
                _("Use"), renderer_toggle, active=self.AUDIT_COL_CHECKBOX
            )
        )
        self.audit_tree.append_column(
            Gtk.TreeViewColumn(
                _("ID"), Gtk.CellRendererText(), text=self.AUDIT_COL_GRAMPS_ID
            )
        )
        individual_col = Gtk.TreeViewColumn(
            _("Individual"),
            Gtk.CellRendererText(),
            text=self.AUDIT_COL_DISPLAY_NAME,
        )
        individual_col.set_expand(True)
        self.audit_tree.append_column(individual_col)
        current_col = Gtk.TreeViewColumn(
            _("Current"), Gtk.CellRendererText(), text=self.AUDIT_COL_CURRENT_PAT
        )
        current_col.set_expand(True)
        self.audit_tree.append_column(current_col)
        correction_col = Gtk.TreeViewColumn(
            _("Correction"),
            Gtk.CellRendererText(),
            markup=self.AUDIT_COL_DIFF_MARKUP,
        )
        correction_col.set_expand(True)
        self.audit_tree.append_column(correction_col)
        self.audit_tree.append_column(
            Gtk.TreeViewColumn(
                _("Year"), Gtk.CellRendererText(), text=self.AUDIT_COL_REF_YEAR
            )
        )
        self.audit_tree.append_column(
            Gtk.TreeViewColumn(
                _("Rule"), Gtk.CellRendererText(), text=self.AUDIT_COL_RULE_ID
            )
        )
        self.audit_tree.append_column(
            Gtk.TreeViewColumn(
                _("Source"), Gtk.CellRendererText(), text=self.AUDIT_COL_RULE_SOURCE
            )
        )

    def setup_log_columns(self):
        id_col = Gtk.TreeViewColumn(_("ID"), Gtk.CellRendererText(), text=0)
        id_col.set_expand(True)
        self.log_tree.append_column(id_col)
        date_col = Gtk.TreeViewColumn(_("Date"), Gtk.CellRendererText(), text=1)
        date_col.set_expand(True)
        self.log_tree.append_column(date_col)
        self.log_tree.append_column(
            Gtk.TreeViewColumn(_("Count"), Gtk.CellRendererText(), text=2)
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
        for row in self.given_store:
            row[self.GIVEN_COL_CHECKBOX] = widget.get_active()
        self.update_given_apply_button()

    def on_audit_select_all_toggled(self, widget):
        for row in self.audit_store:
            row[self.AUDIT_COL_CHECKBOX] = widget.get_active()
        self.update_audit_apply_button()

    def on_configure_rules_clicked(self, widget):
        dialog = Gtk.Dialog(
            title=_("Configure Rules"), parent=self.window, flags=Gtk.DialogFlags.MODAL
        )
        dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        dialog.get_content_area().add(vbox)
        checks = {}
        for rule in self.presenter.audit_service.linter_engine.rules:
            chk = Gtk.CheckButton(label=rule.rule_id)
            chk.set_active(self.enabled_rules[rule.rule_id])
            vbox.pack_start(chk, False, False, 0)
            checks[rule.rule_id] = chk
        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            for r_id, chk in checks.items():
                self.enabled_rules[r_id] = chk.get_active()
        dialog.destroy()

    def _open_person_edit_dialog(self, treeview, path, handle_column):
        handle = treeview.get_model()[path][handle_column]
        person = self.db.get_person_from_handle(handle)
        if person:
            try:
                EditPerson(
                    self.dbstate, getattr(self.user, "uistate", None), [], person
                )
            except WindowActiveError:
                pass

    def on_list_row_activated(self, tv, path, col):
        self._open_person_edit_dialog(tv, path, self.LIST_COL_HANDLE)

    def on_audit_row_activated(self, tv, path, col):
        self._open_person_edit_dialog(tv, path, self.AUDIT_COL_HANDLE)

    def on_given_row_activated(self, tv, path, col):
        self._open_person_edit_dialog(tv, path, self.GIVEN_COL_HANDLE)


class EastSlavicNameToolsOptions(tool.ToolOptions):
    def __init__(self, name, person_id=None):
        tool.ToolOptions.__init__(self, name, person_id)

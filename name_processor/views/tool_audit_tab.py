"""
Audit Tab UI component for the Names Tool.
Contains all GTK widgets, layout structures, and column definitions for the audit tab.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gi.repository import Gtk

from gramps.gen.const import GRAMPS_LOCALE as glocale

from name_processor.models.audit import AuditIssue, AuditScope
from name_processor.presentation.markup import format_confidence, generate_pango_diff
from name_processor.presentation.row_schemas import AuditRowData

if TYPE_CHECKING:
    from gi.repository.Gtk import Window
    from name_processor.controllers.tool import ToolController


_ = glocale.translation.gettext


class AuditTab:
    """
    GTK Audit Tab component. Manages the audit patronymics tab UI.
    All business logic is delegated to the controller.
    """

    def __init__(self, parent_window: Window, controller: ToolController) -> None:
        """
        Initialize the AuditTab.

        Args:
            parent_window: The parent GTK window for dialog references
            controller: The tool controller for business logic calls
        """
        self.parent_window = parent_window
        self.controller = controller

        # Local view state (UI specific)
        self.enabled_rules: dict[str, bool] = {}
        self.audit_issues: list[AuditIssue] = []

        # Widget properties (initialized in build())
        self.scope_combo: Gtk.ComboBoxText
        self.rules_btn: Gtk.Button
        self.pre_reform_check: Gtk.CheckButton
        self.run_btn: Gtk.Button
        self.progress: Gtk.ProgressBar
        self.store: Gtk.ListStore
        self.tree: Gtk.TreeView
        self.select_all: Gtk.CheckButton
        self.apply_btn: Gtk.Button

    def build(self) -> Gtk.Widget:
        """
        Build and return the audit tab UI widget.

        Returns:
            Gtk.Box: The audit tab container widget
        """
        audit_tab_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        audit_tab_box.set_border_width(8)

        audit_header_frame = Gtk.Frame(label=_("Auditing Settings"))
        audit_tab_box.pack_start(audit_header_frame, False, False, 0)

        audit_header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        audit_header_box.set_border_width(8)
        audit_header_frame.add(audit_header_box)

        self.scope_combo = Gtk.ComboBoxText()
        self.scope_combo.append_text(_("All Records"))
        self.scope_combo.append_text(_("Males Only"))
        self.scope_combo.append_text(_("Females Only"))
        self.scope_combo.set_active(0)
        audit_header_box.pack_start(self.scope_combo, False, False, 0)

        self.rules_btn = Gtk.Button(label=_("Configure Rules..."))
        self.rules_btn.connect("clicked", self.on_configure_rules_clicked)
        audit_header_box.pack_start(self.rules_btn, False, False, 0)

        self.pre_reform_check = Gtk.CheckButton(
            label=_("Match Pre-Revolutionary Orthography")
        )
        self.pre_reform_check.set_active(False)
        audit_header_box.pack_start(self.pre_reform_check, False, False, 0)

        audit_action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        audit_tab_box.pack_start(audit_action_box, False, False, 0)

        self.run_btn = Gtk.Button(label=_("Audit Database"))
        self.run_btn.connect("clicked", self.on_run_clicked)
        audit_action_box.pack_start(self.run_btn, False, False, 0)

        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        audit_action_box.pack_start(self.progress, True, True, 0)

        audit_scroll = Gtk.ScrolledWindow()
        audit_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        audit_tab_box.pack_start(audit_scroll, True, True, 0)

        self.store = Gtk.ListStore(
            bool, str, str, str, str, str, str, str, str, str, str, str
        )
        self.tree = Gtk.TreeView(model=self.store)
        audit_scroll.add(self.tree)
        self.setup_columns()

        audit_footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        audit_tab_box.pack_start(audit_footer_box, False, False, 0)

        self.select_all = Gtk.CheckButton(label=_("Select All Safe Corrections"))
        self.select_all.set_active(True)
        self.select_all.connect("toggled", self.on_select_all_toggled)
        audit_footer_box.pack_start(self.select_all, False, False, 0)

        self.apply_btn = Gtk.Button(label=_("Apply Selected Corrections"))
        self.apply_btn.set_sensitive(False)
        self.apply_btn.connect("clicked", self.on_apply_clicked)
        audit_footer_box.pack_end(self.apply_btn, False, False, 0)
        self.tree.connect("row-activated", self.on_row_activated)
        return audit_tab_box

    # --- Event Handlers ---
    def on_run_clicked(self, widget: Any) -> None:
        self.run_btn.set_sensitive(False)
        scope_idx = self.scope_combo.get_active()
        audit_scope = {
            0: AuditScope.ALL,
            1: AuditScope.MALES_ONLY,
            2: AuditScope.FEMALES_ONLY,
        }.get(scope_idx, AuditScope.ALL)
        use_pre_reform = self.pre_reform_check.get_active()
        enabled_rules_set = {
            r_id for r_id, enabled in self.enabled_rules.items() if enabled
        }
        self.controller.run_audit_scan(audit_scope, enabled_rules_set, use_pre_reform)

    def on_apply_clicked(self, widget: Any) -> None:
        use_pre_reform = self.pre_reform_check.get_active()
        if self.controller.apply_checked_audit_fixes(use_pre_reform):
            self.clear_results()
            self.update_apply_button()

    def on_row_toggled(self, widget: Any, path: str) -> None:
        chk_idx = AuditRowData._fields.index("checkbox")
        self.store[path][chk_idx] = not self.store[path][chk_idx]
        self.update_apply_button()
        all_selected = all(row[chk_idx] for row in self.store)
        self.select_all.handler_block_by_func(self.on_select_all_toggled)
        self.select_all.set_active(all_selected)
        self.select_all.handler_unblock_by_func(self.on_select_all_toggled)

    def on_select_all_toggled(self, widget: Any) -> None:
        chk_idx = AuditRowData._fields.index("checkbox")
        for row in self.store:
            row[chk_idx] = widget.get_active()
        self.update_apply_button()

    def on_row_activated(
        self, tv: Gtk.TreeView, path: str, col: Gtk.TreeViewColumn
    ) -> None:
        handle = tv.get_model()[path][AuditRowData._fields.index("handle")]
        gramps_person = self.controller.get_gramps_person(handle)
        dbstate = self.controller.dbstate
        uistate = getattr(self.controller.user, "uistate", None)
        if gramps_person is None or dbstate is None or uistate is None:
            return
        try:
            from gramps.gui.editors import EditPerson
            from gramps.gen.errors import WindowActiveError

            EditPerson(dbstate, uistate, [], gramps_person)
        except WindowActiveError:
            pass

    def on_configure_rules_clicked(self, widget: Any) -> None:
        dialog = Gtk.Dialog(
            title=_("Configure Rules"),
            parent=self.parent_window,
            flags=Gtk.DialogFlags.MODAL,
        )
        dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        dialog.get_content_area().add(vbox)
        checks = {}
        for rule_id in self.controller.get_available_audit_rules():
            chk = Gtk.CheckButton(label=rule_id)
            chk.set_active(self.enabled_rules[rule_id])
            vbox.pack_start(chk, False, False, 0)
            checks[rule_id] = chk
        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            for r_id, chk in checks.items():
                self.enabled_rules[r_id] = chk.get_active()
        dialog.destroy()

    # --- Column Setup ---
    def _add_text_column(
        self,
        title: str,
        field_name: str,
        expand: bool = False,
        use_markup: bool = False,
        sort_field: str | None = None,
    ) -> None:
        attr = "markup" if use_markup else "text"
        sort_id = AuditRowData._fields.index(sort_field if sort_field else field_name)
        col = Gtk.TreeViewColumn(
            title,
            Gtk.CellRendererText(),
            **{attr: AuditRowData._fields.index(field_name)},
        )
        col.set_expand(expand)
        col.set_sort_column_id(sort_id)
        self.tree.append_column(col)

    def setup_columns(self) -> None:
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self.on_row_toggled)
        self.tree.append_column(
            Gtk.TreeViewColumn(
                _("Use"), renderer_toggle, active=AuditRowData._fields.index("checkbox")
            )
        )
        self._add_text_column(_("ID"), "gramps_id")
        self._add_text_column(_("Individual"), "display_name", expand=True)
        self._add_text_column(_("Father"), "father_name", expand=True)
        self._add_text_column(_("Current"), "current_patronymic", expand=True)
        self._add_text_column(
            _("Correction"),
            "diff_markup",
            expand=True,
            use_markup=True,
            sort_field="suggested_string",
        )
        self._add_text_column(_("Conf"), "confidence")
        self._add_text_column(_("Ref Year"), "ref_year")
        self._add_text_column(_("Rule"), "rule_id")
        self._add_text_column(_("Explanation"), "explanation", expand=True)

    # --- Port Methods (Controller → View) ---
    def clear_results(self) -> None:
        self.store.clear()
        self.audit_issues = []

    def get_result_count(self) -> int:
        return len(self.audit_issues)

    def append_issue(self, issue: AuditIssue) -> None:
        diff_markup = generate_pango_diff(issue.current_value, issue.suggested_fix)
        confidence_str = format_confidence(getattr(issue, "confidence", 0))
        row = AuditRowData(
            checkbox=True,
            display_name=issue.display_name,
            gramps_id=issue.gramps_id,
            father_name=issue.father_name,
            current_patronymic=issue.current_value,
            diff_markup=diff_markup,
            confidence=confidence_str,
            ref_year=issue.reference_year,
            rule_id=issue.rule_id,
            handle=issue.person_handle,
            suggested_string=issue.suggested_fix,
            explanation=issue.explanation,
        )
        self.store.append(list(row))
        self.audit_issues.append(issue)

    def update_progress(self, fraction: float, text: str) -> None:
        self.progress.set_fraction(fraction)
        self.progress.set_text(text)

    def on_complete(self, total_found: int) -> None:
        from gramps.gui.dialog import OkDialog

        self.progress.set_fraction(1.0)
        self.progress.set_text(_("Audit Complete!"))
        self.run_btn.set_sensitive(True)
        self.select_all.set_active(True)
        self.update_apply_button()
        if total_found == 0:
            OkDialog(_("No Results"), _("No issues found."), self.parent_window)

    def update_apply_button(self) -> None:
        chk_idx = AuditRowData._fields.index("checkbox")
        self.apply_btn.set_sensitive(any(row[chk_idx] for row in self.store))

    def get_checked_keys(self) -> set[tuple[str, str]]:
        chk_idx = AuditRowData._fields.index("checkbox")
        h_idx = AuditRowData._fields.index("handle")
        r_idx = AuditRowData._fields.index("rule_id")
        return {(row[h_idx], row[r_idx]) for row in self.store if row[chk_idx]}

    def get_enabled_rules(self) -> set[str]:
        return {r_id for r_id, enabled in self.enabled_rules.items() if enabled}

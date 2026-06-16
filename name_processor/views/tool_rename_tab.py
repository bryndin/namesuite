"""
Rename Tab UI component for the Names Tool.
Contains all GTK widgets, layout structures, and column definitions for the rename tab.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gi.repository import Gtk

from gramps.gen.const import GRAMPS_LOCALE as glocale

from name_processor.models.renamer import AltAction, MatchMode
from name_processor.presentation.row_schemas import GivenRowData

if TYPE_CHECKING:
    from gi.repository.Gtk import Window
    from name_processor.controllers.tool import ToolController


_ = glocale.translation.gettext


class RenameTab:
    """
    GTK Rename Tab component. Manages the rename given names tab UI.
    All business logic is delegated to the controller.
    """

    def __init__(self, parent_window: Window, controller: ToolController) -> None:
        """
        Initialize the RenameTab.

        Args:
            parent_window: The parent GTK window for dialog references
            controller: The tool controller for business logic calls
        """
        self.parent_window = parent_window
        self.controller = controller

        # Widget properties (initialized in build())
        self.source_entry: Gtk.Entry
        self.target_entry: Gtk.Entry
        self.match_combo: Gtk.ComboBoxText
        self.scan_btn: Gtk.Button
        self.preserve_check: Gtk.CheckButton
        self.store: Gtk.ListStore
        self.tree: Gtk.TreeView
        self.select_all: Gtk.CheckButton
        self.apply_btn: Gtk.Button

    def build(self) -> Gtk.Widget:
        """
        Build and return the rename tab UI widget.

        Returns:
            Gtk.Box: The rename tab container widget
        """
        given_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        given_box.set_border_width(8)

        given_config_frame = Gtk.Frame(label=_("Search and Replace Options"))
        given_box.pack_start(given_config_frame, False, False, 0)

        given_config_grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        given_config_grid.set_border_width(8)
        given_config_frame.add(given_config_grid)

        given_config_grid.attach(Gtk.Label(label=_("Source Name:")), 0, 0, 1, 1)
        self.source_entry = Gtk.Entry()
        self.source_entry.set_placeholder_text(_("e.g. Иоанн"))
        given_config_grid.attach(self.source_entry, 1, 0, 1, 1)

        given_config_grid.attach(Gtk.Label(label=_("Target Name:")), 0, 1, 1, 1)
        self.target_entry = Gtk.Entry()
        self.target_entry.set_placeholder_text(_("e.g. Иван"))
        given_config_grid.attach(self.target_entry, 1, 1, 1, 1)

        given_config_grid.attach(Gtk.Label(label=_("Match Mode:")), 2, 0, 1, 1)
        self.match_combo = Gtk.ComboBoxText()
        self.match_combo.append_text(_("Exact Match"))
        self.match_combo.append_text(_("Substring"))
        self.match_combo.append_text(_("Regular Expression"))
        self.match_combo.set_active(0)
        given_config_grid.attach(self.match_combo, 3, 0, 1, 1)

        self.scan_btn = Gtk.Button(label=_("Scan for Names"))
        self.scan_btn.connect("clicked", self.on_scan_clicked)
        given_config_grid.attach(self.scan_btn, 3, 1, 1, 1)

        self.preserve_check = Gtk.CheckButton(
            label=_("Preserve original name as alternative")
        )
        self.preserve_check.set_active(True)
        self.preserve_check.connect("toggled", self.on_preserve_toggled)
        given_box.pack_start(self.preserve_check, False, False, 0)

        given_scroll_win = Gtk.ScrolledWindow()
        given_scroll_win.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        given_box.pack_start(given_scroll_win, True, True, 0)

        self.store = Gtk.ListStore(bool, str, str, str, str, str, str)
        self.tree = Gtk.TreeView(model=self.store)
        given_scroll_win.add(self.tree)
        self.setup_columns()

        given_footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        given_box.pack_start(given_footer_box, False, False, 0)

        self.select_all = Gtk.CheckButton(label=_("Select All"))
        self.select_all.set_active(True)
        self.select_all.connect("toggled", self.on_select_all_toggled)
        given_footer_box.pack_start(self.select_all, False, False, 0)

        self.apply_btn = Gtk.Button(label=_("Apply Selected Corrections"))
        self.apply_btn.set_sensitive(False)
        self.apply_btn.connect("clicked", self.on_apply_clicked)
        given_footer_box.pack_end(self.apply_btn, False, False, 0)

        self.tree.connect("row-activated", self.on_row_activated)
        return given_box

    # --- Event Handlers ---

    def on_scan_clicked(self, widget: Any) -> None:
        if not self.controller:
            return
        source = self.source_entry.get_text().strip()
        target = self.target_entry.get_text().strip()
        match_mode = {
            0: MatchMode.EXACT,
            1: MatchMode.SUBSTRING,
            2: MatchMode.REGEX,
        }.get(self.match_combo.get_active(), MatchMode.EXACT)
        self.controller.on_rename_scan_requested(source, target, match_mode)
        self.update_apply_button()

    def on_apply_clicked(self, widget: Any) -> None:
        if self.controller.apply_checked_renamings():
            self.store.clear()
            self.update_apply_button()

    def on_row_toggled(self, widget: Any, path: str) -> None:
        chk_idx = GivenRowData._fields.index("checkbox")
        self.store[path][chk_idx] = not self.store[path][chk_idx]
        self.update_apply_button()

    def on_select_all_toggled(self, widget: Any) -> None:
        chk_idx = GivenRowData._fields.index("checkbox")
        for row in self.store:
            row[chk_idx] = widget.get_active()
        self.update_apply_button()

    def on_row_activated(
        self, tv: Gtk.TreeView, path: str, col: Gtk.TreeViewColumn
    ) -> None:
        handle = tv.get_model()[path][GivenRowData._fields.index("handle")]
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

    def on_preserve_toggled(self, widget: Gtk.CheckButton) -> None:
        if self.controller:
            self.controller.update_preserve_alt(
                AltAction.PRESERVE if widget.get_active() else AltAction.OVERWRITE
            )

    # --- Column Setup ---
    def _add_text_column(
        self,
        title: str,
        field_name: str,
        expand: bool = False,
        use_markup: bool = False,
    ) -> None:
        """Helper to add a text column to the treeview."""
        attr = "markup" if use_markup else "text"
        col = Gtk.TreeViewColumn(
            title,
            Gtk.CellRendererText(),
            **{attr: GivenRowData._fields.index(field_name)},
        )
        col.set_expand(expand)
        col.set_sort_column_id(GivenRowData._fields.index(field_name))
        self.tree.append_column(col)

    def setup_columns(self) -> None:
        """Setup treeview columns for the rename tab."""
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self.on_row_toggled)
        self.tree.append_column(
            Gtk.TreeViewColumn(
                _("Use"), renderer_toggle, active=GivenRowData._fields.index("checkbox")
            )
        )
        self._add_text_column(_("ID"), "gramps_id")
        self._add_text_column(_("Individual"), "display_name", expand=True)
        self._add_text_column(_("Current"), "current", expand=True)
        self._add_text_column(_("Proposed"), "proposed", expand=True, use_markup=True)
        self._add_text_column(_("Action"), "alt_action")

    # --- Port Methods (Controller → View) ---

    def setup_autocompletion(self) -> None:
        given_names_set = self.controller.get_given_names()
        if not given_names_set:
            return
        completion_store = Gtk.ListStore(str)
        for name in sorted(given_names_set):
            completion_store.append([name])
        completion = Gtk.EntryCompletion()
        completion.set_model(completion_store)
        completion.set_text_column(0)
        completion.set_minimum_key_length(1)
        completion.set_inline_completion(True)
        completion.set_inline_selection(True)
        self.source_entry.set_completion(completion)

    def clear_proposals(self) -> None:
        self.store.clear()

    def append_proposal(self, row_data: GivenRowData) -> None:
        self.store.append(list(row_data))

    def update_actions(self, new_action: AltAction) -> None:
        act_idx = GivenRowData._fields.index("alt_action")
        translated = _(new_action.value)
        for row in self.store:
            row[act_idx] = translated

    def update_apply_button(self) -> None:
        chk_idx = GivenRowData._fields.index("checkbox")
        self.apply_btn.set_sensitive(any(row[chk_idx] for row in self.store))

    def get_checked_handles(self) -> set[str]:
        chk_idx = GivenRowData._fields.index("checkbox")
        h_idx = GivenRowData._fields.index("handle")
        return {row[h_idx] for row in self.store if row[chk_idx]}

    def is_preserve_enabled(self) -> bool:
        return self.preserve_check.get_active()

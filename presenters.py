# -*- coding: utf-8 -*-
"""
ui/presenters.py

Presenter layer for the East Slavic Name Tools.
Orchestrates services, formats UI data, and manages long-running idle loops.
"""

from gi.repository import GLib
from gramps.gen.const import GRAMPS_LOCALE as glocale

from pat_engine.inference_service import PatronymicInferenceService
from pat_engine.standardizer_service import GivenNameStandardizerService
from pat_engine.audit_service import PatronymicAuditService
from pat_engine.rollback_service import RollbackService
from pat_engine.logging import generate_execution_id
from pat_engine.rule_utils import pango_escape

_ = glocale.translation.gettext


class EastSlavicToolsPresenter:
    """COORDINATOR: Translates UI events to Service calls and formats UI data."""

    def __init__(self, view, dbstate):
        self.view = view
        self.dbstate = dbstate
        self.db = dbstate.db

        # Initialize Headless Services
        self.inference_service = PatronymicInferenceService(self.db)
        self.standardizer_service = GivenNameStandardizerService(self.db)
        self.audit_service = PatronymicAuditService(self.db, self.inference_service)
        self.rollback_service = RollbackService(
            self.db, self.inference_service.log_manager
        )

        # Session state
        self.scanned_candidates = []
        self.audit_issues = []
        self.rename_proposals = []

    def initialize_async(self):
        """Calculates DB metadata in the background to avoid UI freeze."""
        handles = list(self.db.get_person_handles())
        total = len(handles)
        if total == 0:
            return

        years = []
        idx = [0]

        def init_idle():
            try:
                for _ in range(200):  # Larger chunks for simple metadata
                    if idx[0] >= total:
                        if years:
                            self.inference_service.db_median_year = sorted(years)[
                                len(years) // 2
                            ]
                        return False

                    handle = handles[idx[0]]
                    person = self.db.get_person_from_handle(handle)
                    if person:
                        for event_ref in person.get_event_ref_list():
                            event = self.db.get_event_from_handle(event_ref.ref)
                            if (
                                event
                                and event.get_date_object()
                                and event.get_date_object().get_year()
                            ):
                                years.append(event.get_date_object().get_year())
                    idx[0] += 1
            except (StopIteration, IndexError):
                if years:
                    self.inference_service.db_median_year = sorted(years)[
                        len(years) // 2
                    ]
                return False
            return True

        GLib.idle_add(init_idle)

    # --- TAB 1: Inference ---

    def run_inference_scan(self, pre_reform: bool):
        """Orchestrates database scan for patronymic candidates using idle loops."""
        self.view.list_store.clear()
        self.scanned_candidates = []

        candidate_gen = self.inference_service.scan_candidates_generator(
            pre_reform=pre_reform
        )

        def scan_idle():
            try:
                for _ in range(20):  # Smaller chunks as inference is heavy
                    candidate = next(candidate_gen)
                    self.scanned_candidates.append(candidate)

                    row = [None] * 9
                    row[self.view.LIST_COL_CHECKBOX] = True
                    row[self.view.LIST_COL_DISPLAY_NAME] = candidate.display_name
                    row[self.view.LIST_COL_FATHER_NAME] = candidate.father_name
                    row[self.view.LIST_COL_REF_YEAR] = candidate.reference_year
                    row[self.view.LIST_COL_PATRONYMIC] = candidate.inferred_patronymic
                    row[self.view.LIST_COL_CONFIDENCE] = (
                        f"{int(candidate.confidence * 100)}%"
                    )
                    row[self.view.LIST_COL_RULE_SOURCE] = _(candidate.rule_source)
                    row[self.view.LIST_COL_GRAMPS_ID] = candidate.gramps_id
                    row[self.view.LIST_COL_HANDLE] = candidate.person_handle
                    self.view.list_store.append(row)
            except StopIteration:
                self.view.update_action_buttons()
                return False
            return True

        GLib.idle_add(scan_idle)

    def apply_checked_inferences(self, pre_reform: bool):
        """Gathers checked inferences from view and applies them."""
        checked_handles = set()
        for row in self.view.list_store:
            if row[self.view.LIST_COL_CHECKBOX]:
                checked_handles.add(row[self.view.LIST_COL_HANDLE])

        if not checked_handles:
            return False

        to_apply = [
            c for c in self.scanned_candidates if c.person_handle in checked_handles
        ]
        exec_id = generate_execution_id()
        self.inference_service.apply_patronymics_batch(to_apply, exec_id, pre_reform)
        return True

    # --- TAB 2: Audit ---

    def run_audit_scan(self, scope_idx: int, enabled_rules: set, use_pre_reform: bool):
        """Runs the consistency auditor with responsive idle-loading."""
        self.view.audit_store.clear()
        self.audit_issues = []

        handles = list(self.db.get_person_handles())
        total = len(handles)
        if total == 0:
            return

        audit_gen = self.audit_service.audit_generator(
            scope_idx, enabled_rules, use_pre_reform
        )
        idx = [0]

        def audit_idle():
            try:
                for _ in range(50):
                    issue = next(audit_gen)
                    self.audit_issues.append(issue)

                    row = [None] * 11
                    row[self.view.AUDIT_COL_CHECKBOX] = True
                    row[self.view.AUDIT_COL_DISPLAY_NAME] = issue.display_name
                    row[self.view.AUDIT_COL_GRAMPS_ID] = issue.gramps_id
                    row[self.view.AUDIT_COL_CURRENT_PAT] = issue.current_value
                    row[self.view.AUDIT_COL_REF_YEAR] = issue.reference_year
                    row[self.view.AUDIT_COL_RULE_ID] = issue.rule_id

                    diff_markup = f'<span foreground="red">{pango_escape(issue.current_value)}</span> \u2192 <span foreground="green" weight="bold">{pango_escape(issue.suggested_fix)}</span>'
                    row[self.view.AUDIT_COL_DIFF_MARKUP] = diff_markup

                    row[self.view.AUDIT_COL_HANDLE] = issue.person_handle
                    row[self.view.AUDIT_COL_RULE_ID_DUP] = issue.rule_id
                    row[self.view.AUDIT_COL_SUGGESTED_STRING] = issue.suggested_fix
                    row[self.view.AUDIT_COL_RULE_SOURCE] = _(issue.rule_source)
                    self.view.audit_store.append(row)
            except StopIteration:
                self.view.on_audit_complete(len(self.audit_issues))
                return False

            idx[0] += 50
            fraction = min(idx[0] / total, 1.0)
            self.view.update_audit_progress(fraction, f"{min(idx[0], total)} / {total}")
            return True

        GLib.idle_add(audit_idle)

    def apply_checked_audit_fixes(self, use_pre_reform: bool):
        """Gathers checked audit fixes from view and applies them."""
        checked_issues = []
        for i, row in enumerate(self.view.audit_store):
            if row[self.view.AUDIT_COL_CHECKBOX]:
                checked_issues.append(self.audit_issues[i])

        if not checked_issues:
            return False

        exec_id = generate_execution_id()
        from pat_engine.entities import InferenceCandidate

        candidates = [
            InferenceCandidate(
                person_handle=i.person_handle,
                gramps_id=i.gramps_id,
                display_name=i.display_name,
                father_name="",
                reference_year=i.reference_year,
                inferred_patronymic=i.suggested_fix,
                confidence=1.0,
                rule_source=i.rule_id,
            )
            for i in checked_issues
        ]

        self.inference_service.apply_patronymics_batch(
            candidates, exec_id, use_pre_reform
        )
        return True

    # --- TAB 3: Standardize ---

    def run_standardize_scan(self, source: str, target: str, match_type: int):
        """Scans for given name standardization proposals."""
        self.view.given_store.clear()
        self.rename_proposals = self.standardizer_service.scan_given_names(
            source, target, match_type
        )

        for prop in self.rename_proposals:
            row = [None] * 8
            row[self.view.GIVEN_COL_CHECKBOX] = True
            row[self.view.GIVEN_COL_GRAMPS_ID] = prop.gramps_id
            row[self.view.GIVEN_COL_DISPLAY_NAME] = prop.display_name
            row[self.view.GIVEN_COL_CURRENT] = prop.current_name

            markup = f'<span weight="bold" foreground="blue">{pango_escape(prop.proposed_name)}</span>'
            row[self.view.GIVEN_COL_PROPOSED] = markup

            row[self.view.GIVEN_COL_ALT_ACTION] = _(prop.alt_action)
            row[self.view.GIVEN_COL_HANDLE] = prop.person_handle
            row[self.view.GIVEN_COL_PROPOSED_RAW] = prop.proposed_name
            self.view.given_store.append(row)

        return len(self.rename_proposals) > 0

    def apply_checked_standardizations(self, preserve_alt: bool):
        """Gathers checked standardizations from view and applies them."""
        checked_handles = set()
        for row in self.view.given_store:
            if row[self.view.GIVEN_COL_CHECKBOX]:
                checked_handles.add(row[self.view.GIVEN_COL_HANDLE])

        if not checked_handles:
            return False

        to_apply = [
            p for p in self.rename_proposals if p.person_handle in checked_handles
        ]
        exec_id = generate_execution_id()
        self.standardizer_service.apply_standardizations(
            to_apply, exec_id, preserve_alt
        )
        return True

    # --- TAB 4: Rollback ---

    def refresh_history(self):
        """Reloads the execution history into the view."""
        self.view.log_store.clear()
        history = self.rollback_service.get_history()
        for run in history:
            row = [None] * 4
            row[self.view.LOG_COL_EXEC_ID] = run.get("execution_id", "")
            row[self.view.LOG_COL_TIMESTAMP] = run.get("timestamp", "")
            row[self.view.LOG_COL_CHANGES_COUNT] = len(run.get("changes", []))
            row[self.view.LOG_COL_PLUGIN_ID] = run.get("plugin_id", "")
            self.view.log_store.append(row)

    def rollback_run(self, exec_id: str):
        """Reverts a specific execution run."""
        return self.rollback_service.rollback_execution(exec_id)

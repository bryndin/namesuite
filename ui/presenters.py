# -*- coding: utf-8 -*-
"""
ui/presenters.py

Presenter layer for the East Slavic Name Tools.
Orchestrates services, formats UI data, and manages long-running idle loops.
"""

from gi.repository import GLib
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.display.name import displayer as name_displayer

from engine.inference_service import PatronymicInferenceService
from engine.standardizer_service import GivenNameStandardizerService
from engine.audit_service import PatronymicAuditService
from engine.rollback_service import RollbackService
from engine.logging import generate_execution_id
from engine.rule_utils import pango_escape

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
        self.rollback_service = RollbackService(self.db, self.inference_service.log_manager)

        # Session state
        self.scanned_candidates = []
        self.audit_issues = []
        self.rename_proposals = []

    # --- TAB 1: Inference ---

    def run_inference_scan(self, pre_reform: bool):
        """Orchestrates database scan for patronymic candidates."""
        self.view.list_store.clear()
        self.scanned_candidates = []
        
        # We can use a simple loop here or idle_add if it's too slow.
        # For now, following the pattern of yielding from the generator.
        for candidate in self.inference_service.scan_candidates_generator(pre_reform=pre_reform):
            self.scanned_candidates.append(candidate)
            row = [None] * 9
            row[self.view.LIST_COL_CHECKBOX] = True
            row[self.view.LIST_COL_DISPLAY_NAME] = candidate.display_name
            row[self.view.LIST_COL_FATHER_NAME] = candidate.father_name
            row[self.view.LIST_COL_REF_YEAR] = candidate.reference_year
            row[self.view.LIST_COL_PATRONYMIC] = candidate.inferred_patronymic
            row[self.view.LIST_COL_CONFIDENCE] = f"{int(candidate.confidence * 100)}%"
            row[self.view.LIST_COL_RULE_SOURCE] = _(candidate.rule_source)
            row[self.view.LIST_COL_GRAMPS_ID] = candidate.gramps_id
            row[self.view.LIST_COL_HANDLE] = candidate.person_handle
            self.view.list_store.append(row)
        
        return len(self.scanned_candidates) > 0

    def apply_inferences(self, checked_handles: set, pre_reform: bool):
        """Commits selected inferences via service."""
        to_apply = [c for c in self.scanned_candidates if c.person_handle in checked_handles]
        if not to_apply:
            return False
        
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

        # Generator for the audit issues
        audit_gen = self.audit_service.audit_generator(scope_idx, enabled_rules, use_pre_reform)
        
        # Progress tracking
        idx = [0]
        
        def audit_idle():
            try:
                # Process in chunks of 50 to keep UI alive
                for _ in range(50):
                    issue = next(audit_gen)
                    self.audit_issues.append(issue)
                    
                    # Format for UI
                    row = [None] * 11
                    row[self.view.AUDIT_COL_CHECKBOX] = True
                    row[self.view.AUDIT_COL_DISPLAY_NAME] = issue.display_name
                    row[self.view.AUDIT_COL_GRAMPS_ID] = issue.gramps_id
                    row[self.view.AUDIT_COL_CURRENT_PAT] = issue.current_value
                    row[self.view.AUDIT_COL_REF_YEAR] = issue.reference_year
                    row[self.view.AUDIT_COL_RULE_ID] = issue.rule_id
                    
                    # Formatting Pango markup for diff
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

    def apply_audit_fixes(self, checked_indices: list, use_pre_reform: bool):
        """Applies selected fixes from the audit results."""
        # Note: Audit results are many-to-one (person might have multiple issues)
        # However, our current logic seems to treat them as individual fixes.
        # For MVP, we map them back to InferenceCandidate or similar for batch apply
        # OR we just implement a small conversion here.
        
        # Actually, PatronymicInferenceService.apply_patronymics_batch expects InferenceCandidate.
        # Let's use a simpler approach for audit fixes for now or expand the service.
        # For consistency with Step 4, we'll use a transaction here or add it to a service.
        
        # To keep it clean, let's assume we can reuse apply_patronymics_batch 
        # by creating temporary InferenceCandidate objects from the AuditIssues.
        to_apply = []
        for idx in checked_indices:
            issue = self.audit_issues[idx]
            to_apply.append(issue)
            
        if not to_apply:
            return False

        exec_id = generate_execution_id()
        # Create a mini-adapter to InferenceCandidate if needed, 
        # or just use the service directly if we added a method there.
        # Since I didn't add an audit-apply specifically, I'll adapt them.
        from engine.entities import InferenceCandidate
        candidates = [
            InferenceCandidate(
                person_handle=i.person_handle,
                gramps_id=i.gramps_id,
                display_name=i.display_name,
                father_name="", # Not strictly needed for apply
                reference_year=i.reference_year,
                inferred_patronymic=i.suggested_fix,
                confidence=1.0,
                rule_source=i.rule_id
            ) for i in to_apply
        ]
        
        self.inference_service.apply_patronymics_batch(candidates, exec_id, use_pre_reform)
        return True

    # --- TAB 3: Standardize ---

    def run_standardize_scan(self, source: str, target: str, match_type: int):
        """Scans for given name standardization proposals."""
        self.view.given_store.clear()
        self.rename_proposals = self.standardizer_service.scan_given_names(source, target, match_type)
        
        for prop in self.rename_proposals:
            row = [None] * 8
            row[self.view.GIVEN_COL_CHECKBOX] = True
            row[self.view.GIVEN_COL_GRAMPS_ID] = prop.gramps_id
            row[self.view.GIVEN_COL_DISPLAY_NAME] = prop.display_name
            row[self.view.GIVEN_COL_CURRENT] = prop.current_name
            
            # Format Pango Markup for proposal
            # (In a real scenario, we might want more sophisticated diffing)
            markup = f'<span weight="bold" foreground="blue">{pango_escape(prop.proposed_name)}</span>'
            row[self.view.GIVEN_COL_PROPOSED] = markup
            
            row[self.view.GIVEN_COL_ALT_ACTION] = _(prop.alt_action)
            row[self.view.GIVEN_COL_HANDLE] = prop.person_handle
            row[self.view.GIVEN_COL_PROPOSED_RAW] = prop.proposed_name
            self.view.given_store.append(row)
            
        return len(self.rename_proposals) > 0

    def apply_standardizations(self, checked_handles: set, preserve_alt: bool):
        """Commits selected standardizations."""
        to_apply = [p for p in self.rename_proposals if p.person_handle in checked_handles]
        if not to_apply:
            return False
        
        exec_id = generate_execution_id()
        self.standardizer_service.apply_standardizations(to_apply, exec_id, preserve_alt)
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

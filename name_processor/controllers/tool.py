from typing import TYPE_CHECKING

from name_processor.models.audit import AuditScope
from name_processor.models.renamer import ProposedRename
from name_processor.utils.gtk_runner import run_in_idle_loop

if TYPE_CHECKING:
    from name_processor.services.alt_names import AltNamesService
    from name_processor.services.audit import AuditService
    from name_processor.services.chronology import ChronologyService
    from name_processor.services.patronymic import PatronymicInferenceService
    from name_processor.services.renamer import RenamerService
    from name_processor.models.audit import AuditIssue
    from name_processor.repositories.gramps_read import GrampsReadRepository
    from name_processor.repositories.gramps_write import GrampsWriteRepository
    from name_processor.views.tool import ToolWindow
    from names_tool import NamesTool


class ToolController:
    def __init__(
        self,
        tool_instance: "NamesTool",
        view: "ToolWindow",
        read_repo: "GrampsReadRepository",
        write_repo: "GrampsWriteRepository",
        patronymic_service: "PatronymicInferenceService",
        renamer_service: "RenamerService",
        alt_names_service: "AltNamesService",
        audit_service: "AuditService",
        chronology_service: "ChronologyService",
    ) -> None:
        self.tool = tool_instance
        self.dbstate = tool_instance.dbstate
        self.user = getattr(tool_instance, "user", None)

        # Kept strictly for View compatibility (`if self.controller.db.is_open()`)
        self.db = self.dbstate.db

        # MVCS Layers
        self._view = view
        self._read_repo = read_repo
        self._write_repo = write_repo
        self._patronymic_service = patronymic_service
        self._renamer_service = renamer_service
        self._alt_names_service = alt_names_service
        self._audit_service = audit_service
        self._chronology_service = chronology_service

        # State Caches
        self._given_names_cache: set[str] = set()
        self._standardize_candidates: dict[str, ProposedRename] = {}
        self._inference_candidates: dict[str, object] = {}
        self._audit_candidates: dict[str, AuditIssue] = {}

    def cleanup(self) -> None:
        pass

    def get_gramps_person(self, handle: str) -> object:
        """Used by the view to open the native Gramps Person Editor."""
        return self._read_repo.get_raw_person(handle)

    # ==========================================
    # Initialization & Caching
    # ==========================================
    def initialize_median_year_async(self) -> None:
        generator = self._read_repo.get_database_median_year_chunked()

        def on_complete(median_year: int | None) -> None:
            if median_year is not None:
                self._chronology_service.set_db_median_year(median_year)

        run_in_idle_loop(generator, on_complete)

    def initialize_given_names_async(self) -> None:
        def generator():
            names = set()
            for proxy_chunk in self._read_repo.get_person_proxies_chunked(
                chunk_size=500
            ):
                for proxy in proxy_chunk:
                    if proxy.given_name:
                        names.add(proxy.given_name)
                yield None
            return names

        def on_complete(final_names: set[str] | None) -> None:
            if final_names:
                self._given_names_cache.update(final_names)
                self._view.setup_given_name_autocompletion()

        run_in_idle_loop(generator(), on_complete)

    def get_given_names(self) -> set[str]:
        return self._given_names_cache

    # ==========================================
    # Tab 1: Standardize Names
    # ==========================================
    def run_standardize_scan(
        self, source: str, target: str, match_type_idx: int
    ) -> bool:
        mode_map = {0: "exact", 1: "substring", 2: "regex"}
        rule = self._renamer_service.create_rule(
            mode_map.get(match_type_idx, "exact"), source, target
        )
        if not rule.is_valid:
            return False

        self._view.given_store.clear()
        self._standardize_candidates.clear()
        preserve_alt = self._view.preserve_alt_check.get_active()

        def scan_generator():
            found_any = False
            for proxy_chunk in self._read_repo.get_person_proxies_chunked(
                chunk_size=250
            ):
                for person_proxy in proxy_chunk:
                    proposal = self._renamer_service.evaluate_person(person_proxy, rule)
                    if proposal:
                        proposal.alt_action = (
                            "Preserve" if preserve_alt else "Overwrite"
                        )
                        self._standardize_candidates[person_proxy.handle] = proposal
                        self._view._append_rename_proposal_to_store(proposal)
                        found_any = True
                yield None
            return found_any

        def on_complete(found_any: bool) -> None:
            self._view.update_given_apply_button()
            if not found_any:
                self._view.show_no_results_message()

            if not found_any:
                self._view.show_ok_dialog(
                    "No Results", "No matching given names found."
                )

        run_in_idle_loop(scan_generator(), on_complete)
        return True

    def apply_checked_standardizations(self) -> bool:
        handles = self._view.get_checked_standardization_handles()
        if not handles:
            return False

        preserve_alt = self._view.preserve_alt_check.get_active()
        approved_changes = [
            self._standardize_candidates[h]
            for h in handles
            if h in self._standardize_candidates
        ]

        with self._write_repo.transaction("Batch Given Name Standardization") as t:
            for change in approved_changes:
                person = self._read_repo.get_raw_person(change.handle)
                if not person:
                    continue

                if preserve_alt:
                    self._alt_names_service.preserve_primary_name(person)

                self._write_repo.apply_first_name_correction(
                    t, person, change.proposed_given_name
                )

        return True

    # ==========================================
    # Tab 2: Infer Patronymics
    # ==========================================
    def run_inference_scan(self, pre_reform: bool) -> None:
        self._view.list_store.clear()
        self._inference_candidates.clear()

        def scan_generator():
            found_count = 0
            for proxy_chunk in self._read_repo.get_person_proxies_chunked(
                chunk_size=250
            ):
                for person_proxy in proxy_chunk:
                    father_proxy = None
                    if person_proxy.father_handle:
                        father_proxy = self._read_repo.get_person_proxy(
                            person_proxy.father_handle
                        )

                    result = self._patronymic_service.infer_patronymic(
                        person_proxy, father_proxy
                    )

                    if result.status.name == "SUCCESS":

                        class DummyCandidate:
                            pass

                        candidate = DummyCandidate()
                        candidate.display_name = person_proxy.display_name
                        candidate.father_name = (
                            result.context.father_name if result.context else ""
                        )
                        candidate.reference_year = str(
                            self._chronology_service.estimate_reference_year(
                                person_proxy.handle
                            )
                            or "N/A"
                        )
                        candidate.inferred_patronymic = result.value
                        candidate.confidence = 0.95
                        candidate.rule_source = "Morphology Engine"
                        candidate.gramps_id = person_proxy.gramps_id
                        candidate.person_handle = person_proxy.handle

                        self._inference_candidates[person_proxy.handle] = candidate
                        self._view._append_candidate_to_store(candidate)
                        found_count += 1
                yield None
            return found_count

        run_in_idle_loop(scan_generator(), on_complete=self._view.on_scan_complete)

    def apply_checked_inferences(self) -> bool:
        handles = self._view.get_checked_inference_handles()
        if not handles:
            return False

        with self._write_repo.transaction("Batch Patronymic Inference") as trans:
            for handle in handles:
                candidate = self._inference_candidates.get(handle)
                if not candidate:
                    continue

                self._write_repo.apply_patronymic_correction(
                    trans, handle, candidate.inferred_patronymic
                )

        return True

    # ==========================================
    # Tab 3: Audit Patronymics
    # ==========================================
    def get_available_audit_rules(self) -> list[str]:
        return self._audit_service.get_available_audit_rules()

    def run_audit_scan(
        self, audit_scope: AuditScope, enabled_rules_set: set[str], use_pre_reform: bool
    ) -> None:
        self._view.clear_audit_results()
        self._audit_candidates.clear()

        # Get total person count dynamically from the repo for the progress bar
        total_people = self._read_repo.get_person_count()

        def generator():
            # View idle loop natively calls next(generator) chunk by chunk
            for person_proxy in self._read_repo.iter_all_person_proxies():
                # Apply scope filter
                if audit_scope == AuditScope.MALES_ONLY:
                    if person_proxy.gender.name != "MALE":
                        continue
                elif audit_scope == AuditScope.FEMALES_ONLY:
                    if person_proxy.gender.name != "FEMALE":
                        continue

                issues = self._audit_service.audit_person(
                    person_proxy, enabled_rules_set, use_pre_reform
                )
                for issue in issues:
                    self._audit_candidates[person_proxy.handle] = issue
                    yield issue

        self._view.start_idle_audit(
            generator(), total_people, self._view.on_audit_complete
        )

    def apply_checked_audit_fixes(self, use_pre_reform: bool) -> bool:
        handles = self._view.get_checked_audit_handles()
        if not handles:
            return False

        with self._write_repo.transaction("Batch Patronymic Audit Fixes") as t:
            for handle in handles:
                issue = self._audit_candidates.get(handle)
                if not issue:
                    continue

                self._write_repo.apply_patronymic_correction(
                    t, handle, issue.suggested_fix
                )

        return True

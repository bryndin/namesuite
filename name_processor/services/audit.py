import logging
from typing import TYPE_CHECKING

from name_processor.models.audit import AuditIssue, RuleContext
from name_processor.models.constants import LOCALE_RU
from name_processor.services.audit_rules.gender_mismatch import ErrGenderMismatch
from name_processor.services.audit_rules.lineage_mismatch import ErrLineageMismatch
from name_processor.services.audit_rules.modern_suffix_archaic_era import (
    WarnModernSuffixArchaicEra,
)
from name_processor.services.audit_rules.archaic_suffix_modern_era import (
    WarnArchaicSuffixModernEra,
)
from name_processor.services.audit_rules.mixed_scripts import ErrMixedScripts
from name_processor.services.audit_rules.morphological_typo import WarnMorphologicalTypo
from name_processor.services.audit_rules.missing_hard_sign import WarnMissingHardSign

if TYPE_CHECKING:
    from name_processor.repositories.gramps_read import GrampsReadRepository
    from name_processor.services.chronology import ChronologyService
    from name_processor.repositories.person import GrampsPersonProxy

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(
        self, read_repo: "GrampsReadRepository", chronology_service: "ChronologyService"
    ):
        self._read_repo = read_repo
        self._chronology_service = chronology_service

        # Instantiate active rules
        self._rules = [
            ErrGenderMismatch(),
            ErrLineageMismatch(),
            WarnModernSuffixArchaicEra(),
            WarnArchaicSuffixModernEra(),
            ErrMixedScripts(),
            WarnMorphologicalTypo(),
            WarnMissingHardSign(),
        ]

    def get_available_audit_rules(self) -> list[str]:
        """Returns the IDs of all loaded rules to populate the UI configuration dialog."""
        return [rule.rule_id for rule in self._rules]

    def audit_person(
        self, person: "GrampsPersonProxy", enabled_rules: set[str], use_pre_reform: bool
    ) -> list[AuditIssue]:
        """Evaluates a single person against enabled rules and yields formatted DTOs."""
        issues: list[AuditIssue] = []

        # Determine existing patronymic. If none, there is nothing to audit.
        # (Assuming your person proxy exposes standard grammatical name parts)
        current_patronymic = person.patronymic or ""
        if not current_patronymic:
            return issues

        # Build Context
        father_given_name = None
        if person.father_handle:
            father_proxy = self._read_repo.get_person_proxy(person.father_handle)
            if father_proxy:
                father_given_name = father_proxy.given_name

        ref_year = self._chronology_service.estimate_reference_year(person.handle)

        ctx = RuleContext(
            person_handle=person.handle,
            gramps_id=person.gramps_id,
            display_name=person.display_name,
            gender=person.gender,
            current_patronymic=current_patronymic,
            father_given_name=father_given_name,
            reference_year=ref_year,
            locale=LOCALE_RU,  # Can be expanded dynamically later
        )

        # Evaluate rules
        for rule in self._rules:
            if rule.rule_id not in enabled_rules:
                continue

            # Era evaluation
            start, end = rule.active_era
            if ctx.reference_year is not None:
                if start is not None and ctx.reference_year < start:
                    continue
                if end is not None and ctx.reference_year > end:
                    continue

            # Safe execution
            try:
                change = rule.evaluate(ctx, use_pre_reform)
            except Exception as e:
                logger.error(
                    f"Rule {rule.rule_id} failed for person {ctx.person_handle}: {e}"
                )
                continue
            if change:
                issues.append(
                    AuditIssue(
                        person_handle=ctx.person_handle,
                        gramps_id=ctx.gramps_id,
                        display_name=ctx.display_name,
                        current_value=ctx.current_patronymic,
                        suggested_fix=change.suggested_string,
                        reference_year=str(ctx.reference_year)
                        if ctx.reference_year
                        else "N/A",
                        rule_id=rule.rule_id,
                        rule_source=rule.rule_id,  # Or custom name
                        explanation=change.explanation,
                        severity=rule.severity,
                        is_pre_reform=use_pre_reform,
                    )
                )
        return issues

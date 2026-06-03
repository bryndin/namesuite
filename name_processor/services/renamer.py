import re
from typing import Optional, TYPE_CHECKING

from name_processor.models.renamer import MatchMode, RuleConfig, ProposedRename

if TYPE_CHECKING:
    from name_processor.repositories.person import GrampsPersonProxy


class RenamerService:
    def create_rule(
        self, match_type: str, source_str: str, target_str: str
    ) -> RuleConfig:
        """
        Validates the user configuration before the batch scan begins.
        Catches invalid Regular Expressions immediately.
        """
        try:
            mode = MatchMode(match_type.lower())
        except ValueError:
            return RuleConfig(
                mode=MatchMode.EXACT,
                source=source_str,
                target=target_str,
                is_valid=False,
                error_msg=f"Unsupported match type: {match_type}",
            )

        config = RuleConfig(mode=mode, source=source_str, target=target_str)

        if mode == MatchMode.REGEX:
            try:
                # Compile regex early to validate syntax and catch re.error
                config.pattern = re.compile(source_str)
            except re.error as e:
                config.is_valid = False
                config.error_msg = f"Invalid Regular Expression: {e.msg}"

        return config

    def evaluate_person(
        self, person: "GrampsPersonProxy", rule: RuleConfig
    ) -> Optional[ProposedRename]:
        """
        Evaluates a person's primary given name against the replacement rule.

        :returns: ProposedRename DTO if a valid change is found, otherwise None.
        """
        if not rule.is_valid:
            return None

        # Edge Case 1: Missing object or missing Primary Name field
        if not person or not person.given_name:
            return None

        original_name = person.given_name
        proposed_name = None

        # Execution based on user strategy
        if rule.mode == MatchMode.EXACT:
            if original_name == rule.source:
                proposed_name = rule.target

        elif rule.mode == MatchMode.SUBSTRING:
            if rule.source in original_name:
                proposed_name = original_name.replace(rule.source, rule.target)

        elif rule.mode == MatchMode.REGEX and rule.pattern:
            if rule.pattern.search(original_name):
                proposed_name = rule.pattern.sub(rule.target, original_name)

        # Edge Case 2: No match found, or replacement resulted in the exact same string
        if not proposed_name or proposed_name == original_name:
            return None

        return ProposedRename(
            handle=person.handle,
            gramps_id=person.gramps_id,
            display_name=person.display_name,
            original_given_name=original_name,
            proposed_given_name=proposed_name,
        )

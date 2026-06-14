from __future__ import annotations

import re
from typing import TYPE_CHECKING

from name_processor.models.renamer import (
    AltAction,
    MatchMode,
    ProposedRename,
    RenameConfig,
)

if TYPE_CHECKING:
    from name_processor.protocols.renamer import RenameSubject


class RenamerService:
    def create_config(
        self, match_type: MatchMode, source_str: str, target_str: str
    ) -> RenameConfig:
        config = RenameConfig(mode=match_type, source=source_str, target=target_str)
        if match_type == MatchMode.REGEX:
            try:
                config.pattern = re.compile(source_str)
            except re.error as e:
                config.is_valid = False
                config.error_msg = f"Invalid Regular Expression: {e.msg}"
        return config

    def evaluate_person(
        self, person: RenameSubject, cfg: RenameConfig
    ) -> ProposedRename | None:
        if not cfg.is_valid or not person:
            return None

        original_name = person.given_name
        if not original_name:
            return None

        proposed_name = None

        if cfg.mode == MatchMode.EXACT:
            proposed_name = cfg.target

        elif cfg.mode == MatchMode.SUBSTRING:
            proposed_name = original_name.replace(cfg.source, cfg.target)

        elif cfg.mode == MatchMode.REGEX and cfg.pattern:
            proposed_name = cfg.pattern.sub(cfg.target, original_name)

        if not proposed_name or proposed_name == original_name:
            return None

        return ProposedRename(
            handle=person.handle,
            gramps_id=person.gramps_id,
            display_name=person.display_name,
            original_given_name=original_name,
            proposed_given_name=proposed_name,
            alt_action=AltAction.PRESERVE,
        )

from __future__ import annotations

import re

from name_processor.models.renamer import MatchMode, RenameConfig


class RenamerService:
    def create_config(
        self, match_type: MatchMode, source: str, target: str
    ) -> RenameConfig:
        config = RenameConfig(mode=match_type, source=source, target=target)
        if match_type == MatchMode.REGEX:
            config.pattern = re.compile(source)
        return config

    def evaluate_person(self, name: str | None, cfg: RenameConfig) -> str | None:
        """Returns the transformed given name, or None if no change."""
        if not name:
            return None

        original_name = name
        proposed_name = None

        if cfg.mode == MatchMode.EXACT:
            proposed_name = cfg.target

        elif cfg.mode == MatchMode.SUBSTRING:
            proposed_name = original_name.replace(cfg.source, cfg.target)

        elif cfg.mode == MatchMode.REGEX and cfg.pattern:
            proposed_name = cfg.pattern.sub(cfg.target, original_name)

        if not proposed_name or proposed_name == original_name:
            return None

        return proposed_name

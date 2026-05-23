# -*- coding: utf-8 -*-
"""
engine/linter.py

Implementation of Phase 3 Quality & Consistency Auditing (The Linter) for Gramps.
Provides a validation engine, context models, dynamic rule registry, and
the standard linter ruleset.
"""

import functools
import logging
from typing import Optional, List, Any, Set, Tuple


from engine.rule import (
    BaseRule,
    RuleContext,
    ProposedChange,
)
from engine.constants import LOCALE_UNIVERSAL
from engine.rules import (
    ErrGenderMismatch,
    ErrLineageMismatch,
    WarnModernSuffixArchaicEra,
    WarnArchaicSuffixModernEra,
    ErrMixedScripts,
    WarnMorphologicalTypo,
    WarnMissingHardSign,
)

logger = logging.getLogger(__name__)


class PlaceCache:
    """Session-scoped place cache. Instantiate per batch run to avoid memory leaks."""

    def __init__(self, db: Any):
        self.db = db

        @functools.lru_cache(maxsize=None)
        def _get_places(person_handle: str) -> List[str]:
            places = []
            if not self.db or not person_handle:
                return places
            try:
                person = self.db.get_person_from_handle(person_handle)
                if person:
                    for event_ref in person.get_event_ref_list():
                        event = self.db.get_event_from_handle(event_ref.ref)
                        if event:
                            place_handle = event.get_place_handle()
                            if place_handle:
                                place = self.db.get_place_from_handle(place_handle)
                                if place:
                                    title = ""
                                    if hasattr(place, "get_title"):
                                        title = place.get_title()
                                    elif hasattr(place, "title"):
                                        title = place.title
                                    if title:
                                        places.append(title)
            except Exception:
                pass
            return places

        self.get_places = _get_places


# =========================================================================
# The Dispatcher Engine
# =========================================================================


class RuleEngine:
    """Dispatches evaluation rules dynamically over target person records."""

    def __init__(self, rules: Optional[List[BaseRule]] = None):
        """Indexes registered rules."""
        if rules is None:
            self.rules = [
                ErrGenderMismatch(),
                ErrLineageMismatch(),
                WarnModernSuffixArchaicEra(),
                WarnArchaicSuffixModernEra(),
                ErrMixedScripts(),
                WarnMorphologicalTypo(),
                WarnMissingHardSign(),
            ]
        else:
            self.rules = rules

    def evaluate_person(
        self, ctx: RuleContext, enabled_rules: Optional[Set[str]] = None
    ) -> List[Tuple[BaseRule, ProposedChange]]:
        """
        Evaluates a single Person context against all applicable rules.
        Includes graceful degradation to ensure that single-rule failures
        do not crash the process.
        """
        triggered = []
        for rule in self.rules:
            # 1. Check if the rule is enabled
            if enabled_rules is not None and rule.rule_id not in enabled_rules:
                continue

            # 2. Match locale
            if (
                rule.supported_locales != {LOCALE_UNIVERSAL}
                and ctx.locale not in rule.supported_locales
            ):
                continue

            # 3. Match era bounds
            if ctx.reference_year is None:
                continue
            start, end = rule.active_era
            if start is not None and ctx.reference_year < start:
                continue
            if end is not None and ctx.reference_year > end:
                continue

            # 4. Evaluate with safe crash protection
            try:
                change = rule.evaluate(ctx)
                if change:
                    triggered.append((rule, change))
            except Exception as e:
                # Log or print the issue to ensure graceful continuation
                logger.error(
                    f"[Linter Error] Rule '{rule.rule_id}' failed on '{ctx.person_id}': {e}",
                    exc_info=True,
                )

        return triggered

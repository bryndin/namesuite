# -*- coding: utf-8 -*-
"""
engine/base.py

Base classes and data structures for the linter validation engine.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Set, Tuple, List, Callable

# Severity level constants
SEVERITY_ERROR = "ERROR"
SEVERITY_WARNING = "WARNING"
SEVERITY_INFO = "INFO"

# Locale constants
LOCALE_RU = "ru"
LOCALE_UK = "uk"
LOCALE_BE = "be"
LOCALE_UNIVERSAL = "*"
LOCALE_EAST_SLAVIC = {LOCALE_RU, LOCALE_UK, LOCALE_BE}


@dataclass(frozen=True)
class RuleContext:
    """Frozen evaluation context for linter validation rules."""

    person_id: str
    current_patronymic: str
    father_given_name: str
    gramps_gender: int
    reference_year: int
    locale: str
    _place_resolver: Optional[Callable[[str], List[str]]] = None

    @property
    def place_context(self) -> List[str]:
        """Lazy-evaluated place list using the session-scoped cache."""
        if self._place_resolver:
            return self._place_resolver(self.person_id)
        return []


@dataclass
class ProposedChange:
    """Holds structural feedback and suggestions from the validation rule."""

    explanation: str
    suggested_string: str
    diff_markup: str


class BaseRule(ABC):
    """Abstract Base Class for all linter consistency rules."""

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Unique rule identifier (e.g. ERR_GENDER_MISMATCH)."""
        pass

    @property
    @abstractmethod
    def severity(self) -> str:
        """Rule severity: 'ERROR', 'WARNING', or 'INFO'."""
        pass

    @property
    @abstractmethod
    def supported_locales(self) -> Set[str]:
        """Set of supported locale ISO codes (e.g. {'ru', 'uk'} or {'*'} for universal)."""
        pass

    @property
    @abstractmethod
    def active_era(self) -> Tuple[Optional[int], Optional[int]]:
        """Active chronological window (start_year, end_year) this rule applies to."""
        pass

    @abstractmethod
    def evaluate(self, ctx: RuleContext) -> Optional[ProposedChange]:
        """
        Evaluates context. Returns None if rule passes, or a ProposedChange
        if consistency issues are detected.
        """
        pass

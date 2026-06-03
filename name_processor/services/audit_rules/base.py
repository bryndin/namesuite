from abc import ABC, abstractmethod
from typing import Optional, Set, Tuple
from name_processor.models.audit import RuleContext, ProposedChange


class BaseRule(ABC):
    """Abstract Base Class for all linter consistency rules."""

    @property
    @abstractmethod
    def rule_id(self) -> str:
        pass

    @property
    @abstractmethod
    def severity(self) -> str:
        pass

    @property
    @abstractmethod
    def supported_locales(self) -> Set[str]:
        pass

    @property
    @abstractmethod
    def active_era(self) -> Tuple[Optional[int], Optional[int]]:
        pass

    @abstractmethod
    def evaluate(
        self, ctx: RuleContext, use_pre_reform: bool
    ) -> Optional[ProposedChange]:
        """
        Evaluates context. Returns None if rule passes, or a ProposedChange
        if consistency issues are detected.
        """
        pass

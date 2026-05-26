# -*- coding: utf-8 -*-
"""
engine/entities.py

Domain entities for the East Slavic patronymic and name tool.
These classes are pure data containers decoupled from GTK and DB logic.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class InferenceCandidate:
    """Holds demographic and generational context for candidates missing patronymics."""
    person_handle: str
    gramps_id: str
    display_name: str
    father_name: str
    reference_year: int
    inferred_patronymic: str
    confidence: float
    rule_source: str


@dataclass(frozen=True)
class AuditIssue:
    """Captures raw properties of a linting violation."""
    person_handle: str
    gramps_id: str
    display_name: str
    current_value: str
    reference_year: int
    rule_id: str
    rule_source: str
    suggested_fix: str


@dataclass(frozen=True)
class RenameProposal:
    """Models a proposed change for given name standardization."""
    person_handle: str
    gramps_id: str
    display_name: str
    current_name: str
    proposed_name: str
    alt_action: str  # e.g., "None", "Add as AKA", "Merge Existing Alt Name"

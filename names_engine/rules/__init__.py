# -*- coding: utf-8 -*-
"""
engine/rules

Linter validation rules for patronymic consistency checking.
Each rule is implemented as a separate module extending BaseRule.
"""

from .gender_mismatch import ErrGenderMismatch
from .lineage_mismatch import ErrLineageMismatch
from .modern_suffix_archaic_era import WarnModernSuffixArchaicEra
from .archaic_suffix_modern_era import WarnArchaicSuffixModernEra
from .mixed_scripts import ErrMixedScripts
from .morphological_typo import WarnMorphologicalTypo
from .missing_hard_sign import WarnMissingHardSign

__all__ = [
    'ErrGenderMismatch',
    'ErrLineageMismatch',
    'WarnModernSuffixArchaicEra',
    'WarnArchaicSuffixModernEra',
    'ErrMixedScripts',
    'WarnMorphologicalTypo',
    'WarnMissingHardSign',
]

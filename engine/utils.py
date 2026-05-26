# -*- coding: utf-8 -*-
"""
engine/utils.py

Utility functions for the linter validation engine.
"""
from engine.constants import LOCALE_RU, REFORM_YEAR_1918

def is_pre_reform(ctx) -> bool:
    """Check if the context satisfies the pre-reform conditions."""
    return (
        ctx.locale == LOCALE_RU
        and ctx.reference_year is not None
        and ctx.reference_year < REFORM_YEAR_1918
        and ctx.use_pre_reform
    )

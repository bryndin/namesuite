# -*- coding: utf-8 -*-
"""
engine/compat.py

Compatibility layer for Gramps library imports.
Provides fallback stubs for Gramps types when running outside of Gramps environment.
"""

try:
    from gramps.gen.lib import Person
except ImportError:
    class Person:
        """Fallback stub for gramps.gen.lib.Person when Gramps is not available."""
        OTHER = 3
        UNKNOWN = 2
        MALE = 1
        FEMALE = 0

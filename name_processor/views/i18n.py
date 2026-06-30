"""
Internationalization (i18n) module for the NameSuite addon.
Provides translation binding anchored at the addon root directory.
"""

import os
from gramps.gen.const import GRAMPS_LOCALE as glocale

# This file is at name_processor/views/i18n.py
# The addon root (which holds locale/) is three directories up
_ADDON_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
try:
    _trans = glocale.get_addon_translator(os.path.join(_ADDON_ROOT, ""))
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

# Run mock setup at package-import time so all sys.modules are populated
# before any test module imports project code.
from __future__ import annotations

import sys
from pathlib import Path

from .compat_mocks import mock_gramps

# Add parent directory to sys.path to support running tests from parent directory
# (e.g., python3 -m unittest NameSuite.tests.controllers.test_tool)
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

mock_gramps()

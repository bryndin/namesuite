import sys
from unittest.mock import MagicMock

# Inject the mock modules into sys.modules so imports don't fail
sys.modules["gramps"] = MagicMock()
sys.modules["gramps.gen"] = MagicMock()
sys.modules["gramps.gen.lib"] = MagicMock()

# Explicitly mock the deep submodule path
sys.modules["gramps.gen.lib.nameorigintype"] = MagicMock()

sys.modules["gramps.gen.db"] = MagicMock()
sys.modules["gramps.gen.plug"] = MagicMock()
sys.modules["gramps.gen.types"] = MagicMock()

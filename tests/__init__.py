# Run mock setup at package-import time so all sys.modules are populated
# before any test module imports project code.
from tests.compat_mocks import mock_gramps

mock_gramps()

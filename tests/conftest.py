import sys
from unittest.mock import MagicMock


# Create mocks for MATLAB-related modules if they are not available
def pytest_sessionstart(session):
    if "SimPackage" not in sys.modules:
        mock_sim = MagicMock()
        mock_sim.initialize.return_value = MagicMock()
        sys.modules["SimPackage"] = mock_sim

    if "matlab" not in sys.modules:
        sys.modules["matlab"] = MagicMock()

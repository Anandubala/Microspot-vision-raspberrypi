import os

# Must be set before any Qt import happens, so tests can run on a machine
# (or CI) with no display attached — e.g. this is how the dev-loop tests
# in spec Section 4.2 run on Windows without a monitor requirement.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def qapp_session():
    app = QApplication.instance() or QApplication([])
    yield app

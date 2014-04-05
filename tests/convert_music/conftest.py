import logging.config
import os
import sys
import pytest
from color_logging_misc import LoggingSetup


@pytest.fixture(autouse=True, scope='session')
def log():
    """Initialize logging, to capture log messages."""
    assert '--capture' in sys.argv or '--capture=sys' in sys.argv  # Be sure you run: py.test --capture=sys
    with LoggingSetup(verbose=True) as cm:
        logging.config.fileConfig(cm.config)


@pytest.fixture
def threads():
    """Returns the default number of threads, which are number of logical CPUs on this system."""
    num = os.sysconf('SC_NPROCESSORS_ONLN')
    assert isinstance(num, int)
    assert 0 < num < 100
    return num

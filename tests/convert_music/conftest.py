import pytest

from convert_music import OPTIONS


@pytest.fixture(autouse=True, scope='function')
def reset_options():
    OPTIONS.clear()

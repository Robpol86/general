import tempfile
import pytest


@pytest.fixture
def log_file(request):
    f = tempfile.NamedTemporaryFile()
    request.addfinalizer(lambda: f.close())
    return f

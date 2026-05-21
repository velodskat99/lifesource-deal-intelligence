import os
import tempfile

import pytest


@pytest.fixture
def tmp_db():
    """Create a temporary SQLite database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def db(tmp_db):
    """Create an initialized test database."""
    from lifesource.db import init_db, get_connection

    init_db(tmp_db)
    conn = get_connection(tmp_db)
    yield conn
    conn.close()

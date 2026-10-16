'''
fsdelta: test fixtures
'''

# Import external dependencies
import pytest, sqlite3
from collections.abc import Iterator
from pathlib import Path

# Import internal fsdelta objects
from fsdelta.db import connect

# conn: create a new database in a temp dir
@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = connect(tmp_path / 'db' / 'fsdelta.db')
    yield connection
    connection.close()

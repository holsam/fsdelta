'''
fsdelta: tests for the sqlite db
'''

# Import external dependencies
import pytest, sqlite3

# Import internal fsdelta objects
from fsdelta.db import (
    add_scan,
    delete_diff,
    delete_scan,
    diff_entries,
    list_diffs,
    list_scans,
    resolve_scan,
    save_diff,
)
from fsdelta.diff import compute_diff
from fsdelta.schema import DiffEntry, Entry

# _entry: build a plain file entry for storage tests
def _entry(path: str, hash: str | None = 'h') -> Entry:
    return Entry(path=path, kind='file', size=1, mode=0o644, mtime_ns=0, hash=hash)

# test_add_and_resolve_scan: a stored scan resolves by name and by id
def test_add_and_resolve_scan(conn: sqlite3.Connection) -> None:
    info = add_scan(conn, 'pre', '/root', [_entry('a'), _entry('b')])
    assert info.entry_count == 2
    assert resolve_scan(conn, 'pre') == info
    assert resolve_scan(conn, str(info.id)) == info

# test_duplicate_name_rejected: names are unique
def test_duplicate_name_rejected(conn: sqlite3.Connection) -> None:
    add_scan(conn, 'pre', '/root', [])
    with pytest.raises(ValueError, match='already exists'):
        add_scan(conn, 'pre', '/root', [])

# test_digit_name_rejected: all-digit names would clash with ids
def test_digit_name_rejected(conn: sqlite3.Connection) -> None:
    with pytest.raises(ValueError, match='invalid name'):
        add_scan(conn, '42', '/root', [])

# test_unknown_scan: unknown selectors raise LookupError
def test_unknown_scan(conn: sqlite3.Connection) -> None:
    with pytest.raises(LookupError, match='unknown scan'):
        resolve_scan(conn, 'nope')

# test_saved_diff_survives_scan_deletion: deleting a scan drops its entries but keeps saved diffs
def test_saved_diff_survives_scan_deletion(conn: sqlite3.Connection) -> None:
    before = add_scan(conn, 'pre', '/root', [_entry('x')])
    after = add_scan(conn, 'post', '/root', [])
    entries = compute_diff(conn, before.id, after.id)
    info = save_diff(conn, 'change', 'pre', 'post', entries)
    delete_scan(conn, 'pre')
    assert [s.name for s in list_scans(conn)] == ['post']
    assert conn.execute('SELECT COUNT(*) FROM entry WHERE scan_id = ?', (before.id,)).fetchone()[0] == 0
    assert diff_entries(conn, info.id) == entries

# test_delete_diff: deleting a diff removes its rows
def test_delete_diff(conn: sqlite3.Connection) -> None:
    info = save_diff(conn, 'change', 'a', 'b', [DiffEntry(path='x', change='added')])
    delete_diff(conn, 'change')
    assert list_diffs(conn) == []
    assert conn.execute('SELECT COUNT(*) FROM diff_entry WHERE diff_id = ?', (info.id,)).fetchone()[0] == 0

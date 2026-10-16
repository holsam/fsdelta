'''
fsdelta: tests for diff command
'''

# Import external dependencies
import sqlite3
from pathlib import Path

# Import internal fsdelta objects
from fsdelta.db import add_scan
from fsdelta.diff import compute_diff
from fsdelta.scan import scan_tree

# _snap: scan a root into the database and return the scan id
def _snap(conn: sqlite3.Connection, root: Path, name: str) -> int:
    return add_scan(conn, name, str(root), scan_tree(root)).id

# test_each_change_type: added, modified, deleted, renamed and mode-only changes are all found
def test_each_change_type(conn: sqlite3.Connection, tmp_path: Path) -> None:
    root = tmp_path / 'r'
    root.mkdir()
    for name, text in [('keep', 'k'), ('edit', '1'), ('gone', 'g'), ('mv', 'move me'), ('perm', 'p')]:
        (root / name).write_text(text)
    before = _snap(conn, root, 'before')
    (root / 'edit').write_text('2')
    (root / 'gone').unlink()
    (root / 'mv').rename(root / 'moved')
    (root / 'new').write_text('n')
    (root / 'perm').chmod(0o755)
    after = _snap(conn, root, 'after')
    got = {(e.change, e.path, e.old_path) for e in compute_diff(conn, before, after)}
    assert got == {
        ('modified', 'edit', None),
        ('deleted', 'gone', None),
        ('renamed', 'moved', 'mv'),
        ('added', 'new', None),
        ('modified', 'perm', None),
    }

# test_ambiguous_hash_not_paired: duplicate content stays as plain add and delete
def test_ambiguous_hash_not_paired(conn: sqlite3.Connection, tmp_path: Path) -> None:
    root = tmp_path / 'r'
    root.mkdir()
    (root / 'x1').write_text('same')
    (root / 'x2').write_text('same')
    before = _snap(conn, root, 'before')
    (root / 'x1').unlink()
    (root / 'x2').unlink()
    (root / 'y').write_text('same')
    after = _snap(conn, root, 'after')
    got = {(e.change, e.path) for e in compute_diff(conn, before, after)}
    assert got == {('deleted', 'x1'), ('deleted', 'x2'), ('added', 'y')}

# test_identical_scans_have_no_changes: diffing a scan against itself is empty
def test_identical_scans_have_no_changes(conn: sqlite3.Connection, tmp_path: Path) -> None:
    root = tmp_path / 'r'
    root.mkdir()
    (root / 'a').write_text('a')
    scan_id = _snap(conn, root, 'only')
    assert compute_diff(conn, scan_id, scan_id) == []

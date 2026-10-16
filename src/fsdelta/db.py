'''
fsdelta: sqlite storage for scans and saved diffs
'''

# Import external dependencies
import sqlite3, typer
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

# Import internal fsdelta objects
from fsdelta.schema import Entry, ScanInfo

# _Table: tables with unique names
_Table = Literal['scan', 'diff']

# _SCHEMA: tables for scans, their entries, saved diffs and diff entries
_SCHEMA = '''
CREATE TABLE IF NOT EXISTS scan (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    root TEXT NOT NULL,
    created_at TEXT NOT NULL,
    entry_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS entry (
    scan_id INTEGER NOT NULL REFERENCES scan(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    kind TEXT NOT NULL,
    size INTEGER NOT NULL,
    mode INTEGER NOT NULL,
    mtime_ns INTEGER NOT NULL,
    hash TEXT,
    PRIMARY KEY (scan_id, path)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS diff (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    scan_a TEXT NOT NULL,
    scan_b TEXT NOT NULL,
    created_at TEXT NOT NULL,
    entry_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS diff_entry (
    diff_id INTEGER NOT NULL REFERENCES diff(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    change TEXT NOT NULL,
    old_path TEXT,
    PRIMARY KEY (diff_id, path)
) WITHOUT ROWID;
'''

# default_db_path: global database location under the platform app dir
def default_db_path() -> Path:
    return Path(typer.get_app_dir('fsdelta')) / 'fsdelta.db'

# connect: open the database, creating the parent dir and schema if absent
def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')  # cascade deletes need this on every connection
    conn.executescript(_SCHEMA)
    return conn

# check_name: raise ValueError when a scan or diff name is unusable
def check_name(conn: sqlite3.Connection, table: _Table, name: str) -> None:
    # all-digit names would clash with ids in selectors
    if not name or name.isdigit():
        raise ValueError(f'invalid name {name!r}: must be non-empty and not all digits')
    if conn.execute(f'SELECT 1 FROM {table} WHERE name = ?', (name,)).fetchone():
        raise ValueError(f'{table} name {name!r} already exists')

# add_scan: store a scan and its entries in one transaction
def add_scan(conn: sqlite3.Connection, name: str, root: str, entries: Iterable[Entry]) -> ScanInfo:
    check_name(conn, 'scan', name)
    with conn:
        scan_id = conn.execute(
            'INSERT INTO scan (name, root, created_at) VALUES (?, ?, ?)',
            (name, root, _now()),
        ).lastrowid
        conn.executemany(
            'INSERT INTO entry VALUES (?, ?, ?, ?, ?, ?, ?)',
            ((scan_id, e.path, e.kind, e.size, e.mode, e.mtime_ns, e.hash) for e in entries),
        )
        conn.execute(
            'UPDATE scan SET entry_count = (SELECT COUNT(*) FROM entry WHERE scan_id = ?) WHERE id = ?',
            (scan_id, scan_id),
        )
    return resolve_scan(conn, name)

# resolve_scan: look up a scan by id or name
def resolve_scan(conn: sqlite3.Connection, selector: str) -> ScanInfo:
    return ScanInfo.model_validate(dict(_resolve(conn, 'scan', selector)))

# _resolve: fetch one row of a named table by id or name
def _resolve(conn: sqlite3.Connection, table: _Table, selector: str) -> sqlite3.Row:
    by_id = selector.isdigit()  # safe because check_name rejects all-digit names
    row = conn.execute(
        f'SELECT * FROM {table} WHERE {"id" if by_id else "name"} = ?',
        (int(selector) if by_id else selector,),
    ).fetchone()
    if row is None:
        raise LookupError(f'unknown {table} {selector!r}')
    return row

# _now: current UTC time as an ISO 8601 string
def _now() -> str:
    return datetime.now(UTC).isoformat(timespec='seconds')

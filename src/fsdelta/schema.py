'''
fsdelta: schemas shared by scan, diff, storage and export
'''

# Import external dependencies
from pydantic import BaseModel
from typing import Literal

# Kind: filesystem object types recorded in a scan
Kind = Literal['file', 'dir', 'symlink', 'other']

# ChangeKind: change types a diff can report
ChangeKind = Literal['added', 'modified', 'deleted', 'renamed']

# Entry: one scanned filesystem object, path relative to the scan root
class Entry(BaseModel):
    path: str
    kind: Kind
    size: int
    mode: int
    mtime_ns: int
    hash: str | None

# ScanInfo: stored scan metadata
class ScanInfo(BaseModel):
    id: int
    name: str
    root: str
    created_at: str
    entry_count: int

# DiffEntry: one change between two scans
class DiffEntry(BaseModel):
    path: str
    change: ChangeKind
    old_path: str | None = None

# DiffInfo: stored diff metadata
class DiffInfo(BaseModel):
    id: int
    name: str
    scan_a: str
    scan_b: str
    created_at: str
    entry_count: int

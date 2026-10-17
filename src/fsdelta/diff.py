'''
fsdelta: compute difference between two stored scans
'''

# Import external dependencies
import sqlite3
from collections import defaultdict

# Import internal fsdelta objects
from fsdelta.schema import DiffEntry

# _DIFF_SQL: added, deleted and modified paths between scan :a and scan :b
_DIFF_SQL = '''
SELECT b.path AS path, 'added' AS change, b.hash AS hash
FROM entry b
WHERE b.scan_id = :b
  AND NOT EXISTS (SELECT 1 FROM entry a WHERE a.scan_id = :a AND a.path = b.path)
UNION ALL
SELECT a.path, 'deleted', a.hash
FROM entry a
WHERE a.scan_id = :a
  AND NOT EXISTS (SELECT 1 FROM entry b WHERE b.scan_id = :b AND b.path = a.path)
UNION ALL
SELECT b.path, 'modified', b.hash
FROM entry a
JOIN entry b ON b.path = a.path
WHERE a.scan_id = :a AND b.scan_id = :b
  AND (a.hash IS NOT b.hash OR a.mode != b.mode OR a.kind != b.kind
       -- no hash on either side (sparse or unreadable), compare metadata instead
       OR (a.kind = 'file' AND a.hash IS NULL AND b.hash IS NULL
           AND (a.size != b.size OR a.mtime_ns != b.mtime_ns)))
ORDER BY path
'''

# compute_diff: changes from scan_a to scan_b, ordered by path, with renames paired up
def compute_diff(conn: sqlite3.Connection, scan_a: int, scan_b: int) -> list[DiffEntry]:
    rows = conn.execute(_DIFF_SQL, {'a': scan_a, 'b': scan_b}).fetchall()
    return _pair_renames([(row['path'], row['change'], row['hash']) for row in rows])

# _pair_renames: fold a deleted and an added path into one rename when their hash is unique on both sides
def _pair_renames(rows: list[tuple[str, str, str | None]]) -> list[DiffEntry]:
    by_hash: dict[str, dict[str, list[str]]] = defaultdict(lambda: {'added': [], 'deleted': []})
    for path, change, digest in rows:
        if digest is not None and change in ('added', 'deleted'):
            by_hash[digest][change].append(path)
    # new path -> old path
    renames = {
        sides['added'][0]: sides['deleted'][0]
        for sides in by_hash.values()
        if len(sides['added']) == 1 and len(sides['deleted']) == 1
    }
    old_paths = set(renames.values())
    entries: list[DiffEntry] = []
    for path, change, _ in rows:
        if change == 'added' and path in renames:
            entries.append(DiffEntry(path=path, change='renamed', old_path=renames[path]))
        elif change == 'deleted' and path in old_paths:
            continue
        else:
            entries.append(DiffEntry(path=path, change=change))
    return entries

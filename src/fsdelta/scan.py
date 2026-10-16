'''
fsdelta: walk a directory tree and hash contents
'''

# Import external dependencies
import hashlib, os, stat
from collections.abc import Callable, Iterator
from pathlib import Path

# Import internal fsdelta objects
from fsdelta.schema import Entry, Kind

# _CHUNK: read size when hashing, 1 MiB
_CHUNK = 1024 * 1024

# scan_tree: yield an entry per object under root, never following symlinks
def scan_tree(root: Path, *, on_warning: Callable[[str], None] | None = None) -> Iterator[Entry]:
    warn = on_warning or (lambda message: None)
    walker = os.walk(root, onerror=lambda exc: warn(f'cannot read {exc.filename!r}: {exc.strerror}'))
    for dirpath, dirnames, filenames in walker:
        dirnames.sort()  # deterministic traversal order
        for name in sorted(dirnames + filenames):
            full = Path(dirpath) / name
            entry = _stat_entry(root, full, warn)
            if entry is not None:
                yield entry.model_copy(update={'hash': _hash(full, entry.kind, warn)})

# _stat_entry: build an entry without its hash, or None when it cannot be recorded
def _stat_entry(root: Path, full: Path, warn: Callable[[str], None]) -> Entry | None:
    try:
        st = full.lstat()
    except OSError as exc:
        warn(f'cannot stat {str(full)!r}: {exc.strerror}')
        return None
    rel = full.relative_to(root).as_posix()
    try:
        rel.encode()
    except UnicodeEncodeError:
        # sqlite text column cannot hold it
        warn(f'skipping non-utf8 name {rel!r}')
        return None
    return Entry(
        path=rel,
        kind=_kind(st.st_mode),
        size=st.st_size,
        mode=stat.S_IMODE(st.st_mode),
        mtime_ns=st.st_mtime_ns,
        hash=None,
    )

# _kind: classify an lstat mode
def _kind(mode: int) -> Kind:
    if stat.S_ISLNK(mode):
        return 'symlink'
    if stat.S_ISDIR(mode):
        return 'dir'
    if stat.S_ISREG(mode):
        return 'file'
    return 'other'

# _hash: blake2b of file content or link target, None for dirs, other kinds and unreadable files
def _hash(path: Path, kind: Kind, warn: Callable[[str], None]) -> str | None:
    digest = hashlib.blake2b()
    try:
        if kind == 'symlink':
            # prefix keeps a link distinct from a file holding the same text
            digest.update(b'link:' + os.readlink(path).encode(errors='surrogateescape'))
        elif kind == 'file':
            with path.open('rb') as handle:
                while chunk := handle.read(_CHUNK):
                    digest.update(chunk)
        else:
            return None
    except OSError as exc:
        warn(f'cannot hash {str(path)!r}: {exc.strerror}')
        return None
    return digest.hexdigest()

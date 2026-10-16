'''
fsdelta: tests for scan command
'''

# Import external dependencies
import hashlib, os, pytest
from pathlib import Path

# Import internal fsdelta objects
from fsdelta.scan import scan_tree

# _tree: small tree with a nested file, a file symlink and a directory symlink
def _tree(tmp_path: Path) -> Path:
    root = tmp_path / 'root'
    (root / 'sub').mkdir(parents=True)
    (root / 'a.txt').write_text('a')
    (root / 'sub' / 'b.txt').write_text('b')
    (root / 'link').symlink_to('a.txt')
    (root / 'dlink').symlink_to('sub')
    return root

# test_records_kinds_and_hashes: every object appears once with the right kind and hash
def test_records_kinds_and_hashes(tmp_path: Path) -> None:
    entries = {e.path: e for e in scan_tree(_tree(tmp_path))}
    assert set(entries) == {'a.txt', 'sub', 'sub/b.txt', 'link', 'dlink'}
    assert entries['sub'].kind == 'dir'
    assert entries['sub'].hash is None
    assert entries['a.txt'].hash == hashlib.blake2b(b'a').hexdigest()
    assert entries['link'].kind == 'symlink'
    assert entries['link'].hash == hashlib.blake2b(b'link:a.txt').hexdigest()

# test_symlinked_dir_not_followed: nothing is recorded beneath a directory symlink
def test_symlinked_dir_not_followed(tmp_path: Path) -> None:
    paths = {e.path for e in scan_tree(_tree(tmp_path))}
    assert 'dlink/b.txt' not in paths

# test_unreadable_file_has_null_hash: a warning is raised and the scan continues
@pytest.mark.skipif(os.geteuid() == 0, reason='root can read anything')
def test_unreadable_file_has_null_hash(tmp_path: Path) -> None:
    root = tmp_path / 'root'
    root.mkdir()
    (root / 'secret').write_text('x')
    (root / 'secret').chmod(0)
    (root / 'ok').write_text('y')
    warnings: list[str] = []
    entries = {e.path: e for e in scan_tree(root, on_warning=warnings.append)}
    assert entries['secret'].hash is None
    assert entries['ok'].hash is not None
    assert len(warnings) == 1

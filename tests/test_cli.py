'''
fsdelta: tests for cli
'''

# Import external dependencies
from pathlib import Path
from typer.testing import CliRunner

# Import internal fsdelta objects
from fsdelta.cli import app
from fsdelta.db import connect, diff_entries, resolve_scan

# runner: shared typer test runner
runner = CliRunner()

# _invoke: run the app against a specific database file
def _invoke(db: Path, *args: str) -> Result:
    return runner.invoke(app, ['--db', str(db), *args])

# _seed: two scans around a change plus a saved diff named 'change'
def _seed(tmp_path: Path) -> Path:
    root = tmp_path / 'root'
    root.mkdir()
    (root / 'old.txt').write_text('old')
    db = tmp_path / 'fsdelta.db'
    _invoke(db, 'scan', str(root), '--name', 'pre')
    (root / 'new.txt').write_text('new')
    _invoke(db, 'scan', str(root), '--name', 'post')
    _invoke(db, 'diff', 'pre', 'post', '--save', 'change')
    return db

# test_scan_command: scan stores a named scan and rejects a repeated name
def test_scan_command(tmp_path: Path) -> None:
    root = tmp_path / 'root'
    root.mkdir()
    (root / 'a').write_text('a')
    db = tmp_path / 'fsdelta.db'
    result = _invoke(db, 'scan', str(root), '--name', 'pre')
    assert result.exit_code == 0, result.output
    assert resolve_scan(connect(db), 'pre').entry_count == 1
    again = _invoke(db, 'scan', str(root), '--name', 'pre')
    assert again.exit_code == 1
    assert 'already exists' in again.output

# test_diff_command_saves: --save stores the diff and a repeated name is rejected
def test_diff_command_saves(tmp_path: Path) -> None:
    db = _seed(tmp_path)
    assert [e.path for e in diff_entries(connect(db), 1)] == ['new.txt']
    again = _invoke(db, 'diff', 'pre', 'post', '--save', 'change')
    assert again.exit_code == 1
    assert 'already exists' in again.output

# test_diff_command_renders: an unsaved diff prints the changes
def test_diff_command_renders(tmp_path: Path) -> None:
    db = _seed(tmp_path)
    result = _invoke(db, 'diff', 'pre', 'post')
    assert result.exit_code == 0, result.output
    assert 'new.txt' in result.output
    assert '1 added' in result.output

# test_diff_unknown_scan: an unknown scan is a clean error
def test_diff_unknown_scan(tmp_path: Path) -> None:
    db = _seed(tmp_path)
    result = _invoke(db, 'diff', 'pre', 'nope')
    assert result.exit_code == 1
    assert 'unknown scan' in result.output

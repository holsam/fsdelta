'''
fsdelta: tests for cli
'''

# Import external dependencies
from pathlib import Path
from typer.testing import CliRunner

# Import internal fsdelta objects
from fsdelta.cli import app
from fsdelta.db import connect, resolve_scan

# runner: shared typer test runner
runner = CliRunner()

# _invoke: run the app against a specific database file
def _invoke(db: Path, *args: str) -> Result:
    return runner.invoke(app, ['--db', str(db), *args])

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

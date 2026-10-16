'''
fsdelta: tests for rich rendering
'''

# Import external dependencies
from rich.console import Console

# Import internal fsdelta objects
from fsdelta.schema import DiffEntry
from fsdelta.render import render_diff

# test_render_diff_lists_changes: paths, rename arrow text and summary all appear
def test_render_diff_lists_changes() -> None:
    console = Console(record=True, width=100)
    entries = [DiffEntry(path='new', change='added'), DiffEntry(path='b', change='renamed', old_path='a')]
    render_diff(entries, title='pre to post', console=console)
    out = console.export_text()
    assert 'new' in out
    assert 'a to b' in out
    assert '1 added, 1 renamed' in out

# test_render_diff_empty: an empty diff says so
def test_render_diff_empty() -> None:
    console = Console(record=True, width=100)
    render_diff([], title='pre to post', console=console)
    assert 'no changes' in console.export_text()

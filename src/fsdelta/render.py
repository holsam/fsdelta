'''
fsdelta: render diffs and listings with rich
'''

# Import external dependencies
from collections import Counter
from rich.console import Console
from rich.table import Table
from rich.text import Text

# Import internal fsdelta objects
from fsdelta.schema import DiffEntry

# _ORDER: display order of change types
_ORDER = ('added', 'modified', 'renamed', 'deleted')

# _STYLES: rich style per change type
_STYLES = {'added': 'green', 'modified': 'yellow', 'renamed': 'cyan', 'deleted': 'red'}

# render_diff: print a diff as a coloured table, paged when taller than the terminal
def render_diff(entries: list[DiffEntry], *, title: str, console: Console | None = None) -> None:
    console = console or Console()
    counts = Counter(entry.change for entry in entries)
    summary = ', '.join(f'{counts[change]} {change}' for change in _ORDER if counts[change]) or 'no changes'
    table = Table(title=Text(title), caption=summary, caption_justify='left')
    table.add_column('change')
    table.add_column('path', overflow='fold')
    for entry in sorted(entries, key=lambda e: (_ORDER.index(e.change), e.path)):
        path = f'{entry.old_path} to {entry.path}' if entry.old_path else entry.path
        # Text, not str, so brackets in paths are not read as markup
        table.add_row(Text(entry.change, style=_STYLES[entry.change]), Text(path))
    if console.is_terminal and len(entries) + 6 > console.height:  # rows plus title, header, caption and borders
        with console.pager(styles=True):
            console.print(table)
    else:
        console.print(table)

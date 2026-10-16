'''
fsdelta: typer command line interface
'''

# Import external dependencies
import typer
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from rich.console import Console
from typing import Annotated

# Import internal fsdelta objects
from fsdelta.db import add_scan, check_name, connect, default_db_path, resolve_scan, save_diff
from fsdelta.diff import compute_diff
from fsdelta.render import render_diff
from fsdelta.scan import scan_tree
from fsdelta.schema import Entry

# app: root typer application
app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help='Snapshot a directory tree and diff the snapshots.',
)

# scan: snapshot a directory tree into the database
@app.command()
def scan(
    ctx: typer.Context,
    root: Annotated[Path, typer.Argument(exists=True, file_okay=False, resolve_path=True, help='Directory to scan.')],
    *,
    name: Annotated[str, typer.Option('--name', '-n', help='Unique name for this scan.')],
) -> None:
    with _errors():
        conn = connect(ctx.obj)
        check_name(conn, 'scan', name)  # fail before the slow part
        entries: list[Entry] = []
        with _err.status('scanning') as status:
            for entry in scan_tree(root, on_warning=lambda message: _err.print(f'warning: {message}', markup=False)):
                entries.append(entry)
                if len(entries) % 1000 == 0:
                    status.update(f'scanning ({len(entries)} entries)')
        info = add_scan(conn, name, str(root), entries)
    typer.echo(f'scan {info.id}: {info.name} ({info.entry_count} entries)')

# diff: compare two scans, optionally saving the result under a name
@app.command()
def diff(
    ctx: typer.Context,
    a: Annotated[str, typer.Argument(help='Earlier scan id or name.')],
    b: Annotated[str, typer.Argument(help='Later scan id or name.')],
    *,
    save: Annotated[str | None, typer.Option('--save', '-s', help='Save the diff under this name.')] = None,
) -> None:
    with _errors():
        conn = connect(ctx.obj)
        if save is not None:
            check_name(conn, 'diff', save)
        scan_a, scan_b = resolve_scan(conn, a), resolve_scan(conn, b)
        entries = compute_diff(conn, scan_a.id, scan_b.id)
        if save is not None:
            save_diff(conn, save, scan_a.name, scan_b.name, entries)
            _err.print(f'saved diff {save!r}', markup=False)
    render_diff(entries, title=f'{scan_a.name} to {scan_b.name}')

# _main: store the database path for subcommands
@app.callback()
def _main(
    ctx: typer.Context,
    db: Annotated[Path, typer.Option('--db', envvar='FSDELTA_DB', help='Database file.')] = default_db_path(),
) -> None:
    ctx.obj = db

# _err: stderr console for status and errors
_err = Console(stderr=True)

# _errors: turn lookup and validation failures into a clean exit
@contextmanager
def _errors() -> Iterator[None]:
    try:
        yield
    except (LookupError, ValueError) as exc:
        _err.print(f'error: {exc}', style='red', markup=False)
        raise typer.Exit(1) from exc

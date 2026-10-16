'''
fsdelta: typer command line interface
'''

# Import external dependencies
import typer
from pathlib import Path
from typing import Annotated

# Import internal fsdelta objects
from fsdelta.db import default_db_path

# app: root typer application
app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help='Snapshot a directory tree and diff the snapshots.',
)

# _main: store the database path for subcommands
@app.callback()
def _main(
    ctx: typer.Context,
    db: Annotated[Path, typer.Option('--db', envvar='FSDELTA_DB', help='Database file.')] = default_db_path(),
) -> None:
    ctx.obj = db

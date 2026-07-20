from datetime import date
from pathlib import Path

import click

from .journal import create_journal


@click.group()
@click.version_option()
def cli():
    "An accounting tool"


@cli.command()
@click.argument("path", type=click.Path(path_type=Path), default="journal.sou")
@click.option(
    "-y",
    "--year",
    type=int,
    default=lambda: date.today().year,
    show_default="current year",
)
def init(path: Path, year: int):
    "Create a new journal file."
    try:
        create_journal(path, year)
    except FileExistsError:
        raise click.ClickException(f"{path} already exists") from None

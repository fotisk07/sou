from pathlib import Path

import click


@click.group()
@click.version_option()
def cli():
    "An accounting tool"


@cli.command()
@click.argument("path", type=click.Path(path_type=Path), default="journal.sou")
def init(path: Path):
    "Create an empty journal file."
    if path.exists():
        raise click.ClickException(f"{path} already exists")
    path.touch()

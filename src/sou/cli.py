from datetime import date
from pathlib import Path

import click

from sou.accounts import AccountError, add_account
from sou.models import Account, AccountCategory
from sou.parser import JournalParseError
from sou.storage import init_journal, load_journal, save_journal

CATEGORY_NAMES: dict[str, AccountCategory] = {
    "a": "Assets",
    "assets": "Assets",
    "l": "Liabilities",
    "liabilities": "Liabilities",
    "eq": "Equity",
    "equity": "Equity",
    "i": "Income",
    "income": "Income",
    "e": "Expenses",
    "expenses": "Expenses",
}


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
        init_journal(path, year)
    except FileExistsError:
        raise click.ClickException(f"{path} already exists") from None


@cli.command()
@click.argument(
    "category",
    type=click.Choice(list(CATEGORY_NAMES), case_sensitive=False),
)
@click.argument("name")
@click.option(
    "-j",
    "--journal",
    "journal_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path("journal.sou"),
    show_default=True,
)
def add(category: str, name: str, journal_path: Path):
    """Add NAME to an account CATEGORY.

    NAME may be a colon-separated path, such as Bank:Checking. Add parent
    accounts before adding their children.
    """
    account = Account(
        category=CATEGORY_NAMES[category.lower()],
        path=tuple(name.split(":")),
    )

    try:
        journal = load_journal(journal_path)
        add_account(journal, account)
        save_journal(journal_path, journal)
    except FileNotFoundError:
        raise click.ClickException(f"{journal_path} does not exist") from None
    except (AccountError, JournalParseError) as error:
        raise click.ClickException(str(error)) from None

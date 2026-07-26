from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import click

from sou.accounts import CATEGORY_NAMES, AccountError, add_account, resolve_account
from sou.models import Account, Posting, Transaction
from sou.parser import JournalParseError
from sou.storage import init_journal, load_journal, save_journal
from sou.transactions import TransactionError, add_transaction


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


@cli.command()
@click.argument("amount")
@click.argument("source")
@click.argument("target")
@click.argument("description", nargs=-1, required=True)
@click.option(
    "-d",
    "--date",
    "date_text",
    help="Transaction date in MM-DD format. Defaults to today.",
)
@click.option(
    "-j",
    "--journal",
    "journal_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path("journal.sou"),
    show_default=True,
)
def post(
    amount: str,
    source: str,
    target: str,
    description: tuple[str, ...],
    date_text: str | None,
    journal_path: Path,
):
    """Post AMOUNT from SOURCE to TARGET.

    Account references use a concise category prefix, for example a:Bank or
    e:Food. DESCRIPTION may contain multiple words without quoting.
    """
    try:
        parsed_amount = Decimal(amount)
    except InvalidOperation:
        raise click.ClickException(f"invalid amount '{amount}'") from None

    if not parsed_amount.is_finite() or parsed_amount <= 0:
        raise click.ClickException("amount must be a positive finite number")

    try:
        journal = load_journal(journal_path)
        if date_text:
            try:
                transaction_date = date.fromisoformat(f"{journal.year}-{date_text}")
            except ValueError:
                raise click.ClickException(
                    f"invalid date '{date_text}'; expected MM-DD"
                ) from None
        else:
            transaction_date = date.today()

        source_account = resolve_account(journal, source)
        target_account = resolve_account(journal, target)
        transaction = Transaction(
            date=transaction_date,
            description=" ".join(description),
            postings=[
                Posting(account=source_account, amount=-parsed_amount),
                Posting(account=target_account, amount=parsed_amount),
            ],
        )
        add_transaction(journal, transaction)
        save_journal(journal_path, journal)
    except FileNotFoundError:
        raise click.ClickException(f"{journal_path} does not exist") from None
    except (AccountError, JournalParseError, TransactionError) as error:
        raise click.ClickException(str(error)) from None

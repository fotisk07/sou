from calendar import monthrange
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import click
from click.shell_completion import CompletionItem

from sou.accounts import (
    CATEGORY_NAMES,
    AccountError,
    account_balance,
    account_ledger,
    add_account,
    resolve_account,
)
from sou.console import format_balance, format_ledger
from sou.models import Account, Posting, Transaction
from sou.parser import JournalParseError
from sou.renderer import render_accounts
from sou.storage import init_journal, load_journal, save_journal
from sou.transactions import TransactionError, add_transaction


def _report_dates(
    journal_year: int,
    from_text: str | None,
    to_text: str | None,
    current_month: bool,
) -> tuple[date | None, date | None]:
    """Parse report date options and expand --month to its date range."""
    if current_month:
        if from_text is not None or to_text is not None:
            raise click.UsageError("--month cannot be combined with --from or --to")

        today = date.today()
        if journal_year != today.year:
            raise click.ClickException(
                f"current month is outside journal year {journal_year}"
            )

        return (
            date(today.year, today.month, 1),
            date(today.year, today.month, monthrange(today.year, today.month)[1]),
        )

    try:
        from_date = (
            date.fromisoformat(f"{journal_year}-{from_text}") if from_text else None
        )
    except ValueError:
        raise click.ClickException(
            f"invalid from date '{from_text}'; expected MM-DD"
        ) from None

    try:
        to_date = date.fromisoformat(f"{journal_year}-{to_text}") if to_text else None
    except ValueError:
        raise click.ClickException(
            f"invalid to date '{to_text}'; expected MM-DD"
        ) from None

    return from_date, to_date


CATEGORY_PREFIXES = {
    "Assets": "a",
    "Liabilities": "l",
    "Equity": "eq",
    "Income": "i",
    "Expenses": "e",
}


def complete_account(
    ctx: click.Context,
    param: click.Parameter,
    incomplete: str,
) -> list[CompletionItem]:
    """Complete concise account references from the default journal."""
    try:
        journal = load_journal(Path("journal.sou"))
    except (OSError, UnicodeError, JournalParseError):
        return []

    references = (
        f"{CATEGORY_PREFIXES[account.category]}:{':'.join(account.path)}"
        for account in journal.accounts
    )
    return [
        CompletionItem(reference)
        for reference in sorted(references, key=str.casefold)
        if reference.casefold().startswith(incomplete.casefold())
    ]


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


@cli.command("list")
@click.option(
    "-j",
    "--journal",
    "journal_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path("journal.sou"),
    show_default=True,
)
def list_accounts(journal_path: Path):
    """List the accounts in the journal."""
    try:
        journal = load_journal(journal_path)
    except FileNotFoundError:
        raise click.ClickException(f"{journal_path} does not exist") from None
    except JournalParseError as error:
        raise click.ClickException(str(error)) from None

    click.echo("\n".join(render_accounts(journal.accounts)))


@cli.command()
@click.argument("amount")
@click.argument("source", shell_complete=complete_account)
@click.argument("target", shell_complete=complete_account)
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


@cli.command()
@click.argument("account_reference", shell_complete=complete_account)
@click.option("--from", "from_text", help="Start date in MM-DD format.")
@click.option("--to", "to_text", help="End date in MM-DD format.")
@click.option(
    "-m",
    "--month",
    "current_month",
    is_flag=True,
    help="Show only the current calendar month.",
)
@click.option(
    "-j",
    "--journal",
    "journal_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path("journal.sou"),
    show_default=True,
)
def balance(
    account_reference: str,
    from_text: str | None,
    to_text: str | None,
    current_month: bool,
    journal_path: Path,
):
    """Show the balance of ACCOUNT_REFERENCE and its descendants."""
    try:
        journal = load_journal(journal_path)

        from_date, to_date = _report_dates(
            journal.year, from_text, to_text, current_month
        )

        account = resolve_account(journal, account_reference)
        result = account_balance(journal, account, from_date, to_date)
    except FileNotFoundError:
        raise click.ClickException(f"{journal_path} does not exist") from None
    except (AccountError, JournalParseError) as error:
        raise click.ClickException(str(error)) from None

    detailed = from_text is not None or to_text is not None or current_month
    click.echo(format_balance(account, result, detailed))


@cli.command()
@click.argument("account_reference", shell_complete=complete_account)
@click.option("--from", "from_text", help="Start date in MM-DD format.")
@click.option("--to", "to_text", help="End date in MM-DD format.")
@click.option(
    "-m",
    "--month",
    "current_month",
    is_flag=True,
    help="Show only the current calendar month.",
)
@click.option(
    "-j",
    "--journal",
    "journal_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path("journal.sou"),
    show_default=True,
)
def ledger(
    account_reference: str,
    from_text: str | None,
    to_text: str | None,
    current_month: bool,
    journal_path: Path,
):
    """Show postings and running balances for ACCOUNT_REFERENCE."""
    try:
        journal = load_journal(journal_path)

        from_date, to_date = _report_dates(
            journal.year, from_text, to_text, current_month
        )

        account = resolve_account(journal, account_reference)
        result = account_ledger(journal, account, from_date, to_date)
    except FileNotFoundError:
        raise click.ClickException(f"{journal_path} does not exist") from None
    except (AccountError, JournalParseError) as error:
        raise click.ClickException(str(error)) from None

    click.echo(format_ledger(account, result, show_opening=from_date is not None))

from datetime import date, datetime
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
from sou.balance_sheet import BalanceSheetError, balance_sheet
from sou.cli_periods import (
    report_period_options,
    report_range_options,
    resolve_balance_sheet_date,
    resolve_report_dates,
)
from sou.console import (
    format_balance,
    format_balance_sheet,
    format_ledger,
    format_profit_and_loss,
)
from sou.models import (
    Account,
    Journal,
    Posting,
    RecurrenceFrequency,
    RecurringTransaction,
    Transaction,
)
from sou.parser import JournalParseError
from sou.pnl import ProfitAndLossError, profit_and_loss
from sou.recurring import (
    RecurringTransactionError,
    add_recurring_transaction,
    post_due_transactions,
)
from sou.renderer import render_accounts
from sou.storage import init_journal, load_journal, save_journal
from sou.transactions import TransactionError, add_transaction

CATEGORY_PREFIXES = {
    "Assets": "a",
    "Liabilities": "l",
    "Equity": "eq",
    "Income": "i",
    "Expenses": "e",
}


def _today() -> date:
    return datetime.now().astimezone().date()


def _parse_date(journal: Journal, date_text: str | None, label: str) -> date:
    if date_text is None:
        return _today()
    try:
        return date.fromisoformat(f"{journal.year}-{date_text}")
    except ValueError:
        raise click.ClickException(
            f"invalid {label} '{date_text}'; expected MM-DD"
        ) from None


def _parse_posting_values(
    journal: Journal, posting_values: tuple[str, ...]
) -> list[Posting]:
    if len(posting_values) % 2:
        raise click.ClickException("each account must be followed by an amount")
    if len(posting_values) < 4:
        raise click.ClickException("a split transaction requires at least two postings")

    postings = []
    for account_reference, amount_text in zip(
        posting_values[::2], posting_values[1::2], strict=True
    ):
        account = resolve_account(journal, account_reference)
        try:
            amount = Decimal(amount_text)
        except InvalidOperation:
            raise click.ClickException(
                f"invalid amount '{amount_text}' for account '{account_reference}'"
            ) from None
        postings.append(Posting(account=account, amount=amount))
    return postings


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
    default=lambda: _today().year,
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
@click.option(
    "-j",
    "--journal",
    "journal_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path("journal.sou"),
    show_default=True,
)
def check(journal_path: Path):
    """Validate a journal."""
    try:
        _ = load_journal(journal_path)
    except FileNotFoundError:
        raise click.ClickException(f"{journal_path} does not exist") from None
    except JournalParseError as error:
        raise click.ClickException(str(error)) from None

    click.echo(f"{journal_path} is valid")


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
            transaction_date = _today()

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


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("description")
@click.argument("posting_values", nargs=-1, required=True)
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
def split(
    description: str,
    posting_values: tuple[str, ...],
    date_text: str | None,
    journal_path: Path,
):
    """Post a transaction with multiple ACCOUNT AMOUNT pairs.

    Amounts are signed and must sum to zero. Quote DESCRIPTION if it contains
    spaces, for example: sou split "Mixed shopping" a:Bank -12 e:Food 12
    """
    try:
        journal = load_journal(journal_path)
        transaction_date = _parse_date(journal, date_text, "date")
        postings = _parse_posting_values(journal, posting_values)

        transaction = Transaction(
            date=transaction_date,
            description=description,
            postings=postings,
        )
        add_transaction(journal, transaction)
        save_journal(journal_path, journal)
    except FileNotFoundError:
        raise click.ClickException(f"{journal_path} does not exist") from None
    except (AccountError, JournalParseError, TransactionError) as error:
        raise click.ClickException(str(error)) from None


@cli.group()
def recur():
    """Manage recurring transaction templates."""


@recur.command("add", context_settings={"ignore_unknown_options": True})
@click.argument("description")
@click.argument("posting_values", nargs=-1, required=True)
@click.option(
    "--start",
    "start_text",
    help="First occurrence in MM-DD format. Defaults to today.",
)
@click.option(
    "--repeat",
    "frequency",
    type=click.Choice(["daily", "weekly", "monthly"]),
    default="monthly",
    show_default=True,
)
@click.option(
    "-j",
    "--journal",
    "journal_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path("journal.sou"),
    show_default=True,
)
def add_recurring(
    description: str,
    posting_values: tuple[str, ...],
    start_text: str | None,
    frequency: RecurrenceFrequency,
    journal_path: Path,
):
    """Add a recurring transaction with signed ACCOUNT AMOUNT pairs."""
    try:
        journal = load_journal(journal_path)
        start_date = _parse_date(journal, start_text, "start date")
        postings = _parse_posting_values(journal, posting_values)
        recurring_transaction = RecurringTransaction(
            frequency=frequency,
            start_date=start_date,
            next_date=start_date,
            description=description,
            postings=postings,
        )
        add_recurring_transaction(journal, recurring_transaction)
        save_journal(journal_path, journal)
    except FileNotFoundError:
        raise click.ClickException(f"{journal_path} does not exist") from None
    except (
        AccountError,
        JournalParseError,
        RecurringTransactionError,
    ) as error:
        raise click.ClickException(str(error)) from None


@recur.command("list")
@click.option(
    "-j",
    "--journal",
    "journal_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path("journal.sou"),
    show_default=True,
)
def list_recurring(journal_path: Path):
    """List recurring transaction templates."""
    try:
        journal = load_journal(journal_path)
    except FileNotFoundError:
        raise click.ClickException(f"{journal_path} does not exist") from None
    except JournalParseError as error:
        raise click.ClickException(str(error)) from None

    if not journal.recurring_transactions:
        click.echo("No recurring transactions.")
        return

    for recurring_transaction in journal.recurring_transactions:
        click.echo(
            f"{recurring_transaction.frequency} "
            f"{recurring_transaction.start_date.isoformat()} "
            f"{recurring_transaction.description} "
            f"(next: {recurring_transaction.next_date.isoformat()})"
        )
        for posting in recurring_transaction.postings:
            click.echo(f"  {posting.account}  {posting.amount:.2f}")


@cli.command("post-rec")
@click.option(
    "--through",
    "through_text",
    help="Post occurrences through MM-DD. Defaults to today.",
)
@click.option("--dry-run", is_flag=True, help="Show due transactions without saving.")
@click.option(
    "-j",
    "--journal",
    "journal_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path("journal.sou"),
    show_default=True,
)
def post_recurring(through_text: str | None, dry_run: bool, journal_path: Path):
    """Post all due recurring transactions."""
    try:
        journal = load_journal(journal_path)
        through_date = _parse_date(journal, through_text, "date")
        transactions = post_due_transactions(journal, through_date)
        if not dry_run:
            save_journal(journal_path, journal)
    except FileNotFoundError:
        raise click.ClickException(f"{journal_path} does not exist") from None
    except (JournalParseError, RecurringTransactionError) as error:
        raise click.ClickException(str(error)) from None

    if not transactions:
        click.echo("No recurring transactions due.")
        return

    action = "Would post" if dry_run else "Posted"
    noun = "transaction" if len(transactions) == 1 else "transactions"
    click.echo(f"{action} {len(transactions)} recurring {noun}:")
    for transaction in transactions:
        click.echo(f"  {transaction.date.isoformat()} {transaction.description}")


@cli.command()
@click.argument("account_reference", shell_complete=complete_account)
@report_period_options
@report_range_options
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
    month: int | None,
    quarter: int | None,
    all_time: bool,
    journal_path: Path,
):
    """Show the balance of ACCOUNT_REFERENCE and its descendants."""
    try:
        journal = load_journal(journal_path)

        from_date, to_date = resolve_report_dates(
            journal.year,
            from_text,
            to_text,
            month,
            quarter,
            all_time,
            _today(),
        )

        account = resolve_account(journal, account_reference)
        result = account_balance(journal, account, from_date, to_date)
    except FileNotFoundError:
        raise click.ClickException(f"{journal_path} does not exist") from None
    except (AccountError, JournalParseError) as error:
        raise click.ClickException(str(error)) from None

    detailed = not all_time
    click.echo(format_balance(account, result, detailed))


@cli.command()
@click.argument("account_reference", shell_complete=complete_account)
@report_period_options
@report_range_options
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
    month: int | None,
    quarter: int | None,
    all_time: bool,
    journal_path: Path,
):
    """Show postings and running balances for ACCOUNT_REFERENCE."""
    try:
        journal = load_journal(journal_path)

        from_date, to_date = resolve_report_dates(
            journal.year,
            from_text,
            to_text,
            month,
            quarter,
            all_time,
            _today(),
        )

        account = resolve_account(journal, account_reference)
        result = account_ledger(journal, account, from_date, to_date)
    except FileNotFoundError:
        raise click.ClickException(f"{journal_path} does not exist") from None
    except (AccountError, JournalParseError) as error:
        raise click.ClickException(str(error)) from None

    click.echo(format_ledger(account, result, show_opening=from_date is not None))


@cli.command()
@report_period_options
@report_range_options
@click.option(
    "--depth",
    type=click.IntRange(min=0),
    default=1,
    show_default=True,
    help="Number of account levels to display.",
)
@click.option(
    "-j",
    "--journal",
    "journal_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path("journal.sou"),
    show_default=True,
)
def pnl(
    from_text: str | None,
    to_text: str | None,
    month: int | None,
    quarter: int | None,
    all_time: bool,
    depth: int,
    journal_path: Path,
):
    """Show income, expenses, and net profit."""
    try:
        journal = load_journal(journal_path)
        from_date, to_date = resolve_report_dates(
            journal.year,
            from_text,
            to_text,
            month,
            quarter,
            all_time,
            _today(),
        )
        report = profit_and_loss(journal, from_date, to_date)
    except FileNotFoundError:
        raise click.ClickException(f"{journal_path} does not exist") from None
    except (JournalParseError, ProfitAndLossError) as error:
        raise click.ClickException(str(error)) from None

    click.echo(format_profit_and_loss(report, depth))


@cli.command()
@click.option("--at", "at_text", help="Balance sheet date in MM-DD format.")
@report_period_options
@click.option(
    "--depth",
    type=click.IntRange(min=0),
    default=1,
    show_default=True,
    help="Number of account levels to display.",
)
@click.option(
    "-j",
    "--journal",
    "journal_path",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path("journal.sou"),
    show_default=True,
)
def bs(
    at_text: str | None,
    quarter: int | None,
    month: int | None,
    depth: int,
    journal_path: Path,
):
    """Show assets, liabilities, and net worth."""
    try:
        journal = load_journal(journal_path)
        at_date = resolve_balance_sheet_date(
            journal.year,
            at_text,
            month,
            quarter,
            _today(),
        )
        report = balance_sheet(journal, at_date)
    except FileNotFoundError:
        raise click.ClickException(f"{journal_path} does not exist") from None
    except (BalanceSheetError, JournalParseError) as error:
        raise click.ClickException(str(error)) from None

    click.echo(format_balance_sheet(report, depth))

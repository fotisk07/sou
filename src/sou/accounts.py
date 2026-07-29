from datetime import date
from decimal import Decimal

from sou.models import (
    ACCOUNT_CATEGORIES,
    Account,
    AccountBalance,
    AccountCategory,
    AccountLedger,
    Journal,
    LedgerEntry,
)

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


class AccountError(ValueError):
    """Raised when an account cannot be added to or found in a journal."""


def resolve_account(journal: Journal, reference: str) -> Account:
    """Resolve a concise or canonical account reference."""
    if "::" in reference:
        account = next(
            (account for account in journal.accounts if str(account) == reference),
            None,
        )
    else:
        category_name, separator, path_text = reference.partition(":")
        category = CATEGORY_NAMES.get(category_name.lower())
        if not separator or category is None or not path_text:
            raise AccountError(f"invalid account reference '{reference}'")

        account = Account(category=category, path=tuple(path_text.split(":")))
        if account not in journal.accounts:
            account = None

    if account is None:
        raise AccountError(f"unknown account '{reference}'")

    return account


def add_account(journal: Journal, account: Account) -> None:
    """Validate and add an account to a journal.

    Parent accounts must be added before their children. This keeps account
    creation explicit and guarantees that the journal can always be rendered.
    """
    if account.category not in ACCOUNT_CATEGORIES:
        raise AccountError(f"unknown account category '{account.category}'")

    if not account.path:
        raise AccountError("an account path cannot be empty")

    for name in account.path:
        if not name or name != name.strip():
            raise AccountError("account names cannot be empty or have outer whitespace")
        if ":" in name:
            raise AccountError("account names cannot contain ':'")

    if account in journal.accounts:
        raise AccountError(f"account '{account}' already exists")

    if len(account.path) > 1:
        parent = Account(category=account.category, path=account.path[:-1])
        if parent not in journal.accounts:
            raise AccountError(f"parent account '{parent}' does not exist")

    journal.accounts.add(account)


def account_balance(
    journal: Journal,
    account: Account,
    from_date: date | None = None,
    to_date: date | None = None,
) -> AccountBalance:
    """Calculate the signed balance of an account and its descendants."""
    if account not in journal.accounts:
        raise AccountError(f"unknown account '{account}'")

    start = from_date or date(journal.year, 1, 1)
    end = to_date or date(journal.year, 12, 31)

    if start.year != journal.year or end.year != journal.year:
        raise AccountError(f"balance dates must be within journal year {journal.year}")
    if start > end:
        raise AccountError("from date cannot be after to date")

    opening = Decimal("0")
    activity = Decimal("0")

    for transaction in journal.transactions:
        for posting in transaction.postings:
            is_selected = (
                posting.account.category == account.category
                and posting.account.path[: len(account.path)] == account.path
            )
            if not is_selected:
                continue

            if transaction.date < start:
                opening += posting.amount
            elif transaction.date <= end:
                activity += posting.amount

    return AccountBalance(
        opening=opening,
        activity=activity,
        closing=opening + activity,
    )


def account_ledger(
    journal: Journal,
    account: Account,
    from_date: date | None = None,
    to_date: date | None = None,
) -> AccountLedger:
    """Return chronological postings and running balances for an account."""
    summary = account_balance(journal, account, from_date, to_date)
    start = from_date or date(journal.year, 1, 1)
    end = to_date or date(journal.year, 12, 31)
    running_balance = summary.opening
    entries: list[LedgerEntry] = []

    ordered_transactions = sorted(
        enumerate(journal.transactions),
        key=lambda item: (item[1].date, item[0]),
    )

    for _, transaction in ordered_transactions:
        if not start <= transaction.date <= end:
            continue

        for posting in transaction.postings:
            is_selected = (
                posting.account.category == account.category
                and posting.account.path[: len(account.path)] == account.path
            )
            if not is_selected:
                continue

            running_balance += posting.amount
            entries.append(
                LedgerEntry(
                    date=transaction.date,
                    description=transaction.description,
                    account=posting.account,
                    amount=posting.amount,
                    balance=running_balance,
                )
            )

    return AccountLedger(
        opening=summary.opening,
        entries=entries,
        closing=summary.closing,
    )

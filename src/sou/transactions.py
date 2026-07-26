from decimal import Decimal

from sou.models import Journal, Transaction


class TransactionError(ValueError):
    """Raised when a transaction cannot be added to a journal."""


def add_transaction(journal: Journal, transaction: Transaction) -> None:
    """Validate and append a transaction to a journal."""
    if transaction.date.year != journal.year:
        raise TransactionError(
            f"transaction date is outside journal year {journal.year}"
        )

    if not transaction.description.strip():
        raise TransactionError("transaction description cannot be empty")

    if len(transaction.postings) < 2:
        raise TransactionError("transaction must have at least two postings")

    posting_accounts = [posting.account for posting in transaction.postings]
    if len(set(posting_accounts)) != len(posting_accounts):
        raise TransactionError("an account cannot appear more than once")

    for posting in transaction.postings:
        if posting.account not in journal.accounts:
            raise TransactionError(f"unknown account '{posting.account}'")
        if not posting.amount.is_finite():
            raise TransactionError("posting amounts must be finite")
        if posting.amount == 0:
            raise TransactionError("posting amounts cannot be zero")

    balance = sum((posting.amount for posting in transaction.postings), Decimal("0"))
    if balance != 0:
        raise TransactionError(f"transaction is not balanced (difference: {balance})")

    journal.transactions.append(transaction)

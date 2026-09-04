import calendar
from datetime import date, timedelta

from sou.models import Journal, Posting, RecurringTransaction, Transaction
from sou.transactions import validate_transaction


class RecurringTransactionError(ValueError):
    """Raised when a recurring transaction is invalid."""


def add_recurring_transaction(
    journal: Journal, recurring: RecurringTransaction
) -> None:
    """Validate and append a recurring transaction template."""
    if recurring.start_date.year != journal.year:
        raise RecurringTransactionError(
            f"recurring start date is outside journal year {journal.year}"
        )
    if recurring.next_date < recurring.start_date:
        raise RecurringTransactionError(
            "recurring next date cannot precede its start date"
        )

    transaction = _materialize(recurring, recurring.start_date)
    try:
        validate_transaction(journal, transaction)
    except ValueError as error:
        raise RecurringTransactionError(str(error)) from None

    journal.recurring_transactions.append(recurring)


def next_occurrence(recurring: RecurringTransaction, occurrence_date: date) -> date:
    """Return the occurrence following occurrence_date."""
    if recurring.frequency == "daily":
        return occurrence_date + timedelta(days=1)
    if recurring.frequency == "weekly":
        return occurrence_date + timedelta(weeks=1)

    year = occurrence_date.year + occurrence_date.month // 12
    month = occurrence_date.month % 12 + 1
    day = min(recurring.start_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def due_dates(recurring: RecurringTransaction, through: date) -> list[date]:
    """Return unposted occurrence dates up to and including through."""
    dates = []
    occurrence_date = recurring.next_date
    while occurrence_date <= through:
        dates.append(occurrence_date)
        occurrence_date = next_occurrence(recurring, occurrence_date)
    return dates


def post_due_transactions(journal: Journal, through: date) -> list[Transaction]:
    """Materialize all due recurring transactions in chronological order."""
    if through.year != journal.year:
        raise RecurringTransactionError(
            f"posting date is outside journal year {journal.year}"
        )

    due: list[tuple[date, int, RecurringTransaction]] = []
    for index, recurring in enumerate(journal.recurring_transactions):
        due.extend(
            (occurrence_date, index, recurring)
            for occurrence_date in due_dates(recurring, through)
            if occurrence_date.year == journal.year
        )

    due.sort(key=lambda item: (item[0], item[1]))
    transactions = [
        _materialize(recurring, occurrence_date)
        for occurrence_date, _, recurring in due
    ]

    # Validate every generated transaction before mutating the journal.
    try:
        for transaction in transactions:
            validate_transaction(journal, transaction)
    except ValueError as error:
        raise RecurringTransactionError(str(error)) from None

    journal.transactions.extend(transactions)
    for recurring in journal.recurring_transactions:
        while recurring.next_date <= through:
            recurring.next_date = next_occurrence(recurring, recurring.next_date)

    return transactions


def _materialize(
    recurring: RecurringTransaction, transaction_date: date
) -> Transaction:
    return Transaction(
        date=transaction_date,
        description=recurring.description,
        postings=[
            Posting(account=posting.account, amount=posting.amount)
            for posting in recurring.postings
        ],
    )

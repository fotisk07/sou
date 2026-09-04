from datetime import date
from decimal import Decimal

import pytest

from sou.models import Account, Journal, Posting, RecurringTransaction, Transaction
from sou.recurring import (
    RecurringTransactionError,
    add_recurring_transaction,
    due_dates,
    post_due_transactions,
)

BANK = Account(category="Assets", path=("Bank",))
FOOD = Account(category="Expenses", path=("Food",))
SAVINGS = Account(category="Assets", path=("Savings",))


def recurring(
    frequency="monthly",
    start=date(2025, 1, 31),
    next_date=None,
    postings=None,
):
    return RecurringTransaction(
        frequency=frequency,
        start_date=start,
        next_date=next_date or start,
        description="Allocation",
        postings=(
            postings
            if postings is not None
            else [
                Posting(account=BANK, amount=Decimal(-100)),
                Posting(account=FOOD, amount=Decimal(60)),
                Posting(account=SAVINGS, amount=Decimal(40)),
            ]
        ),
    )


def journal_with(*recurring_transactions):
    return Journal(
        year=2025,
        accounts={BANK, FOOD, SAVINGS},
        transactions=[],
        recurring_transactions=list(recurring_transactions),
    )


def test_monthly_dates_remain_anchored_after_short_month():
    template = recurring()

    assert due_dates(template, date(2025, 4, 30)) == [
        date(2025, 1, 31),
        date(2025, 2, 28),
        date(2025, 3, 31),
        date(2025, 4, 30),
    ]


def test_daily_and_weekly_dates():
    daily = recurring(frequency="daily", start=date(2025, 7, 1))
    weekly = recurring(frequency="weekly", start=date(2025, 7, 1))

    assert due_dates(daily, date(2025, 7, 3)) == [
        date(2025, 7, 1),
        date(2025, 7, 2),
        date(2025, 7, 3),
    ]
    assert due_dates(weekly, date(2025, 7, 15)) == [
        date(2025, 7, 1),
        date(2025, 7, 8),
        date(2025, 7, 15),
    ]


def test_post_due_transactions_catches_up_split_entries():
    template = recurring(start=date(2025, 1, 30))
    journal = journal_with(template)

    posted = post_due_transactions(journal, date(2025, 3, 30))

    assert [transaction.date for transaction in posted] == [
        date(2025, 1, 30),
        date(2025, 2, 28),
        date(2025, 3, 30),
    ]
    assert posted[0] == Transaction(
        date=date(2025, 1, 30),
        description="Allocation",
        postings=[
            Posting(account=BANK, amount=Decimal(-100)),
            Posting(account=FOOD, amount=Decimal(60)),
            Posting(account=SAVINGS, amount=Decimal(40)),
        ],
    )
    assert journal.transactions == posted
    assert template.next_date == date(2025, 4, 30)


def test_post_due_transactions_is_idempotent():
    template = recurring(start=date(2025, 7, 1))
    journal = journal_with(template)

    first = post_due_transactions(journal, date(2025, 7, 1))
    second = post_due_transactions(journal, date(2025, 7, 1))

    assert len(first) == 1
    assert second == []
    assert len(journal.transactions) == 1


def test_due_transactions_are_posted_chronologically():
    later = recurring(start=date(2025, 7, 10))
    earlier = recurring(start=date(2025, 7, 5))
    journal = journal_with(later, earlier)

    posted = post_due_transactions(journal, date(2025, 7, 10))

    assert [transaction.date for transaction in posted] == [
        date(2025, 7, 5),
        date(2025, 7, 10),
    ]


def test_add_recurring_transaction_validates_template():
    journal = journal_with()
    invalid = recurring(
        postings=[
            Posting(account=BANK, amount=Decimal(-100)),
            Posting(account=FOOD, amount=Decimal(90)),
        ]
    )

    with pytest.raises(RecurringTransactionError, match="not balanced"):
        add_recurring_transaction(journal, invalid)

    assert journal.recurring_transactions == []


def test_reject_posting_outside_journal_year():
    with pytest.raises(RecurringTransactionError, match="outside journal year"):
        post_due_transactions(journal_with(), date(2026, 1, 1))

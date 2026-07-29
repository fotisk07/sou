from datetime import date
from decimal import Decimal

import pytest

from sou.models import Account, Journal, Posting, Transaction
from sou.transactions import TransactionError, add_transaction


BANK = Account(category="Assets", path=("Bank",))
FOOD = Account(category="Expenses", path=("Food",))
UNKNOWN = Account(category="Expenses", path=("Unknown",))


def journal():
    return Journal(year=2025, accounts={BANK, FOOD}, transactions=[])


def transaction(
    *,
    transaction_date=date(2025, 7, 1),
    description="Lunch",
    postings=None,
):
    return Transaction(
        date=transaction_date,
        description=description,
        postings=(
            postings
            if postings is not None
            else [
                Posting(account=BANK, amount=Decimal("-10")),
                Posting(account=FOOD, amount=Decimal("10")),
            ]
        ),
    )


def test_add_transaction_appends_valid_transaction():
    target = journal()
    entry = transaction()

    add_transaction(target, entry)

    assert target.transactions == [entry]


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        (transaction(transaction_date=date(2024, 12, 31)), "outside journal year"),
        (transaction(description=" "), "description cannot be empty"),
        (
            transaction(postings=[Posting(account=BANK, amount=Decimal("10"))]),
            "at least two postings",
        ),
        (
            transaction(
                postings=[
                    Posting(account=BANK, amount=Decimal("-10")),
                    Posting(account=BANK, amount=Decimal("10")),
                ]
            ),
            "cannot appear more than once",
        ),
        (
            transaction(
                postings=[
                    Posting(account=BANK, amount=Decimal("-10")),
                    Posting(account=UNKNOWN, amount=Decimal("10")),
                ]
            ),
            "unknown account",
        ),
        (
            transaction(
                postings=[
                    Posting(account=BANK, amount=Decimal("NaN")),
                    Posting(account=FOOD, amount=Decimal("10")),
                ]
            ),
            "must be finite",
        ),
        (
            transaction(
                postings=[
                    Posting(account=BANK, amount=Decimal("0")),
                    Posting(account=FOOD, amount=Decimal("0")),
                ]
            ),
            "cannot be zero",
        ),
        (
            transaction(
                postings=[
                    Posting(account=BANK, amount=Decimal("-10")),
                    Posting(account=FOOD, amount=Decimal("9")),
                ]
            ),
            "not balanced",
        ),
    ],
)
def test_add_transaction_rejects_invalid_transaction(entry, message):
    target = journal()

    with pytest.raises(TransactionError, match=message):
        add_transaction(target, entry)

    assert target.transactions == []

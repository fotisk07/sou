from datetime import date
from decimal import Decimal

import pytest

from sou.models import Account, Posting, Transaction
from sou.parser import JournalParseError, parse_journal


EXAMPLE_JOURNAL = """[JOURNAL]

year: 2025

[ACCOUNTS]

Assets
  Checkings
Liabilities
  Test
    Tit
Equity
  Hey
Income
  Stuff
Expenses
  Test

[TRANSACTIONS]
2025-10-02 Just some transaction
  Assets::Checkings  -100
  Expenses::Test  100

"""


def test_parse_accounts():
    journal = parse_journal(EXAMPLE_JOURNAL)

    assert journal.year == 2025
    assert journal.accounts == {
        Account(type="Assets", path=("Checkings",)),
        Account(type="Liabilities", path=("Test",)),
        Account(type="Liabilities", path=("Test", "Tit")),
        Account(type="Equity", path=("Hey",)),
        Account(type="Income", path=("Stuff",)),
        Account(type="Expenses", path=("Test",)),
    }


def test_parse_transactions():
    journal = parse_journal(EXAMPLE_JOURNAL)

    assert journal.transactions == [
        Transaction(
            date=date(2025, 10, 2),
            description="Just some transaction",
            postings=[
                Posting(
                    account=Account(type="Assets", path=("Checkings",)),
                    amount=Decimal("-100"),
                ),
                Posting(
                    account=Account(type="Expenses", path=("Test",)),
                    amount=Decimal("100"),
                ),
            ],
        )
    ]


def test_multiple_postings():
    text = EXAMPLE_JOURNAL.replace("Expenses::Test  100", "Expenses::Test  50")
    text = text.rstrip() + "\n  Liabilities::Test:Tit  50\n\n"

    journal = parse_journal(text)

    assert journal.transactions == [
        Transaction(
            date=date(2025, 10, 2),
            description="Just some transaction",
            postings=[
                Posting(
                    account=Account(type="Assets", path=("Checkings",)),
                    amount=Decimal("-100"),
                ),
                Posting(
                    account=Account(type="Expenses", path=("Test",)),
                    amount=Decimal("50"),
                ),
                Posting(
                    account=Account(type="Liabilities", path=("Test", "Tit")),
                    amount=Decimal("50"),
                ),
            ],
        )
    ]


def test_reject_non_balanced_transaction():
    text = EXAMPLE_JOURNAL.replace("Expenses::Test  100", "Expenses::Test  120")

    with pytest.raises(JournalParseError):
        parse_journal(text)

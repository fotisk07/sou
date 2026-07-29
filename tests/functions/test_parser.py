from datetime import date
from decimal import Decimal

import pytest

from sou.models import Account, Posting, Transaction
from sou.parser import JournalParseError, parse_sou


EXAMPLE_SOU = """[JOURNAL]

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
    journal = parse_sou(EXAMPLE_SOU)

    assert journal.year == 2025
    assert journal.accounts == {
        Account(category="Assets", path=("Checkings",)),
        Account(category="Liabilities", path=("Test",)),
        Account(category="Liabilities", path=("Test", "Tit")),
        Account(category="Equity", path=("Hey",)),
        Account(category="Income", path=("Stuff",)),
        Account(category="Expenses", path=("Test",)),
    }


def test_parse_transactions():
    journal = parse_sou(EXAMPLE_SOU)

    assert journal.transactions == [
        Transaction(
            date=date(2025, 10, 2),
            description="Just some transaction",
            postings=[
                Posting(
                    account=Account(category="Assets", path=("Checkings",)),
                    amount=Decimal("-100"),
                ),
                Posting(
                    account=Account(category="Expenses", path=("Test",)),
                    amount=Decimal("100"),
                ),
            ],
        )
    ]


def test_multiple_postings():
    source = EXAMPLE_SOU.replace("Expenses::Test  100", "Expenses::Test  50")
    source = source.rstrip() + "\n  Liabilities::Test:Tit  50\n\n"

    journal = parse_sou(source)

    assert journal.transactions == [
        Transaction(
            date=date(2025, 10, 2),
            description="Just some transaction",
            postings=[
                Posting(
                    account=Account(category="Assets", path=("Checkings",)),
                    amount=Decimal("-100"),
                ),
                Posting(
                    account=Account(category="Expenses", path=("Test",)),
                    amount=Decimal("50"),
                ),
                Posting(
                    account=Account(category="Liabilities", path=("Test", "Tit")),
                    amount=Decimal("50"),
                ),
            ],
        )
    ]


def test_multiple_transactions():
    source = (
        EXAMPLE_SOU.rstrip()
        + "\n\n\n2025-10-02 Just some transaction\n  Assets::Checkings  50\n  Equity::Hey -50\n\n"
    )
    journal = parse_sou(source)

    assert len(journal.transactions) == 2
    assert journal.transactions[1] == Transaction(
        date=date(2025, 10, 2),
        description="Just some transaction",
        postings=[
            Posting(
                account=Account(category="Assets", path=("Checkings",)),
                amount=Decimal("50"),
            ),
            Posting(
                account=Account(category="Equity", path=("Hey",)),
                amount=Decimal("-50"),
            ),
        ],
    )


def test_reject_non_balanced_transaction():
    source = EXAMPLE_SOU.replace("Expenses::Test  100", "Expenses::Test  120")

    with pytest.raises(JournalParseError):
        parse_sou(source)


def test_reject_uknown_account():
    source = EXAMPLE_SOU.replace("Expenses::Test  100", "Expenses::TO  120")

    with pytest.raises(JournalParseError):
        parse_sou(source)

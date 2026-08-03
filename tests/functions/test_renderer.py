from datetime import date
from decimal import Decimal

from sou.renderer import render_sou
from sou.models import Account, Journal, Posting, Transaction
from sou.parser import parse_sou


EXAMPLE_SOU = """[JOURNAL]

year: 2025

[ACCOUNTS]

Assets
  Checkings
Liabilities
Equity
Income
Expenses
  Test

[TRANSACTIONS]

2025-10-02 Just some transaction
  Assets::Checkings  -100.00
  Expenses::Test  100.00
"""


def test_render_sou():
    journal = Journal(
        year=2025,
        accounts={
            Account(category="Assets", path=("Checkings",)),
            Account(category="Expenses", path=("Test",)),
        },
        transactions=[
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
            ),
        ],
    )

    sou = render_sou(journal)

    assert sou == EXAMPLE_SOU


def test_round_trip():
    journal = Journal(
        year=2025,
        accounts={
            Account(category="Assets", path=("Checkings",)),
            Account(category="Expenses", path=("Test",)),
        },
        transactions=[
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
            ),
        ],
    )

    assert parse_sou(render_sou(journal)) == journal

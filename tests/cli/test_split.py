from datetime import date
from decimal import Decimal

import pytest

from sou import cli
from sou.models import Account, Posting, Transaction
from sou.storage import load_journal

BANK = Account(category="Assets", path=("Bank",))
FOOD = Account(category="Expenses", path=("Food",))
SALARY = Account(category="Income", path=("Salary",))


def test_split_posts_multiple_signed_amounts(runner, accounts_journal_path):
    result = runner.invoke(
        cli.cli,
        [
            "split",
            "Payday shopping",
            "i:Salary",
            "-100",
            "a:Bank",
            "70",
            "e:Food",
            "30",
            "--date",
            "07-31",
            "--journal",
            str(accounts_journal_path),
        ],
    )

    assert result.exit_code == 0
    assert load_journal(accounts_journal_path).transactions == [
        Transaction(
            date=date(2025, 7, 31),
            description="Payday shopping",
            postings=[
                Posting(account=SALARY, amount=Decimal(-100)),
                Posting(account=BANK, amount=Decimal(70)),
                Posting(account=FOOD, amount=Decimal(30)),
            ],
        )
    ]


@pytest.mark.parametrize(
    ("values", "message"),
    [
        (["a:Bank", "-10"], "requires at least two postings"),
        (
            ["a:Bank", "-10", "e:Food"],
            "each account must be followed by an amount",
        ),
        (
            ["a:Bank", "-10", "e:Food", "nine"],
            "invalid amount 'nine' for account 'e:Food'",
        ),
        (
            ["a:Bank", "-10", "e:Food", "9"],
            "transaction is not balanced",
        ),
        (
            ["a:Bank", "-10", "a:Bank", "10"],
            "an account cannot appear more than once",
        ),
    ],
)
def test_split_rejects_invalid_postings(runner, accounts_journal_path, values, message):
    result = runner.invoke(
        cli.cli,
        [
            "split",
            "Invalid split",
            *values,
            "-d",
            "07-31",
            "-j",
            str(accounts_journal_path),
        ],
    )

    assert result.exit_code == 1
    assert message in result.output
    assert load_journal(accounts_journal_path).transactions == []

from datetime import date
from decimal import Decimal

import pytest

from sou import cli
from sou.models import Account, Posting, Transaction
from sou.storage import load_journal


def test_post_maps_arguments_and_options_to_transaction(runner, accounts_journal_path):
    result = runner.invoke(
        cli.cli,
        [
            "post",
            "12.50",
            "a:Bank",
            "e:Food",
            "Lunch",
            "with",
            "Alex",
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
            description="Lunch with Alex",
            postings=[
                Posting(
                    account=Account(category="Assets", path=("Bank",)),
                    amount=Decimal("-12.50"),
                ),
                Posting(
                    account=Account(category="Expenses", path=("Food",)),
                    amount=Decimal("12.50"),
                ),
            ],
        )
    ]


def test_post_defaults_to_today(runner, current_accounts_journal_path):
    result = runner.invoke(
        cli.cli,
        [
            "post",
            "10",
            "a:Bank",
            "e:Food",
            "Lunch",
            "-j",
            str(current_accounts_journal_path),
        ],
    )

    assert result.exit_code == 0
    transaction = load_journal(current_accounts_journal_path).transactions[0]
    assert transaction.date == date.today()


@pytest.mark.parametrize("amount", ["0", "NaN", "not-a-number"])
def test_post_rejects_invalid_amount(runner, accounts_journal_path, amount):
    result = runner.invoke(
        cli.cli,
        [
            "post",
            amount,
            "a:Bank",
            "e:Food",
            "Lunch",
            "-j",
            str(accounts_journal_path),
        ],
    )

    assert result.exit_code != 0
    assert load_journal(accounts_journal_path).transactions == []


def test_post_rejects_invalid_date(runner, accounts_journal_path):
    result = runner.invoke(
        cli.cli,
        [
            "post",
            "10",
            "a:Bank",
            "e:Food",
            "Lunch",
            "-d",
            "02-30",
            "-j",
            str(accounts_journal_path),
        ],
    )

    assert result.exit_code == 1
    assert "invalid date '02-30'; expected MM-DD" in result.output

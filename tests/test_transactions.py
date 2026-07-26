from datetime import date
from decimal import Decimal

import pytest
from click.testing import CliRunner

from sou import cli
from sou.models import Account, Journal, Posting, Transaction
from sou.storage import load_journal, save_journal


def create_journal(path, year=None):
    accounts = {
        Account(category="Assets", path=("Bank",)),
        Account(category="Income", path=("Salary",)),
        Account(category="Expenses", path=("Food",)),
    }
    save_journal(
        path,
        Journal(year=year or date.today().year, accounts=accounts, transactions=[]),
    )
    return accounts


def test_post_transaction(tmp_path):
    journal_path = tmp_path / "journal.sou"
    accounts = create_journal(journal_path)

    result = CliRunner().invoke(
        cli.cli,
        [
            "post",
            "12.50",
            "a:Bank",
            "e:Food",
            "Lunch",
            "with",
            "Alex",
            "--journal",
            str(journal_path),
        ],
    )

    assert result.exit_code == 0
    assert load_journal(journal_path).transactions == [
        Transaction(
            date=date.today(),
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
    assert load_journal(journal_path).accounts == accounts


def test_post_with_explicit_date_and_canonical_accounts(tmp_path):
    journal_path = tmp_path / "journal.sou"
    create_journal(journal_path, year=2025)

    result = CliRunner().invoke(
        cli.cli,
        [
            "post",
            "2000",
            "Income::Salary",
            "Assets::Bank",
            "Salary",
            "-d",
            "07-31",
            "-j",
            str(journal_path),
        ],
    )

    assert result.exit_code == 0
    transaction = load_journal(journal_path).transactions[0]
    assert transaction.date == date(2025, 7, 31)
    assert transaction.postings[0].amount == Decimal("-2000")
    assert transaction.postings[1].amount == Decimal("2000")


@pytest.mark.parametrize("amount", ["0", "-1", "NaN", "not-a-number"])
def test_reject_invalid_amount(tmp_path, amount):
    journal_path = tmp_path / "journal.sou"
    create_journal(journal_path)

    result = CliRunner().invoke(
        cli.cli,
        ["post", amount, "a:Bank", "e:Food", "Lunch", "-j", str(journal_path)],
    )

    assert result.exit_code != 0
    assert load_journal(journal_path).transactions == []


def test_reject_unknown_account(tmp_path):
    journal_path = tmp_path / "journal.sou"
    create_journal(journal_path)

    result = CliRunner().invoke(
        cli.cli,
        [
            "post",
            "10",
            "a:Cash",
            "e:Food",
            "Lunch",
            "-j",
            str(journal_path),
        ],
    )

    assert result.exit_code == 1
    assert "unknown account 'a:Cash'" in result.output
    assert load_journal(journal_path).transactions == []


def test_reject_same_source_and_target(tmp_path):
    journal_path = tmp_path / "journal.sou"
    create_journal(journal_path)

    result = CliRunner().invoke(
        cli.cli,
        [
            "post",
            "10",
            "a:Bank",
            "a:Bank",
            "Nothing",
            "-j",
            str(journal_path),
        ],
    )

    assert result.exit_code == 1
    assert "account cannot appear more than once" in result.output
    assert load_journal(journal_path).transactions == []


def test_reject_default_date_outside_journal_year(tmp_path):
    journal_path = tmp_path / "journal.sou"
    journal_year = date.today().year - 1
    create_journal(journal_path, year=journal_year)

    result = CliRunner().invoke(
        cli.cli,
        [
            "post",
            "10",
            "a:Bank",
            "e:Food",
            "Lunch",
            "-j",
            str(journal_path),
        ],
    )

    assert result.exit_code == 1
    assert f"outside journal year {journal_year}" in result.output
    assert load_journal(journal_path).transactions == []

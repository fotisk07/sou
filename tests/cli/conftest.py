from datetime import date
from decimal import Decimal

import pytest
from click.testing import CliRunner

from sou.models import Account, Journal, Posting, Transaction
from sou.storage import init_journal, save_journal


BANK = Account(category="Assets", path=("Bank",))
OPENING_BALANCES = Account(category="Equity", path=("OpeningBalances",))
FOOD = Account(category="Expenses", path=("Food",))
COFFEE = Account(category="Expenses", path=("Food", "Coffee"))
SALARY = Account(category="Income", path=("Salary",))


def transaction(month, day, description, *postings):
    return Transaction(
        date=date(2025, month, day),
        description=description,
        postings=[
            Posting(account=account, amount=Decimal(amount))
            for account, amount in postings
        ],
    )


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def empty_journal_path(tmp_path):
    path = tmp_path / "journal.sou"
    init_journal(path, 2025)
    return path


@pytest.fixture
def accounts_journal_path(tmp_path):
    path = tmp_path / "journal.sou"
    save_journal(
        path,
        Journal(
            year=2025,
            accounts={BANK, FOOD, SALARY},
            transactions=[],
        ),
    )
    return path


@pytest.fixture
def current_accounts_journal_path(tmp_path):
    path = tmp_path / "journal.sou"
    save_journal(
        path,
        Journal(
            year=date.today().year,
            accounts={BANK, FOOD, SALARY},
            transactions=[],
        ),
    )
    return path


@pytest.fixture
def report_journal_path(tmp_path):
    path = tmp_path / "journal.sou"
    save_journal(
        path,
        Journal(
            year=2025,
            accounts={BANK, OPENING_BALANCES, FOOD, COFFEE, SALARY},
            transactions=[
                transaction(
                    1,
                    1,
                    "Opening balance",
                    (OPENING_BALANCES, "-1000"),
                    (BANK, "1000"),
                ),
                transaction(6, 30, "Earlier", (BANK, "-10"), (FOOD, "10")),
                transaction(7, 1, "Coffee", (BANK, "-5"), (COFFEE, "5")),
                transaction(7, 31, "Groceries", (BANK, "-20"), (FOOD, "20")),
                transaction(8, 1, "Salary", (SALARY, "-100"), (BANK, "100")),
            ],
        ),
    )
    return path

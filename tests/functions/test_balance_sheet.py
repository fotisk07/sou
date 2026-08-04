from datetime import date
from decimal import Decimal

import pytest

from sou.balance_sheet import BalanceSheetError, balance_sheet
from sou.models import Account, Journal, Posting, Transaction

BANK = Account(category="Assets", path=("Bank",))
CHECKING = Account(category="Assets", path=("Bank", "Checking"))
CARD = Account(category="Liabilities", path=("Card",))
OPENING = Account(category="Equity", path=("OpeningBalances",))
SALARY = Account(category="Income", path=("Salary",))
FOOD = Account(category="Expenses", path=("Food",))
ACCOUNTS = {BANK, CHECKING, CARD, OPENING, SALARY, FOOD}


def transaction(month, day, description, postings):
    return Transaction(
        date=date(2025, month, day),
        description=description,
        postings=[
            Posting(account=account, amount=Decimal(amount))
            for account, amount in postings
        ],
    )


def journal_with_activity():
    return Journal(
        year=2025,
        accounts=ACCOUNTS,
        transactions=[
            transaction(
                1,
                1,
                "Opening balances",
                [(OPENING, "-1100"), (BANK, "100"), (CHECKING, "1000")],
            ),
            transaction(
                2,
                1,
                "Salary",
                [(SALARY, "-500"), (CHECKING, "500")],
            ),
            transaction(
                3,
                1,
                "Food",
                [(CHECKING, "-100"), (FOOD, "100")],
            ),
            transaction(
                4,
                1,
                "Credit card purchase",
                [(CARD, "-200"), (FOOD, "200")],
            ),
        ],
    )


def test_balance_sheet_rolls_up_accounts_and_current_year_result():
    report = balance_sheet(journal_with_activity(), date(2025, 3, 31))
    lines = {line.account: line for line in report.asset_lines}

    assert lines[BANK].direct == Decimal("100")
    assert lines[BANK].total == Decimal("1500")
    assert lines[CHECKING].total == Decimal("1400")
    assert report.total_assets == Decimal("1500")
    assert report.total_liabilities == Decimal("0")
    assert report.equity_account_total == Decimal("1100")
    assert report.current_year_result == Decimal("400")
    assert report.total_net_worth == Decimal("1500")
    assert report.total_liabilities_and_net_worth == Decimal("1500")
    assert report.difference == Decimal("0")


def test_balance_sheet_displays_liabilities_with_their_natural_sign():
    report = balance_sheet(journal_with_activity(), date(2025, 4, 30))

    assert report.liability_lines[0].total == Decimal("200")
    assert report.current_year_result == Decimal("200")
    assert report.total_net_worth == Decimal("1300")
    assert report.total_liabilities_and_net_worth == Decimal("1500")
    assert report.difference == Decimal("0")


def test_balance_sheet_rejects_a_date_outside_the_journal_year():
    with pytest.raises(BalanceSheetError, match="within journal year 2025"):
        balance_sheet(journal_with_activity(), date(2026, 1, 1))

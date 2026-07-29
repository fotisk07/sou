from datetime import date
from decimal import Decimal

import pytest

from sou.accounts import AccountError, account_balance
from sou.models import Account, AccountBalance, Journal, Posting, Transaction


BANK = Account(category="Assets", path=("Bank",))
GROCERIES = Account(category="Expenses", path=("Groceries",))
COFFEE = Account(category="Expenses", path=("Groceries", "Coffee"))
OTHER_GROCERIES = Account(category="Expenses", path=("Groceries", "Other"))
UNUSED = Account(category="Expenses", path=("Unused",))
INCOME_GROCERIES = Account(category="Income", path=("Groceries",))
ACCOUNTS = {
    BANK,
    GROCERIES,
    COFFEE,
    OTHER_GROCERIES,
    UNUSED,
    INCOME_GROCERIES,
}


def expense_transaction(month: int, day: int, account: Account, amount: str):
    value = Decimal(amount)
    return Transaction(
        date=date(2025, month, day),
        description="Expense",
        postings=[
            Posting(account=BANK, amount=-value),
            Posting(account=account, amount=value),
        ],
    )


def journal_with(*transactions: Transaction) -> Journal:
    return Journal(year=2025, accounts=ACCOUNTS, transactions=list(transactions))


def test_balance_for_leaf_account_only_includes_that_account():
    journal = journal_with(
        expense_transaction(10, 1, GROCERIES, "100"),
        expense_transaction(10, 2, COFFEE, "25"),
        expense_transaction(10, 3, OTHER_GROCERIES, "30"),
    )

    balance = account_balance(journal, COFFEE)

    assert balance == AccountBalance(
        opening=Decimal("0"),
        activity=Decimal("25"),
        closing=Decimal("25"),
    )


def test_balance_for_parent_includes_direct_postings_and_descendants():
    income_transaction = Transaction(
        date=date(2025, 10, 4),
        description="Unrelated account with the same path",
        postings=[
            Posting(account=INCOME_GROCERIES, amount=Decimal("-500")),
            Posting(account=BANK, amount=Decimal("500")),
        ],
    )
    journal = journal_with(
        expense_transaction(10, 1, GROCERIES, "100"),
        expense_transaction(10, 2, COFFEE, "25"),
        expense_transaction(10, 3, OTHER_GROCERIES, "30"),
        income_transaction,
    )

    balance = account_balance(journal, GROCERIES)

    assert balance.closing == Decimal("155")


def test_balance_range_has_opening_activity_and_closing():
    journal = journal_with(
        expense_transaction(9, 30, GROCERIES, "10"),
        expense_transaction(10, 1, COFFEE, "20"),
        expense_transaction(10, 31, GROCERIES, "30"),
        expense_transaction(11, 1, COFFEE, "40"),
    )

    balance = account_balance(
        journal,
        GROCERIES,
        from_date=date(2025, 10, 1),
        to_date=date(2025, 10, 31),
    )

    assert balance == AccountBalance(
        opening=Decimal("10"),
        activity=Decimal("50"),
        closing=Decimal("60"),
    )


def test_balance_supports_only_from_date():
    journal = journal_with(
        expense_transaction(9, 30, GROCERIES, "10"),
        expense_transaction(10, 1, COFFEE, "20"),
        expense_transaction(10, 31, GROCERIES, "30"),
        expense_transaction(11, 1, COFFEE, "40"),
    )

    balance = account_balance(
        journal,
        GROCERIES,
        from_date=date(2025, 10, 31),
    )

    assert balance == AccountBalance(
        opening=Decimal("30"),
        activity=Decimal("70"),
        closing=Decimal("100"),
    )


def test_balance_supports_only_to_date():
    journal = journal_with(
        expense_transaction(9, 30, GROCERIES, "10"),
        expense_transaction(10, 1, COFFEE, "20"),
        expense_transaction(10, 2, GROCERIES, "30"),
    )

    balance = account_balance(
        journal,
        GROCERIES,
        to_date=date(2025, 10, 1),
    )

    assert balance == AccountBalance(
        opening=Decimal("0"),
        activity=Decimal("30"),
        closing=Decimal("30"),
    )


def test_balance_without_postings_returns_decimal_zeros():
    balance = account_balance(journal_with(), UNUSED)

    assert balance == AccountBalance(
        opening=Decimal("0"),
        activity=Decimal("0"),
        closing=Decimal("0"),
    )


def test_balance_rejects_unknown_account():
    journal = journal_with()
    unknown = Account(category="Expenses", path=("Unknown",))

    with pytest.raises(AccountError, match="unknown account"):
        account_balance(journal, unknown)


def test_balance_rejects_reversed_date_range():
    with pytest.raises(AccountError, match="from date cannot be after to date"):
        account_balance(
            journal_with(),
            GROCERIES,
            from_date=date(2025, 11, 1),
            to_date=date(2025, 10, 31),
        )


def test_balance_rejects_dates_outside_journal_year():
    with pytest.raises(AccountError, match="within journal year 2025"):
        account_balance(
            journal_with(),
            GROCERIES,
            from_date=date(2024, 12, 31),
        )

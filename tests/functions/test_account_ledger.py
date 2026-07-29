from datetime import date
from decimal import Decimal

from sou.accounts import account_ledger
from sou.models import (
    Account,
    AccountLedger,
    Journal,
    LedgerEntry,
    Posting,
    Transaction,
)


BANK = Account(category="Assets", path=("Bank",))
CHECKING = Account(category="Assets", path=("Bank", "Checking"))
SAVINGS = Account(category="Assets", path=("Bank", "Savings"))
FOOD = Account(category="Expenses", path=("Food",))
COFFEE = Account(category="Expenses", path=("Food", "Coffee"))


def expense_transaction(month, day, account, amount, description):
    value = Decimal(amount)
    return Transaction(
        date=date(2025, month, day),
        description=description,
        postings=[
            Posting(account=CHECKING, amount=-value),
            Posting(account=account, amount=value),
        ],
    )


def journal_with(*transactions):
    return Journal(
        year=2025,
        accounts={BANK, CHECKING, SAVINGS, FOOD, COFFEE},
        transactions=list(transactions),
    )


def test_account_ledger_includes_descendants_and_orders_entries_by_date():
    october_second = expense_transaction(10, 2, COFFEE, "10", "Coffee")
    september = expense_transaction(9, 30, FOOD, "5", "September groceries")
    october_first = expense_transaction(10, 1, FOOD, "20", "Groceries")
    journal = journal_with(october_second, september, october_first)

    ledger = account_ledger(
        journal,
        FOOD,
        from_date=date(2025, 10, 1),
        to_date=date(2025, 10, 31),
    )

    assert ledger == AccountLedger(
        opening=Decimal("5"),
        entries=[
            LedgerEntry(
                date=date(2025, 10, 1),
                description="Groceries",
                account=FOOD,
                amount=Decimal("20"),
                balance=Decimal("25"),
            ),
            LedgerEntry(
                date=date(2025, 10, 2),
                description="Coffee",
                account=COFFEE,
                amount=Decimal("10"),
                balance=Decimal("35"),
            ),
        ],
        closing=Decimal("35"),
    )


def test_account_ledger_for_child_excludes_parent_postings():
    journal = journal_with(
        expense_transaction(10, 1, FOOD, "20", "Groceries"),
        expense_transaction(10, 2, COFFEE, "10", "Coffee"),
    )

    ledger = account_ledger(journal, COFFEE)

    assert len(ledger.entries) == 1
    assert ledger.entries[0].account == COFFEE
    assert ledger.closing == Decimal("10")


def test_account_ledger_keeps_each_matching_posting_in_a_split_transaction():
    transfer = Transaction(
        date=date(2025, 10, 3),
        description="Transfer to savings",
        postings=[
            Posting(account=CHECKING, amount=Decimal("-100")),
            Posting(account=SAVINGS, amount=Decimal("100")),
        ],
    )

    ledger = account_ledger(journal_with(transfer), BANK)

    assert [
        (entry.account, entry.amount, entry.balance) for entry in ledger.entries
    ] == [
        (CHECKING, Decimal("-100"), Decimal("-100")),
        (SAVINGS, Decimal("100"), Decimal("0")),
    ]
    assert ledger.closing == Decimal("0")

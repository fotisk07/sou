from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal


AccountCategory = Literal["Assets", "Liabilities", "Equity", "Income", "Expenses"]
ACCOUNT_CATEGORIES: tuple[AccountCategory, ...] = (
    "Assets",
    "Liabilities",
    "Equity",
    "Income",
    "Expenses",
)


@dataclass(frozen=True)
class Account:
    category: AccountCategory
    path: tuple[str, ...]

    def __str__(self) -> str:
        return f"{self.category}::" + ":".join(self.path)


@dataclass
class Posting:
    account: Account
    amount: Decimal


@dataclass
class Transaction:
    date: date
    description: str
    postings: list[Posting]


@dataclass
class Journal:
    year: int
    accounts: set[Account]
    transactions: list[Transaction]


@dataclass(frozen=True)
class AccountBalance:
    opening: Decimal
    activity: Decimal
    closing: Decimal


@dataclass(frozen=True)
class LedgerEntry:
    date: date
    description: str
    account: Account
    amount: Decimal
    balance: Decimal


@dataclass(frozen=True)
class AccountLedger:
    opening: Decimal
    entries: list[LedgerEntry]
    closing: Decimal

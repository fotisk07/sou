from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class Account:
    category: Literal["Assets", "Liabilities", "Equity", "Income", "Expenses"]
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

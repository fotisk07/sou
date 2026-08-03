from datetime import date
from decimal import Decimal

from sou.accounts import account_contains
from sou.models import Journal, ProfitAndLoss, ProfitAndLossLine


class ProfitAndLossError(ValueError):
    """Raised when a profit and loss report cannot be calculated."""


def profit_and_loss(
    journal: Journal,
    from_date: date | None = None,
    to_date: date | None = None,
) -> ProfitAndLoss:
    """Calculate income, expenses, and net profit for a date range."""
    start = from_date or date(journal.year, 1, 1)
    end = to_date or date(journal.year, 12, 31)

    if start.year != journal.year or end.year != journal.year:
        raise ProfitAndLossError(
            f"profit and loss dates must be within journal year {journal.year}"
        )
    if start > end:
        raise ProfitAndLossError("from date cannot be after to date")

    report_accounts = {
        account
        for account in journal.accounts
        if account.category in {"Income", "Expenses"}
    }
    direct_activity = {account: Decimal("0") for account in report_accounts}

    for transaction in journal.transactions:
        if not start <= transaction.date <= end:
            continue

        for posting in transaction.postings:
            if posting.account not in direct_activity:
                continue

            if posting.account.category == "Income":
                direct_activity[posting.account] -= posting.amount
            else:
                direct_activity[posting.account] += posting.amount

    def lines_for(category: str) -> list[ProfitAndLossLine]:
        accounts = sorted(
            (account for account in report_accounts if account.category == category),
            key=lambda account: tuple(part.casefold() for part in account.path),
        )
        return [
            ProfitAndLossLine(
                account=account,
                direct=direct_activity[account],
                total=sum(
                    (
                        amount
                        for candidate, amount in direct_activity.items()
                        if account_contains(account, candidate)
                    ),
                    start=Decimal("0"),
                ),
            )
            for account in accounts
        ]

    income_lines = lines_for("Income")
    expense_lines = lines_for("Expenses")
    total_income = sum(
        (line.direct for line in income_lines),
        start=Decimal("0"),
    )
    total_expenses = sum(
        (line.direct for line in expense_lines),
        start=Decimal("0"),
    )

    return ProfitAndLoss(
        from_date=start,
        to_date=end,
        income_lines=income_lines,
        expense_lines=expense_lines,
        total_income=total_income,
        total_expenses=total_expenses,
        net=total_income - total_expenses,
    )

from datetime import date
from decimal import Decimal

from sou.accounts import account_contains
from sou.models import AccountReportLine, BalanceSheet, Journal


class BalanceSheetError(ValueError):
    """Raised when a balance sheet cannot be calculated."""


def balance_sheet(journal: Journal, at_date: date | None = None) -> BalanceSheet:
    """Calculate assets, liabilities, and net worth at a point in time."""
    report_date = at_date or date(journal.year, 12, 31)
    if report_date.year != journal.year:
        raise BalanceSheetError(
            f"balance sheet date must be within journal year {journal.year}"
        )

    report_accounts = {
        account
        for account in journal.accounts
        if account.category in {"Assets", "Liabilities", "Equity"}
    }
    direct_balances = {account: Decimal("0") for account in report_accounts}
    current_year_result = Decimal("0")

    for transaction in journal.transactions:
        if transaction.date > report_date:
            continue

        for posting in transaction.postings:
            if posting.account.category == "Assets":
                direct_balances[posting.account] += posting.amount
            elif posting.account.category in {"Liabilities", "Equity"}:
                direct_balances[posting.account] -= posting.amount
            elif posting.account.category in {"Income", "Expenses"}:
                current_year_result -= posting.amount

    def lines_for(category: str) -> list[AccountReportLine]:
        accounts = sorted(
            (account for account in report_accounts if account.category == category),
            key=lambda account: tuple(part.casefold() for part in account.path),
        )
        return [
            AccountReportLine(
                account=account,
                direct=direct_balances[account],
                total=sum(
                    (
                        amount
                        for candidate, amount in direct_balances.items()
                        if account_contains(account, candidate)
                    ),
                    start=Decimal("0"),
                ),
            )
            for account in accounts
        ]

    asset_lines = lines_for("Assets")
    liability_lines = lines_for("Liabilities")
    equity_lines = lines_for("Equity")
    total_assets = sum(
        (line.direct for line in asset_lines),
        start=Decimal("0"),
    )
    total_liabilities = sum(
        (line.direct for line in liability_lines),
        start=Decimal("0"),
    )
    equity_account_total = sum(
        (line.direct for line in equity_lines),
        start=Decimal("0"),
    )
    total_net_worth = equity_account_total + current_year_result
    total_liabilities_and_net_worth = total_liabilities + total_net_worth

    return BalanceSheet(
        at_date=report_date,
        asset_lines=asset_lines,
        liability_lines=liability_lines,
        equity_lines=equity_lines,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        equity_account_total=equity_account_total,
        current_year_result=current_year_result,
        total_net_worth=total_net_worth,
        total_liabilities_and_net_worth=total_liabilities_and_net_worth,
        difference=total_assets - total_liabilities_and_net_worth,
    )

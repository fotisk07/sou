from decimal import Decimal

from prettytable import PrettyTable

from sou.models import (
    Account,
    AccountBalance,
    AccountLedger,
    AccountReportLine,
    BalanceSheet,
    ProfitAndLoss,
)


def _display_sign(account: Account) -> Decimal:
    """Return the multiplier used to display an account's natural balance."""
    if account.category in {"Liabilities", "Equity", "Income"}:
        return Decimal("-1")
    return Decimal("1")


def format_balance(
    account: Account,
    result: AccountBalance,
    detailed: bool,
) -> str:
    """Format an account balance for display in the command line."""
    sign = _display_sign(account)
    opening = result.opening * sign
    activity = result.activity * sign
    closing = result.closing * sign

    if not detailed:
        return f"{account}  {format(closing, 'f')}"

    return "\n".join([
        str(account),
        f"Opening:  {format(opening, 'f')}",
        f"Activity:  {format(activity, 'f')}",
        f"Closing:  {format(closing, 'f')}",
    ])


def format_ledger(
    account: Account,
    result: AccountLedger,
    show_opening: bool,
) -> str:
    """Format an account ledger for display in the command line."""
    sign = _display_sign(account)
    table = PrettyTable()
    table.field_names = ["Date", "Account", "Description", "Amount", "Balance"]
    table.align["Date"] = "l"
    table.align["Account"] = "l"
    table.align["Description"] = "l"
    table.align["Amount"] = "r"
    table.align["Balance"] = "r"

    if show_opening:
        table.add_row([
            "",
            "",
            "Opening balance",
            "",
            format(result.opening * sign, "f"),
        ])

    for entry in result.entries:
        table.add_row([
            entry.date.strftime("%m-%d"),
            str(entry.account),
            entry.description,
            format(entry.amount * sign, "f"),
            format(entry.balance * sign, "f"),
        ])

    table.add_row([
        "",
        "",
        "Closing balance",
        "",
        format(result.closing * sign, "f"),
    ])

    return f"{account}\n{table}"


def _format_report_amount(amount: Decimal) -> str:
    return f"{amount:,.2f}"


def _add_account_report_section(
    table: PrettyTable,
    name: str,
    lines: list[AccountReportLine],
    total: Decimal,
    depth: int,
    extra_rows: tuple[tuple[str, Decimal], ...] = (),
) -> None:
    if depth > 0:
        table.add_row([name, ""])

        def add_line(line: AccountReportLine) -> None:
            indentation = "  " * len(line.account.path)
            table.add_row([
                f"{indentation}{line.account.path[-1]}",
                _format_report_amount(line.total),
            ])

            if len(line.account.path) >= depth:
                return

            children = [
                candidate
                for candidate in lines
                if candidate.total != 0
                and candidate.account.category == line.account.category
                and candidate.account.path[:-1] == line.account.path
            ]
            if line.direct != 0 and children:
                table.add_row([
                    f"{'  ' * (len(line.account.path) + 1)}(direct)",
                    _format_report_amount(line.direct),
                ])

            for child in children:
                add_line(child)

        for line in lines:
            if len(line.account.path) == 1 and line.total != 0:
                add_line(line)

        for label, amount in extra_rows:
            if amount != 0:
                table.add_row([f"  {label}", _format_report_amount(amount)])

    table.add_row(
        [f"TOTAL {name}", _format_report_amount(total)],
        divider=True,
    )


def format_profit_and_loss(report: ProfitAndLoss, depth: int = 1) -> str:
    """Format a profit and loss report for display in the command line."""
    if depth < 0:
        raise ValueError("profit and loss depth cannot be negative")

    table = PrettyTable()
    table.field_names = ["Account", "Amount"]
    table.align["Account"] = "l"
    table.align["Amount"] = "r"

    _add_account_report_section(
        table,
        "INCOME",
        report.income_lines,
        report.total_income,
        depth,
    )
    _add_account_report_section(
        table,
        "EXPENSES",
        report.expense_lines,
        report.total_expenses,
        depth,
    )

    net_name = "NET PROFIT" if report.net >= 0 else "NET LOSS"
    table.add_row([net_name, _format_report_amount(abs(report.net))])

    heading = f"Profit and Loss — {report.from_date} to {report.to_date}"
    return f"{heading}\n\n{table}"


def format_balance_sheet(report: BalanceSheet, depth: int = 1) -> str:
    """Format a balance sheet for display in the command line."""
    if depth < 0:
        raise ValueError("balance sheet depth cannot be negative")

    table = PrettyTable()
    table.field_names = ["Account", "Amount"]
    table.align["Account"] = "l"
    table.align["Amount"] = "r"

    _add_account_report_section(
        table,
        "ASSETS",
        report.asset_lines,
        report.total_assets,
        depth,
    )
    _add_account_report_section(
        table,
        "LIABILITIES",
        report.liability_lines,
        report.total_liabilities,
        depth,
    )
    _add_account_report_section(
        table,
        "NET WORTH",
        report.equity_lines,
        report.total_net_worth,
        depth,
        extra_rows=(("Current year result", report.current_year_result),),
    )
    table.add_row([
        "TOTAL LIABILITIES AND NET WORTH",
        _format_report_amount(report.total_liabilities_and_net_worth),
    ])

    if report.difference != 0:
        table.add_row(["DIFFERENCE", _format_report_amount(report.difference)])

    heading = f"Balance Sheet — {report.at_date}"
    return f"{heading}\n\n{table}"

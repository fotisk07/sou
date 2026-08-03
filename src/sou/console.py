from decimal import Decimal

from prettytable import PrettyTable

from sou.models import Account, AccountBalance, AccountLedger


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

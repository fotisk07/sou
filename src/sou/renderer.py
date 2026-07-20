from decimal import Decimal

from sou.models import ACCOUNT_CATEGORIES, Account, Journal


def render_sou(journal: Journal) -> str:
    """Render a Journal as canonical Sou source text."""
    lines = [
        "[JOURNAL]",
        "",
        f"year: {journal.year}",
        "",
        "[ACCOUNTS]",
        "",
    ]

    lines.extend(_render_accounts(journal.accounts))
    lines.extend(["", "[TRANSACTIONS]"])

    for transaction in journal.transactions:
        # A blank line separates the section heading and each transaction.
        lines.append("")
        lines.append(f"{transaction.date.isoformat()} {transaction.description}")

        for posting in transaction.postings:
            lines.append(f"  {posting.account}  {_render_amount(posting.amount)}")

    return "\n".join(lines) + "\n"


def _render_accounts(accounts: set[Account]) -> list[str]:
    """Render accounts as an ordered, indentation-based tree."""
    lines: list[str] = []

    for category in ACCOUNT_CATEGORIES:
        lines.append(category)

        # Tuple sorting places a parent before its children and keeps output
        # deterministic even though Journal.accounts is a set.
        category_accounts = sorted(
            (account for account in accounts if account.category == category),
            key=lambda account: account.path,
        )

        for account in category_accounts:
            if not account.path:
                raise ValueError("an account path cannot be empty")

            # Only the final component is written because preceding components
            # are already represented by the indentation and parent lines.
            indentation = "  " * len(account.path)
            lines.append(f"{indentation}{account.path[-1]}")

    known_categories = set(ACCOUNT_CATEGORIES)
    for account in accounts:
        if account.category not in known_categories:
            raise ValueError(f"unknown account category '{account.category}'")
        if len(account.path) > 1:
            parent = Account(category=account.category, path=account.path[:-1])
            if parent not in accounts:
                raise ValueError(f"account '{account}' has no declared parent")

    return lines


def _render_amount(amount: Decimal) -> str:
    """Render a Decimal without scientific notation."""
    return format(amount, "f")

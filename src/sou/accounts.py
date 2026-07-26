from sou.models import ACCOUNT_CATEGORIES, Account, AccountCategory, Journal


CATEGORY_NAMES: dict[str, AccountCategory] = {
    "a": "Assets",
    "assets": "Assets",
    "l": "Liabilities",
    "liabilities": "Liabilities",
    "eq": "Equity",
    "equity": "Equity",
    "i": "Income",
    "income": "Income",
    "e": "Expenses",
    "expenses": "Expenses",
}


class AccountError(ValueError):
    """Raised when an account cannot be added to or found in a journal."""


def resolve_account(journal: Journal, reference: str) -> Account:
    """Resolve a concise or canonical account reference."""
    if "::" in reference:
        account = next(
            (account for account in journal.accounts if str(account) == reference),
            None,
        )
    else:
        category_name, separator, path_text = reference.partition(":")
        category = CATEGORY_NAMES.get(category_name.lower())
        if not separator or category is None or not path_text:
            raise AccountError(f"invalid account reference '{reference}'")

        account = Account(category=category, path=tuple(path_text.split(":")))
        if account not in journal.accounts:
            account = None

    if account is None:
        raise AccountError(f"unknown account '{reference}'")

    return account


def add_account(journal: Journal, account: Account) -> None:
    """Validate and add an account to a journal.

    Parent accounts must be added before their children. This keeps account
    creation explicit and guarantees that the journal can always be rendered.
    """
    if account.category not in ACCOUNT_CATEGORIES:
        raise AccountError(f"unknown account category '{account.category}'")

    if not account.path:
        raise AccountError("an account path cannot be empty")

    for name in account.path:
        if not name or name != name.strip():
            raise AccountError("account names cannot be empty or have outer whitespace")
        if ":" in name:
            raise AccountError("account names cannot contain ':'")

    if account in journal.accounts:
        raise AccountError(f"account '{account}' already exists")

    if len(account.path) > 1:
        parent = Account(category=account.category, path=account.path[:-1])
        if parent not in journal.accounts:
            raise AccountError(f"parent account '{parent}' does not exist")

    journal.accounts.add(account)

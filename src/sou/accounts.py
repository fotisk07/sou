from sou.models import ACCOUNT_CATEGORIES, Account, Journal


class AccountError(ValueError):
    """Raised when an account cannot be added to a journal."""


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

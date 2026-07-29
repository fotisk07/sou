import pytest

from sou.accounts import AccountError, add_account, resolve_account
from sou.models import Account, Journal


BANK = Account(category="Assets", path=("Bank",))
CHECKING = Account(category="Assets", path=("Bank", "Checking"))


def journal_with(*accounts):
    return Journal(year=2025, accounts=set(accounts), transactions=[])


def test_add_account():
    journal = journal_with()

    add_account(journal, BANK)

    assert journal.accounts == {BANK}


def test_add_nested_account_when_parent_exists():
    journal = journal_with(BANK)

    add_account(journal, CHECKING)

    assert journal.accounts == {BANK, CHECKING}


def test_add_account_rejects_missing_parent_without_mutating_journal():
    journal = journal_with()

    with pytest.raises(
        AccountError, match="parent account 'Assets::Bank' does not exist"
    ):
        add_account(journal, CHECKING)

    assert journal.accounts == set()


def test_add_account_rejects_duplicate():
    journal = journal_with(BANK)

    with pytest.raises(AccountError, match="already exists"):
        add_account(journal, BANK)


def test_resolve_account_accepts_short_and_canonical_references():
    journal = journal_with(BANK, CHECKING)

    assert resolve_account(journal, "a:Bank:Checking") == CHECKING
    assert resolve_account(journal, "Assets::Bank:Checking") == CHECKING


@pytest.mark.parametrize("reference", ["Bank", "x:Bank", "a:"])
def test_resolve_account_rejects_invalid_reference(reference):
    with pytest.raises(AccountError, match="invalid account reference"):
        resolve_account(journal_with(BANK), reference)


def test_resolve_account_rejects_unknown_account():
    with pytest.raises(AccountError, match="unknown account 'a:Cash'"):
        resolve_account(journal_with(BANK), "a:Cash")

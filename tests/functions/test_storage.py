from datetime import date
from decimal import Decimal

import pytest

from sou.models import Account, Journal, Posting, Transaction
from sou.storage import init_journal, load_journal, save_journal


def test_init_journal_creates_loadable_empty_journal(tmp_path):
    path = tmp_path / "journal.sou"

    init_journal(path, 2025)

    assert load_journal(path) == Journal(year=2025, accounts=set(), transactions=[])


def test_init_journal_does_not_overwrite_existing_file(tmp_path):
    path = tmp_path / "journal.sou"
    path.write_text("existing", encoding="utf-8")

    with pytest.raises(FileExistsError):
        init_journal(path, 2025)

    assert path.read_text(encoding="utf-8") == "existing"


def test_save_and_load_journal_round_trip(tmp_path):
    path = tmp_path / "journal.sou"
    bank = Account(category="Assets", path=("Bank",))
    food = Account(category="Expenses", path=("Food",))
    journal = Journal(
        year=2025,
        accounts={bank, food},
        transactions=[
            Transaction(
                date=date(2025, 7, 1),
                description="Lunch",
                postings=[
                    Posting(account=bank, amount=Decimal("-10")),
                    Posting(account=food, amount=Decimal("10")),
                ],
            )
        ],
    )

    save_journal(path, journal)

    assert load_journal(path) == journal
    assert not (tmp_path / ".journal.sou.tmp").exists()

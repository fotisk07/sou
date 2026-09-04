from datetime import date
from decimal import Decimal

from sou import cli
from sou.models import Account, Posting, RecurringTransaction, Transaction
from sou.storage import load_journal

BANK = Account(category="Assets", path=("Bank",))
FOOD = Account(category="Expenses", path=("Food",))
SALARY = Account(category="Income", path=("Salary",))


def test_recur_add_creates_monthly_split_template(runner, accounts_journal_path):
    result = runner.invoke(
        cli.cli,
        [
            "recur",
            "add",
            "Monthly allocation",
            "a:Bank",
            "-100",
            "e:Food",
            "60",
            "i:Salary",
            "40",
            "--start",
            "01-31",
            "--journal",
            str(accounts_journal_path),
        ],
    )

    assert result.exit_code == 0
    assert load_journal(accounts_journal_path).recurring_transactions == [
        RecurringTransaction(
            frequency="monthly",
            start_date=date(2025, 1, 31),
            next_date=date(2025, 1, 31),
            description="Monthly allocation",
            postings=[
                Posting(account=BANK, amount=Decimal(-100)),
                Posting(account=FOOD, amount=Decimal(60)),
                Posting(account=SALARY, amount=Decimal(40)),
            ],
        )
    ]


def test_recur_add_accepts_other_frequencies(runner, accounts_journal_path):
    result = runner.invoke(
        cli.cli,
        [
            "recur",
            "add",
            "Weekly transfer",
            "a:Bank",
            "-10",
            "e:Food",
            "10",
            "--repeat",
            "weekly",
            "--start",
            "07-01",
            "-j",
            str(accounts_journal_path),
        ],
    )

    assert result.exit_code == 0
    recurring = load_journal(accounts_journal_path).recurring_transactions[0]
    assert recurring.frequency == "weekly"


def test_recur_add_rejects_unbalanced_split(runner, accounts_journal_path):
    result = runner.invoke(
        cli.cli,
        [
            "recur",
            "add",
            "Invalid",
            "a:Bank",
            "-10",
            "e:Food",
            "9",
            "--start",
            "07-01",
            "-j",
            str(accounts_journal_path),
        ],
    )

    assert result.exit_code == 1
    assert "not balanced" in result.output
    assert load_journal(accounts_journal_path).recurring_transactions == []


def test_post_rec_posts_all_due_occurrences(runner, accounts_journal_path):
    add_result = runner.invoke(
        cli.cli,
        [
            "recur",
            "add",
            "Monthly food",
            "a:Bank",
            "-10",
            "e:Food",
            "10",
            "--start",
            "01-31",
            "-j",
            str(accounts_journal_path),
        ],
    )
    assert add_result.exit_code == 0

    result = runner.invoke(
        cli.cli,
        [
            "post-rec",
            "--through",
            "03-31",
            "-j",
            str(accounts_journal_path),
        ],
    )

    assert result.exit_code == 0
    assert "Posted 3 recurring transactions" in result.output
    journal = load_journal(accounts_journal_path)
    assert [transaction.date for transaction in journal.transactions] == [
        date(2025, 1, 31),
        date(2025, 2, 28),
        date(2025, 3, 31),
    ]
    assert all(
        transaction
        == Transaction(
            date=transaction.date,
            description="Monthly food",
            postings=[
                Posting(account=BANK, amount=Decimal(-10)),
                Posting(account=FOOD, amount=Decimal(10)),
            ],
        )
        for transaction in journal.transactions
    )
    assert journal.recurring_transactions[0].next_date == date(2025, 4, 30)

    second_result = runner.invoke(
        cli.cli,
        [
            "post-rec",
            "--through",
            "03-31",
            "-j",
            str(accounts_journal_path),
        ],
    )
    assert second_result.exit_code == 0
    assert "No recurring transactions due" in second_result.output
    assert len(load_journal(accounts_journal_path).transactions) == 3


def test_post_rec_dry_run_does_not_change_journal(runner, accounts_journal_path):
    runner.invoke(
        cli.cli,
        [
            "recur",
            "add",
            "Monthly food",
            "a:Bank",
            "-10",
            "e:Food",
            "10",
            "--start",
            "07-01",
            "-j",
            str(accounts_journal_path),
        ],
    )

    result = runner.invoke(
        cli.cli,
        [
            "post-rec",
            "--through",
            "07-01",
            "--dry-run",
            "-j",
            str(accounts_journal_path),
        ],
    )

    assert result.exit_code == 0
    assert "Would post 1 recurring transaction" in result.output
    journal = load_journal(accounts_journal_path)
    assert journal.transactions == []
    assert journal.recurring_transactions[0].next_date == date(2025, 7, 1)


def test_recur_list_displays_templates(runner, accounts_journal_path):
    runner.invoke(
        cli.cli,
        [
            "recur",
            "add",
            "Monthly food",
            "a:Bank",
            "-10",
            "e:Food",
            "10",
            "--start",
            "07-01",
            "-j",
            str(accounts_journal_path),
        ],
    )

    result = runner.invoke(
        cli.cli,
        ["recur", "list", "-j", str(accounts_journal_path)],
    )

    assert result.exit_code == 0
    assert "monthly 2025-07-01 Monthly food (next: 2025-07-01)" in result.output
    assert "Assets::Bank  -10.00" in result.output

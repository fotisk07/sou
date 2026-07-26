from click.testing import CliRunner

from sou import cli
from sou.models import Account
from sou.storage import init_journal, load_journal


def test_add_account(tmp_path):
    journal_path = tmp_path / "journal.sou"
    init_journal(journal_path, 2026)

    result = CliRunner().invoke(
        cli.cli,
        ["add", "a", "Bank", "--destination", str(journal_path)],
    )

    assert result.exit_code == 0
    assert load_journal(journal_path).accounts == {
        Account(category="Assets", path=("Bank",)),
    }


def test_add_nested_account(tmp_path):
    journal_path = tmp_path / "journal.sou"
    init_journal(journal_path, 2026)
    runner = CliRunner()
    runner.invoke(cli.cli, ["add", "assets", "Bank", "-d", str(journal_path)])

    result = runner.invoke(
        cli.cli,
        ["add", "a", "Bank:Checking", "-d", str(journal_path)],
    )

    assert result.exit_code == 0
    assert load_journal(journal_path).accounts == {
        Account(category="Assets", path=("Bank",)),
        Account(category="Assets", path=("Bank", "Checking")),
    }


def test_reject_account_without_parent(tmp_path):
    journal_path = tmp_path / "journal.sou"
    init_journal(journal_path, 2026)

    result = CliRunner().invoke(
        cli.cli,
        ["add", "a", "Bank:Checking", "-d", str(journal_path)],
    )

    assert result.exit_code == 1
    assert "parent account 'Assets::Bank' does not exist" in result.output
    assert load_journal(journal_path).accounts == set()


def test_reject_duplicate_account_without_changing_journal(tmp_path):
    journal_path = tmp_path / "journal.sou"
    init_journal(journal_path, 2026)
    runner = CliRunner()
    command = ["add", "e", "Food", "-d", str(journal_path)]
    assert runner.invoke(cli.cli, command).exit_code == 0
    source = journal_path.read_text(encoding="utf-8")

    result = runner.invoke(cli.cli, command)

    assert result.exit_code == 1
    assert "account 'Expenses::Food' already exists" in result.output
    assert journal_path.read_text(encoding="utf-8") == source


def test_add_account_reports_missing_journal(tmp_path):
    journal_path = tmp_path / "missing.sou"

    result = CliRunner().invoke(
        cli.cli,
        ["add", "i", "Salary", "-d", str(journal_path)],
    )

    assert result.exit_code == 1
    assert f"{journal_path} does not exist" in result.output

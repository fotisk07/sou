from sou import cli
from sou.models import Account
from sou.storage import load_journal


def test_add_maps_cli_arguments_and_saves_account(runner, empty_journal_path):
    result = runner.invoke(
        cli.cli,
        ["add", "a", "Bank", "--journal", str(empty_journal_path)],
    )

    assert result.exit_code == 0
    assert load_journal(empty_journal_path).accounts == {
        Account(category="Assets", path=("Bank",)),
    }


def test_add_accepts_full_category_and_short_journal_option(runner, empty_journal_path):
    runner.invoke(
        cli.cli,
        ["add", "assets", "Bank", "-j", str(empty_journal_path)],
    )

    result = runner.invoke(
        cli.cli,
        ["add", "assets", "Bank:Checking", "-j", str(empty_journal_path)],
    )

    assert result.exit_code == 0
    assert (
        Account(category="Assets", path=("Bank", "Checking"))
        in load_journal(empty_journal_path).accounts
    )


def test_add_rejects_category_outside_click_choice(runner, empty_journal_path):
    result = runner.invoke(
        cli.cli,
        ["add", "invalid", "Bank", "-j", str(empty_journal_path)],
    )

    assert result.exit_code == 2
    assert "'invalid' is not one of" in result.output


def test_add_reports_missing_journal(runner, tmp_path):
    journal_path = tmp_path / "missing.sou"

    result = runner.invoke(
        cli.cli,
        ["add", "i", "Salary", "-j", str(journal_path)],
    )

    assert result.exit_code == 1
    assert f"{journal_path} does not exist" in result.output

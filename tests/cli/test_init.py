from datetime import date

from sou import cli
from sou.storage import load_journal


def test_init_uses_current_year_by_default(runner, tmp_path):
    journal_path = tmp_path / "journal.sou"

    result = runner.invoke(cli.cli, ["init", str(journal_path)])

    assert result.exit_code == 0
    assert load_journal(journal_path).year == date.today().year


def test_init_accepts_year_option(runner, tmp_path):
    journal_path = tmp_path / "journal.sou"

    result = runner.invoke(
        cli.cli,
        ["init", str(journal_path), "--year", "2024"],
    )

    assert result.exit_code == 0
    assert load_journal(journal_path).year == 2024


def test_init_translates_existing_file_error(runner, tmp_path):
    journal_path = tmp_path / "journal.sou"
    journal_path.write_text("existing journal", encoding="utf-8")

    result = runner.invoke(cli.cli, ["init", str(journal_path)])

    assert result.exit_code == 1
    assert f"{journal_path} already exists" in result.output
    assert journal_path.read_text(encoding="utf-8") == "existing journal"

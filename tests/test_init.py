from datetime import date

from click.testing import CliRunner

from sou import cli


def expected_journal(year):
    return f"""[JOURNAL]

year: {year}

[ACCOUNTS]

Assets
Liabilities
Equity
Income
Expenses

[TRANSACTIONS]
"""


def test_init(tmpdir):
    journal_path = tmpdir / "journal.sou"
    assert not journal_path.exists()

    result = CliRunner().invoke(cli.cli, ["init", str(journal_path)])

    assert result.exit_code == 0
    assert journal_path.exists()
    assert journal_path.read_text(encoding="utf-8") == expected_journal(
        date.today().year
    )


def test_init_with_year(tmpdir):
    journal_path = tmpdir / "journal.sou"

    result = CliRunner().invoke(
        cli.cli, ["init", str(journal_path), "--year", "2024"]
    )

    assert result.exit_code == 0
    assert journal_path.read_text(encoding="utf-8") == expected_journal(2024)


def test_no_overwrite(tmpdir):
    journal_path = tmpdir / "journal.sou"
    journal_path.write_text("existing journal", encoding="utf-8")

    CliRunner().invoke(cli.cli, ["init", str(journal_path)])
    result = CliRunner().invoke(cli.cli, ["init", str(journal_path)])

    assert result.exit_code == 1
    assert journal_path.read_text(encoding="utf-8") == "existing journal"

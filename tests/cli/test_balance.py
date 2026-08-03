from datetime import date

from sou import cli


class July2025(date):
    @classmethod
    def today(cls):
        return cls(2025, 7, 15)


def test_balance_renders_closing_balance(runner, report_journal_path):
    result = runner.invoke(
        cli.cli,
        ["balance", "e:Food", "-j", str(report_journal_path)],
    )

    assert result.exit_code == 0
    assert result.output == "Expenses::Food  35.00\n"


def test_balance_maps_date_options_to_range_summary(runner, report_journal_path):
    result = runner.invoke(
        cli.cli,
        [
            "balance",
            "e:Food",
            "--from",
            "07-01",
            "--to",
            "07-31",
            "-j",
            str(report_journal_path),
        ],
    )

    assert result.exit_code == 0
    assert result.output == (
        "Expenses::Food\nOpening:  10.00\nActivity:  25.00\nClosing:  35.00\n"
    )


def test_balance_month_uses_current_calendar_month(
    runner, report_journal_path, monkeypatch
):
    monkeypatch.setattr(cli, "date", July2025)

    result = runner.invoke(
        cli.cli,
        ["balance", "e:Food", "--month", "-j", str(report_journal_path)],
    )

    assert result.exit_code == 0
    assert result.output == (
        "Expenses::Food\nOpening:  10.00\nActivity:  25.00\nClosing:  35.00\n"
    )


def test_balance_renders_natural_income_sign(runner, report_journal_path):
    result = runner.invoke(
        cli.cli,
        ["balance", "i:Salary", "-j", str(report_journal_path)],
    )

    assert result.exit_code == 0
    assert result.output == "Income::Salary  100.00\n"


def test_balance_rejects_month_with_explicit_range(
    runner, report_journal_path, monkeypatch
):
    monkeypatch.setattr(cli, "date", July2025)

    result = runner.invoke(
        cli.cli,
        [
            "balance",
            "e:Food",
            "--month",
            "--from",
            "07-01",
            "-j",
            str(report_journal_path),
        ],
    )

    assert result.exit_code == 2
    assert "--month cannot be combined with --from or --to" in result.output


def test_balance_rejects_invalid_date(runner, report_journal_path):
    result = runner.invoke(
        cli.cli,
        [
            "balance",
            "e:Food",
            "--from",
            "02-30",
            "-j",
            str(report_journal_path),
        ],
    )

    assert result.exit_code == 1
    assert "invalid from date '02-30'; expected MM-DD" in result.output

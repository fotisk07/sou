from datetime import date

from sou import cli


def test_balance_renders_closing_balance(runner, report_journal_path):
    result = runner.invoke(
        cli.cli,
        ["balance", "e:Food", "--all", "-j", str(report_journal_path)],
    )

    assert result.exit_code == 0
    assert result.output == (
        "Balance — Expenses::Food — 2025-01-01 to 2025-12-31\nClosing:  35.00\n"
    )


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
        "Balance — Expenses::Food — 2025-07-01 to 2025-07-31\n"
        "Opening:  10.00\nActivity:  25.00\nClosing:  35.00\n"
    )


def test_balance_defaults_to_current_calendar_month(
    runner, report_journal_path, monkeypatch
):
    monkeypatch.setattr(cli, "_today", lambda: date(2025, 7, 15))

    result = runner.invoke(
        cli.cli,
        ["balance", "e:Food", "-j", str(report_journal_path)],
    )

    assert result.exit_code == 0
    assert result.output == (
        "Balance — Expenses::Food — 2025-07-01 to 2025-07-31\n"
        "Opening:  10.00\nActivity:  25.00\nClosing:  35.00\n"
    )


def test_balance_accepts_a_month_number(runner, report_journal_path):
    result = runner.invoke(
        cli.cli,
        ["balance", "e:Food", "-m", "6", "-j", str(report_journal_path)],
    )

    assert result.exit_code == 0
    assert result.output == (
        "Balance — Expenses::Food — 2025-06-01 to 2025-06-30\n"
        "Opening:  0\nActivity:  10.00\nClosing:  10.00\n"
    )


def test_balance_renders_natural_income_sign(runner, report_journal_path):
    result = runner.invoke(
        cli.cli,
        ["balance", "i:Salary", "--all", "-j", str(report_journal_path)],
    )

    assert result.exit_code == 0
    assert result.output == (
        "Balance — Income::Salary — 2025-01-01 to 2025-12-31\nClosing:  100.00\n"
    )


def test_balance_rejects_month_with_explicit_range(runner, report_journal_path):

    result = runner.invoke(
        cli.cli,
        [
            "balance",
            "e:Food",
            "--month",
            "7",
            "--from",
            "07-01",
            "-j",
            str(report_journal_path),
        ],
    )

    assert result.exit_code == 2
    assert "--month, --quarter, --all, and --from/--to are mutually exclusive" in (
        result.output
    )


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

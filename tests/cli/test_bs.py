from datetime import date

from sou import cli


def table_rows(output):
    return [
        [cell.strip() for cell in line.split("|")[1:-1]]
        for line in output.splitlines()
        if line.startswith("|")
    ]


def test_bs_defaults_to_end_of_current_month(runner, report_journal_path, monkeypatch):
    monkeypatch.setattr(cli, "_today", lambda: date(2025, 7, 15))

    result = runner.invoke(
        cli.cli,
        ["bs", "-j", str(report_journal_path)],
    )

    assert result.exit_code == 0
    assert result.output.startswith("Balance Sheet — 2025-07-31\n")
    assert table_rows(result.output) == [
        ["Account", "Amount"],
        ["ASSETS", ""],
        ["Bank", "965.00"],
        ["TOTAL ASSETS", "965.00"],
        ["LIABILITIES", ""],
        ["TOTAL LIABILITIES", "0.00"],
        ["NET WORTH", ""],
        ["OpeningBalances", "1,000.00"],
        ["Current year result", "-35.00"],
        ["TOTAL NET WORTH", "965.00"],
        ["TOTAL LIABILITIES AND NET WORTH", "965.00"],
    ]


def test_bs_accepts_a_month_number(runner, report_journal_path):
    result = runner.invoke(
        cli.cli,
        ["bs", "-m", "6", "-j", str(report_journal_path)],
    )

    assert result.exit_code == 0
    assert result.output.startswith("Balance Sheet — 2025-06-30\n")


def test_bs_accepts_a_quarter_number(runner, report_journal_path):
    result = runner.invoke(
        cli.cli,
        ["bs", "-q", "3", "-j", str(report_journal_path)],
    )

    assert result.exit_code == 0
    assert result.output.startswith("Balance Sheet — 2025-09-30\n")


def test_bs_accepts_an_explicit_date_and_depth(runner, report_journal_path):
    result = runner.invoke(
        cli.cli,
        [
            "bs",
            "--at",
            "06-30",
            "--depth",
            "0",
            "-j",
            str(report_journal_path),
        ],
    )

    assert result.exit_code == 0
    assert result.output.startswith("Balance Sheet — 2025-06-30\n")
    assert table_rows(result.output) == [
        ["Account", "Amount"],
        ["TOTAL ASSETS", "990.00"],
        ["TOTAL LIABILITIES", "0.00"],
        ["TOTAL NET WORTH", "990.00"],
        ["TOTAL LIABILITIES AND NET WORTH", "990.00"],
    ]


def test_bs_rejects_an_invalid_date(runner, report_journal_path):
    result = runner.invoke(
        cli.cli,
        ["bs", "--at", "02-30", "-j", str(report_journal_path)],
    )

    assert result.exit_code == 1
    assert "invalid date '02-30'; expected MM-DD" in result.output

from datetime import date

from sou import cli


class July2025(date):
    @classmethod
    def today(cls):
        return cls(2025, 7, 15)


def table_rows(output):
    return [
        [cell.strip() for cell in line.split("|")[1:-1]]
        for line in output.splitlines()
        if line.startswith("|")
    ]


def test_bs_defaults_to_today(runner, report_journal_path, monkeypatch):
    monkeypatch.setattr(cli, "date", July2025)

    result = runner.invoke(
        cli.cli,
        ["bs", "-j", str(report_journal_path)],
    )

    assert result.exit_code == 0
    assert result.output.startswith("Balance Sheet — 2025-07-15\n")
    assert table_rows(result.output) == [
        ["Account", "Amount"],
        ["ASSETS", ""],
        ["Bank", "985.00"],
        ["TOTAL ASSETS", "985.00"],
        ["LIABILITIES", ""],
        ["TOTAL LIABILITIES", "0.00"],
        ["NET WORTH", ""],
        ["OpeningBalances", "1,000.00"],
        ["Current year result", "-15.00"],
        ["TOTAL NET WORTH", "985.00"],
        ["TOTAL LIABILITIES AND NET WORTH", "985.00"],
    ]


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

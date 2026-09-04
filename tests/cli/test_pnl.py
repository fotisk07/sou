from datetime import date

from sou import cli


class July2025(date):
    @classmethod
    def today(cls):
        return cls(2025, 7, 15)


def test_pnl_defaults_to_current_month(runner, report_journal_path, monkeypatch):
    monkeypatch.setattr(cli, "date", July2025)

    result = runner.invoke(
        cli.cli,
        ["pnl", "-j", str(report_journal_path)],
    )

    assert result.exit_code == 0
    assert result.output.startswith("Profit and Loss — 2025-07-01 to 2025-07-31\n")


def test_pnl_accepts_a_month_number(runner, report_journal_path):
    result = runner.invoke(
        cli.cli,
        ["pnl", "-m", "6", "-j", str(report_journal_path)],
    )

    assert result.exit_code == 0
    assert result.output.startswith("Profit and Loss — 2025-06-01 to 2025-06-30\n")


def test_pnl_accepts_a_quarter_number(runner, report_journal_path):
    result = runner.invoke(
        cli.cli,
        ["pnl", "-q", "3", "-j", str(report_journal_path)],
    )

    assert result.exit_code == 0
    assert result.output.startswith("Profit and Loss — 2025-07-01 to 2025-09-30\n")


def test_pnl_rejects_month_and_quarter_together(runner, report_journal_path):
    result = runner.invoke(
        cli.cli,
        [
            "pnl",
            "--month",
            "7",
            "--quarter",
            "3",
            "-j",
            str(report_journal_path),
        ],
    )

    assert result.exit_code == 2
    assert "--month, --quarter, --all, and --from/--to are mutually exclusive" in (
        result.output
    )

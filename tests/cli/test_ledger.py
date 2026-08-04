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


def test_ledger_renders_table_and_maps_date_options(runner, report_journal_path):
    result = runner.invoke(
        cli.cli,
        [
            "ledger",
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
    assert result.output.startswith("Expenses::Food\n+")
    assert table_rows(result.output) == [
        ["Date", "Account", "Description", "Amount", "Balance"],
        ["", "", "Opening balance", "", "10.00"],
        ["07-01", "Expenses::Food:Coffee", "Coffee", "5.00", "15.00"],
        ["07-31", "Expenses::Food", "Groceries", "20.00", "35.00"],
        ["", "", "Closing balance", "", "35.00"],
    ]


def test_ledger_defaults_to_current_calendar_month(
    runner, report_journal_path, monkeypatch
):
    monkeypatch.setattr(cli, "date", July2025)

    result = runner.invoke(
        cli.cli,
        ["ledger", "e:Food", "-j", str(report_journal_path)],
    )

    assert result.exit_code == 0
    assert table_rows(result.output)[1:] == [
        ["", "", "Opening balance", "", "10.00"],
        ["07-01", "Expenses::Food:Coffee", "Coffee", "5.00", "15.00"],
        ["07-31", "Expenses::Food", "Groceries", "20.00", "35.00"],
        ["", "", "Closing balance", "", "35.00"],
    ]


def test_ledger_renders_natural_income_sign(runner, report_journal_path):
    result = runner.invoke(
        cli.cli,
        ["ledger", "i:Salary", "--all", "-j", str(report_journal_path)],
    )

    assert result.exit_code == 0
    assert table_rows(result.output)[-2:] == [
        ["08-01", "Income::Salary", "Salary", "100.00", "100.00"],
        ["", "", "Closing balance", "", "100.00"],
    ]

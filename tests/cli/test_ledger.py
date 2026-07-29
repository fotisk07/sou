from sou import cli


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
        ["", "", "Opening balance", "", "10"],
        ["07-01", "Expenses::Food:Coffee", "Coffee", "5", "15"],
        ["07-31", "Expenses::Food", "Groceries", "20", "35"],
        ["", "", "Closing balance", "", "35"],
    ]


def test_ledger_renders_natural_income_sign(runner, report_journal_path):
    result = runner.invoke(
        cli.cli,
        ["ledger", "i:Salary", "-j", str(report_journal_path)],
    )

    assert result.exit_code == 0
    assert table_rows(result.output)[-2:] == [
        ["08-01", "Income::Salary", "Salary", "100", "100"],
        ["", "", "Closing balance", "", "100"],
    ]

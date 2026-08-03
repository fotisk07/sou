from sou import cli


def test_list_renders_account_tree(runner, report_journal_path):
    result = runner.invoke(
        cli.cli,
        ["list", "--journal", str(report_journal_path)],
    )

    assert result.exit_code == 0
    assert result.output == (
        "Assets\n"
        "  Bank\n"
        "Liabilities\n"
        "Equity\n"
        "  OpeningBalances\n"
        "Income\n"
        "  Salary\n"
        "Expenses\n"
        "  Food\n"
        "    Coffee\n"
    )


def test_list_reports_missing_journal(runner, tmp_path):
    journal_path = tmp_path / "missing.sou"

    result = runner.invoke(cli.cli, ["list", "-j", str(journal_path)])

    assert result.exit_code == 1
    assert f"{journal_path} does not exist" in result.output

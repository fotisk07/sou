from sou import cli


def test_check_accepts_valid_journal(runner, empty_journal_path):
    result = runner.invoke(cli.cli, ["check", "-j", str(empty_journal_path)])

    assert result.exit_code == 0
    assert result.output == f"{empty_journal_path} is valid\n"


def test_check_reports_invalid_journal(runner, empty_journal_path):
    empty_journal_path.write_text("not a journal\n", encoding="utf-8")

    result = runner.invoke(cli.cli, ["check", "-j", str(empty_journal_path)])

    assert result.exit_code == 1
    assert "content appears before the first section" in result.output


def test_check_reports_missing_journal(runner, tmp_path):
    path = tmp_path / "missing.sou"

    result = runner.invoke(cli.cli, ["check", "-j", str(path)])

    assert result.exit_code == 1
    assert result.output == f"Error: {path} does not exist\n"

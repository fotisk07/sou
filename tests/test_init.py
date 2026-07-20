from click.testing import CliRunner

from sou import cli


def test_init(tmpdir):
    journal_path = tmpdir / "journal.sou"
    assert not journal_path.exists()

    result = CliRunner().invoke(cli.cli, ["init", str(journal_path)])

    assert result.exit_code == 0
    assert journal_path.exists()


def test_no_overwrite(tmpdir):
    journal_path = tmpdir / "journal.sou"
    journal_path.write_text("existing journal", encoding="utf-8")

    CliRunner().invoke(cli.cli, ["init", str(journal_path)])
    result = CliRunner().invoke(cli.cli, ["init", str(journal_path)])

    assert result.exit_code == 1
    assert journal_path.read_text(encoding="utf-8") == "existing journal"

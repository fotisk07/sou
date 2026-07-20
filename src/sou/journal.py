from pathlib import Path


def journal_template(year: int) -> str:
    return f"""[JOURNAL]

year: {year}

[ACCOUNTS]

Assets
Liabilities
Equity
Income
Expenses

[TRANSACTIONS]
"""


def create_journal(path: Path, year: int) -> None:
    with path.open("x", encoding="utf-8") as journal:
        journal.write(journal_template(year))

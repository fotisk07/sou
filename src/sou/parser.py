import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import cast

from sou.models import (
    ACCOUNT_CATEGORIES,
    Account,
    Journal,
    Posting,
    RecurrenceFrequency,
    RecurringTransaction,
    Transaction,
)

REQUIRED_SECTIONS = ("JOURNAL", "ACCOUNTS", "TRANSACTIONS")
SECTIONS = (*REQUIRED_SECTIONS, "RECURRING")
YEAR_PATTERN = re.compile(r"year:\s*(\d{4})")
SECTION_PATTERN = re.compile(r"\[(.+)]")
TRANSACTION_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})\s+(.+)")
RECURRING_PATTERN = re.compile(r"(daily|weekly|monthly)\s+(\d{4}-\d{2}-\d{2})\s+(.+)")
NEXT_DATE_PATTERN = re.compile(r" {2}next:\s*(\d{4}-\d{2}-\d{2})")
POSTING_PATTERN = re.compile(r" {2}(\S(?:.*\S)?)\s+([+-]?\d+(?:\.\d+)?)")


class JournalParseError(ValueError):
    pass


def parse_sou(source: str) -> Journal:
    # First split the document into named sections. We retain line numbers so
    # later validation errors can point to the exact source line.
    sections: dict[str, list[tuple[int, str]]] = {name: [] for name in SECTIONS}
    seen_sections: set[str] = set()
    current_section: str | None = None

    for line_number, line in enumerate(source.splitlines(), start=1):
        if "\t" in line:
            raise JournalParseError(f"line {line_number}: tabs are not allowed")

        stripped = line.strip()
        if not stripped:
            continue

        # A section header changes where subsequent non-empty lines are stored.
        section_match = SECTION_PATTERN.fullmatch(stripped)
        if section_match:
            section = section_match.group(1)
            if section not in sections:
                raise JournalParseError(
                    f"line {line_number}: unknown section [{section}]"
                )
            if section in seen_sections:
                raise JournalParseError(
                    f"line {line_number}: duplicate section [{section}]"
                )
            seen_sections.add(section)
            current_section = section
            continue

        if current_section is None:
            raise JournalParseError(
                f"line {line_number}: content appears before the first section"
            )

        sections[current_section].append((line_number, line))

    # All sections must exist, even when they contain no accounts or transactions.
    missing_sections = set(REQUIRED_SECTIONS) - seen_sections
    if missing_sections:
        missing = ", ".join(sorted(missing_sections))
        raise JournalParseError(f"missing sections: {missing}")

    # Parse each section independently after validating the document structure.
    # Transactions receive the accounts so their references can be resolved.
    year = _parse_year(sections["JOURNAL"])
    accounts = _parse_accounts(sections["ACCOUNTS"])
    transactions = _parse_transactions(sections["TRANSACTIONS"], accounts, year)
    recurring_transactions = _parse_recurring(sections["RECURRING"], accounts, year)

    return Journal(
        year=year,
        accounts=accounts,
        transactions=transactions,
        recurring_transactions=recurring_transactions,
    )


def _parse_year(lines: list[tuple[int, str]]) -> int:
    """Parse the single `year: YYYY` entry from [JOURNAL]."""
    if len(lines) != 1:
        raise JournalParseError("[JOURNAL] must contain exactly one year")

    line_number, line = lines[0]
    match = YEAR_PATTERN.fullmatch(line.strip())
    if not match:
        raise JournalParseError(
            f"line {line_number}: expected a year in the form 'year: 2025'"
        )

    return int(match.group(1))


def _parse_accounts(lines: list[tuple[int, str]]) -> set[Account]:
    """Parse account categories and their indentation-based account trees."""
    accounts: set[Account] = set()
    category_index = 0
    account_category: str | None = None
    # `parents` holds the current account path. For example, after reading
    # "  Bank" it is ["Bank"], so "    Checking" becomes Bank:Checking.
    parents: list[str] = []

    for line_number, line in lines:
        # Unindented headings must follow ACCOUNT_CATEGORIES in order.
        if not line.startswith(" "):
            if category_index == len(ACCOUNT_CATEGORIES):
                raise JournalParseError(
                    f"line {line_number}: unexpected account category '{line}'"
                )

            expected_category = ACCOUNT_CATEGORIES[category_index]
            if line != expected_category:
                raise JournalParseError(
                    f"line {line_number}: expected account category "
                    f"'{expected_category}', found '{line}'"
                )

            account_category = expected_category
            category_index += 1
            parents = []
            continue

        if account_category is None:
            raise JournalParseError(
                f"line {line_number}: account appears before a category"
            )

        # Every two spaces represent one account level below the category.
        indentation = len(line) - len(line.lstrip(" "))
        if indentation % 2:
            raise JournalParseError(
                f"line {line_number}: account indentation must use two spaces"
            )

        depth = indentation // 2
        if depth > len(parents) + 1:
            raise JournalParseError(
                f"line {line_number}: account indentation skips a level"
            )

        name = line.strip()
        if ":" in name:
            raise JournalParseError(
                f"line {line_number}: account names cannot contain ':'"
            )

        # Discard path components from a previous sibling, then append this
        # account to the remaining parent path.
        parents = parents[: depth - 1]
        path = (*parents, name)
        account = Account(category=account_category, path=path)
        if account in accounts:
            raise JournalParseError(
                f"line {line_number}: duplicate account '{account}'"
            )
        accounts.add(account)
        parents.append(name)

    if category_index < len(ACCOUNT_CATEGORIES):
        expected_category = ACCOUNT_CATEGORIES[category_index]
        raise JournalParseError(f"missing account category '{expected_category}'")

    return accounts


def _parse_transactions(
    lines: list[tuple[int, str]], accounts: set[Account], year: int
) -> list[Transaction]:
    """Parse transaction headings and their indented postings."""
    transactions: list[Transaction] = []
    current: Transaction | None = None
    current_line = 0

    # Transactions refer to accounts by their complete rendered name, such as
    # "Assets::Bank:Checking". This map resolves that text to the Account model.
    accounts_by_name = {str(account): account for account in accounts}

    for line_number, line in lines:
        if not line.startswith(" "):
            # An unindented line starts a transaction. Finish the previous one
            # before moving to the next heading.
            if current is not None:
                _validate_transaction(current, current_line, year)
                transactions.append(current)

            match = TRANSACTION_PATTERN.fullmatch(line.strip())
            if not match:
                raise JournalParseError(
                    f"line {line_number}: expected 'YYYY-MM-DD DESCRIPTION'"
                )

            try:
                transaction_date = date.fromisoformat(match.group(1))
            except ValueError:
                raise JournalParseError(
                    f"line {line_number}: invalid transaction date '{match.group(1)}'"
                ) from None

            current = Transaction(
                date=transaction_date,
                description=match.group(2),
                postings=[],
            )
            current_line = line_number
            continue

        if current is None:
            raise JournalParseError(
                f"line {line_number}: posting appears before a transaction"
            )

        current.postings.append(_parse_posting(line, line_number, accounts_by_name))

    # The final transaction has no following heading to trigger completion.
    if current is not None:
        _validate_transaction(current, current_line, year)
        transactions.append(current)

    return transactions


def _parse_recurring(
    lines: list[tuple[int, str]], accounts: set[Account], year: int
) -> list[RecurringTransaction]:
    """Parse recurring transaction templates and their next due dates."""
    recurring_transactions: list[RecurringTransaction] = []
    current: RecurringTransaction | None = None
    current_line = 0
    next_date_seen = False
    accounts_by_name = {str(account): account for account in accounts}

    for line_number, line in lines:
        if not line.startswith(" "):
            if current is not None:
                _validate_recurring(current, current_line, year)
                recurring_transactions.append(current)

            match = RECURRING_PATTERN.fullmatch(line.strip())
            if not match:
                raise JournalParseError(
                    f"line {line_number}: expected 'FREQUENCY YYYY-MM-DD DESCRIPTION'"
                )

            frequency, start_text, description = match.groups()
            try:
                start_date = date.fromisoformat(start_text)
            except ValueError:
                raise JournalParseError(
                    f"line {line_number}: invalid recurring start date '{start_text}'"
                ) from None

            current = RecurringTransaction(
                frequency=cast(RecurrenceFrequency, frequency),
                start_date=start_date,
                next_date=start_date,
                description=description,
                postings=[],
            )
            current_line = line_number
            next_date_seen = False
            continue

        if current is None:
            raise JournalParseError(
                f"line {line_number}: recurring detail appears before a template"
            )

        next_match = NEXT_DATE_PATTERN.fullmatch(line)
        if next_match:
            if next_date_seen:
                raise JournalParseError(
                    f"line {line_number}: duplicate recurring next date"
                )
            try:
                current.next_date = date.fromisoformat(next_match.group(1))
            except ValueError:
                raise JournalParseError(
                    f"line {line_number}: invalid recurring next date "
                    f"'{next_match.group(1)}'"
                ) from None
            next_date_seen = True
            continue

        current.postings.append(_parse_posting(line, line_number, accounts_by_name))

    if current is not None:
        _validate_recurring(current, current_line, year)
        recurring_transactions.append(current)

    return recurring_transactions


def _parse_posting(
    line: str, line_number: int, accounts_by_name: dict[str, Account]
) -> Posting:
    """Parse a posting shared by ordinary and recurring transactions."""
    match = POSTING_PATTERN.fullmatch(line)
    if not match:
        raise JournalParseError(f"line {line_number}: expected '  ACCOUNT AMOUNT'")

    account_name, amount_text = match.groups()
    account = accounts_by_name.get(account_name)
    if account is None:
        raise JournalParseError(f"line {line_number}: unknown account '{account_name}'")

    try:
        amount = Decimal(amount_text)
    except InvalidOperation:
        raise JournalParseError(
            f"line {line_number}: invalid amount '{amount_text}'"
        ) from None

    return Posting(account=account, amount=amount)


def _validate_recurring(
    recurring: RecurringTransaction, line_number: int, year: int
) -> None:
    if recurring.start_date.year != year:
        raise JournalParseError(
            f"line {line_number}: recurring start date is outside journal year {year}"
        )
    if recurring.next_date < recurring.start_date:
        raise JournalParseError(
            f"line {line_number}: recurring next date precedes its start date"
        )
    if not recurring.description.strip():
        raise JournalParseError(
            f"line {line_number}: recurring description cannot be empty"
        )
    _validate_postings(recurring.postings, line_number)


def _validate_transaction(
    transaction: Transaction, line_number: int, year: int
) -> None:
    """Validate the accounting rules that apply to one parsed transaction."""
    if transaction.date.year != year:
        raise JournalParseError(
            f"line {line_number}: transaction date is outside journal year {year}"
        )

    _validate_postings(transaction.postings, line_number)


def _validate_postings(postings: list[Posting], line_number: int) -> None:
    if len(postings) < 2:
        raise JournalParseError(
            f"line {line_number}: transaction must have at least two postings"
        )

    posting_accounts = [posting.account for posting in postings]
    if len(set(posting_accounts)) != len(posting_accounts):
        raise JournalParseError(
            f"line {line_number}: an account cannot appear more than once"
        )

    if any(posting.amount == 0 for posting in postings):
        raise JournalParseError(f"line {line_number}: posting amounts cannot be zero")

    balance = sum((posting.amount for posting in postings), Decimal(0))
    if balance != 0:
        raise JournalParseError(
            f"line {line_number}: transaction is not balanced (difference: {balance})"
        )

from calendar import monthrange
from datetime import date

import click


def report_period_options(function):
    """Add numbered month and quarter options to a report."""
    function = click.option(
        "-q",
        "--quarter",
        type=click.IntRange(1, 4),
        help="Show calendar quarter 1-4.",
    )(function)
    return click.option(
        "-m",
        "--month",
        type=click.IntRange(1, 12),
        help="Show calendar month 1-12.",
    )(function)


def report_range_options(function):
    """Add all-time and explicit date-range options to a report."""
    function = click.option(
        "--all",
        "all_time",
        is_flag=True,
        help="Show the entire journal year.",
    )(function)
    function = click.option(
        "--to",
        "to_text",
        help="End date in MM-DD format.",
    )(function)
    return click.option(
        "--from",
        "from_text",
        help="Start date in MM-DD format.",
    )(function)


def resolve_balance_sheet_date(
    journal_year: int,
    at_text: str | None,
    month: int | None,
    quarter: int | None,
    today: date,
) -> date:
    """Resolve the closing date for a balance sheet period."""
    selected_periods = sum((
        at_text is not None,
        month is not None,
        quarter is not None,
    ))
    if selected_periods > 1:
        raise click.UsageError("--at, --month, and --quarter are mutually exclusive")

    if at_text is not None:
        try:
            return date.fromisoformat(f"{journal_year}-{at_text}")
        except ValueError:
            raise click.ClickException(
                f"invalid date '{at_text}'; expected MM-DD"
            ) from None

    if month is None and quarter is None:
        if today.year != journal_year:
            raise click.ClickException(
                f"current month is outside journal year {journal_year}; use --month, --quarter, or --at"
            )
        month = today.month

    if month is not None:
        end_month = month
    else:
        assert quarter is not None
        end_month = quarter * 3
    return date(journal_year, end_month, monthrange(journal_year, end_month)[1])


def resolve_report_dates(
    journal_year: int,
    from_text: str | None,
    to_text: str | None,
    month: int | None,
    quarter: int | None,
    all_time: bool,
    today: date,
) -> tuple[date | None, date | None]:
    """Resolve report period options to inclusive date boundaries."""
    has_explicit_range = from_text is not None or to_text is not None
    selected_periods = sum((
        has_explicit_range,
        month is not None,
        quarter is not None,
        all_time,
    ))
    if selected_periods > 1:
        raise click.UsageError(
            "--month, --quarter, --all, and --from/--to are mutually exclusive"
        )

    if all_time:
        return None, None

    if has_explicit_range:
        try:
            from_date = (
                date.fromisoformat(f"{journal_year}-{from_text}") if from_text else None
            )
        except ValueError:
            raise click.ClickException(
                f"invalid from date '{from_text}'; expected MM-DD"
            ) from None

        try:
            to_date = (
                date.fromisoformat(f"{journal_year}-{to_text}") if to_text else None
            )
        except ValueError:
            raise click.ClickException(
                f"invalid to date '{to_text}'; expected MM-DD"
            ) from None
        return from_date, to_date

    if month is None and quarter is None:
        if journal_year != today.year:
            raise click.ClickException(
                f"current month is outside journal year {journal_year}"
            )
        month = today.month

    if month is not None:
        start_month = end_month = month
    else:
        assert quarter is not None
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2

    return (
        date(journal_year, start_month, 1),
        date(journal_year, end_month, monthrange(journal_year, end_month)[1]),
    )

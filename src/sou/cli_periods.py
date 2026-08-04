from calendar import monthrange
from datetime import date

import click


def report_period_options(function):
    """Add the common period options used by financial reports."""
    function = click.option(
        "--all",
        "all_time",
        is_flag=True,
        help="Show the entire journal year.",
    )(function)
    function = click.option(
        "-q",
        "--quarter",
        "current_quarter",
        is_flag=True,
        help="Show the current calendar quarter.",
    )(function)
    function = click.option(
        "-m",
        "--month",
        "current_month",
        is_flag=True,
        help="Show the current calendar month.",
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


def resolve_report_date(
    journal_year: int,
    at_text: str | None,
    today: date,
) -> date:
    """Resolve an optional MM-DD value for a point-in-time report."""
    if at_text is None:
        if today.year != journal_year:
            raise click.ClickException(
                f"current date is outside journal year {journal_year}; use --at"
            )
        return today

    try:
        return date.fromisoformat(f"{journal_year}-{at_text}")
    except ValueError:
        raise click.ClickException(
            f"invalid date '{at_text}'; expected MM-DD"
        ) from None


def resolve_report_dates(
    journal_year: int,
    from_text: str | None,
    to_text: str | None,
    current_month: bool,
    current_quarter: bool,
    all_time: bool,
    today: date,
) -> tuple[date | None, date | None]:
    """Resolve shared report period options to inclusive date boundaries."""
    has_explicit_range = from_text is not None or to_text is not None
    if current_month and has_explicit_range:
        raise click.UsageError("--month cannot be combined with --from or --to")

    selected_periods = sum((
        has_explicit_range,
        current_month,
        current_quarter,
        all_time,
    ))
    if selected_periods > 1:
        raise click.UsageError(
            "--month, --quarter, --all, and --from/--to are mutually exclusive"
        )

    if all_time:
        return None, None

    use_current_month = current_month or selected_periods == 0
    if use_current_month or current_quarter:
        period_name = "month" if use_current_month else "quarter"
        if journal_year != today.year:
            raise click.ClickException(
                f"current {period_name} is outside journal year {journal_year}"
            )

        if use_current_month:
            start_month = today.month
            end_month = today.month
        else:
            start_month = ((today.month - 1) // 3) * 3 + 1
            end_month = start_month + 2

        return (
            date(today.year, start_month, 1),
            date(today.year, end_month, monthrange(today.year, end_month)[1]),
        )

    try:
        from_date = (
            date.fromisoformat(f"{journal_year}-{from_text}") if from_text else None
        )
    except ValueError:
        raise click.ClickException(
            f"invalid from date '{from_text}'; expected MM-DD"
        ) from None

    try:
        to_date = date.fromisoformat(f"{journal_year}-{to_text}") if to_text else None
    except ValueError:
        raise click.ClickException(
            f"invalid to date '{to_text}'; expected MM-DD"
        ) from None

    return from_date, to_date

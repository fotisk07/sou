# Journal format

Sou journals are plain-text files. You can maintain them with the CLI, edit them directly, or generate them with your own tools.

For everyday commands, see the [usage guide](usage.md). For an introduction to Sou, see the [README](../README.md).

## Complete example

This example can be saved as `journal.sou` and validated with `sou check`. Explanations follow the example rather than appearing as inline comments: the journal format does not support comments.

```text
[JOURNAL]

name: Personal journal
author: Your name
year: 2026
currency: EUR

[ACCOUNTS]

Assets
  Bank
  Savings
Liabilities
Equity
  OpeningBalances
Income
  Salary
Expenses
  Food
  Household

[ALIASES]

bank = Assets/Bank
food = Expenses/Food

[RECURRING]

weekly 2026-03-16 Lunch
  next: 2026-03-16
  Assets/Bank  -10.00
  Expenses/Food  10.00

[TRANSACTIONS]

2026-01-01 Opening balance
  Equity/OpeningBalances  -1000.00
  Assets/Bank  1000.00

2026-03-01 Salary
  Income/Salary  -2500.00
  Assets/Bank  2500.00

2026-03-15 Grocery run
  Assets/Bank  -50.00
  Expenses/Food  40.00
  Expenses/Household  10.00

2026-03-15 Transfer to savings
  Assets/Bank  -200.00
  Assets/Savings  200.00
```

The opening balance records money already owned, not new income. Salary increases the bank account and credits income. The grocery purchase splits an expense between two categories. The savings transfer moves an asset without creating an expense.

## Sections and layout

Use these sections in this order:

1. `[JOURNAL]` — required metadata.
2. `[ACCOUNTS]` — account hierarchy.
3. `[ALIASES]` — optional account shortcuts.
4. `[RECURRING]` — optional recurring templates.
5. `[TRANSACTIONS]` — recorded transactions; this section must exist even when empty.

Section names are uppercase. Blank lines separate entries for readability. Use spaces, not tabs, for indentation: two spaces per account level and two spaces before transaction postings and recurring-template fields.

Dates inside the file use `YYYY-MM-DD`, unlike command-line dates, which use `DD-MM` within the journal year.

## Metadata

All four fields are required:

```text
[JOURNAL]

name: Personal journal
author:
year: 2026
currency: EUR
```

- `name`: a nonempty journal name.
- `author`: a name, or blank. PDF reports include it only when present.
- `year`: an integer from 1 to 9999. Transaction dates and recurring start dates must belong to this year.
- `currency`: exactly three uppercase ASCII letters, such as `EUR` or `USD`.

Names and authors cannot contain control characters or square brackets. Unknown or duplicate metadata fields are rejected.

A journal uses a single currency; postings contain amounts without currency symbols. Changing `currency` changes the journal's denomination label, not the amounts—it does not perform a conversion.

## Account hierarchy

Sou has five root accounts: `Assets`, `Liabilities`, `Equity`, `Income`, and `Expenses`.

Declare children by indenting two spaces for each level:

```text
Assets
  Bank
    Checking
    Savings
Expenses
  Food
```

The full paths here include `Assets/Bank/Checking` and `Expenses/Food`. Declare a parent before its children; don't skip indentation levels. Tabs and odd numbers of leading spaces are rejected.

Each full account path, including each root, may be declared only once. The same name can appear under different parents, such as `Assets/Other` and `Expenses/Other`.

Each individual account name must be nonempty and contain no whitespace, control characters, slashes, colons, or square brackets. Slashes separate account names in paths, not in hierarchy declarations.

Postings must refer to existing accounts. Creating a posting does not implicitly create its account.

## Transactions and signs

A transaction begins with an unindented date and description, followed by at least two indented postings:

```text
2026-03-15 Coffee and lunch
  Assets/Bank  -10.00
  Expenses/Food  10.00
```

Each posting contains a full account path and a signed decimal amount. Use a decimal point, without thousands separators, currency symbols, or trailing annotations. Amounts must be representable with at most two decimal places.

Every transaction must sum to exactly zero. Descriptions must be nonempty and fit on one line.

The signs follow debit/credit accounting, not a universal positive-means-more rule:

| Account type | Positive posting | Negative posting |
| --- | --- | --- |
| Assets | Increase | Decrease |
| Expenses | Increase | Decrease |
| Liabilities | Decrease | Increase |
| Equity | Decrease | Increase |
| Income | Decrease | Increase |

For `sou post AMOUNT FROM TO DESCRIPTION`, Sou writes a negative posting to `FROM` and a positive posting to `TO` when the amount is positive. A negative amount reverses that direction.

Report presentation may differ from these raw posting signs; for example, earned income is credited in the journal.

## Aliases

The optional `[ALIASES]` section maps shortcuts to existing account paths:

```text
[ALIASES]

bank = Assets/Bank
food = Expenses/Food
```

You can then use those shortcuts in commands:

```sh
sou post 10 bank food Lunch
sou ledger bank --year
```

Alias names must be unique, must not conflict with account names, and follow the account-name restrictions. They also cannot start with `-` or contain `=`.

Use full account paths in the file's transaction and recurring-template postings; aliases are shortcuts for CLI input, not replacements for stored account paths.

## Recurring templates

The optional `[RECURRING]` section stores schedules separately from recorded transactions:

```text
[RECURRING]

monthly 2026-01-01 Rent
  next: 2026-04-01
  Assets/Bank  -800.00
  Expenses/Rent  800.00
```

This example assumes `Expenses/Rent` has been declared under `[ACCOUNTS]`.

The header contains the frequency, start date, and description. Supported frequencies are `daily`, `weekly`, `biweekly`, and `monthly`.

`next:` is required and identifies the next occurrence to post. It must not precede the start date. After the final occurrence in the journal year, it can point into the following year.

Template postings follow the same rules as transaction postings: at least two, existing accounts, amounts representable with two decimal places, and a zero sum.

A template is not a transaction and does not affect reports until you run `sou recur post`. Posting due occurrences advances `next:`. Moving that date backwards can cause occurrences to be posted again; moving it forwards can skip them. Prefer the CLI for schedule management unless you intend to change this state.

See the [recurring-postings workflow](usage.md#recurring-postings) for commands and previews.

## Editing safely

1. Save a backup or commit your current journal before large edits.
2. Make changes in your editor.
3. Run `sou check`, or `sou -j path/to/journal.sou check`.
4. Inspect the relevant ledger and reports.
5. Review the diff before committing.

Validation checks structural and accounting constraints, including known accounts, dates within the journal year, precision, and balanced transactions. It does not prove that the amounts, categories, or completeness of your records are correct.

Commands that write the journal serialize the whole file in Sou's standard format. Custom spacing may be normalized. There is no supported comment syntax, so keep explanatory notes outside the journal or in transaction descriptions.

Run `sou sort` if you want transactions ordered by date after editing.

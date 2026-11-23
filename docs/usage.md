# Using Sou

For installation and your first transactions, start with the [README](../README.md#quick-start). For direct editing or tooling, see the [journal format](journal-format.md).

Use `sou --help` or `sou <command> --help` for command syntax and available options.

## Journal selection and dates

Sou uses `journal.sou` in the current directory by default. For another file, put `-j` before the command:

```sh
sou -j path/to/journal.sou pnl --year
```

A journal has one year and one currency. Set these when creating it:

```sh
sou init --year 2026 --currency EUR --author "Your name"
```

Command-line dates use `DD-MM` within that journal year. Use `--date DD-MM` when posting to choose a date instead of today:

```sh
sou post 10 Assets/Bank Expenses/Food Lunch --date 15-03
```

For current-year journals, `pnl` and `ledger` default to the current month; `bs` defaults to the current month-end. For other journal years, the defaults cover the whole year. Use explicit dates when entering transactions in a historical journal.

## Reporting periods

Choose the reporting period, column breakdown, and account depth:

```sh
sou pnl --month
sou pnl --quarter 2
sou pnl --from 01-03 --to 15-06
sou pnl --year --by-month --depth 2
sou bs --to 30-06
```

Dates are inclusive. A bare `--month` or `--quarter` selects the current month or quarter and requires a current-year journal; a number selects that period in the journal year.

`--depth` controls how many account levels are displayed; the default is 1, and 0 shows totals only.

Compare balance-sheet snapshots at month- or quarter-end:

```sh
sou bs --year --by-quarter
sou bs --quarter 2 --by-month
sou bs --to 15-05 --by-month
```

Each balance-sheet column is a cumulative balance at its labelled date, not activity during the period. There is no Total column. An explicit mid-period cutoff produces a final snapshot on that exact date. Without a month or quarter selection, comparisons start in January.

## Exporting reports

P&L and balance-sheet reports support `--format csv`, `--format xlsx`, and `--format pdf`. The same date filters, account depth, and monthly or quarterly breakdowns apply to exports.

Redirect XLSX and PDF output to files rather than displaying it in the terminal.

### XLSX

For Excel or LibreOffice, preserving account indentation and numeric amounts:

```sh
sou pnl --year --depth 2 --format xlsx > pnl.xlsx
sou pnl --year --by-month --depth 2 --format xlsx > monthly.xlsx
sou bs --to 31-12 --depth 2 --format xlsx > bs.xlsx
```

Bold parent rows are subtotals, not additional amounts to sum.

### PDF

Print-ready reports, generated directly in Rust without a browser or external converter:

```sh
sou pnl --quarter 4 --by-month --format pdf > pnl-q4.pdf
sou pnl --year --by-quarter --format pdf > pnl-year.pdf
sou bs --year --format pdf > bs.pdf
sou bs --year --by-quarter --format pdf > bs-quarterly.pdf
```

PDF reports include embedded fonts, repeated table headers, and page numbers. Wide reports automatically use landscape or A3 paper. Reports reflect the transactions entered; they do not certify that your records are complete.

### CSV

For plain data:

```sh
sou pnl --year --depth 2 --format csv > pnl.csv
sou pnl --year --by-month --depth 2 --format csv > monthly.csv
sou bs --to 31-12 --depth 2 --format csv > bs.csv
```

CSV includes full account paths, depth, and row type (`account`, `subtotal`, `direct`, or `result`). Subtotals include their children; do not sum all rows together. Amounts are plain decimals without thousands separators.

## Recurring postings

Create a template, then explicitly post what is due. Adding a template does not post anything:

```sh
sou recur add Lunch Assets/Bank -10 Expenses/Food 10 --week
sou recur list
sou recur post --dry-run
sou recur post
```

Templates are monthly by default. You can also use `--day`, `--week`, or `--biweekly`. Use `--start DD-MM` to choose the first occurrence; otherwise it starts today in a current-year journal.

Previewing with `--dry-run` lets you inspect the proposed entries before writing them. See `sou recur post --help` for cutoff options, and the [journal-format reference](journal-format.md#recurring-templates) before editing a template's schedule directly.

## Account completion

For zsh, add this to `~/.zshrc`:

```sh
autoload -Uz compinit
compinit
source <(COMPLETE=zsh sou)
```

For bash, add this to `~/.bashrc`:

```sh
source <(COMPLETE=bash sou)
```

Accounts come from `journal.sou` in the current directory, or from the file selected with `-j`.

## Journal author

Every journal requires an `author:` line under `[JOURNAL]`, but the name may be blank. `sou init` writes an empty line when no author is supplied. PDFs show the author only when a name is present. Older journals need this line added before they can be used.

## Editing and checking

You can edit the journal in any text editor. See the [journal format](journal-format.md) for syntax and examples.

After editing, validate the file and optionally sort its transactions by date:

```sh
sou check
sou sort
```

`check` validates the journal without rewriting it. `sort` writes the sorted journal. Commands that write the journal serialize it in Sou's standard format, so hand-adjusted spacing may change. Review changes with `git diff` if you keep the journal under version control.

# Sou

Sou is a small command-line accounting tool backed by a human-readable text file. It uses double-entry bookkeeping while keeping common operations quick to type.

> Sou is currently an early personal-finance project. Back up your journal and review the text file regularly.

## Install

Sou requires [uv](https://docs.astral.sh/uv/). Install uv if necessary:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install Sou directly from GitHub:

```bash
uv tool install git+https://github.com/fotisk07/sou.git
```

You can then use `sou` from any directory:

```bash
sou --help
```

To upgrade or uninstall it later:

```bash
uv tool upgrade sou
uv tool uninstall sou
```

## Quick start

Create a directory for your finances and initialize the current year:

```bash
mkdir my-finances
cd my-finances
sou init
```

Sou uses `journal.sou` in the current directory by default. Use `-j PATH` to operate on another journal.

### Create accounts

Account categories have short forms:

| Short form | Category |
|---|---|
| `a` | Assets |
| `l` | Liabilities |
| `eq` | Equity |
| `i` | Income |
| `e` | Expenses |

Create parent accounts before their children:

```bash
sou add a Bank
sou add a Bank:Checking
sou add eq OpeningBalances
sou add i Salary
sou add e Food
sou add e Food:Coffee
```

### Enter opening balances

An existing asset balance flows from equity into the asset:

```bash
sou post 1500 eq:OpeningBalances a:Bank:Checking Opening balance -d 01-01
```

An existing liability flows from the liability into opening equity:

```bash
sou add l CreditCard
sou post 300 l:CreditCard eq:OpeningBalances Opening balance -d 01-01
```

### Post transactions

The syntax is:

```text
sou post AMOUNT FROM TO DESCRIPTION...
```

Examples:

```bash
sou post 12.50 a:Bank:Checking e:Food Lunch
sou post 4.20 a:Bank:Checking e:Food:Coffee Coffee with Alex
sou post 2000 i:Salary a:Bank:Checking July salary -d 07-31
```

The date defaults to today. Explicit dates use `MM-DD`; the journal already supplies the year.

### Check a balance

A parent balance includes postings to all of its children:

```bash
sou balance e:Food
sou balance a:Bank:Checking --from 07-01 --to 07-31
```

When a date boundary is supplied, Sou displays opening balance, period activity, and closing balance.

### Inspect an account ledger

```bash
sou ledger e:Food
sou ledger a:Bank:Checking --from 07-01 --to 07-31
```

The ledger displays matching postings and a running balance.

## Journal format

Sou journals are plain UTF-8 text and can be inspected or edited with any text editor:

```sou
[JOURNAL]

year: 2026

[ACCOUNTS]

Assets
  Bank
    Checking
Liabilities
Equity
  OpeningBalances
Income
Expenses
  Food

[TRANSACTIONS]

2026-07-27 Lunch
  Assets::Bank:Checking  -12.50
  Expenses::Food  12.50
```

Every transaction must have at least two postings whose amounts sum to zero.

## Current scope

- One year per journal
- One implicit currency
- Two-account transaction entry through `sou post`
- Hierarchical accounts with rolled-up balances
- Account balance and ledger queries

The underlying model supports transactions with more than two postings, but split-entry CLI automation is not implemented yet.

## Development

Clone the repository and run:

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

To use the working tree as your globally installed command:

```bash
uv tool install --editable .
```

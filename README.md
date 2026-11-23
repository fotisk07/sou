# Sou

**Your finances, in plain text.**

Sou is a command-line tool for personal double-entry accounting, inspired by [Beancount](https://github.com/beancount/beancount) and written in Rust 🦀.

Keep your financial journal in a single, human-readable file. Record transactions from the terminal or edit them in your favourite text editor. Track changes with Git. Generate financial statements from the same file whenever you need them, view them in the terminal or export them for safekeeping. 

[Why Sou?](#why-sou) · [Double-entry accounting](#why-double-entry-accounting) · [Installation](#installation) · [Quick start](#quick-start) · [Docs](#further-documentation)

## Why Sou?

Sou is for people who like simple setups, owning their data and understanding their work deeply. It is well suited to computer nerds with accounting-nerd tendencies. If that makes you cringe, then Sou is not for you. If you like that sort of thing, keep reading! You don't have to be an accountant or a computer expert.

What Sou gives you:
- **One file you control.** Plain text, Git-diffable, no proprietary database. Use the CLI, edit it in your editor or have your agent use the CLI.
- **Financial statements.** Organise your money like a business. View reports in the terminal or export them to PDF and other formats.
- **Local and offline.** One binary, no internet required. Your journal lives wherever you want.

Sou is not a budgeting app, has no graphical dashboard, and won't connect to your bank. Recording transactions is part of paying attention to my money, not just work to eliminate.

Want something outside that scope? Point your agent at the code and make it yours.

## Why double-entry accounting?

The history of accounting is a fascinating one, tracing back to ancient Mesopotamia. Humans have always tried to count things, particularly the things they cared about. In ancient Mesopotamia clay tokens were used to simply count how many of the thing we had. In Italy during the Renaissance however something incredible happened: We created **double-entry accounting**. 

Double-entry accounting has an elegant constraint: every transaction must balance. Instead of recording only an amount spent, you record where value came from and where it went.

- Buying lunch reduces your bank balance and increases a food expense.
- Moving money from your bank account to savings changes where you hold it; it isn't an expense.
- Taking out a loan increases your cash, but also what you owe. It isn't income.

A transaction can involve two accounts or several. The amounts across its postings must sum to zero. That constraint helps catch mistakes, though a balanced entry can still use the wrong accounts or amounts.

Sou applies this model to your personal finances. This README isn't an accounting course; for the foundations, see:

- [Beancount](https://beancount.github.io/), my inspiration. Beancount is much more complete than sou and has extensive documentation.
- [Plain Text Accounting](https://plaintextaccounting.org/), for introductions and resources about keeping accounts in text files.

## Installation

With Rust and Cargo installed, clone this repository, enter its directory, and run:

```sh
cargo install --path .
```

This installs `sou` in `~/.cargo/bin`. Make sure that directory is in your `PATH`.

## Quick start

### Create your journal

In the directory where you want to keep your finances:

```sh
sou init --author "Your name"
```

This creates `journal.sou` for the current year, using EUR by default. Use `--year` and `--currency` to choose something else. The author is optional.

### Create a few accounts

```sh
sou add Assets/Bank
sou add Equity/OpeningBalances
sou add Income/Salary
sou add Expenses/Food
sou add Expenses/Household
```

Account paths form a hierarchy: `Expenses/Food` is a child of `Expenses`.

### Record some transactions

Suppose you begin tracking with 1,000 in your bank account. Record that starting balance against equity, not income—you already had this money:

```sh
sou post 1000 Equity/OpeningBalances Assets/Bank Opening balance
```

Now record a salary payment and lunch:

```sh
sou post 2500 Income/Salary Assets/Bank Salary
sou post 10 Assets/Bank Expenses/Food Coffee and lunch
```

The basic form is `sou post AMOUNT FROM TO DESCRIPTION`.

For a purchase split between categories, use `split`. Its signed amounts must sum to zero:

```sh
sou split "Grocery run" Assets/Bank -50 Expenses/Food 40 Expenses/Household 10
```

### Look at the file

Open `journal.sou` in your editor. The lunch transaction looks like this, with its posting date (shown here as an example):

```text
2026-03-15 Coffee and lunch
  Assets/Bank  -10.00
  Expenses/Food  10.00
```

You can edit the journal directly, not just through Sou. After making changes, check it:

```sh
sou check
```

The file is plain text, so you can also version it with Git and review changes using `git diff`. Financial records are sensitive: keep your repository private. Git history is not encryption.

### See where you stand

```sh
sou list
sou ledger Assets/Bank --year
sou pnl --year
sou bs --year
```

- `list` shows your account tree.
- `ledger` shows an account's transactions and running balance.
- `pnl` shows income and expenses over a period.
- `bs` shows assets, liabilities, and equity at a point in time.

Export a report when you need to share it or work in a spreadsheet:

```sh
sou pnl --year --format xlsx > pnl.xlsx
```

That's the basic loop: record, inspect, adjust. Use `sou --help` or `sou <command> --help` to explore the commands.

## Further documentation

- [Usage guide](docs/usage.md): dates, reporting periods, exports, recurring postings, and shell completion.
- [Journal format](docs/journal-format.md): how to read and edit the file, with a complete example.


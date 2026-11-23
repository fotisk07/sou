# Sou

**Your finances, in plain text.**

Sou is a command-line tool for personal double-entry accounting, inspired by [Beancount](https://github.com/beancount/beancount) and written in Rust 🦀.

Keep your financial journal in a single, human-readable file. Record transactions from the terminal, edit them in your favourite text editor, or have your agent do it if you trust it with your data. Track changes with Git. Generate financial statements from the same file whenever you need them, view them in the terminal or export them for safekeeping. 

**Anti-pitch**
If you don't like using the terminal, or looking for automation, bank syncing and graphs sou is not for you.

[Why Sou?](#why-sou) · [Double-entry accounting](#why-double-entry-accounting) · [Installation](#installation) · [Quick start](#quick-start) · [Docs](#further-documentation)

## Why Sou?

What Sou gives you:
- **One local offline file** You can keep a year's worth of your financial life in one human readable file, offline. 
- **Financial statements.** Organise your money like a business. View reports in the terminal or export them to PDF and other formats.

Sou is not a budgeting app, has no graphical dashboard, and won't connect to your bank. The whole point is the offline bare bones CLI. If you prefer to see graphs, or use it like budget app you can build on it ! My gf did exactly that here :


## Why double-entry accounting?

As boring as it sounds, accounting goes hand in hard with human civilization. In ancient Mesopotamia they used clay tokens to count who owned and owed livestock. During the founding of modern capitalism in Italy, the need to handle more complex transactions gave birth to **double entry accounting**.  

Double-entry accounting has one main constraint: every transaction must balance. Instead of recording only an amount spent, you record where value came from and where it went.

- Buying lunch reduces your bank balance and increases a food expense.
- Moving money from your bank account to savings changes where you hold it; it isn't an expense.
- Taking out a loan increases your cash, but also what you owe. It isn't income.

Sou applies this model to your personal finances. Explaining accounting in detail is not the scope of this REAMDE, you can see :

- [Beancount](https://beancount.github.io/), my inspiration. Beancount is much more complete than sou and has extensive documentation.
- [Plain Text Accounting](https://plaintextaccounting.org/), for introductions and resources about keeping accounts in text files.

## Installation

On macOS or Linux, no Rust required:

```sh
curl --proto '=https' --tlsv1.2 -LsSf \
  https://github.com/fotisk07/sou/releases/latest/download/sou-installer.sh | sh
```

Or build from source with Rust installed, from the cloned repository:

```sh
cargo install --path .
```

Both install to `~/.cargo/bin` by default. Make sure it is in your `PATH`, then run `sou --version`.

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


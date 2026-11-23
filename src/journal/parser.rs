use crate::models::{
    Account, AccountAlias, Accounts, Journal, JournalMetadata, Posting, RecurringTransaction,
    Transaction,
};
use jiff::civil::Date;
use rust_decimal::Decimal;
use std::{collections::HashSet, str::FromStr};

#[derive(Debug)]
pub struct ParseError {
    pub line: Option<usize>,
    pub message: String,
}

impl ParseError {
    fn new(message: impl Into<String>) -> Self {
        Self {
            line: None,
            message: message.into(),
        }
    }

    fn at(line: usize, message: impl Into<String>) -> Self {
        Self {
            line: Some(line),
            message: message.into(),
        }
    }
}

pub fn parse_journal(journal_text: &str) -> Result<Journal, ParseError> {
    let (before_accounts, sections_text) = journal_text
        .split_once("[ACCOUNTS]")
        .ok_or_else(|| ParseError::new("missing [ACCOUNTS] section"))?;
    let (before_journal, metadata_text) = before_accounts
        .split_once("[JOURNAL]")
        .ok_or_else(|| ParseError::new("missing [JOURNAL] section"))?;
    let (before_transactions, transactions_text) = sections_text
        .split_once("[TRANSACTIONS]")
        .ok_or_else(|| ParseError::new("missing [TRANSACTIONS] section"))?;

    let metadata_line = before_journal.bytes().filter(|&byte| byte == b'\n').count() + 1;
    let accounts_line = before_accounts
        .bytes()
        .filter(|&byte| byte == b'\n')
        .count()
        + 1;
    let transactions_line = accounts_line
        + before_transactions
            .bytes()
            .filter(|&byte| byte == b'\n')
            .count();
    let (account_sections, recurring_text) = before_transactions
        .split_once("[RECURRING]")
        .unwrap_or((before_transactions, ""));
    let (accounts_text, aliases_text) = account_sections
        .split_once("[ALIASES]")
        .map_or((account_sections, None), |(accounts, aliases)| {
            (accounts, Some(aliases))
        });
    let accounts = parse_accounts(accounts_text, accounts_line)?;
    let aliases = if let Some(text) = aliases_text {
        let line = accounts_line + accounts_text.bytes().filter(|&byte| byte == b'\n').count();
        parse_aliases(text, line)?
    } else {
        Vec::new()
    };
    let recurring_line = accounts_line + account_sections.bytes().filter(|&b| b == b'\n').count();
    let transactions = parse_transactions(transactions_text, transactions_line)?;
    let recurring_transactions = parse_recurring(recurring_text, recurring_line)?;
    let metadata = parse_metadata(metadata_text, metadata_line)?;

    Ok(Journal {
        metadata,
        accounts,
        aliases,
        transactions,
        recurring_transactions,
    })
}

fn parse_accounts(accounts_text: &str, section_line: usize) -> Result<Accounts, ParseError> {
    let mut accounts = Accounts::new();
    let mut stack: Vec<String> = Vec::new();
    let mut declared = HashSet::new();

    for (index, line) in accounts_text.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let line_number = section_line + index;
        let indentation = line.len() - line.trim_start().len();
        if !indentation.is_multiple_of(2)
            || !line.as_bytes()[..indentation]
                .iter()
                .all(|&byte| byte == b' ')
        {
            return Err(ParseError::at(
                line_number,
                "account indentation must use two spaces per level",
            ));
        }
        let depth = indentation / 2;
        let name = line.trim().to_string();

        if depth > stack.len() {
            return Err(ParseError::at(line_number, "account is missing a parent"));
        }
        stack.truncate(depth);
        stack.push(name.clone());
        let path = stack.join("/");
        if !declared.insert(path.clone()) {
            return Err(ParseError::at(
                line_number,
                format!("duplicate account `{path}`"),
            ));
        }

        if depth == 0 {
            accounts.root_mut(&name).ok_or_else(|| {
                ParseError::at(line_number, format!("unknown root account `{name}`"))
            })?;
            continue;
        }

        let root_name = &stack[0];
        let mut parent = accounts.root_mut(root_name).ok_or_else(|| {
            ParseError::at(line_number, format!("unknown root account `{root_name}`"))
        })?;

        for parent_name in &stack[1..depth] {
            parent = parent
                .children
                .iter_mut()
                .find(|account| account.name == *parent_name)
                .ok_or_else(|| {
                    ParseError::at(
                        line_number,
                        format!("parent account `{parent_name}` not found"),
                    )
                })?;
        }

        parent.children.push(Account {
            name,
            children: vec![],
        });
    }
    Ok(accounts)
}

fn parse_aliases(text: &str, section_line: usize) -> Result<Vec<AccountAlias>, ParseError> {
    let mut aliases: Vec<AccountAlias> = Vec::new();
    for (index, line) in text.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let line_number = section_line + index;
        let (name, account) = line
            .split_once('=')
            .ok_or_else(|| ParseError::at(line_number, "expected ALIAS = ACCOUNT"))?;
        let (name, account) = (name.trim(), account.trim());
        aliases.push(AccountAlias {
            name: name.to_string(),
            account: account.to_string(),
        });
    }
    Ok(aliases)
}

fn parse_transactions(
    transactions_text: &str,
    section_line: usize,
) -> Result<Vec<Transaction>, ParseError> {
    let mut lines = transactions_text
        .lines()
        .enumerate()
        .filter(|(_, line)| !line.trim().is_empty())
        .peekable();

    let mut transactions: Vec<Transaction> = vec![];

    while let Some((index, header)) = lines.next() {
        let line_number = section_line + index;
        let (date_str, description) = header
            .split_once(char::is_whitespace)
            .ok_or_else(|| ParseError::at(line_number, "expected DATE DESCRIPTION"))?;

        let date: Date = date_str
            .parse()
            .map_err(|_| ParseError::at(line_number, format!("invalid date `{date_str}`")))?;

        let mut postings: Vec<Posting> = vec![];

        while lines.peek().is_some_and(|(_, line)| line.starts_with(' ')) {
            let (index, posting_line) = lines.next().unwrap(); // Safe: peek found a posting.
            postings.push(parse_posting(posting_line, section_line + index)?);
        }
        transactions.push(Transaction {
            date,
            description: description.to_string(),
            postings,
        });
    }
    Ok(transactions)
}

fn parse_posting(line: &str, line_number: usize) -> Result<Posting, ParseError> {
    let mut parts = line.split_whitespace();
    let account = parts
        .next()
        .ok_or_else(|| ParseError::at(line_number, "missing posting account"))?;
    let amount = parts
        .next()
        .ok_or_else(|| ParseError::at(line_number, "missing posting amount"))?;
    if parts.next().is_some() {
        return Err(ParseError::at(
            line_number,
            "unexpected text after posting amount",
        ));
    }
    let amount = Decimal::from_str(amount)
        .map_err(|_| ParseError::at(line_number, format!("invalid amount `{amount}`")))?;
    Ok(Posting {
        account: account.to_string(),
        amount,
    })
}

fn parse_recurring(
    text: &str,
    section_line: usize,
) -> Result<Vec<RecurringTransaction>, ParseError> {
    let mut lines = text
        .lines()
        .enumerate()
        .filter(|(_, line)| !line.trim().is_empty())
        .peekable();
    let mut templates = Vec::new();
    while let Some((index, header)) = lines.next() {
        let line_number = section_line + index;
        let (frequency, rest) = header
            .split_once(char::is_whitespace)
            .ok_or_else(|| ParseError::at(line_number, "expected FREQUENCY DATE DESCRIPTION"))?;
        let frequency = frequency
            .parse()
            .map_err(|error: String| ParseError::at(line_number, error))?;
        let (start, description) = rest
            .trim_start()
            .split_once(char::is_whitespace)
            .ok_or_else(|| ParseError::at(line_number, "expected FREQUENCY DATE DESCRIPTION"))?;
        let start_date = start.parse::<Date>().map_err(|_| {
            ParseError::at(
                line_number,
                format!("invalid recurring start date `{start}`"),
            )
        })?;
        let mut next_date = None;
        let mut postings = Vec::new();
        while lines.peek().is_some_and(|(_, line)| line.starts_with(' ')) {
            let (index, line) = lines.next().unwrap();
            let line_number = section_line + index;
            if let Some(value) = line.trim().strip_prefix("next:") {
                if next_date.is_some() {
                    return Err(ParseError::at(line_number, "duplicate recurring next date"));
                }
                next_date = Some(
                    value
                        .trim()
                        .parse::<Date>()
                        .map_err(|_| ParseError::at(line_number, "invalid recurring next date"))?,
                );
            } else {
                postings.push(parse_posting(line, line_number)?);
            }
        }
        templates.push(RecurringTransaction {
            frequency,
            start_date,
            next_date: next_date
                .ok_or_else(|| ParseError::at(line_number, "missing recurring next date"))?,
            description: description.to_string(),
            postings,
        });
    }
    Ok(templates)
}

fn parse_metadata(header_text: &str, section_line: usize) -> Result<JournalMetadata, ParseError> {
    let mut name: Option<String> = None;
    let mut author: Option<String> = None;
    let mut year: Option<i32> = None;
    let mut currency: Option<String> = None;
    for (index, line) in header_text.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        let line_number = section_line + index;
        let (key, value) = line
            .split_once(":")
            .ok_or_else(|| ParseError::at(line_number, "expected metadata KEY: VALUE"))?;
        let key = key.trim();
        let value = value.trim();

        match key {
            "name" => {
                if name.is_some() {
                    return Err(ParseError::at(line_number, "Duplicate key metadata"));
                }
                if value.is_empty() {
                    return Err(ParseError::at(line_number, "No values"));
                }
                name = Some(value.to_string());
            }
            "author" => {
                if author.is_some() {
                    return Err(ParseError::at(line_number, "Duplicate key metadata"));
                }
                if value
                    .chars()
                    .any(|c| c.is_control() || matches!(c, '[' | ']'))
                {
                    return Err(ParseError::at(
                        line_number,
                        "author must contain no control characters or brackets",
                    ));
                }
                author = Some(value.to_string());
            }
            "year" => {
                if year.is_some() {
                    return Err(ParseError::at(line_number, "Duplicate key metadata"));
                }
                let parsed_year = value
                    .parse::<i32>()
                    .map_err(|_| ParseError::at(line_number, "year must be an integer"))?;
                if !(1..=9999).contains(&parsed_year) {
                    return Err(ParseError::at(
                        line_number,
                        "year must be between 1 and 9999",
                    ));
                }
                year = Some(parsed_year);
            }
            "currency" => {
                if currency.is_some() {
                    return Err(ParseError::at(line_number, "Duplicate key metadata"));
                }
                if value.len() != 3 || !value.bytes().all(|byte| byte.is_ascii_uppercase()) {
                    return Err(ParseError::at(
                        line_number,
                        "currency must be three uppercase ASCII letters",
                    ));
                }
                currency = Some(value.to_string());
            }
            _ => {
                return Err(ParseError::at(
                    line_number,
                    format!("unknown metadata field `{key}`"),
                ));
            }
        }
    }
    let author = author.ok_or_else(|| {
        ParseError::new("missing metadata field `author`; add `author:` (a name is optional)")
    })?;
    Ok(JournalMetadata {
        name: name.ok_or_else(|| ParseError::new("missing metadata field `name`"))?,
        author: (!author.is_empty()).then_some(author),
        year: year.ok_or_else(|| ParseError::new("missing metadata field `year`"))?,
        currency: currency.ok_or_else(|| ParseError::new("missing metadata field `currency`"))?,
    })
}

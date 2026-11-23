mod parser;
mod write;

pub(crate) use parser::parse_journal;
pub use write::{create_journal, write_journal};

use crate::{
    models::Journal,
    validation::{validate_journal, validate_metadata},
};
use std::fs;

pub fn load_journal(path: &str) -> Result<Journal, String> {
    let contents =
        fs::read_to_string(path).map_err(|error| format!("cannot read {path}: {error}"))?;

    let journal = parse_journal(&contents).map_err(|error| match error.line {
        Some(line) => format!("parse error (line {line}): {}", error.message),
        None => format!("parse error: {}", error.message),
    })?;

    validate_metadata(&journal.metadata).map_err(|error| format!("validation error: {error}"))?;
    validate_journal(&journal).map_err(|error| format!("validation error: {error}"))?;

    Ok(journal)
}

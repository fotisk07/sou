use std::process::Command;

fn journal_file() -> (tempfile::TempDir, std::path::PathBuf) {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("journal.sou");
    std::fs::write(
        &path,
        "[JOURNAL]
name: Test
author:
year: 2024
currency: EUR
[ACCOUNTS]
Assets
  Bank
Expenses
  Food
[ALIASES]
bank = Assets/Bank
food = Expenses/Food
[TRANSACTIONS]
",
    )
    .unwrap();
    (directory, path)
}

fn assert_invalid_journal(path: &std::path::Path, contents: &str, expected_error: &str) {
    std::fs::write(path, contents).unwrap();
    for args in [&["check"][..], &["sort"][..], &["bs", "--year"][..]] {
        let output = Command::new(env!("CARGO_BIN_EXE_sou"))
            .arg("-j")
            .arg(path)
            .args(args)
            .output()
            .unwrap();
        assert!(
            !output.status.success(),
            "{args:?} accepted invalid journal"
        );
        let error = String::from_utf8_lossy(&output.stderr);
        assert!(error.contains(expected_error), "{args:?}: {error}");
        assert_eq!(std::fs::read_to_string(path).unwrap(), contents);
    }
}

#[test]
fn duplicate_account_declarations_are_rejected() {
    let (_directory, path) = journal_file();
    let contents = std::fs::read_to_string(&path).unwrap();
    for (original, replacement, duplicate) in [
        ("Assets\n", "Assets\nAssets\n", "Assets"),
        ("  Bank\n", "  Bank\n  Bank\n", "Assets/Bank"),
        ("  Bank\n", "  Bank\n  Savings\n  Bank\n", "Assets/Bank"),
        (
            "  Bank\n",
            "  Bank\n    Checking\n    Checking\n",
            "Assets/Bank/Checking",
        ),
        (
            "Assets\n  Bank\n",
            "Assets\n  Bank\nAssets\n  Savings\n",
            "Assets",
        ),
    ] {
        assert_invalid_journal(
            &path,
            &contents.replace(original, replacement),
            &format!("duplicate account `{duplicate}`"),
        );
    }
}

#[test]
fn account_indentation_requires_pairs_of_spaces_and_existing_parents() {
    let (_directory, path) = journal_file();
    let contents = std::fs::read_to_string(&path).unwrap();
    for indentation in [" ", "   ", "\t", " \t", "\u{a0}\u{a0}"] {
        assert_invalid_journal(
            &path,
            &contents.replace("  Bank", &format!("{indentation}Bank")),
            "account indentation must use two spaces per level",
        );
    }
    assert_invalid_journal(
        &path,
        &contents.replace("  Bank", "    Bank"),
        "account is missing a parent",
    );
}

#[test]
fn account_names_can_repeat_under_different_parents() {
    let (_directory, path) = journal_file();
    let contents = std::fs::read_to_string(&path)
        .unwrap()
        .replace("  Bank\n", "  Bank\n    Bank\n")
        .replace("  Food\n", "  Food\n  Bank\n");
    std::fs::write(&path, contents).unwrap();
    for args in [&["check"][..], &["sort"][..], &["check"][..]] {
        let output = Command::new(env!("CARGO_BIN_EXE_sou"))
            .arg("-j")
            .arg(&path)
            .args(args)
            .output()
            .unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
    }
}

#[test]
fn loaded_metadata_uses_the_same_name_validation_as_init() {
    let (_directory, path) = journal_file();
    let contents = std::fs::read_to_string(&path).unwrap();
    for name in [
        "[Example]",
        "[RECURRING]",
        "Example\tjournal",
        "Example\u{1b}journal",
    ] {
        assert_invalid_journal(
            &path,
            &contents.replace("name: Test", &format!("name: {name}")),
            "journal name must be nonempty and contain no control characters or brackets",
        );
        let output = Command::new(env!("CARGO_BIN_EXE_sou"))
            .arg("-j")
            .arg(path.with_file_name("invalid-init.sou"))
            .args(["init", "--name", name])
            .output()
            .unwrap();
        assert!(!output.status.success());
        assert!(!path.with_file_name("invalid-init.sou").exists());
    }
}

#[test]
fn posting_saves_exact_transfers_and_rejects_fractional_cents_without_writing() {
    let (_directory, path) = journal_file();
    let post = |amount| {
        Command::new(env!("CARGO_BIN_EXE_sou"))
            .arg("-j")
            .arg(&path)
            .args(["post", amount, "bank", "food", "Meal", "--date", "29-02"])
            .output()
            .unwrap()
    };
    for amount in ["12.34", "-2.34"] {
        let output = post(amount);
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
    }
    let contents = std::fs::read_to_string(&path).unwrap();
    assert!(contents.contains("2024-02-29 Meal\n  Assets/Bank  -12.34\n  Expenses/Food  12.34"));
    assert!(contents.contains("2024-02-29 Meal\n  Assets/Bank  2.34\n  Expenses/Food  -2.34"));

    let output = post("12.345");
    assert!(!output.status.success());
    assert!(String::from_utf8_lossy(&output.stderr).contains("two decimal places"));
    assert_eq!(std::fs::read_to_string(&path).unwrap(), contents);
}

#[test]
fn ledger_alias_matches_canonical_account_report() {
    let (_directory, path) = journal_file();
    let run = |args: &[&str]| {
        let output = Command::new(env!("CARGO_BIN_EXE_sou"))
            .arg("-j")
            .arg(&path)
            .args(args)
            .output()
            .unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        String::from_utf8(output.stdout).unwrap()
    };
    run(&[
        "post",
        "12.34",
        "Assets/Bank",
        "Expenses/Food",
        "Meal",
        "--date",
        "29-02",
    ]);
    let report = run(&["ledger", "bank", "--year"]);
    assert_eq!(report, run(&["ledger", "Assets/Bank", "--year"]));
    assert!(report.starts_with("Ledger | Assets/Bank |"));
    assert!(report.contains("Meal"));
}

#[test]
fn invalid_splits_fail_without_changing_the_journal() {
    let (_directory, path) = journal_file();
    let contents = std::fs::read_to_string(&path).unwrap();

    for (postings, expected_error) in [
        (
            ["Assets/Bank", "-10", "Expenses/Food", "9.99"],
            "unbalanced",
        ),
        (
            ["Assets/Bank", "-10", "Expenses/Missing", "10"],
            "unknown account",
        ),
    ] {
        let output = Command::new(env!("CARGO_BIN_EXE_sou"))
            .arg("-j")
            .arg(&path)
            .args(["split", "Meal"])
            .args(postings)
            .args(["--date", "29-02"])
            .output()
            .unwrap();

        assert!(!output.status.success());
        let error = String::from_utf8_lossy(&output.stderr);
        assert!(error.contains(expected_error), "{error}");
        assert_eq!(std::fs::read_to_string(&path).unwrap(), contents);
    }
}

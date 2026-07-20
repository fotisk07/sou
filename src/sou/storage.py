from pathlib import Path

from sou.models import Journal
from sou.parser import parse_sou
from sou.renderer import render_sou


def load_journal(path: Path) -> Journal:
    """Read and parse a Journal from a Sou file."""
    source = path.read_text(encoding="utf-8")
    return parse_sou(source)


def save_journal(path: Path, journal: Journal) -> None:
    """Render and atomically replace an existing Sou file."""
    source = render_sou(journal)
    temporary_path = path.with_name(f".{path.name}.tmp")

    try:
        temporary_path.write_text(source, encoding="utf-8")
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def init_journal(path: Path, year: int) -> None:
    """Create a new, empty Sou journal without overwriting an existing file."""
    journal = Journal(year=year, accounts=set(), transactions=[])
    source = render_sou(journal)

    with path.open("x", encoding="utf-8") as file:
        file.write(source)

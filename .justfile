# Run all tests, or choose: fast, last, or debug.

test:
  uv run pytest

test-last:
  uv run pytest --lf

# Format the code and check it with Ruff.
format-check:
  uv run ruff format .
  uv run ruff check .

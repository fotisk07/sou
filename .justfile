# Run all tests, or choose: fast, last, or debug.

just test-debug
  uv run pytest --pdb -x

just test-last
  uv run pytest --lf


# Format the code and check it with Ruff.
format-check:
  uv run ruff format .
  uv run ruff check .

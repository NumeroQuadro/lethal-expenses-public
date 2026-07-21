# Lethal Expenses parser

The Python package discovers local PDF statements, selects a bank-specific parser, normalizes transactions into a shared schema, deduplicates overlapping exports, detects transfers, applies categories, and writes deterministic JSON for the dashboard.

## Install

From the repository root:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e 'parser[dev]'
```

## Use

```bash
mkdir -p parser/pdfs
# Add your own statement PDFs under parser/pdfs/
.venv/bin/lethal-expenses build --verbose
.venv/bin/lethal-expenses inspect parser/data/transactions.json
```

Both input statements and generated output are ignored by Git. The PDFs under `tests/fixtures/` are synthetic regression fixtures and are safe to publish.

## Test

```bash
cd parser
../.venv/bin/ruff check tests src
../.venv/bin/pyright
../.venv/bin/pytest
```

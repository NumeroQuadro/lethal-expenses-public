# Lethal Expenses

[![CI](https://github.com/NumeroQuadro/lethal-expenses-public/actions/workflows/ci.yml/badge.svg)](https://github.com/NumeroQuadro/lethal-expenses-public/actions/workflows/ci.yml)

A privacy-first expense dashboard that turns local PDF bank statements into a normalized, searchable static website.

PDFs are parsed on your machine, the resulting transaction data is embedded at build time, and the finished dashboard has no backend or runtime data API. Personal statements and generated transaction files are deliberately excluded from version control.

## Features

- Parsers for Sberbank, Ozon Bank, Yandex Bank, and Bank Saint Petersburg statements
- One normalized schema across cards, savings accounts, and deposits
- Deterministic deduplication for overlapping monthly statements
- Self-transfer detection and merchant categorization
- React dashboard with filtering, summaries, category breakdowns, and analytics
- Fully static production build with self-hosted fonts
- Parser unit/property tests, frontend component tests, and Playwright smoke tests

## How it works

```text
Local statement PDFs
        │
        ▼
Python parser ──► normalized transactions.json
                              │
                              ▼
                    React/Vite static build
                              │
                              ▼
                     Browser or static host
```

The parser and dashboard are separate stages by design. The browser never receives the source PDFs, and the deployed site does not need a database.

## Quick start

Prerequisites: Python 3.12+ and Node.js 24+.

1. Create a virtual environment and install the parser:

   ```bash
   python3.12 -m venv .venv
   .venv/bin/python -m pip install -e 'parser[dev]'
   ```

2. Put your statement PDFs under `parser/pdfs/`. Subdirectories are supported; directories whose names begin with `_` are skipped.

3. Parse the statements:

   ```bash
   .venv/bin/lethal-expenses build --verbose
   ```

4. Build or run the dashboard:

   ```bash
   cd web
   npm ci
   npm run dev
   ```

The Vite hook copies `parser/data/transactions.json` into the web application before development and production builds.

## Safe demo

The committed parser fixtures and frontend demo transactions are synthetic. You can build a public demo without using any personal statements:

```bash
make prepare-web-test-data
cd web
npm ci
npm run build
```

## Verification

```bash
make parser-ci
make web-ci
```

The CI workflow runs formatting and type checks, the parser test suite with coverage enforcement, frontend component tests, a production build, and Playwright browser tests.

## Repository layout

```text
parser/src/             Python parser and normalization pipeline
parser/tests/           unit tests and synthetic PDF fixtures
web/src/                React dashboard
web/tests/              component and data tests
web/e2e/                browser smoke tests
docs/adr/               architecture decision records
deploy/                 optional nginx deployment tooling
```

## Privacy and security

- `parser/pdfs/`, generated JSON, local account overrides, environment files, and credentials are ignored.
- Treat a built dashboard as sensitive: it contains the normalized transactions supplied at build time.
- Review generated data before deployment and use access controls if the output contains real finances.
- See [SECURITY.md](SECURITY.md) for vulnerability reporting.

This public edition contains source code, documentation, and synthetic fixtures only. It intentionally excludes real statements, generated financial data, deployment state, and private project-management files.

More detail is available in [BUILD.md](BUILD.md) and the [architecture decision records](docs/adr/).

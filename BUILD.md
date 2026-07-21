# Build Pipeline

`Lethal Expenses` ships as a static site. The parser runs locally against PDFs, the web app imports the generated JSON at build time, and the final artifact is a tarball of `web/dist/` ready for nginx or any other static file host.

## Prerequisites

- Python 3.12 with the parser CLI installed locally: `python -m pip install -e parser[dev]`
- Node 24+
- Local bank statement PDFs under `parser/pdfs/` (kept out of git by `.gitignore`)

## Commands

- `make data`
  - Verifies that `parser/pdfs/` exists and contains at least one PDF.
  - Runs `lethal-expenses build` to refresh `parser/data/transactions.json`.
- `make web`
  - Runs `npm ci` inside `web/`.
  - Runs the production web build, which copies `parser/data/transactions.json` into `web/src/data/transactions.json` during `prebuild`.
- `make dist`
  - Runs `make data` and `make web`.
  - Packages the static output into `dist/lethal-expenses-<git-sha>.tar.gz`.
- `make clean`
  - Removes `web/dist/`, `parser/data/`, and `dist/`.

## Production Defaults

- Production builds are minified.
- Source maps are disabled by default.
- To opt in to source maps for debugging, run `VITE_SOURCEMAPS=1 make web` or `VITE_SOURCEMAPS=1 make dist`.

## Artifact Verification

Inspect the packaged files:

```bash
tar tzf dist/*.tar.gz | grep -E '\.(js|css|html|woff2|json)$'
```

Serve the built site locally:

```bash
cd web/dist
python -m http.server 4173
```

Because data is imported at build time and fonts are self-hosted, the app renders as a fully static site and does not require outbound network requests at runtime.

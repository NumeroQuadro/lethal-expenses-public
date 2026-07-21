# Lethal Expenses dashboard

The React/Vite frontend imports normalized transaction JSON at build time and produces a fully static expense dashboard. It does not fetch transaction data from a backend at runtime.

## Development

First generate `parser/data/transactions.json` with the parser, or prepare the committed synthetic demo data from the repository root:

```bash
make prepare-web-test-data
```

Then:

```bash
cd web
npm ci
npm run dev
```

## Verification

```bash
npm run lint
npm run test
npm run build
npx playwright install chromium
npm run test:e2e
```

The generated `src/data/transactions.json`, production build, and Playwright reports are ignored because they may contain private financial information or generated artifacts.

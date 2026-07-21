# ADR-0009 — External Account Scope For Relay-Only Statements

Status: Accepted

## Context

The refreshed active dataset now includes statements for an account that does not belong to the primary dashboard user, but is still useful for transfer pairing. Real relay flows between the user's own Sber accounts and this external-owned account should pair normally, yet counting the external account's debit rows as the user's spending materially breaks the product's single-user expense model.

## Decision

Extend the canonical transaction schema with `is_external_account: bool = False` and allow a local ownership-scope config at `parser/external_accounts.yaml`.

- The parser build step loads that config when present and marks matching `(bank, account)` rows with `is_external_account=True` before transfer deduplication.
- External-account rows remain in `transactions.json` and remain fully eligible for Pass A, Pass B, and Pass C transfer handling.
- Default expense reporting in both the CLI inspect output and the web dashboard excludes rows marked `is_external_account=True`, regardless of the transfer-visibility toggle.

## Consequences

- Relay or third-party accounts can stay in the dataset for pairing and audit without contaminating the primary user's expense totals.
- Account ownership scope becomes an explicit part of the parser-to-web contract.
- Older fixtures and schema snapshots must evolve to carry the new field, usually with the default value `false`.

## Trade-Offs

- The dashboard now distinguishes between transaction type (`is_transfer`) and account ownership scope (`is_external_account`).
- A local config file adds one more operator-managed input, but keeping it gitignored avoids committing personal ownership decisions.

## Implementation Notes

- The local config uses masked logical account identities in `(bank, account)` form, for example `sberbank` + `****4000`.
- Missing config is valid and preserves previous behavior.
- Optional UI affordances for revealing external-account rows can be added later without changing the default privacy and scoping behavior.

## Alternatives Considered

- Drop external-owned statements entirely: rejected because that would lose useful counterpart rows for transfer pairing.
- Hardcode excluded accounts in source code: rejected because ownership scope is user-local data.
- Apply the filter only in the web app: rejected because CLI inspect should use the same default expense semantics.

## Links To Relevant Code

- `parser/src/lethal_expenses/schema.py`
- `parser/src/lethal_expenses/cli.py`
- `web/src/lib/expenses.ts`
- `web/src/types/transaction.ts`
- `parser/tests/test_cli.py`
- `web/tests/expenses.test.ts`

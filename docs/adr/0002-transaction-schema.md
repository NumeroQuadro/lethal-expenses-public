# ADR-0002 — Transaction Schema And ID Strategy

Status: Accepted

## Context

All bank-specific parsers must emit one canonical transaction contract so downstream normalization and the web app can operate against a stable interface.

## Decision

Use a shared Pydantic v2 `Transaction` schema as the single contract between the parser package and the web app.

The contract fields are:

- `id` — deterministic transaction identifier.
- `date` — aware Moscow-local datetime.
- `amount` — negative for expenses, positive for income.
- `currency` — fixed to `RUB` in v1.
- `merchant_raw` — cleaned merchant or counterparty label as parsed.
- `description` — full source description.
- `bank` — one of `sberbank`, `yandex`, `ozon`, `spb`.
- `account` — masked last-four suffix in the form `****1234`, or `ЭДС` for Yandex electronic wallet rows that do not carry a card suffix.
- `category` — normalized category, defaulting to `Прочее` before rule assignment.
- `is_transfer` — boolean transfer flag, default `False` before dedup.
- `is_external_account` — boolean ownership-scope flag, default `False`, used to exclude external-owned relay accounts from default expense reporting while preserving them for pairing.
- `transfer_pair_id` — shared transfer identifier when dedup matches both sides.
- `raw` — bank-native parsed row payload for debugging and reconciliation.

Parser IDs should remain deterministic and be built from a bank prefix, account suffix, Moscow-local timestamp, and stable row-specific tokens such as an authorization code plus enough extra entropy to avoid same-statement collisions.

## Consequences

- The web app can treat `transactions.json` as a stable source-of-truth contract.
- Parser-specific quirks stay isolated in `raw` instead of leaking into downstream code.
- Schema changes are high-impact and must be reconciled in docs, tests, and parser implementations.

## Implementation Notes

- The schema forbids extra fields so accidental contract drift fails fast.
- Datetimes are normalized to the `Europe/Moscow` timezone.
- `account` is stored masked for safer debugging while preserving a deterministic suffix, except for Yandex `ЭДС` rows where the source statement has no card suffix.
- Shared parsing helpers live in `BaseParser` for amount parsing, RU date parsing, merchant cleanup, and ID construction.
- The build pipeline may collapse duplicate logical rows before normalization when they share the same deterministic ID and canonical transaction fields, preferring the shorter description when one source carries extra page noise.
- If duplicate IDs still survive duplicate collapse, the build pipeline deterministically appends a stable content-based suffix only to the colliding rows so the final JSON stays unique-ID clean without perturbing unaffected rows.

## Alternatives Considered

- Per-bank ad hoc dictionaries: rejected because they make normalization brittle.
- Frontend-specific reshaping only: rejected because it couples ingestion to presentation.
- Storing full account numbers: rejected because the web app only needs stable masked suffixes in v1.

## Links To Relevant Code

- `parser/src/lethal_expenses/schema.py`
- `parser/src/lethal_expenses/parsers/base.py`
- `parser/src/lethal_expenses/registry.py`
- `parser/tests/test_schema.py`

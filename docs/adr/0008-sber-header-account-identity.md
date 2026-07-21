# ADR-0008 — Sber Account Identity From Statement Header

Status: Accepted

## Context

Newer Sber statement families expose one payment account in the statement header while individual transaction descriptions may mention multiple masked card suffixes. Real examples include `Выписка по платёжному счёту` files where the header account is `****6000` or `****4000`, while row descriptions mention linked cards such as `****7000` or `****5000`, plus third-party card suffixes inside transfer text. The previous implicit row-first behavior was inherited from older fixtures where one statement effectively contained one card suffix, so the ambiguity stayed hidden.

## Decision

Treat the Sber statement header as the authoritative logical account identity for every Sber parser family.

- `Transaction.account` for Sber rows is always derived from the statement header `Номер счёта ...`.
- Masked card suffixes mentioned inside row descriptions are preserved for audit only under `raw["card_suffix"]` and `raw["card_suffixes"]`.
- Row-level suffixes do not override the statement identity and are not used for self-transfer pairing.

This supersedes the implicit row-first identity assumption inherited from ADR-0002 for Sber statements.

## Consequences

- Sber rows from one statement stay on one logical account even when the statement references multiple linked cards.
- Self-transfer pairing becomes more accurate for Sber payment-account statements because relay rows no longer fragment across `7000`, `5000`, `7875`, and other embedded suffixes.
- Historical synthetic fixtures that previously surfaced row-derived Sber accounts must now assert header-first identity instead.

## Trade-Offs

- The web UI no longer treats embedded Sber card suffixes as separate logical accounts.
- Analysts who need row-level card provenance must inspect `raw` rather than `account`.

## Implementation Notes

- `SberbankCardParser`, `SberbankSavingsParser`, and `SberbankDepositParser` extract the last four digits from the statement header before processing rows.
- Dash-description card rows such as `01.08.2023 565367 -` are still emitted as real transactions; they simply carry an empty normalized description.
- Repeated page headers and QR instruction lines are treated as parser noise for the refreshed `Выписка по платёжному счёту` family.

## Alternatives Considered

- Keep row-first identity: rejected because one statement can mention several different card suffixes that belong to linked cards or counterparties.
- Add a bank-specific merge pass after parsing: rejected because header-first identity is simpler and aligns the parser with the statement scope directly.

## Links To Relevant Code

- `parser/src/lethal_expenses/parsers/sberbank.py`
- `parser/tests/test_sberbank.py`
- `parser/tests/conftest.py`

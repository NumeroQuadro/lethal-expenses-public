# ADR-0006 — Two-Pass Self-Transfer Dedup With Date-Only Fallback

Status: Superseded by ADR-0007

## Context

The parser now supports statement families that expose different timestamp precision levels. Card-family statements usually provide minute-level timestamps, while savings and ledger-style statements may only expose a calendar date. The timed-only transfer heuristic from ADR-0003 misses legitimate self-transfers when one side is date-only. Real datasets also include same-bank relay flows across different own accounts, such as Sber internal transfers between `****2000`, `****7000`, and `****1000`, and Ozon internal relays between savings `****0950` and card `****0784`.

## Decision

Use a two-pass self-transfer dedupe algorithm.

- Pass A handles timed-to-timed matching only. Both sides must have `precision != "date"`, the absolute amounts must match exactly, the rows must belong to different logical accounts `(<bank>, <account>)`, the descriptions must look transfer-like, and the timestamps must be within thirty minutes. Smallest time delta still wins.
- Pass B runs on the remaining unmatched rows and considers only transactions whose `precision == "date"`. A date-only row may pair with an opposite-sign row from a different logical account `(<bank>, <account>)` when the absolute amounts match, at least one description matches the transfer-indicator regex set, and both rows fall on the same Moscow-local calendar day.
- When Pass B finds exactly one candidate, it pairs the rows.
- When Pass B finds multiple candidates, it prefers a candidate whose `precision == "date"`. If that still leaves more than one candidate, the row stays unmatched and the normalizer writes a warning log instead of guessing.

## Consequences

- Date-only savings statements become eligible for transfer pairing without weakening the minute-level matcher for timed statements.
- Same-bank relays across different own accounts become eligible for pairing, which better reflects the user's real transfer topology.
- Same-account opposite-sign rows remain ineligible, which avoids collapsing refund-like activity on one logical account into a transfer pair.
- Ambiguous date-only situations fail safe: they are logged and left unmatched instead of risking a false positive collapse.
- The schema contract must preserve timestamp precision explicitly so downstream normalization can distinguish minute-level and date-only rows.

## Implementation Notes

- `Transaction.precision` is part of the canonical schema and uses `second`, `minute`, or `date`.
- Parsers must set `precision` explicitly according to the precision actually exposed by the source statement family.
- Date-only matching uses Moscow-local calendar days, not UTC dates.
- Transfer eligibility remains structural only: precision, logical account identity `(bank, account)`, amount, calendar day, and the transfer-indicator regex. Description fuzzy-matching is intentionally out of scope.

## Alternatives Considered

- Expanding the thirty-minute window globally: rejected because it would over-match unrelated timed transactions.
- Fuzzy description similarity for date-only rows: rejected because it adds brittle semantics to MVP dedupe.
- Leaving date-only rows unmatched: rejected because it materially understates transfer detection for savings statements.

## Links To Relevant Code

- `parser/src/lethal_expenses/schema.py`
- `parser/src/lethal_expenses/normalize.py`
- `parser/src/lethal_expenses/parsers/`
- `parser/tests/test_normalize.py`
- `web/src/types/transaction.ts`

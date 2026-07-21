# ADR-0003 — Self-Transfer Detection Heuristic

Status: Superseded by ADR-0006

## Context

The product must exclude transfers between the user's own accounts from displayed expense totals, even when banks export them as ordinary debit and credit rows.

## Decision

The original heuristic matched opposite-sign transactions with the same absolute amount within a thirty-minute window across different banks owned by the user, as long as at least one side's description contained a transfer indicator such as `Перевод`, `СБП`, `carta`, `перенос`, or `собственных`.

This ADR is superseded because date-only statement families need a fallback path that does not rely on minute-level timestamps.

## Consequences

- The original timed-only rule remains useful as the first-pass matcher for statements with real time precision.
- Date-only statement families require a second-pass fallback, documented in ADR-0006.

## Implementation Notes

- See ADR-0006 for the current accepted implementation details.

## Alternatives Considered

- No transfer detection: rejected because totals would overstate expenses.
- Exact statement labels only: rejected because wording varies across banks.

## Links To Relevant Code

- `parser/src/lethal_expenses/normalize.py`
- `parser/tests/test_normalize.py`
- `docs/adr/0006-two-pass-self-transfer-dedup.md`

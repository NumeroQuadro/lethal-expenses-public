# ADR-0011 — Same-Account Reversal Pairing For Cancelled Transfers

Status: Accepted

## Context

Some statement families, notably the active Ozon card statement, emit cancelled transfer attempts as a same-account debit row plus a same-account credit reversal row marked with `Отмена перевода`. The existing transfer normalizer from ADR-0007 only pairs opposite-sign rows across different logical accounts, so these cancellation pairs stay visible as expenses even though the statement already proves they net to zero.

## Decision

Keep Pass A, Pass B, and Pass C from ADR-0007 unchanged, then add a fourth stage.

- Pass D runs after Pass C and only considers remaining timed rows.
- A Pass D pair requires the same logical account `(bank, account)`, equal absolute amounts, opposite signs, and timestamps within five minutes.
- Pass D also requires a linkage signal: either both descriptions share the same transfer token (for example `AD...`, `BD...`, `A610...`, `B610...`) or at least one description explicitly contains `Отмена перевода`.
- When matched, both rows remain in the normalized dataset and are marked `is_transfer=True` with a shared `transfer_pair_id`.
- Pass D does not rewrite raw descriptions or amounts; it only changes transfer metadata.

## Consequences

- Cancelled same-account transfer attempts stop contaminating expense totals while remaining auditable in the dataset.
- Same-account debit/credit rows without a strong cancellation linkage remain untouched, which limits false positives for unrelated refunds.
- Downstream consumers continue to rely on the same `is_transfer` / `transfer_pair_id` contract instead of learning a new exclusion field.

## Trade-Offs

- Pass D is intentionally narrow and may leave some real cancellation patterns unmatched if the bank omits both a reversal marker and a reusable transfer token.
- Ozon parser quirks can still affect the exact description text that reaches Pass D, so parser row-boundary handling remains part of correctness.

## Alternatives Considered

- Exclude all `Отмена перевода` debits by description only: rejected because some rows carry the marker due to parser bleed and because a literal marker alone is not always proof of a completed reversal pair.
- Reclassify reversal rows through categorization only: rejected because the web app excludes expenses by `is_transfer`, not by category label.
- Introduce a separate `is_cancelled` field: rejected for now because the existing transfer metadata is sufficient for v1 reporting.

## Links To Relevant Code

- `parser/src/lethal_expenses/normalize.py`
- `parser/src/lethal_expenses/parsers/ozon.py`
- `parser/tests/test_normalize.py`
- `parser/tests/test_ozon.py`

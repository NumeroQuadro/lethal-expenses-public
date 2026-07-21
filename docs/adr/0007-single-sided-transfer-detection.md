# ADR-0007 — Single-Sided Transfer Detection By Description Structure

Status: Accepted

## Context

The real active dataset may omit some counterpart bank statements for the user's own accounts. In that situation, the two-pass matcher from ADR-0006 can only mark transfers when both sides are present in the dataset. This leaves clearly internal Sber relay rows counted as expenses even when the source description itself already proves the row is an internal account transfer.

## Decision

Keep the existing structural pair matcher from ADR-0006 as the first two stages, then add a third fallback stage.

- Pass A still pairs timed rows when absolute amounts match, timestamps are within thirty minutes, logical accounts differ, and at least one side matches the transfer-indicator regex.
- Pass B still pairs remaining date-only rows on the same Moscow-local calendar day under the same logical-account and transfer-indicator rules.
- Pass C runs on the remaining unmatched rows only and applies a high-confidence single-sided transfer regex. Rows that match Pass C are marked `is_transfer=True` and keep `transfer_pair_id=None`.

The high-confidence single-sided shapes are currently:

- Sber savings ledger rows like `Списание|Пополнение|Зачисление ... к/с ...` that explicitly reference an internal account number.
- Sber card relay descriptions `SBERBANK ONL@IN VKLAD-KARTA` and `SBERBANK ONL@IN KARTA-VKLAD`.
- Sber card relay description `MAPP_SBERBANK_ONL@IN_PAY`.

Zero-amount rows such as account-opening lines or zero-interest capitalization rows are not tagged by Pass C.

## Consequences

- Expense totals stay closer to reality even when the user has not loaded every counterpart Sber statement.
- Explicit two-sided transfer pairs remain preferred whenever both statements are present.
- Some transfer rows become single-sided markers rather than full pairs, which means downstream consumers must tolerate `is_transfer=True` with `transfer_pair_id=None`.

## Trade-Offs

- Pass C intentionally relies on a narrow allowlist of shapes to avoid false positives.
- Pass C does not reconstruct the missing counterpart; it only removes a guaranteed internal-transfer row from expense totals.

## Alternatives Considered

- Require explicit counterparts only: rejected because missing statements would keep obviously internal rows in expenses.
- Broaden pair matching heuristics further without single-sided tagging: rejected because absent counterpart data is a completeness problem, not just a matching-window problem.

## Links To Relevant Code

- `parser/src/lethal_expenses/normalize.py`
- `parser/tests/test_normalize.py`
- `parser/src/lethal_expenses/cli.py`

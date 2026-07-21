# ADR-0010 — Deterministic Category Fallbacks With Bank Labels

Status: Superseded by ADR-0012

## Context

Pure regex matching over `merchant_raw + description` leaves a meaningful residue of low-information rows in `Прочее`, especially Sber card rows whose merchant is empty, `-`, or generic `SBOL.` while the statement already provides a high-signal bank-native category label in `raw["category_label"]`.

## Decision

The original accepted decision kept categorization fully local and deterministic, while extending the allowed input surface.

- Category assignment is a pure deterministic function over `merchant_raw + description + raw["category_label"]`.
- Ordered regex rules over `merchant_raw + description` remain the primary classifier.
- A committed fallback map may use `raw["category_label"]` only after regex rules fail, and only for narrow low-information Sber merchant shapes such as empty merchants, dash merchants, or `SBOL`-like merchants. This gate is now superseded by ADR-0012.
- No external categorization APIs or ML models are allowed.

## Consequences

- Categorization stays explainable and reproducible.
- Weak Sber merchants can resolve to useful categories without expanding regexes into brittle bank-specific guesses.
- The contract now explicitly allows bank-native labels as a fallback signal, so docs and tests must encode that behavior.

## Trade-Offs

- Categorization is no longer strictly regex-only over free-text fields.
- The fallback map becomes another maintained piece of product logic.

## Implementation Notes

- `merchant_raw + description` rules still run first and win when they match.
- The fallback map is currently used for Sber `raw["category_label"]` values such as `Супермаркеты`, `Перевод с карты`, and `Рестораны и кафе`. See ADR-0012 for the current relaxed gate.
- Generic labels like `Сервисы Яндекса` remain intentionally uncategorized unless a stronger user-approved rule exists.

## Alternatives Considered

- Stay regex-only forever: rejected because it leaves known bank-provided signals unused and materially worsens `Прочее` quality.
- Use ML or external APIs: rejected for privacy, determinism, and constraint reasons.

## Links To Relevant Code

- `parser/src/lethal_expenses/categories.py`
- `parser/tests/test_categories.py`
- `AGENT_CONSTRAINTS.md`

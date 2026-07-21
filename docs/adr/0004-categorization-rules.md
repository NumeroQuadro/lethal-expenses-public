# ADR-0004 — Categorization Via Regex Rules

Status: Superseded by ADR-0010

## Context

The project needs deterministic categorization without outbound network calls or external enrichment services.

## Decision

The original decision used ordered regex rules evaluated only against `merchant_raw + description`, with an optional local override file at `parser/categories_overrides.yaml`.

This ADR is superseded because the user-approved categorization contract now allows bank-provided labels such as Sber `category_label` as a deterministic fallback signal for otherwise weak merchants.

## Consequences

- Categorization remains local and explainable.
- Rule maintenance becomes an ongoing product task as merchants vary.
- Users can teach overrides locally without editing committed source files.

## Implementation Notes

- See ADR-0010 for the current accepted fallback behavior.
- Rules are evaluated in declaration order and the first match wins.
- The default category is `Прочее`.

## Alternatives Considered

- MCC-based categorization: rejected because statements may not expose reliable MCC data.
- External ML or API categorization: rejected for privacy and determinism reasons.

## Links To Relevant Code

- `parser/src/lethal_expenses/categories.py`
- `parser/tests/test_categories.py`

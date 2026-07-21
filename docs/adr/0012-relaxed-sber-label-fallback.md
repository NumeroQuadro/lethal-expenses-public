# ADR-0012 — Relaxed Sber Label Fallback After Regex Miss

Status: Accepted

## Context

ADR-0010 allowed Sber `raw["category_label"]` values to act as a deterministic fallback signal, but only when `merchant_raw` was empty, `-`, or `SBOL`-like. A live-data audit on 2026-05-03 showed that this gate left a large residue of clearly classifiable Sber rows in `Прочее`: 412 expense rows totaling 176,077.17 RUB still carried high-signal Sber labels such as `Рестораны и кафе`, `Супермаркеты`, `Транспорт`, and `Коммунальные платежи, связь, интернет.` while failing regex classification only because the merchant string was present but unmatched.

The fallback gate was therefore excluding authoritative bank-native categorization without reducing false-positive risk in any meaningful way.

## Decision

Keep categorization fully local and deterministic, but relax the Sber fallback gate:

- Ordered regex rules over `merchant_raw + description` remain the primary classifier.
- If no regex rule matches and `raw["category_label"]` is present in the committed Sber fallback map, that mapped category is used regardless of whether `merchant_raw` is empty, dash-like, `SBOL`-like, or non-empty.
- The fallback map remains fully committed product logic, not user data and not model output.
- Unknown or intentionally miscellaneous labels may still map to `Прочее`.

## Consequences

- The categorizer can recover a large amount of previously stranded Sber signal without introducing network calls, ML inference, or nondeterminism.
- Regex rules remain authoritative and still win whenever they match, so broad fallback labels cannot override a stronger merchant-specific rule.
- The effective category set can expand when the committed fallback map adds explicit product-approved categories such as `Развлечения`, `Электроника`, or `Образование`.

## Trade-Offs

- Bank-native labels influence more rows than before, so product semantics now depend more heavily on the quality and stability of Sber labels.
- The committed fallback map becomes a more important surface that must be regression-tested whenever labels are added or remapped.

## Implementation Notes

- The decision is implemented in `parser/src/lethal_expenses/categories.py` by applying regex rules first and then consulting `SBER_LABEL_FALLBACK_MAP` for any remaining miss.
- The fallback map should cover every live Sber `category_label` value that the product chooses to recognize, mapping each either to a concrete category or to `Прочее` intentionally.
- Regression tests must assert both priority directions: regex beats Sber label fallback, and Sber label fallback beats `Прочее` after a regex miss.

## Alternatives Considered

- Keep the empty/dash/SBOL gate from ADR-0010: rejected because it stranded hundreds of authoritative Sber-labeled rows in `Прочее`.
- Extend regexes only, without relaxing the fallback gate: rejected because it would duplicate bank-native categorization knowledge in brittle hand-written patterns.
- Use ML or external APIs: rejected for privacy, determinism, and constraint reasons.

## Links To Relevant Code

- `parser/src/lethal_expenses/categories.py`
- `parser/tests/test_categories.py`
- `/tmp/lethal-expenses-category-diagnosis-2026-05-03.md`
- `AGENT_CONSTRAINTS.md`

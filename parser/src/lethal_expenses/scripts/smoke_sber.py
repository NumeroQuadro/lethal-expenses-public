from __future__ import annotations

import json
import re
import sys
from decimal import Decimal
from pathlib import Path

from lethal_expenses.parsers.sberbank import SberbankParser

FOOTER_TOTAL_RE = re.compile(r"ВСЕГО\s+СПИСАНИЙ\s+(?P<amount>\d[\d\s]*,\d{2})")


def parse_russian_amount(value: str) -> Decimal:
    return Decimal(value.replace(" ", "").replace(",", "."))


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python -m lethal_expenses.scripts.smoke_sber <statement.pdf>")
        return 1

    pdf_path = Path(sys.argv[1])
    parser = SberbankParser()
    statement_text = parser.extract_text(pdf_path)
    transactions = list(parser.parse_text(statement_text, source_name=pdf_path.name))

    for transaction in transactions[:5]:
        print(json.dumps(transaction.model_dump(mode="json"), ensure_ascii=False))

    debit_total = sum(
        (transaction.amount for transaction in transactions if transaction.amount < 0),
        Decimal("0"),
    )
    footer_match = FOOTER_TOTAL_RE.search(statement_text)
    if footer_match:
        footer_total = -parse_russian_amount(footer_match.group("amount"))
        delta = abs(debit_total - footer_total)
        pct = Decimal("0") if footer_total == 0 else (delta / abs(footer_total)) * 100
        print(f"parsed_debit_total={debit_total}")
        print(f"footer_debit_total={footer_total}")
        print(f"difference_percent={pct.quantize(Decimal('0.01'))}")
    else:
        print("Footer total not found in statement text.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

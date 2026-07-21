# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUntypedFunctionDecorator=false
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from lethal_expenses.parsers.base import BaseParser
from lethal_expenses.schema import MOSCOW_TZ, Transaction


class UnparseableParser(BaseParser):
    bank = "sberbank"

    def can_parse_text(self, text: str) -> bool:
        return False

    def parse_text(self, text: str, *, source_name: str | None = None) -> list[Transaction]:
        return []


def format_amount(absolute_value: Decimal, *, decimal_separator: str = ",") -> str:
    integer_part, fractional_part = f"{absolute_value:.2f}".split(".")
    grouped = f"{int(integer_part):,}".replace(",", " ")
    return f"{grouped}{decimal_separator}{fractional_part}"


@st.composite
def amount_case(draw: st.DrawFn) -> tuple[str, int, Decimal]:
    kopeks = draw(st.integers(min_value=0, max_value=999_999_999))
    explicit_sign = draw(st.sampled_from([None, "+", "-", "–", "−"]))
    default_sign = draw(st.sampled_from([-1, 1]))
    suffix = draw(st.sampled_from(["", " ₽", " руб."]))
    prefix_spaces = draw(st.sampled_from(["", " "]))
    nbsp_between = draw(st.booleans())
    decimal_separator = draw(st.sampled_from([",", "."]))

    absolute_value = Decimal(kopeks) / Decimal("100")
    amount_core = format_amount(absolute_value, decimal_separator=decimal_separator)
    if nbsp_between:
        amount_core = amount_core.replace(" ", "\xa0")

    sign_text = "" if explicit_sign is None else f"{explicit_sign} "
    parsed_sign = default_sign
    if explicit_sign == "+":
        parsed_sign = 1
    elif explicit_sign in {"-", "–", "−"}:
        parsed_sign = -1

    text = f"{prefix_spaces}{sign_text}{amount_core}{suffix}\x00"
    expected = Decimal(parsed_sign) * absolute_value
    return text, default_sign, expected


@given(amount_case())
def test_parse_amount_property(case: tuple[str, int, Decimal]) -> None:
    text, default_sign, expected = case
    assert BaseParser.parse_amount(text, default_sign=default_sign) == expected


@given(st.dates(min_value=date(2000, 1, 1), max_value=date(2035, 12, 31)))
def test_parse_date_ru_property_without_time(value: date) -> None:
    parsed = BaseParser.parse_date_ru(value.strftime("%d.%m.%Y"))

    assert parsed == datetime.combine(value, time.min, tzinfo=MOSCOW_TZ)


@given(
    st.dates(min_value=date(2000, 1, 1), max_value=date(2035, 12, 31)),
    st.times(),
)
def test_parse_date_ru_property_with_time(value: date, time_value: time) -> None:
    hhmm = time_value.strftime("%H:%M")
    parsed = BaseParser.parse_date_ru(value.strftime("%d.%m.%Y"), hhmm)

    assert parsed == datetime.combine(
        value,
        time(hour=time_value.hour, minute=time_value.minute),
        tzinfo=MOSCOW_TZ,
    )


def test_parse_date_ru_supports_second_precision() -> None:
    parsed = BaseParser.parse_date_ru("25.12.2025", "22:40:59")

    assert parsed.isoformat() == "2025-12-25T22:40:59+03:00"


def test_parse_amount_supports_dot_decimal_separator() -> None:
    assert BaseParser.parse_amount("- 1 234.56 ₽") == Decimal("-1234.56")
    assert BaseParser.parse_amount("+ 2 000.00", default_sign=1) == Decimal("2000.00")


def test_build_id_discards_empty_or_invalid_parts() -> None:
    occurred_at = BaseParser.parse_date_ru("25.12.2025", "22:40")

    identifier = BaseParser.build_id(
        "sber",
        "****7000",
        occurred_at,
        " ",
        "AUTH/01",
        "***",
    )

    assert identifier == "sber-7000-20251225-22:40-AUTH01"


def test_parse_raises_when_parser_cannot_handle_statement() -> None:
    parser = UnparseableParser()

    with patch.object(parser, "extract_text", return_value="unknown statement"):
        with pytest.raises(ValueError, match="cannot parse"):
            list(parser.parse(Path("/tmp/unknown.pdf")))


def test_extract_text_can_limit_to_first_page(synthetic_pdf_paths: dict[str, Path]) -> None:
    parser = UnparseableParser()
    text = parser.extract_text(synthetic_pdf_paths["yandex"], max_pages=1)

    assert "Выписка по карте" in text
    assert "Выписка по ЭДС" not in text

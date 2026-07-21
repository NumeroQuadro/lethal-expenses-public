from __future__ import annotations

from decimal import Decimal
from importlib import import_module
from pathlib import Path
from typing import Any, cast

import pytest

from lethal_expenses.parsers.base import BaseParser, extract_pdf_text
from lethal_expenses.parsers.ozon import OzonCardParser, OzonSavingsParser
from lethal_expenses.parsers.sberbank import (
    SberbankCardParser,
    SberbankDepositParser,
    SberbankParser,
    SberbankSavingsParser,
)
from lethal_expenses.parsers.spb import SpbParser
from lethal_expenses.parsers.yandex import YandexCardParser, YandexSavingsParser
from lethal_expenses.registry import (
    get_parser_for_path,
    get_parser_for_text,
    list_registered_parsers,
)


def _write_unknown_pdf(path: Path) -> None:
    canvas_module = cast(Any, import_module("reportlab.pdfgen.canvas"))
    pagesizes = cast(Any, import_module("reportlab.lib.pagesizes"))
    pdf = canvas_module.Canvas(str(path), pagesize=pagesizes.A4)
    text = pdf.beginText(40, 800)
    text.setFont("Helvetica", 10)
    text.textLine("Unknown Bank Statement")
    text.textLine("This PDF should not match any registered parser")
    pdf.drawText(text)
    pdf.save()


def test_base_parser_helpers() -> None:
    assert BaseParser.parse_amount("- 1 234,56 ₽") == Decimal("-1234.56")
    assert BaseParser.parse_amount("– 1 234,56 ₽") == Decimal("-1234.56")
    assert BaseParser.parse_amount("+ 10 000,00 ₽") == Decimal("10000.00")
    assert BaseParser.parse_amount("2 345,00") == Decimal("-2345.00")
    assert BaseParser.clean_merchant("  Магнит   у дома - ") == "Магнит у дома"
    assert (
        BaseParser.parse_date_ru("25.12.2025", "22:40").isoformat() == "2025-12-25T22:40:00+03:00"
    )


def test_registry_selects_sberbank_parser(synthetic_pdf_paths: dict[str, Path]) -> None:
    parser = get_parser_for_path(synthetic_pdf_paths["sberbank"])

    assert isinstance(parser, SberbankCardParser)


def test_registry_selects_parser_from_shared_page_text(
    synthetic_pdf_paths: dict[str, Path],
) -> None:
    parser = get_parser_for_text(extract_pdf_text(synthetic_pdf_paths["yandex"], max_pages=1))

    assert isinstance(parser, YandexCardParser)


def test_registry_selects_sberbank_payment_account_parser(
    synthetic_pdf_fixtures: dict[str, Path],
) -> None:
    parser = get_parser_for_path(synthetic_pdf_fixtures["sberbank_card_payment_account_standalone"])

    assert isinstance(parser, SberbankCardParser)


def test_registry_selects_sberbank_savings_parser(
    synthetic_pdf_fixtures: dict[str, Path],
) -> None:
    parser = get_parser_for_path(synthetic_pdf_fixtures["sberbank_savings_standalone"])

    assert isinstance(parser, SberbankSavingsParser)


def test_registry_selects_sberbank_deposit_parser(
    synthetic_pdf_fixtures: dict[str, Path],
) -> None:
    parser = get_parser_for_path(synthetic_pdf_fixtures["sberbank_deposit_standalone"])

    assert isinstance(parser, SberbankDepositParser)


def test_registry_selects_yandex_card_parser(synthetic_pdf_paths: dict[str, Path]) -> None:
    parser = get_parser_for_path(synthetic_pdf_paths["yandex"])

    assert isinstance(parser, YandexCardParser)


def test_registry_selects_yandex_savings_parser(
    synthetic_pdf_fixtures: dict[str, Path],
) -> None:
    parser = get_parser_for_path(synthetic_pdf_fixtures["yandex_savings_standalone"])

    assert isinstance(parser, YandexSavingsParser)


def test_registry_selects_ozon_card_parser(synthetic_pdf_fixtures: dict[str, Path]) -> None:
    parser = get_parser_for_path(synthetic_pdf_fixtures["ozon_card_standalone"])

    assert isinstance(parser, OzonCardParser)


def test_registry_selects_ozon_savings_parser(synthetic_pdf_paths: dict[str, Path]) -> None:
    parser = get_parser_for_path(synthetic_pdf_paths["ozon"])

    assert isinstance(parser, OzonSavingsParser)


def test_registry_selects_spb_parser(synthetic_pdf_paths: dict[str, Path]) -> None:
    parser = get_parser_for_path(synthetic_pdf_paths["spb"])

    assert isinstance(parser, SpbParser)
    assert SberbankParser is SberbankCardParser
    assert list_registered_parsers() == (
        SberbankCardParser,
        SberbankSavingsParser,
        SberbankDepositParser,
        YandexCardParser,
        YandexSavingsParser,
        OzonCardParser,
        OzonSavingsParser,
        SpbParser,
    )


def test_registry_raises_for_unknown_pdf(tmp_path: Path) -> None:
    unknown_pdf = tmp_path / "unknown.pdf"
    _write_unknown_pdf(unknown_pdf)

    with pytest.raises(ValueError, match="No registered parser could handle"):
        get_parser_for_path(unknown_pdf)


def test_synthetic_pdf_fixtures_exist(
    synthetic_pdf_fixtures: dict[str, Path],
    synthetic_pdf_paths: dict[str, Path],
    synthetic_edge_pdf_paths: dict[str, Path],
    synthetic_all_pdf_dir: Path,
) -> None:
    assert set(synthetic_pdf_paths) == {"sberbank", "yandex", "ozon", "spb"}
    assert set(synthetic_edge_pdf_paths) == {"sberbank", "yandex", "ozon", "spb"}
    assert {
        "sberbank_savings_standalone",
        "sberbank_deposit_standalone",
        "yandex_savings_standalone",
        "ozon_card_standalone",
    } <= set(synthetic_pdf_fixtures)
    assert all(path.exists() for path in synthetic_pdf_paths.values())
    assert all(path.exists() for path in synthetic_edge_pdf_paths.values())
    assert len(list(synthetic_all_pdf_dir.glob("*.pdf"))) == 8

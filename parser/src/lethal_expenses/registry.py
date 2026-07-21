from __future__ import annotations

from pathlib import Path

from lethal_expenses.parsers.base import BaseParser, extract_pdf_text
from lethal_expenses.parsers.ozon import OzonCardParser, OzonSavingsParser
from lethal_expenses.parsers.sberbank import (
    SberbankCardParser,
    SberbankDepositParser,
    SberbankSavingsParser,
)
from lethal_expenses.parsers.spb import SpbParser
from lethal_expenses.parsers.yandex import YandexCardParser, YandexSavingsParser

REGISTERED_PARSER_CLASSES: tuple[type[BaseParser], ...] = (
    SberbankCardParser,
    SberbankSavingsParser,
    SberbankDepositParser,
    YandexCardParser,
    YandexSavingsParser,
    OzonCardParser,
    OzonSavingsParser,
    SpbParser,
)


def list_registered_parsers() -> tuple[type[BaseParser], ...]:
    return REGISTERED_PARSER_CLASSES


def get_parser_for_text(text: str) -> BaseParser:
    for parser_class in REGISTERED_PARSER_CLASSES:
        parser = parser_class()
        if parser.can_parse_text(text):
            return parser
    raise ValueError("No registered parser could handle the provided statement text")


def get_parser_for_path(path: str | Path) -> BaseParser:
    pdf_path = Path(path)
    try:
        return get_parser_for_text(extract_pdf_text(pdf_path, max_pages=1))
    except ValueError as exc:
        raise ValueError(f"No registered parser could handle {pdf_path}") from exc

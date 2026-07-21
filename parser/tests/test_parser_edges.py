# pyright: reportPrivateUsage=false
from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from lethal_expenses.parsers.base import BaseParser
from lethal_expenses.parsers.ozon import OzonSavingsParser
from lethal_expenses.parsers.sberbank import PendingTransaction, SberbankParser
from lethal_expenses.parsers.spb import SpbParser
from lethal_expenses.parsers.yandex import YandexCardParser
from lethal_expenses.schema import Transaction


def find_by_merchant(transactions: list[Transaction], merchant_raw: str) -> Transaction:
    return next(
        transaction for transaction in transactions if transaction.merchant_raw == merchant_raw
    )


def test_sberbank_edge_fixture_uses_header_account_identity(
    synthetic_edge_pdf_paths: dict[str, Path],
) -> None:
    parser = SberbankParser()
    transactions = list(parser.parse(synthetic_edge_pdf_paths["sberbank"]))

    assert len(transactions) == 3
    assert [transaction.raw["auth_code"] for transaction in transactions] == [
        "AUTH09",
        "AUTH10",
        "AUTH11",
    ]
    assert all(transaction.account == "****1111" for transaction in transactions)
    assert all(transaction.raw["header_account"] == "****1111" for transaction in transactions)
    assert find_by_merchant(transactions, "ООО Проба").amount == Decimal("-1250.00")


def test_sberbank_requires_account_from_row_or_header() -> None:
    parser = SberbankParser()
    pending = PendingTransaction(
        date=BaseParser.parse_date_ru("03.03.2026", "11:45"),
        category_label="Разное",
        amount=Decimal("-100.00"),
        auth_code="AUTH11",
        description_parts=["Тестовый сервис без маски счёта"],
    )

    with pytest.raises(ValueError, match="Could not determine Sberbank account suffix"):
        parser._build_transaction(pending, header_account=None, source_name="edge.pdf")


def test_yandex_edge_fixture_covers_combined_rows_and_eds(
    synthetic_edge_pdf_paths: dict[str, Path],
    caplog: Any,
) -> None:
    parser = YandexCardParser()
    with caplog.at_level(logging.WARNING, logger="lethal_expenses.parsers.yandex"):
        transactions = list(parser.parse(synthetic_edge_pdf_paths["yandex"]))

    assert len(transactions) == 4
    assert not [
        record
        for record in caplog.records
        if record.name == "lethal_expenses.parsers.yandex" and record.levelno >= logging.WARNING
    ]
    assert all(transaction.date.hour != 6 for transaction in transactions)
    assert find_by_merchant(transactions, "DNS").amount == Decimal("-5432.10")
    assert find_by_merchant(transactions, "Маркет у дома").amount == Decimal("-250.00")
    assert find_by_merchant(transactions, "Тест Тестович").account == "****1111"
    eds_row = find_by_merchant(transactions, "Альфа Банк на Яндекс Счёт")
    assert eds_row.account == "ЭДС"
    assert eds_row.amount == Decimal("600.00")


def test_ozon_edge_fixture_handles_orphan_and_wrapped_lines(
    synthetic_edge_pdf_paths: dict[str, Path],
) -> None:
    parser = OzonSavingsParser()
    transactions = list(parser.parse(synthetic_edge_pdf_paths["ozon"]))

    assert len(transactions) == 3
    assert all(transaction.account == "****9911" for transaction in transactions)
    assert (
        find_by_merchant(transactions, "Перевод собственных средств. Без НДС.").raw[
            "is_likely_self_transfer"
        ]
        is True
    )
    assert find_by_merchant(transactions, "Оплата сервиса Ozon for Business").amount == Decimal(
        "-321.00"
    )
    assert find_by_merchant(transactions, "Пополнение кошелька").amount == Decimal("2000.00")


def test_ozon_errors_when_header_or_amount_tail_missing() -> None:
    parser = OzonSavingsParser()

    with pytest.raises(ValueError, match="Could not determine Ozon account suffix"):
        parser._extract_header_account("ООО «ОЗОН Банк" + "\n" + "Справка о движении средств")

    with pytest.raises(ValueError, match="Could not parse Ozon transaction row"):
        parser._build_transaction(
            ["not a transaction"],
            header_account="****1111",
            source_name=None,
        )

    with pytest.raises(ValueError, match="Could not parse Ozon amount tail"):
        parser._build_transaction(
            ["25.04.2026 DOC-103 Операция без суммы"],
            header_account="****1111",
            source_name=None,
        )


def test_spb_edge_fixture_handles_continuations(
    synthetic_edge_pdf_paths: dict[str, Path],
) -> None:
    parser = SpbParser()
    transactions = list(parser.parse(synthetic_edge_pdf_paths["spb"]))

    assert len(transactions) == 3
    assert all(transaction.account == "****5151" for transaction in transactions)
    assert find_by_merchant(transactions, "Иван Иванович И").amount == Decimal("-1500.00")
    romashka = find_by_merchant(transactions, "ООО Ромашка")
    assert romashka.description == "Оплата услуг комментарий по договору 42"
    assert find_by_merchant(transactions, "Пополнение вклада").amount == Decimal("10000.00")


def test_spb_helpers_cover_fallback_split_and_invalid_rows() -> None:
    parser = SpbParser()
    line = "14.03.2026  ООО Ромашка  Оплата услуг  -650.50"

    assert parser._split_primary_line(line) == (
        "14.03.2026",
        "ООО Ромашка",
        "Оплата услуг",
        "-650.50",
    )

    with pytest.raises(ValueError, match="Could not determine SPB account suffix"):
        parser._extract_header_account("Выписка" + "\n" + "Период: 01.01.2026 - 02.01.2026")

    with pytest.raises(ValueError, match="Could not split SPB row into columns"):
        parser._split_primary_line("14.03.2026 broken row")

from __future__ import annotations

import logging
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from lethal_expenses.parsers.yandex import YandexCardParser, YandexSavingsParser
from lethal_expenses.schema import Transaction


def find_by_merchant(
    transactions: Sequence[Transaction],
    merchant_raw: str,
) -> Transaction:
    return next(
        transaction for transaction in transactions if transaction.merchant_raw == merchant_raw
    )


def yandex_warnings(caplog: Any) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == "lethal_expenses.parsers.yandex" and record.levelno >= logging.WARNING
    ]


def test_yandex_card_parser_handles_card_and_eds_substatements(
    synthetic_pdf_paths: dict[str, Path],
    caplog: Any,
) -> None:
    parser = YandexCardParser()
    pdf_path = synthetic_pdf_paths["yandex"]

    with caplog.at_level(logging.WARNING, logger="lethal_expenses.parsers.yandex"):
        assert parser.can_parse(pdf_path)
        transactions = list(parser.parse(pdf_path))

    assert len(transactions) == 7
    assert len({transaction.id for transaction in transactions}) == 7
    assert sum(transaction.amount < 0 for transaction in transactions) == 4
    assert sum(transaction.amount > 0 for transaction in transactions) == 3
    assert all(transaction.bank == "yandex" for transaction in transactions)
    assert yandex_warnings(caplog) == []

    card_expense = find_by_merchant(transactions, "Магнит у дома")
    assert card_expense.account == "****9922"
    assert card_expense.amount == Decimal("-1234.56")
    assert card_expense.id.startswith("yandex-9922-2026-04-24T08:10:00+03:00-")

    refund = find_by_merchant(transactions, "Пятёрочка")
    assert refund.amount == Decimal("250.00")
    assert refund.account == "****9922"

    qr_payment = find_by_merchant(transactions, "Сервисы Яндекса")
    assert qr_payment.amount == Decimal("-399.00")
    assert "Плюс Мульти" in qr_payment.description

    incoming_transfer = find_by_merchant(transactions, "Иван Иванович И.")
    assert incoming_transfer.account == "****9922"
    assert incoming_transfer.amount == Decimal("7000.00")

    eds_top_up = find_by_merchant(transactions, "Tinkoff Black")
    assert eds_top_up.account == "ЭДС"
    assert eds_top_up.amount == Decimal("5000.00")
    assert eds_top_up.id.startswith("yandex-eds-2026-04-24T12:50:00+03:00-")

    eds_transfer = next(
        transaction
        for transaction in transactions
        if transaction.account == "ЭДС" and transaction.amount == Decimal("-3000.00")
    )
    assert eds_transfer.merchant_raw == "Иван Иванович И."

    cafe = find_by_merchant(transactions, "Кофейня у дома")
    assert cafe.account == "ЭДС"
    assert cafe.amount == Decimal("-540.40")
    assert "Большой проспект" in cafe.description

    debit_total = sum(
        (transaction.amount for transaction in transactions if transaction.amount < 0),
        Decimal("0"),
    )
    assert debit_total == Decimal("-5173.96")


@pytest.mark.parametrize(
    ("fixture_name", "merchant_raw", "account", "amount", "occurred_at"),
    [
        (
            "yandex_wrapped_time_standalone",
            "Сервисы Яндекса",
            "****9922",
            Decimal("-399.00"),
            "2026-04-24T10:30:00+03:00",
        ),
        (
            "yandex_wrapped_time_suffix",
            "YANDEX MARKET",
            "ЭДС",
            Decimal("-3391.00"),
            "2023-12-23T15:17:00+03:00",
        ),
        (
            "yandex_wrapped_time_transfer",
            "Иван Иванович И.",
            "ЭДС",
            Decimal("2000.00"),
            "2025-06-21T16:10:00+03:00",
        ),
    ],
)
def test_yandex_card_parser_handles_wrapped_time_variants(
    synthetic_pdf_fixtures: dict[str, Path],
    fixture_name: str,
    merchant_raw: str,
    account: str,
    amount: Decimal,
    occurred_at: str,
    caplog: Any,
) -> None:
    parser = YandexCardParser()
    pdf_path = synthetic_pdf_fixtures[fixture_name]

    with caplog.at_level(logging.WARNING, logger="lethal_expenses.parsers.yandex"):
        transactions = list(parser.parse(pdf_path))

    assert len(transactions) == 1
    assert yandex_warnings(caplog) == []

    transaction = transactions[0]
    assert transaction.merchant_raw == merchant_raw
    assert transaction.account == account
    assert transaction.amount == amount
    assert transaction.date.isoformat() == occurred_at


def test_yandex_card_parser_handles_wrapped_time_across_page_boundary(
    synthetic_pdf_fixtures: dict[str, Path],
    caplog: Any,
) -> None:
    parser = YandexCardParser()
    pdf_path = synthetic_pdf_fixtures["yandex_wrapped_time_page_boundary"]

    with caplog.at_level(logging.WARNING, logger="lethal_expenses.parsers.yandex"):
        transactions = list(parser.parse(pdf_path))

    assert len(transactions) == 1
    assert yandex_warnings(caplog) == []

    transaction = transactions[0]
    assert transaction.merchant_raw == "Иван Иванович И."
    assert transaction.account == "ЭДС"
    assert transaction.amount == Decimal("1500.00")
    assert transaction.date.isoformat() == "2026-04-24T18:02:00+03:00"
    assert transaction.description.endswith("Сбербанк")


def test_yandex_savings_parser_handles_save_statement_rows(
    synthetic_pdf_fixtures: dict[str, Path],
) -> None:
    parser = YandexSavingsParser()
    pdf_path = synthetic_pdf_fixtures["yandex_savings_standalone"]

    assert parser.can_parse(pdf_path)

    transactions = list(parser.parse(pdf_path))

    assert len(transactions) == 3
    assert len({transaction.id for transaction in transactions}) == 3
    assert all(transaction.account == "****8398" for transaction in transactions)
    assert all(transaction.bank == "yandex" for transaction in transactions)

    transfer_in = find_by_merchant(transactions, "Перевод между счетами одного клиента")
    assert transfer_in.amount == Decimal("130000.00")
    assert transfer_in.id.startswith("yandex-8398-2025-09-13T00:00:00+03:00-")

    interest = find_by_merchant(transactions, "Капитализация процентов")
    assert interest.amount == Decimal("67.67")
    assert interest.date.isoformat() == "2025-09-14T00:00:00+03:00"

    transfer_out = next(
        transaction for transaction in transactions if transaction.amount == Decimal("-1000.00")
    )
    assert transfer_out.merchant_raw == "Перевод между счетами одного клиента"

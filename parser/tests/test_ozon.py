# pyright: reportPrivateUsage=false
from __future__ import annotations

import logging
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from lethal_expenses.parsers.ozon import OzonCardParser, OzonSavingsParser
from lethal_expenses.schema import Transaction


def find_by_document(transactions: Sequence[Transaction], document: str) -> Transaction:
    return next(
        transaction for transaction in transactions if transaction.raw["document"] == document
    )


def ozon_warnings(caplog: Any) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == "lethal_expenses.parsers.ozon" and record.levelno >= logging.WARNING
    ]


def test_ozon_savings_parser_handles_savings_statement_shapes(
    synthetic_pdf_paths: dict[str, Path],
) -> None:
    parser = OzonSavingsParser()
    pdf_path = synthetic_pdf_paths["ozon"]

    assert parser.can_parse(pdf_path)

    transactions = list(parser.parse(pdf_path))

    assert len(transactions) == 4
    assert len({transaction.id for transaction in transactions}) == 4
    assert sum(transaction.amount < 0 for transaction in transactions) == 3
    assert sum(transaction.amount > 0 for transaction in transactions) == 1
    assert all(transaction.bank == "ozon" for transaction in transactions)
    assert all(transaction.account == "****3456" for transaction in transactions)

    self_transfer = find_by_document(transactions, "DOC-001")
    assert self_transfer.amount == Decimal("-5000.00")
    assert self_transfer.merchant_raw == "Перевод собственных средств. Без НДС."
    assert self_transfer.raw["is_likely_self_transfer"] is True

    interest = find_by_document(transactions, "DOC-002")
    assert interest.amount == Decimal("25.17")
    assert interest.merchant_raw.startswith("Выплата процентов по счету")
    assert interest.raw["is_likely_self_transfer"] is False

    wrapped_amount = find_by_document(transactions, "DOC-003")
    assert wrapped_amount.amount == Decimal("-199.00")
    assert wrapped_amount.merchant_raw == "Оплата подписки Ozon Premium"

    large_debit = find_by_document(transactions, "DOC-004")
    assert large_debit.amount == Decimal("-12345.67")

    debit_total = sum(
        (transaction.amount for transaction in transactions if transaction.amount < 0),
        Decimal("0"),
    )
    assert debit_total == Decimal("-17544.67")


def test_ozon_savings_parser_handles_active_row_families_and_noise(
    synthetic_pdf_fixtures: dict[str, Path],
    caplog: Any,
) -> None:
    parser = OzonSavingsParser()
    pdf_path = synthetic_pdf_fixtures["ozon_savings_active_standalone"]

    with caplog.at_level(logging.WARNING, logger="lethal_expenses.parsers.ozon"):
        assert parser.can_parse(pdf_path)
        transactions = list(parser.parse(pdf_path))

    assert len(transactions) == 3
    assert ozon_warnings(caplog) == []
    assert all(transaction.account == "****5000" for transaction in transactions)
    assert all(transaction.precision == "second" for transaction in transactions)

    split_transfer = find_by_document(transactions, "6966465484")
    assert split_transfer.amount == Decimal("-7000.00")
    assert split_transfer.date.isoformat() == "2026-04-21T19:44:27+03:00"
    assert split_transfer.merchant_raw == "Перевод собственных средств. Без НДС."
    assert split_transfer.raw["is_likely_self_transfer"] is True

    inline_transfer = find_by_document(transactions, "6935053101")
    assert inline_transfer.amount == Decimal("97000.00")
    assert inline_transfer.date.isoformat() == "2026-04-19T13:07:41+03:00"
    assert inline_transfer.merchant_raw == "Перевод собственных средств. Без НДС."
    assert inline_transfer.raw["is_likely_self_transfer"] is True

    interest = find_by_document(transactions, "9711639650")
    assert interest.amount == Decimal("6910.79")
    assert interest.date.isoformat() == "2026-04-05T14:27:28+03:00"
    assert interest.merchant_raw.startswith("Выплата процентов по счету 40817810200000005000")
    assert "за период с 05.03.2026 по 04.04.2026" in interest.description
    assert interest.raw["is_likely_self_transfer"] is False


def test_ozon_card_parser_can_parse_card_family_fixture(
    synthetic_pdf_fixtures: dict[str, Path],
    caplog: Any,
) -> None:
    parser = OzonCardParser()
    pdf_path = synthetic_pdf_fixtures["ozon_card_standalone"]

    with caplog.at_level(logging.WARNING, logger="lethal_expenses.parsers.ozon"):
        assert parser.can_parse(pdf_path)
        transactions = list(parser.parse(pdf_path))

    assert len(transactions) == 2
    assert ozon_warnings(caplog) == []
    assert all(transaction.account == "****4000" for transaction in transactions)
    assert all(transaction.precision == "second" for transaction in transactions)

    transfer = find_by_document(transactions, "5732876450")
    assert transfer.amount == Decimal("2000.00")
    assert transfer.merchant_raw == "Перевод собственных средств"

    steam = find_by_document(transactions, "7762684788")
    assert steam.amount == Decimal("-200.00")
    assert steam.raw["amount_secondary"] == "- 2.27 $"
    assert "Steam" in steam.merchant_raw


@pytest.mark.parametrize(
    ("fixture_name", "document", "amount", "occurred_at", "merchant_substring"),
    [
        (
            "ozon_card_single_line",
            "5732876450",
            Decimal("2000.00"),
            "2026-04-24T08:10:09+03:00",
            "Перевод собственных средств",
        ),
        (
            "ozon_card_split_time",
            "5705865008",
            Decimal("-2040.99"),
            "2026-01-09T16:25:39+03:00",
            "Перевод клиенту Банка",
        ),
        (
            "ozon_card_leading_description",
            "8011593841",
            Decimal("-86.00"),
            "2026-01-01T02:07:53+03:00",
            "METRO TPP SANKT-PETERBU RU",
        ),
        (
            "ozon_card_wrapped_sbp",
            "5671367053",
            Decimal("-722.31"),
            "2026-01-06T05:59:38+03:00",
            "ВАЙБСТРИМ",
        ),
    ],
)
def test_ozon_card_parser_handles_real_row_families(
    synthetic_pdf_fixtures: dict[str, Path],
    fixture_name: str,
    document: str,
    amount: Decimal,
    occurred_at: str,
    merchant_substring: str,
    caplog: Any,
) -> None:
    parser = OzonCardParser()
    pdf_path = synthetic_pdf_fixtures[fixture_name]

    with caplog.at_level(logging.WARNING, logger="lethal_expenses.parsers.ozon"):
        transactions = list(parser.parse(pdf_path))

    assert len(transactions) == 1
    assert ozon_warnings(caplog) == []

    transaction = transactions[0]
    assert transaction.raw["document"] == document
    assert transaction.amount == amount
    assert transaction.date.isoformat() == occurred_at
    assert transaction.precision == "second"
    assert merchant_substring in transaction.merchant_raw


def test_ozon_card_parser_handles_page_boundary_noise(
    synthetic_pdf_fixtures: dict[str, Path],
    caplog: Any,
) -> None:
    parser = OzonCardParser()
    pdf_path = synthetic_pdf_fixtures["ozon_card_page_boundary"]

    with caplog.at_level(logging.WARNING, logger="lethal_expenses.parsers.ozon"):
        transactions = list(parser.parse(pdf_path))

    assert len(transactions) == 1
    assert ozon_warnings(caplog) == []

    transaction = transactions[0]
    assert transaction.raw["document"] == "5733000001"
    assert transaction.amount == Decimal("-500.00")
    assert transaction.date.isoformat() == "2026-04-24T07:20:19+03:00"
    assert "ВАЙБСТРИМ" in transaction.description


def test_ozon_card_parser_attaches_old_service_continuation_without_warnings(
    synthetic_pdf_fixtures: dict[str, Path],
    caplog: Any,
) -> None:
    parser = OzonCardParser()
    pdf_path = synthetic_pdf_fixtures["ozon_card_old_service_continuation"]

    with caplog.at_level(logging.WARNING, logger="lethal_expenses.parsers.ozon"):
        transactions = list(parser.parse(pdf_path))

    assert len(transactions) == 1
    assert ozon_warnings(caplog) == []

    transaction = transactions[0]
    assert transaction.raw["document"] == "6177956002"
    assert transaction.amount == Decimal("-286.55")
    assert transaction.date.isoformat() == "2026-02-19T21:41:49+03:00"
    assert "Оплата услуг по счету 705138871 // ID:290210908" in transaction.description
    assert 'Получатель: АО "АБ "РОССИЯ"' in transaction.description


def test_ozon_card_parser_starts_new_transaction_on_reversal_marker_line(
    synthetic_pdf_fixtures: dict[str, Path],
    caplog: Any,
) -> None:
    parser = OzonCardParser()
    pdf_path = synthetic_pdf_fixtures["ozon_card_reversal_marker_split"]

    with caplog.at_level(logging.WARNING, logger="lethal_expenses.parsers.ozon"):
        transactions = list(parser.parse(pdf_path))

    assert len(transactions) == 2
    assert ozon_warnings(caplog) == []

    debit = find_by_document(transactions, "6933461092")
    assert debit.amount == Decimal("-35343.00")
    assert "Отмена перевода" not in debit.description
    assert "BD100042LUK6C6G18OD9K5OKL252VNPG" in debit.description

    reversal = find_by_document(transactions, "9991056439")
    assert reversal.amount == Decimal("35343.00")
    assert "Отмена перевода" in reversal.description
    assert "AD10002S5PJ6ICA99VSRN8GIAK54N4BP" in reversal.description


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

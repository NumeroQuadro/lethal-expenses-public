from __future__ import annotations

import logging
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

from lethal_expenses.parsers.sberbank import (
    SberbankCardParser,
    SberbankDepositParser,
    SberbankParser,
    SberbankSavingsParser,
)
from lethal_expenses.schema import Transaction

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sberbank_statement.txt"


def load_fixture() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


def find_by_auth(transactions: Sequence[Transaction], auth_code: str) -> Transaction:
    return next(
        transaction for transaction in transactions if transaction.raw["auth_code"] == auth_code
    )


def sberbank_warnings(caplog: Any) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == "lethal_expenses.parsers.sberbank" and record.levelno >= logging.WARNING
    ]


def test_sberbank_card_parser_handles_card_fixture() -> None:
    parser = SberbankCardParser()

    statement_text = load_fixture()
    transactions = list(parser.parse_text(statement_text, source_name="synthetic-sber.pdf"))

    assert parser.can_parse_text(statement_text)
    assert SberbankParser is SberbankCardParser
    assert len(transactions) == 8
    assert len({transaction.id for transaction in transactions}) == 8
    assert sum(transaction.amount > 0 for transaction in transactions) == 1
    assert sum(transaction.amount < 0 for transaction in transactions) == 7
    assert all(transaction.bank == "sberbank" for transaction in transactions)
    assert all(transaction.category == "Прочее" for transaction in transactions)
    assert all(transaction.date.tzinfo is not None for transaction in transactions)
    assert {transaction.account for transaction in transactions} == {"****1000"}

    first = transactions[0]
    assert first.amount == Decimal("-154.00")
    assert first.account == "****1000"
    assert first.merchant_raw == "Яндекс Такси"
    assert first.raw["category_label"] == "Транспорт"
    assert first.raw["card_suffix"] == "7000"
    assert first.id == "sber-1000-20260301-08:15-AUTH01-neg15400"

    income = find_by_auth(transactions, "AUTH03")
    assert income.amount == Decimal("10000.00")
    assert income.merchant_raw == "ООО Ромашка"
    assert income.account == "****1000"
    assert income.raw["card_suffix"] == "1000"

    transfer_like = find_by_auth(transactions, "AUTH04")
    assert transfer_like.amount == Decimal("-3000.00")
    assert transfer_like.merchant_raw == "И. Иван Иванович"
    assert transfer_like.account == "****1000"

    wrapped = find_by_auth(transactions, "AUTH05")
    assert wrapped.account == "****1000"
    assert wrapped.raw["card_suffix"] == "2000"
    assert wrapped.merchant_raw == "Пекарня у дома Большой Сампсониевский проспект, 12"
    assert "Операция по счёту" in wrapped.description

    fallback_account = find_by_auth(transactions, "AUTH07")
    assert fallback_account.account == "****1000"
    assert fallback_account.merchant_raw == "ИП Тестовый Без аккаунта"
    assert fallback_account.raw["card_suffix"] is None

    debit_total = sum(
        (transaction.amount for transaction in transactions if transaction.amount < 0),
        Decimal("0"),
    )
    assert debit_total == Decimal("-9060.17")


def test_sberbank_card_parser_parse_uses_source_name() -> None:
    parser = SberbankCardParser()

    with patch.object(parser, "extract_text", return_value=load_fixture()):
        transactions = list(parser.parse(Path("/tmp/all_card_sberbank_7000.pdf")))

    assert len(transactions) == 8
    assert all(
        transaction.raw["source_name"] == "all_card_sberbank_7000.pdf"
        for transaction in transactions
    )


def test_sberbank_card_parser_disambiguates_same_auth_code_with_amount_token() -> None:
    parser = SberbankCardParser()
    statement_text = "\n".join(
        [
            "СберБанк Онлайн",
            "Индивидуальная выписка",
            "Номер счёта 4081781000000007875",
            "05.09.2025  10:23  Перевод с карты  1 016,00",
            "05.09.2025  971809  УРАЛСИБ. Операция по карте ****7875",
            "05.09.2025  10:23  Перевод с карты  15,24",
            "05.09.2025  971809  Комиссия за операцию. Операция по карте ****7875",
        ]
    )

    transactions = list(parser.parse_text(statement_text, source_name="collision.pdf"))

    assert len(transactions) == 2
    assert len({transaction.id for transaction in transactions}) == 2
    assert {transaction.id for transaction in transactions} == {
        "sber-7875-20250905-10:23-971809-neg101600",
        "sber-7875-20250905-10:23-971809-neg1524",
    }


def test_sberbank_card_parser_handles_payment_account_fixture(
    synthetic_pdf_fixtures: dict[str, Path],
    caplog: Any,
) -> None:
    parser = SberbankCardParser()
    fixture_path = synthetic_pdf_fixtures["sberbank_card_payment_account_standalone"]

    with caplog.at_level(logging.WARNING, logger="lethal_expenses.parsers.sberbank"):
        transactions = list(parser.parse(fixture_path))

    assert parser.can_parse_text(parser.extract_text(fixture_path, max_pages=1))
    assert sberbank_warnings(caplog) == []
    assert len(transactions) == 5
    assert {transaction.account for transaction in transactions} == {"****6000"}
    assert all(transaction.precision == "minute" for transaction in transactions)

    dash_row = find_by_auth(transactions, "565367")
    assert dash_row.description == ""
    assert dash_row.merchant_raw == ""
    assert dash_row.raw["card_suffix"] is None

    merchant_row = find_by_auth(transactions, "377648")
    assert merchant_row.merchant_raw == "BURGER KING 0436 SANKT-PETERBU RUS."
    assert merchant_row.raw["card_suffix"] == "7000"
    assert merchant_row.raw["card_suffixes"] == ["7000"]

    relay_row = find_by_auth(transactions, "912345")
    assert relay_row.account == "****6000"
    assert relay_row.raw["card_suffix"] == "5000"
    assert relay_row.raw["card_suffixes"] == ["5000", "7000"]

    assert sum((transaction.amount for transaction in transactions), Decimal("0")) == Decimal(
        "-982.75"
    )


def test_sberbank_savings_inline_header_summary(
    synthetic_pdf_fixtures: dict[str, Path],
    caplog: Any,
) -> None:
    parser = SberbankSavingsParser()
    fixture_path = synthetic_pdf_fixtures["sberbank_savings_inline_header_summary"]

    with caplog.at_level(logging.WARNING, logger="lethal_expenses.parsers.sberbank"):
        transactions = list(parser.parse(fixture_path))

    assert parser.can_parse_text(parser.extract_text(fixture_path, max_pages=1))
    assert sberbank_warnings(caplog) == []
    assert len(transactions) == 4
    assert all(transaction.account == "****2000" for transaction in transactions)
    assert all(transaction.precision == "date" for transaction in transactions)

    opening_balance = Decimal("0")
    running_balance = opening_balance
    for transaction in reversed(transactions):
        balance_after = cast(Decimal, transaction.raw["balance_after"])
        assert running_balance + transaction.amount == balance_after
        running_balance = balance_after

    assert running_balance == Decimal("1045.67")
    assert sum(
        (transaction.amount for transaction in transactions if transaction.amount > 0), Decimal("0")
    ) == Decimal("2545.67")
    assert sum(
        (-transaction.amount for transaction in transactions if transaction.amount < 0),
        Decimal("0"),
    ) == Decimal("1500.00")


def test_sberbank_savings_parser_handles_savings_pdf_fixture(
    synthetic_pdf_fixtures: dict[str, Path],
    caplog: Any,
) -> None:
    parser = SberbankSavingsParser()
    fixture_path = synthetic_pdf_fixtures["sberbank_savings_standalone"]

    with caplog.at_level(logging.WARNING, logger="lethal_expenses.parsers.sberbank"):
        transactions = list(parser.parse(fixture_path))

    assert parser.can_parse_text(parser.extract_text(fixture_path, max_pages=1))
    assert sberbank_warnings(caplog) == []
    assert len(transactions) == 5
    assert [transaction.merchant_raw for transaction in transactions] == [
        "Пополнение",
        "Капитализация вклада",
        "Списание",
        "Зачисление",
        "Пополнение",
    ]
    assert all(transaction.account == "****1000" for transaction in transactions)
    assert all(transaction.bank == "sberbank" for transaction in transactions)

    split_row = transactions[2]
    assert split_row.amount == Decimal("-5500.00")
    assert split_row.description.endswith("к/с 40817 810 0 5519 0181000")
    assert split_row.raw["document_number"] == "700002-2"
    assert split_row.raw["counterparty_accounts"] == ["40817810055190181000"]

    opening_balance = Decimal("0")
    running_balance = opening_balance
    for transaction in reversed(transactions):
        balance_after = cast(Decimal, transaction.raw["balance_after"])
        assert running_balance + transaction.amount == balance_after
        running_balance = balance_after

    assert running_balance == Decimal("18545.67")
    assert sum(
        (transaction.amount for transaction in transactions if transaction.amount > 0), Decimal("0")
    ) == Decimal("24045.67")
    assert sum(
        (-transaction.amount for transaction in transactions if transaction.amount < 0),
        Decimal("0"),
    ) == Decimal("5500.00")


def test_sberbank_deposit_parser_handles_deposit_pdf_fixture(
    synthetic_pdf_fixtures: dict[str, Path],
    caplog: Any,
) -> None:
    parser = SberbankDepositParser()
    fixture_path = synthetic_pdf_fixtures["sberbank_deposit_standalone"]

    with caplog.at_level(logging.WARNING, logger="lethal_expenses.parsers.sberbank"):
        transactions = list(parser.parse(fixture_path))

    assert parser.can_parse_text(parser.extract_text(fixture_path, max_pages=1))
    assert sberbank_warnings(caplog) == []
    assert len(transactions) == 3
    assert all(transaction.account == "****3000" for transaction in transactions)
    assert all(transaction.precision == "date" for transaction in transactions)
    assert [transaction.merchant_raw for transaction in transactions] == [
        "Закрытие счета",
        "Начисление процентов",
        "Открытие счета",
    ]

    opening_balance = Decimal("0")
    running_balance = opening_balance
    for transaction in reversed(transactions):
        balance_after = cast(Decimal, transaction.raw["balance_after"])
        assert running_balance + transaction.amount == balance_after
        running_balance = balance_after

    assert running_balance == Decimal("0")
    assert sum(
        (transaction.amount for transaction in transactions if transaction.amount > 0), Decimal("0")
    ) == Decimal("100003.58")
    assert sum(
        (-transaction.amount for transaction in transactions if transaction.amount < 0),
        Decimal("0"),
    ) == Decimal("100003.58")
    assert transactions[0].description.endswith("к/с 40817 810 0 5519 0181000")

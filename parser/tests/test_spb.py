# pyright: reportPrivateUsage=false
from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from lethal_expenses.parsers.base import BaseParser
from lethal_expenses.parsers.spb import SpbParser
from lethal_expenses.schema import Transaction


def find_by_merchant(transactions: Sequence[Transaction], merchant_raw: str) -> Transaction:
    return next(
        transaction for transaction in transactions if transaction.merchant_raw == merchant_raw
    )


def find_by_description_prefix(transactions: Sequence[Transaction], prefix: str) -> Transaction:
    return next(
        transaction for transaction in transactions if transaction.description.startswith(prefix)
    )


def spb_warnings(caplog: Any) -> list[str]:
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == "lethal_expenses.parsers.spb" and record.levelno >= logging.WARNING
    ]


def extract_spb_summary(statement_text: str) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    opening_balance: Decimal | None = None
    closing_balance: Decimal | None = None
    total_positive: Decimal | None = None
    total_negative: Decimal | None = None
    opening_re = re.compile(
        r"Входящий остаток(?: на \d{2}\.\d{2}\.\d{4})? (?P<amount>[+-]?\d[\d\s]*\.\d{2})$"
    )
    closing_re = re.compile(
        r"^Исходящий остаток(?: на \d{2}\.\d{2}\.\d{4})? (?P<amount>[+-]?\d[\d\s]*\.\d{2})$"
    )
    total_positive_re = re.compile(r"^Поступление (?P<amount>[+-]?\d[\d\s]*\.\d{2})$")
    total_negative_re = re.compile(r"^Списание (?P<amount>[+-]?\d[\d\s]*\.\d{2})$")

    for raw_line in statement_text.splitlines():
        line = BaseParser.collapse_spaces(raw_line)
        if not line:
            continue
        if (match := opening_re.search(line)) is not None:
            opening_balance = BaseParser.parse_amount(match.group("amount"), default_sign=1)
        elif (match := closing_re.search(line)) is not None:
            closing_balance = BaseParser.parse_amount(match.group("amount"), default_sign=1)
        elif (match := total_positive_re.search(line)) is not None:
            total_positive = BaseParser.parse_amount(match.group("amount"), default_sign=1)
        elif (match := total_negative_re.search(line)) is not None:
            total_negative = BaseParser.parse_amount(match.group("amount"), default_sign=1)

    if (
        opening_balance is None
        or closing_balance is None
        or total_positive is None
        or total_negative is None
    ):
        raise AssertionError("Missing SPB statement summary lines")

    return opening_balance, closing_balance, total_positive, total_negative


def test_spb_parser_handles_salary_transfer_and_counterparty_rows(
    synthetic_pdf_paths: dict[str, Path],
    caplog: Any,
) -> None:
    parser = SpbParser()
    pdf_path = synthetic_pdf_paths["spb"]

    with caplog.at_level(logging.WARNING, logger="lethal_expenses.parsers.spb"):
        assert parser.can_parse(pdf_path)
        transactions = list(parser.parse(pdf_path))

    assert spb_warnings(caplog) == []
    assert len(transactions) == 5
    assert len({transaction.id for transaction in transactions}) == 5
    assert sum(transaction.amount < 0 for transaction in transactions) == 3
    assert sum(transaction.amount > 0 for transaction in transactions) == 2
    assert all(transaction.bank == "spb" for transaction in transactions)
    assert all(transaction.account == "****4242" for transaction in transactions)
    assert all(transaction.precision == "date" for transaction in transactions)

    salary = find_by_merchant(transactions, "ИТМО")
    assert salary.amount == Decimal("55000.00")
    assert salary.description == "Зачисление зарплаты от УНИВЕРСИТЕТ ИТМО"
    assert salary.is_transfer is False

    outgoing_transfer = find_by_merchant(transactions, "Иван Иванович И")
    assert outgoing_transfer.amount == Decimal("-12000.00")
    assert "47422810990001089992" not in outgoing_transfer.description

    intra_bank = find_by_merchant(transactions, "Внутрибанковский перевод между своими счетами")
    assert intra_bank.amount == Decimal("-3500.00")
    assert intra_bank.raw["counterparty"] == "ПАО «БАНК САНКТ-ПЕТЕРБУРГ»"

    counterparty_row = find_by_merchant(transactions, "ООО Лента")
    assert counterparty_row.amount == Decimal("-4321.09")
    assert counterparty_row.description == "Покупка в супермаркете"

    incoming_transfer = find_by_merchant(transactions, "Анна Сергеевна П")
    assert incoming_transfer.amount == Decimal("8000.00")


def test_spb_parser_handles_dense_real_shape_families(
    synthetic_pdf_fixtures: dict[str, Path],
    caplog: Any,
) -> None:
    parser = SpbParser()
    pdf_path = synthetic_pdf_fixtures["spb_real_shapes_standalone"]
    statement_text = parser.extract_text(pdf_path)
    opening_balance, closing_balance, total_positive, total_negative = extract_spb_summary(
        statement_text
    )

    with caplog.at_level(logging.WARNING, logger="lethal_expenses.parsers.spb"):
        transactions = list(parser.parse(pdf_path))

    assert spb_warnings(caplog) == []
    assert len(transactions) == 12
    assert len({transaction.id for transaction in transactions}) == 12
    assert all(transaction.bank == "spb" for transaction in transactions)
    assert all(transaction.account == "****4242" for transaction in transactions)
    assert all(transaction.precision == "date" for transaction in transactions)

    salary = find_by_merchant(transactions, "ИТМО")
    assert salary.amount == Decimal("55000.00")
    assert salary.description.startswith("Зачисление зарплаты")
    assert salary.is_transfer is False

    short_outgoing = find_by_description_prefix(transactions, "Перевод по СБП")
    assert short_outgoing.amount == Decimal("-10000.00")
    assert short_outgoing.merchant_raw.startswith("Перевод по СБП")

    named_counterparty = find_by_merchant(transactions, "ПЕТРОВА АННА СЕРГЕЕВНА")
    assert named_counterparty.amount == Decimal("1000.00")
    assert named_counterparty.description.endswith("Интернет-банк")

    split_name = find_by_merchant(transactions, "Анна Сергеевна П из Сбербанк;")
    assert split_name.amount == Decimal("1500.00")
    assert "30233810990001041000" not in split_name.description

    incoming_sbp = next(
        transaction
        for transaction in transactions
        if transaction.description.startswith("Входящий перевод по СБП")
    )
    assert incoming_sbp.merchant_raw == "Иван Иванович И"
    assert "Код операции" in incoming_sbp.description

    outgoing_sbp = next(
        transaction
        for transaction in transactions
        if transaction.description.startswith("Исходящий перевод по СБП")
    )
    assert outgoing_sbp.amount == Decimal("-3000.00")
    assert outgoing_sbp.merchant_raw == "Иван Иванович И"

    phone_payment = find_by_merchant(
        transactions, 'Северо Западный филиал ОАО "МегаФон" (МегаФон Северо-Запад)'
    )
    assert phone_payment.amount == Decimal("-600.00")
    assert "Интернет" in phone_payment.description

    cashback = find_by_merchant(transactions, "Выплата поощрения")
    assert cashback.amount == Decimal("150.00")

    transfer_fee = find_by_merchant(transactions, "Комиссия за перевод")
    assert transfer_fee.amount == Decimal("-50.00")
    assert "20:34" in transfer_fee.description

    card_to_card = find_by_merchant(transactions, "Перевод с карты на карту")
    assert card_to_card.amount == Decimal("-3000.00")

    ozerki = find_by_merchant(transactions, "Ozerki N2192, g. Sankt-Pete, RU")
    assert ozerki.amount == Decimal("-753.00")
    assert "11:10" in ozerki.description

    split_name_person = find_by_merchant(transactions, "СИДОРОВ ПАВЕЛ АЛЕКСЕЕВИЧ")
    assert split_name_person.amount == Decimal("991.00")
    assert "@Composable" in split_name_person.description
    assert "Интернет" in split_name_person.description

    net_total = sum((transaction.amount for transaction in transactions), Decimal("0"))
    positive_total = sum(
        (transaction.amount for transaction in transactions if transaction.amount > 0), Decimal("0")
    )
    negative_total = sum(
        (transaction.amount for transaction in transactions if transaction.amount < 0), Decimal("0")
    )

    assert opening_balance + net_total == closing_balance
    assert positive_total == total_positive
    assert negative_total == total_negative


def test_spb_helpers_cover_dense_split_and_invalid_rows() -> None:
    parser = SpbParser()

    assert parser._split_primary_line("14.03.2026 ООО Ромашка Оплата услуг -650.50") == (
        "14.03.2026",
        "ООО Ромашка",
        "Оплата услуг",
        "-650.50",
    )
    assert parser._split_primary_line(
        '15.03.2026 ПАО "БАНК "САНКТ-ПЕТЕРБУРГ" Выплата поощрения в рамках Акции 25% 150.00'
    ) == (
        "15.03.2026",
        'ПАО "БАНК "САНКТ-ПЕТЕРБУРГ"',
        "Выплата поощрения в рамках Акции 25%",
        "150.00",
    )

    with pytest.raises(ValueError, match="Could not determine SPB account suffix"):
        parser._extract_header_account("Выписка" + "\n" + "Период: 01.01.2026 - 02.01.2026")

    with pytest.raises(ValueError, match="Could not split SPB row into columns"):
        parser._split_primary_line("14.03.2026 broken row")

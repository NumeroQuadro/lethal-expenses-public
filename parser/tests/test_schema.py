from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from lethal_expenses.parsers.base import BaseParser
from lethal_expenses.schema import (
    Transaction,
    export_transaction_json_schema,
    export_transaction_json_schema_json,
)

SCHEMA_SNAPSHOT_PATH = Path(__file__).parent / "fixtures" / "transaction_schema.snapshot.json"
EXPECTED_FIELDS = {
    "id",
    "date",
    "amount",
    "currency",
    "merchant_raw",
    "description",
    "bank",
    "account",
    "precision",
    "category",
    "is_transfer",
    "is_external_account",
    "transfer_pair_id",
    "raw",
}


def build_sample_transaction() -> Transaction:
    occurred_at = BaseParser.parse_date_ru("25.12.2025", "22:40")
    return Transaction(
        id=BaseParser.build_id("sber", "****7000", occurred_at, "903866"),
        date=occurred_at,
        amount=Decimal("-1234.56"),
        merchant_raw="Яндекс Такси",
        description="SBSCR_Яндекс Такси Операция по карте ****7000",
        bank="sberbank",
        account="****7000",
        raw={"auth_code": "903866", "category_label": "Транспорт"},
    )


def test_transaction_schema_field_set_matches_contract() -> None:
    assert set(Transaction.model_fields) == EXPECTED_FIELDS
    assert set(export_transaction_json_schema()["properties"]) == EXPECTED_FIELDS


def test_transaction_json_schema_snapshot() -> None:
    assert export_transaction_json_schema_json() == SCHEMA_SNAPSHOT_PATH.read_text(encoding="utf-8")


def test_transaction_round_trip_serialization() -> None:
    transaction = build_sample_transaction()
    restored = Transaction.model_validate_json(transaction.model_dump_json())

    assert restored == transaction
    assert restored.date.isoformat() == "2025-12-25T22:40:00+03:00"
    assert restored.precision == "minute"


def test_transaction_id_is_deterministic() -> None:
    occurred_at = BaseParser.parse_date_ru("25.12.2025", "22:40")

    first = BaseParser.build_id("sber", "****7000", occurred_at, "903866")
    second = BaseParser.build_id("sber", "****7000", occurred_at, "903866")

    assert first == second == "sber-7000-20251225-22:40-903866"


def test_transaction_allows_eds_account_identifier() -> None:
    occurred_at = BaseParser.parse_date_ru("24.04.2026", "12:50")

    transaction = Transaction(
        id="yandex-eds-2026-04-24T12:50:00+03:00-deadbeefcafe",
        date=occurred_at,
        amount=Decimal("5000.00"),
        merchant_raw="Tinkoff Black",
        description="Перевод с карты Tinkoff Black на Яндекс Счёт",
        bank="yandex",
        account="ЭДС",
        raw={"source_name": "synthetic-yandex.pdf"},
    )

    assert transaction.account == "ЭДС"


def test_transaction_requires_timezone_aware_date() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        Transaction(
            id="sber-7000-20251225-22:40-903866",
            date=datetime(2025, 12, 25, 22, 40),
            amount=Decimal("-1234.56"),
            merchant_raw="Яндекс Такси",
            description="SBSCR_Яндекс Такси Операция по карте ****7000",
            bank="sberbank",
            account="****7000",
            raw={},
        )


def test_transaction_requires_masked_account_or_eds() -> None:
    occurred_at = BaseParser.parse_date_ru("25.12.2025", "22:40")

    with pytest.raises(ValidationError, match="masked last-4 format"):
        Transaction(
            id="sber-7000-20251225-22:40-903866",
            date=occurred_at,
            amount=Decimal("-1234.56"),
            merchant_raw="Яндекс Такси",
            description="SBSCR_Яндекс Такси Операция по карте ****7000",
            bank="sberbank",
            account="7000",
            raw={},
        )

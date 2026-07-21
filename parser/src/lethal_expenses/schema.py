from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator

type BankName = Literal["sberbank", "yandex", "ozon", "spb"]
type CurrencyCode = Literal["RUB"]
type TransactionPrecision = Literal["second", "minute", "date"]

MOSCOW_TZ = ZoneInfo("Europe/Moscow")
ACCOUNT_MASK_RE = re.compile(r"^\*{4}\d{4}$")
EDS_ACCOUNT = "ЭДС"


class Transaction(BaseModel):
    """Canonical transaction contract shared by all parsers and the web app."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Deterministic transaction identifier.")
    date: datetime = Field(description="Local Moscow time with timezone information.")
    amount: Decimal = Field(description="Negative values are expenses; positive values are income.")
    currency: CurrencyCode = Field(default="RUB", description="Statement currency.")
    merchant_raw: str = Field(
        description="Cleaned merchant or counterparty as found in the source."
    )
    description: str = Field(description="Full source description for the transaction row.")
    bank: BankName = Field(description="Bank identifier for the source statement.")
    account: str = Field(
        description='Masked account suffix in the form "****1234" or the Yandex `ЭДС` bucket.'
    )
    precision: TransactionPrecision = Field(
        default="minute",
        description="Precision of the parsed source timestamp: second, minute, or date-only.",
    )
    category: str = Field(default="Прочее", description="Normalized category assigned later.")
    is_transfer: bool = Field(
        default=False,
        description="Whether the row is a detected self-transfer.",
    )
    is_external_account: bool = Field(
        default=False,
        description="Whether the row belongs to an external-owned account kept for pairing.",
    )
    transfer_pair_id: str | None = Field(
        default=None,
        description="Identifier shared by both sides of a detected transfer pair.",
    )
    raw: dict[str, Any] = Field(
        default_factory=dict,
        description="Original parsed row data preserved for debugging and reconciliation.",
    )

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("date must be timezone-aware and normalized to Moscow time")
        return value.astimezone(MOSCOW_TZ)

    @field_validator("account")
    @classmethod
    def validate_account(cls, value: str) -> str:
        if value != EDS_ACCOUNT and ACCOUNT_MASK_RE.fullmatch(value) is None:
            raise ValueError(
                'account must be either "ЭДС" or match the masked last-4 format "****1234"'
            )
        return value


def export_transaction_json_schema() -> dict[str, Any]:
    return Transaction.model_json_schema()


def export_transaction_json_schema_json() -> str:
    schema = export_transaction_json_schema()
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

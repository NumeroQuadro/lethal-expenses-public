from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from typing import Any, cast

from lethal_expenses.schema import MOSCOW_TZ, BankName, Transaction

ID_TOKEN_RE = re.compile(r"[^0-9A-Za-z._:-]+")
RUBLE_MARKER_RE = re.compile(r"₽|руб\.?", re.IGNORECASE)
UNICODE_MINUS_RE = re.compile(r"[–−]")


def extract_pdf_text(path: str | Path, *, max_pages: int | None = None) -> str:
    pdf_path = Path(path)
    pdfplumber = cast(Any, import_module("pdfplumber"))
    with pdfplumber.open(pdf_path) as pdf:
        pages = cast(list[Any], pdf.pages)
        if max_pages is not None:
            pages = pages[:max_pages]
        return "\n".join(cast(str | None, page.extract_text()) or "" for page in pages)


class BaseParser(ABC):
    bank: BankName

    def can_parse(self, path: str | Path) -> bool:
        return self.can_parse_text(self.extract_text(path, max_pages=1))

    @abstractmethod
    def can_parse_text(self, text: str) -> bool:
        """Return True when extracted statement text matches this bank."""

    @abstractmethod
    def parse_text(self, text: str, *, source_name: str | None = None) -> Iterable[Transaction]:
        """Parse extracted statement text into canonical transactions."""

    def extract_text(self, path: str | Path, *, max_pages: int | None = None) -> str:
        return extract_pdf_text(path, max_pages=max_pages)

    def parse(self, path: str | Path) -> Iterable[Transaction]:
        pdf_path = Path(path)
        if not self.can_parse(pdf_path):
            raise ValueError(f"{self.__class__.__name__} cannot parse {pdf_path}")
        statement_text = self.extract_text(pdf_path)
        return self.parse_text(statement_text, source_name=pdf_path.name)

    @staticmethod
    def collapse_spaces(value: str) -> str:
        normalized = value.replace("\xa0", " ").strip()
        return re.sub(r"\s+", " ", normalized)

    @classmethod
    def clean_merchant(cls, value: str) -> str:
        return cls.collapse_spaces(value).strip(" -")

    @classmethod
    def parse_amount(cls, value: str, *, default_sign: int = -1) -> Decimal:
        normalized = value.replace("\xa0", " ")
        normalized = normalized.replace("\x00", "")
        normalized = RUBLE_MARKER_RE.sub("", normalized)
        normalized = UNICODE_MINUS_RE.sub("-", normalized)
        normalized = cls.collapse_spaces(normalized)

        sign = Decimal("-1") if default_sign < 0 else Decimal("1")
        if normalized.startswith("+"):
            sign = Decimal("1")
            normalized = normalized[1:].lstrip()
        elif normalized.startswith("-"):
            sign = Decimal("-1")
            normalized = normalized[1:].lstrip()

        digits = normalized.replace(" ", "").replace(",", ".")
        return sign * Decimal(digits)

    @staticmethod
    def parse_date_ru(date_text: str, time_text: str | None = None) -> datetime:
        date_value = date_text.strip()
        if time_text is None:
            parsed = datetime.strptime(date_value, "%d.%m.%Y")
        else:
            normalized_time = time_text.strip()
            time_format = "%H:%M:%S" if normalized_time.count(":") == 2 else "%H:%M"
            parsed = datetime.strptime(
                f"{date_value} {normalized_time}",
                f"%d.%m.%Y {time_format}",
            )
        return parsed.replace(tzinfo=MOSCOW_TZ)

    @staticmethod
    def build_id(prefix: str, account: str, occurred_at: datetime, *parts: str) -> str:
        account_digits = re.sub(r"\D", "", account)[-4:]
        timestamp = occurred_at.astimezone(MOSCOW_TZ).strftime("%Y%m%d-%H:%M")
        cleaned_parts: list[str] = []
        for part in parts:
            cleaned = ID_TOKEN_RE.sub("", part.strip())
            if cleaned:
                cleaned_parts.append(cleaned)
        return "-".join([prefix, account_digits, timestamp, *cleaned_parts])

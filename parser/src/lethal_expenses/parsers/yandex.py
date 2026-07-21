from __future__ import annotations

import hashlib
import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass

from lethal_expenses.parsers.base import BaseParser
from lethal_expenses.schema import EDS_ACCOUNT, BankName, Transaction

LOGGER = logging.getLogger(__name__)

DATE_RE = r"\d{2}\.\d{2}\.\d{4}"
TIME_RE = r"\d{2}:\d{2}"
AMOUNT_RE = r"[+\-–−]\s?\d[\d\s]*,\d{2}(?:\s*[₽\x00])?"
CARD_RE = r"\*+\d{4}"

INLINE_METADATA_LINE_RE = re.compile(
    rf"^(?P<operation_date>{DATE_RE})\s+(?P<operation_time>{TIME_RE})\s+"
    rf"(?P<processing_date>{DATE_RE})(?:\s+(?P<card>{CARD_RE}))?\s+"
    rf"(?P<amount_operation>{AMOUNT_RE})\s+(?P<amount_esp>{AMOUNT_RE})$"
)
INLINE_COMBINED_ROW_RE = re.compile(
    rf"^(?P<description>.+?)\s+(?P<operation_date>{DATE_RE})\s+"
    rf"(?P<operation_time>{TIME_RE})\s+(?P<processing_date>{DATE_RE})"
    rf"(?:\s+(?P<card>{CARD_RE}))?\s+(?P<amount_operation>{AMOUNT_RE})\s+"
    rf"(?P<amount_esp>{AMOUNT_RE})$"
)
WRAPPED_MAIN_ROW_RE = re.compile(
    rf"^(?P<description>.+?)\s+(?P<operation_date>{DATE_RE})\s+"
    rf"(?P<processing_date>{DATE_RE})(?:\s+(?P<card>{CARD_RE}))?\s+"
    rf"(?P<amount_operation>{AMOUNT_RE})\s+(?P<amount_esp>{AMOUNT_RE})$"
)
CONTINUATION_TIME_RE = re.compile(
    rf"^(?P<description_tail>.*?)(?:,)?\s*в\s+(?P<operation_time>{TIME_RE})$",
    re.IGNORECASE,
)
SAVINGS_ROW_RE = re.compile(
    rf"^(?P<description>.+?)\s+(?P<operation_date>{DATE_RE})\s+(?P<amount>{AMOUNT_RE})$"
)
QR_MERCHANT_RE = re.compile(r"Оплата\s+СБП\s+QR\s*\((?P<merchant>[^)]+)\)", re.IGNORECASE)
SAVINGS_HEADER_ACCOUNT_PATTERNS = (
    re.compile(r"открыт\s+сч[её]т\s+(?P<account>\d{10,})", re.IGNORECASE),
    re.compile(r"(?P<account>\d{10,})\s+Номер\s+сч[её]та", re.IGNORECASE),
)

DESCRIPTION_PREFIXES = (
    re.compile(r"^Оплата\s+товаров\s+и\s+услуг\s+", re.IGNORECASE),
    re.compile(r"^Перевод\s+с\s+карты\s+", re.IGNORECASE),
    re.compile(r"^Возврат\s+покупки\s+", re.IGNORECASE),
)
TRANSFER_PREFIXES = (
    re.compile(r"^Входящий\s+перевод\s+СБП,\s*", re.IGNORECASE),
    re.compile(r"^Исходящий\s+перевод\s+СБП,\s*", re.IGNORECASE),
)
CARD_NOISE_PREFIXES = (
    "Яндекс Банк",
    "АО «Яндекс Банк»",
    "Файл содержит ",
    "Банковский период",
    "Период по ЭДС",
    "Выписка по карте",
    "Выписка по ЭДС",
    "Выписка по договору",
    "Выписка по Договору",
    "Продолжение на следующей странице",
    "Страница ",
    "Входящий остаток",
    "Исходящий остаток",
    "Всего расходных операций",
    "Всего приходных операций",
    "Всего операций",
)
CARD_TABLE_HEADER_PREFIXES = (
    "Описание операции",
    "Дата и время",
    "Дата обработки",
    "Сумма в валюте",
)
CARD_TABLE_HEADER_EXACT_LINES = {
    "Описание операции",
    "Дата и время операции МСК",
    "Дата обработки МСК",
    "Сумма в валюте операции",
    "Сумма в валюте ЭСП",
    "Дата и время",
    "Дата обработки",
    "операции",
    "обработки",
    "МСК",
    "Карта",
    "Дата",
    "ЭСП",
}
SAVINGS_NOISE_PREFIXES = (
    "Яндекс Банк",
    "АО «Яндекс Банк»",
    "Выписка по договору",
    "Выписка по Договору",
    "Входящий остаток",
    "Исходящий остаток",
    "Описание операции",
    "Всего расходных операций",
    "Всего приходных операций",
    "Всего операций",
    "Номер счёта",
    "Страница ",
    "Продолжение на следующей странице",
)
CARD_STATEMENT_MARKERS = (
    "файл содержит",
    "выписка по карте",
    "выписка по эдс",
    "банковский период",
    "дата и время операции",
)
SAVINGS_STATEMENT_MARKERS = (
    "договор банковского вклада",
    "сейв",
    "сумма в валюте договора",
    "в рамках договора открыт счёт",
)


@dataclass(slots=True)
class PendingWrappedTransaction:
    description_parts: list[str]
    operation_date: str
    processing_date: str
    card: str | None
    amount_operation: str
    amount_esp: str
    operation_time: str | None = None


class BaseYandexParser(BaseParser):
    bank: BankName = "yandex"

    def _has_yandex_header(self, text: str) -> bool:
        return "яндекс банк" in text.lower()

    def _normalize_account(self, card: str | None) -> str:
        if card is None:
            return EDS_ACCOUNT
        digits = re.sub(r"\D", "", card)
        return f"****{digits[-4:]}"

    def _extract_merchant_raw(self, description_lines: list[str]) -> str:
        first_line = description_lines[0]
        full_description = self.collapse_spaces(" ".join(description_lines))

        qr_match = QR_MERCHANT_RE.search(first_line)
        if qr_match is not None:
            return self.clean_merchant(qr_match.group("merchant"))

        for transfer_prefix in TRANSFER_PREFIXES:
            if transfer_prefix.match(full_description):
                stripped = transfer_prefix.sub("", full_description)
                return self.clean_merchant(stripped.split(",", 1)[0])

        merchant = first_line
        for description_prefix in DESCRIPTION_PREFIXES:
            merchant = description_prefix.sub("", merchant)

        if first_line.lower().startswith("перевод с карты "):
            return self.clean_merchant(first_line[len("Перевод с карты ") :])

        merchant = self.clean_merchant(merchant)
        if len(description_lines) > 1 and re.fullmatch(
            r"[A-Za-z0-9._/-]+(?:\s+[A-Za-z0-9._/-]+)*",
            merchant,
        ):
            continuation_tokens: list[str] = []
            for continuation_line in description_lines[1:]:
                cleaned_line = self.clean_merchant(continuation_line)
                if not re.fullmatch(
                    r"[A-Za-z0-9._/-]+(?:\s+[A-Za-z0-9._/-]+)*",
                    cleaned_line,
                ):
                    break
                continuation_tokens.append(cleaned_line)
            if continuation_tokens:
                merchant = self.clean_merchant(" ".join([merchant, *continuation_tokens]))

        return merchant

    def _build_row_hash(self, *parts: str) -> str:
        payload = "|".join(self.collapse_spaces(part) for part in parts)
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]


class YandexCardParser(BaseYandexParser):
    def can_parse_text(self, text: str) -> bool:
        normalized = text.lower()
        return self._has_yandex_header(text) and any(
            marker in normalized for marker in CARD_STATEMENT_MARKERS
        )

    def parse_text(self, text: str, *, source_name: str | None = None) -> Iterable[Transaction]:
        pending_description_lines: list[str] = []
        pending_wrapped: PendingWrappedTransaction | None = None
        inside_transaction_table = False

        for raw_line in text.splitlines():
            line = self.collapse_spaces(raw_line)
            if not line:
                continue

            if self._is_table_header_line(line):
                inside_transaction_table = True
                continue

            if self._is_noise(line):
                if self._ends_transaction_table(line):
                    if pending_wrapped is not None:
                        maybe_transaction = self._finalize_wrapped_transaction(
                            pending_wrapped,
                            source_name=source_name,
                        )
                        if maybe_transaction is not None:
                            yield maybe_transaction
                        pending_wrapped = None
                    if pending_description_lines:
                        self._warn_dropped_lines(
                            pending_description_lines,
                            source_name=source_name,
                            reason="description lines without metadata",
                        )
                        pending_description_lines = []
                    inside_transaction_table = False
                continue

            inline_combined_match = INLINE_COMBINED_ROW_RE.match(line)
            if inline_combined_match is not None:
                inside_transaction_table = True
                if pending_wrapped is not None:
                    maybe_transaction = self._finalize_wrapped_transaction(
                        pending_wrapped,
                        source_name=source_name,
                    )
                    if maybe_transaction is not None:
                        yield maybe_transaction
                    pending_wrapped = None
                if pending_description_lines:
                    self._warn_dropped_lines(
                        pending_description_lines,
                        source_name=source_name,
                        reason="description lines without metadata",
                    )
                    pending_description_lines = []
                yield self._build_transaction(
                    [inline_combined_match.group("description")],
                    operation_date=inline_combined_match.group("operation_date"),
                    operation_time=inline_combined_match.group("operation_time"),
                    processing_date=inline_combined_match.group("processing_date"),
                    card=inline_combined_match.group("card"),
                    amount_operation=inline_combined_match.group("amount_operation"),
                    amount_esp=inline_combined_match.group("amount_esp"),
                    source_name=source_name,
                )
                continue

            inline_metadata_match = INLINE_METADATA_LINE_RE.match(line)
            if inline_metadata_match is not None:
                inside_transaction_table = True
                if pending_wrapped is not None:
                    maybe_transaction = self._finalize_wrapped_transaction(
                        pending_wrapped,
                        source_name=source_name,
                    )
                    if maybe_transaction is not None:
                        yield maybe_transaction
                    pending_wrapped = None
                if not pending_description_lines:
                    continue
                yield self._build_transaction(
                    pending_description_lines,
                    operation_date=inline_metadata_match.group("operation_date"),
                    operation_time=inline_metadata_match.group("operation_time"),
                    processing_date=inline_metadata_match.group("processing_date"),
                    card=inline_metadata_match.group("card"),
                    amount_operation=inline_metadata_match.group("amount_operation"),
                    amount_esp=inline_metadata_match.group("amount_esp"),
                    source_name=source_name,
                )
                pending_description_lines = []
                continue

            wrapped_main_match = WRAPPED_MAIN_ROW_RE.match(line)
            if wrapped_main_match is not None:
                inside_transaction_table = True
                if pending_wrapped is not None:
                    maybe_transaction = self._finalize_wrapped_transaction(
                        pending_wrapped,
                        source_name=source_name,
                    )
                    if maybe_transaction is not None:
                        yield maybe_transaction
                if pending_description_lines:
                    self._warn_dropped_lines(
                        pending_description_lines,
                        source_name=source_name,
                        reason="description lines without metadata",
                    )
                    pending_description_lines = []
                pending_wrapped = PendingWrappedTransaction(
                    description_parts=[wrapped_main_match.group("description")],
                    operation_date=wrapped_main_match.group("operation_date"),
                    processing_date=wrapped_main_match.group("processing_date"),
                    card=wrapped_main_match.group("card"),
                    amount_operation=wrapped_main_match.group("amount_operation"),
                    amount_esp=wrapped_main_match.group("amount_esp"),
                )
                continue

            if pending_wrapped is not None:
                continuation_time_match = CONTINUATION_TIME_RE.match(line)
                if continuation_time_match is not None:
                    description_tail = self.clean_merchant(
                        continuation_time_match.group("description_tail") or ""
                    )
                    if description_tail:
                        pending_wrapped.description_parts.append(description_tail)
                    pending_wrapped.operation_time = continuation_time_match.group("operation_time")
                    continue
                pending_wrapped.description_parts.append(line)
                continue

            if inside_transaction_table:
                pending_description_lines.append(line)
                continue

        if pending_wrapped is not None:
            maybe_transaction = self._finalize_wrapped_transaction(
                pending_wrapped,
                source_name=source_name,
            )
            if maybe_transaction is not None:
                yield maybe_transaction

        if pending_description_lines:
            self._warn_dropped_lines(
                pending_description_lines,
                source_name=source_name,
                reason="description lines without metadata",
            )

    def _is_table_header_line(self, line: str) -> bool:
        normalized = line.lower()
        return (
            line in CARD_TABLE_HEADER_EXACT_LINES
            or any(line.startswith(prefix) for prefix in CARD_TABLE_HEADER_PREFIXES)
            or normalized.startswith("операции обработки операции")
            or normalized == "мск мск"
        )

    def _is_noise(self, line: str) -> bool:
        return any(line.startswith(prefix) for prefix in CARD_NOISE_PREFIXES)

    def _ends_transaction_table(self, line: str) -> bool:
        return line.startswith(
            (
                "Всего расходных операций",
                "Всего приходных операций",
                "Всего операций",
            )
        )

    def _warn_dropped_lines(
        self,
        lines: list[str],
        *,
        source_name: str | None,
        reason: str,
    ) -> None:
        source_label = source_name or "<text>"
        for line in lines:
            LOGGER.warning(
                "Dropped Yandex card line in %s (%s): %s",
                source_label,
                reason,
                line,
            )

    def _finalize_wrapped_transaction(
        self,
        pending_wrapped: PendingWrappedTransaction,
        *,
        source_name: str | None,
    ) -> Transaction | None:
        if pending_wrapped.operation_time is None:
            self._warn_dropped_lines(
                pending_wrapped.description_parts,
                source_name=source_name,
                reason="wrapped row without operation time",
            )
            return None

        return self._build_transaction(
            pending_wrapped.description_parts,
            operation_date=pending_wrapped.operation_date,
            operation_time=pending_wrapped.operation_time,
            processing_date=pending_wrapped.processing_date,
            card=pending_wrapped.card,
            amount_operation=pending_wrapped.amount_operation,
            amount_esp=pending_wrapped.amount_esp,
            source_name=source_name,
        )

    def _build_transaction(
        self,
        description_lines: list[str],
        *,
        operation_date: str,
        operation_time: str,
        processing_date: str,
        card: str | None,
        amount_operation: str,
        amount_esp: str,
        source_name: str | None,
    ) -> Transaction:
        description = self.collapse_spaces(" ".join(description_lines))
        account = self._normalize_account(card)
        occurred_at = self.parse_date_ru(operation_date, operation_time)
        amount = self.parse_amount(amount_operation)
        merchant_raw = self._extract_merchant_raw(description_lines)
        account_token = "eds" if account == EDS_ACCOUNT else re.sub(r"\D", "", account)[-4:]
        row_hash = self._build_row_hash(
            description,
            processing_date,
            account,
            amount_operation,
            amount_esp,
        )

        return Transaction(
            id=f"yandex-{account_token}-{occurred_at.isoformat()}-{row_hash}",
            date=occurred_at,
            amount=amount,
            merchant_raw=merchant_raw,
            description=description,
            bank=self.bank,
            account=account,
            precision="minute",
            raw={
                "processing_date": processing_date,
                "card": card,
                "amount_operation": amount_operation,
                "amount_esp": amount_esp,
                "source_name": source_name,
            },
        )


class YandexSavingsParser(BaseYandexParser):
    def can_parse_text(self, text: str) -> bool:
        normalized = text.lower()
        return self._has_yandex_header(text) and any(
            marker in normalized for marker in SAVINGS_STATEMENT_MARKERS
        )

    def parse_text(self, text: str, *, source_name: str | None = None) -> Iterable[Transaction]:
        account = self._extract_header_account(text)

        for raw_line in text.splitlines():
            line = self.collapse_spaces(raw_line)
            if not line or self._is_noise(line):
                continue

            match = SAVINGS_ROW_RE.match(line)
            if match is None:
                continue

            yield self._build_transaction(
                account=account,
                description=match.group("description"),
                operation_date=match.group("operation_date"),
                amount_text=match.group("amount"),
                source_name=source_name,
            )

    def _is_noise(self, line: str) -> bool:
        return any(line.startswith(prefix) for prefix in SAVINGS_NOISE_PREFIXES)

    def _extract_header_account(self, text: str) -> str:
        for pattern in SAVINGS_HEADER_ACCOUNT_PATTERNS:
            match = pattern.search(text)
            if match is not None:
                digits = re.sub(r"\D", "", match.group("account"))
                return f"****{digits[-4:]}"
        raise ValueError("Could not determine Yandex savings account suffix from statement header")

    def _build_transaction(
        self,
        *,
        account: str,
        description: str,
        operation_date: str,
        amount_text: str,
        source_name: str | None,
    ) -> Transaction:
        normalized_description = self.clean_merchant(description)
        occurred_at = self.parse_date_ru(operation_date)
        row_hash = self._build_row_hash(
            normalized_description,
            operation_date,
            amount_text,
            account,
        )
        account_token = re.sub(r"\D", "", account)[-4:]

        return Transaction(
            id=f"yandex-{account_token}-{occurred_at.isoformat()}-{row_hash}",
            date=occurred_at,
            amount=self.parse_amount(amount_text),
            merchant_raw=normalized_description,
            description=normalized_description,
            bank=self.bank,
            account=account,
            precision="date",
            raw={
                "source_name": source_name,
                "amount_operation": amount_text,
            },
        )


YandexParser = YandexCardParser

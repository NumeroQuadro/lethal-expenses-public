from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter
from collections.abc import Iterable

from lethal_expenses.parsers.base import BaseParser
from lethal_expenses.schema import BankName, Transaction

LOGGER = logging.getLogger(__name__)

DATE_RE = r"\d{2}\.\d{2}\.\d{4}"
AMOUNT_RE = r"[+-]?\d[\d\s]*\.\d{2}"

DATE_LINE_RE = re.compile(rf"^(?P<date>{DATE_RE})\b")
TRAILING_AMOUNT_RE = re.compile(rf"(?P<amount>{AMOUNT_RE})$")
HEADER_ACCOUNT_RE = re.compile(r"Сч[её]т:\s*(?P<account>\d+)")
ACCOUNT_NUMBER_LINE_RE = re.compile(r"^\d{10,}$")
ACCOUNT_NUMBER_PREFIX_RE = re.compile(r"^(?P<account>\d{10,})(?:\s+(?P<rest>.*))?$")
COUNTERPARTY_ACCOUNT_RE = re.compile(r"\b\d{10,}\b")
BANK_SELF_RE = re.compile(
    r'^(?:ПАО\s+[«"]?БАНК\s+САНКТ-?ПЕТЕРБУРГ[»"]?|PAO\s+"Bank\s+"Sankt-Pe,\s*Sankt-Peterburg,?)$',
    re.IGNORECASE,
)
SALARY_RE = re.compile(r"^Зачисление\s+зарплаты\s+от\s+(?P<source>.+)$", re.IGNORECASE)
SBP_RE = re.compile(
    r"^(?:(?:Исходящий|Входящий)\s+перевод(?:\s+по\s+СБП|\s+СБП)?|Перевод(?:\s+по\s+СБП|\s+денежных\s+средств)?)\s*,?\s*(?P<name>.+)$",
    re.IGNORECASE,
)
PHONE_PAYMENT_RE = re.compile(r"^Оплата\s+за\s+телефон\b.*?\s+в\s+(?P<merchant>.+)$", re.IGNORECASE)
SELF_BANK_PREFIXES = (
    'ПАО "БАНК "САНКТ-ПЕТЕРБУРГ"',
    "ПАО «БАНК САНКТ-ПЕТЕРБУРГ»",
    'PAO "Bank "Sankt-Pe, Sankt-Peterburg,',
)
OPERATION_START_MARKERS = (
    re.compile(r"Зачисление\b", re.IGNORECASE),
    re.compile(r"Входящий\s+перевод\b", re.IGNORECASE),
    re.compile(r"Исходящий\s+перевод\b", re.IGNORECASE),
    re.compile(r"Перевод\b", re.IGNORECASE),
    re.compile(r"Оплата\b", re.IGNORECASE),
    re.compile(r"Покупка\b", re.IGNORECASE),
    re.compile(r"Выплата\b", re.IGNORECASE),
    re.compile(r"Комиссия\b", re.IGNORECASE),
    re.compile(r"@\S+"),
)
NAME_TAIL_RE = re.compile(
    r"^(?P<name>(?:[А-ЯЁ][А-ЯЁ-]+(?:\s+[А-ЯЁ][А-ЯЁ-]+){0,2}))\s+(?P<rest>.+)$"
)
PAGE_STAMP_RE = re.compile(r'^ПАО\s+"БАНК\s+"САНКТ-ПЕТЕРБУРГ"\s+\d+/\d+\s+', re.IGNORECASE)
NOISE_PREFIXES = (
    "Выписка",
    "Период:",
    "Счёт:",
    "Дата Плательщик / Получатель Операция Сумма",
    "Дата |",
    "Итого",
    "Всего",
    "Поступление ",
    "Списание ",
    "Исходящий остаток на ",
)
NOISE_EXACT_LINES = {"операции"}


class SpbParser(BaseParser):
    bank: BankName = "spb"

    def can_parse_text(self, text: str) -> bool:
        normalized = text.lower()
        return "выписка" in normalized and "период:" in normalized and "счёт:" in normalized

    def parse_text(self, text: str, *, source_name: str | None = None) -> Iterable[Transaction]:
        header_account = self._extract_header_account(text)
        blocks = self._collect_blocks(text, source_name=source_name)
        block_totals = Counter(tuple(block) for block in blocks)
        block_seen: Counter[tuple[str, ...]] = Counter()

        for block in blocks:
            signature = tuple(block)
            block_seen[signature] += 1
            duplicate_occurrence = None
            if block_totals[signature] > 1:
                duplicate_occurrence = block_seen[signature]
            yield self._build_transaction(
                block,
                header_account=header_account,
                source_name=source_name,
                duplicate_occurrence=duplicate_occurrence,
            )

    def _collect_blocks(self, text: str, *, source_name: str | None) -> list[list[str]]:
        blocks: list[list[str]] = []
        pending_lines: list[str] = []

        for raw_line in text.splitlines():
            line = self._normalize_text(raw_line.replace("\x00", ""))
            if not line:
                continue

            if self._is_noise_line(line):
                continue

            if DATE_LINE_RE.match(line):
                if pending_lines:
                    blocks.append(pending_lines)
                pending_lines = [line]
                continue

            if pending_lines:
                pending_lines.append(line)
                continue

            LOGGER.warning(
                "Dropped SPB line in %s (orphan line): %s",
                source_name or "<memory>",
                line,
            )

        if pending_lines:
            blocks.append(pending_lines)

        return blocks

    def _extract_header_account(self, text: str) -> str:
        match = HEADER_ACCOUNT_RE.search(text)
        if match is None:
            raise ValueError("Could not determine SPB account suffix from statement header")
        digits = re.sub(r"\D", "", match.group("account"))
        return f"****{digits[-4:]}"

    def _is_noise_line(self, line: str) -> bool:
        return (
            line in NOISE_EXACT_LINES
            or any(line.startswith(prefix) for prefix in NOISE_PREFIXES)
            or line.startswith("БИК ")
            or PAGE_STAMP_RE.match(line) is not None
        )

    def _normalize_text(self, value: str) -> str:
        normalized = self.clean_merchant(value)
        normalized = re.sub(r"Интернет-\s+банк", "Интернет-банк", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\.{2,}", ".", normalized)
        normalized = re.sub(r"\.\s+\.", ".", normalized)
        normalized = re.sub(r",\s*,", ",", normalized)
        return self.clean_merchant(normalized)

    def _find_operation_start(self, value: str) -> int | None:
        matches = [
            match.start()
            for pattern in OPERATION_START_MARKERS
            if (match := pattern.search(value)) is not None
        ]
        if not matches:
            return None
        return min(matches)

    def _split_dense_body(self, body: str, *, original_line: str) -> tuple[str, str]:
        for prefix in SELF_BANK_PREFIXES:
            if body.startswith(prefix):
                operation = self._normalize_text(body[len(prefix) :].lstrip(" ,"))
                if not operation:
                    raise ValueError(f"Could not split SPB row into columns: {original_line}")
                return prefix, operation

        operation_start = self._find_operation_start(body)
        if operation_start is None:
            raise ValueError(f"Could not split SPB row into columns: {original_line}")

        if operation_start == 0:
            return "", self._normalize_text(body)

        counterparty = self._normalize_text(body[:operation_start].rstrip(" ,"))
        operation = self._normalize_text(body[operation_start:].lstrip(" ,"))
        if not counterparty or not operation:
            raise ValueError(f"Could not split SPB row into columns: {original_line}")
        return counterparty, operation

    def _split_primary_line(self, line: str) -> tuple[str, str, str, str]:
        if "|" in line:
            parts = [self.collapse_spaces(part) for part in line.split("|")]
            if len(parts) == 4:
                return parts[0], parts[1], parts[2], parts[3]

        parts = re.split(r"\s{2,}", line, maxsplit=3)
        if len(parts) == 4:
            return parts[0], parts[1], parts[2], parts[3]

        date_match = DATE_LINE_RE.match(line)
        amount_match = TRAILING_AMOUNT_RE.search(line)
        if date_match is None or amount_match is None:
            raise ValueError(f"Could not split SPB row into columns: {line}")

        date_text = date_match.group("date")
        body = self.collapse_spaces(line[date_match.end() : amount_match.start()])
        amount_text = amount_match.group("amount")
        counterparty, operation = self._split_dense_body(body, original_line=line)
        return date_text, counterparty, operation, amount_text

    def _strip_account_prefix(self, line: str) -> str | None:
        if ACCOUNT_NUMBER_LINE_RE.fullmatch(line):
            return None

        match = ACCOUNT_NUMBER_PREFIX_RE.match(line)
        if match is None:
            return self.collapse_spaces(line).strip()

        rest = self.collapse_spaces(match.group("rest") or "").strip()
        return rest or None

    def _consume_name_tail(self, line: str) -> tuple[str | None, str]:
        match = NAME_TAIL_RE.match(line)
        if match is None:
            return None, line
        return self._normalize_text(match.group("name")), self._normalize_text(match.group("rest"))

    def _derive_from_operation(self, operation: str) -> str:
        salary_match = SALARY_RE.match(operation)
        if salary_match is not None:
            source = self.clean_merchant(salary_match.group("source"))
            acronym_tokens = re.findall(r"[A-ZА-ЯЁ]{2,}", source)
            return acronym_tokens[-1] if acronym_tokens else source

        if operation.lower().startswith("комиссия за оказание услуги"):
            return "Комиссия за перевод"

        if operation.lower().startswith("перевод с карты на карту"):
            return "Перевод с карты на карту"

        sbp_match = SBP_RE.match(operation)
        if sbp_match is not None:
            candidate = self.clean_merchant(sbp_match.group("name"))
            for fragment in candidate.split(","):
                cleaned_fragment = self.clean_merchant(COUNTERPARTY_ACCOUNT_RE.sub("", fragment))
                cleaned_fragment = (
                    cleaned_fragment.split("НДС", 1)[0].split("Код операции", 1)[0].strip(" .,")
                )
                if cleaned_fragment and re.search(r"[0-9A-Za-zА-Яа-яЁё]", cleaned_fragment):
                    return cleaned_fragment
            return self.clean_merchant(operation)

        phone_match = PHONE_PAYMENT_RE.match(operation)
        if phone_match is not None:
            merchant = phone_match.group("merchant")
            merchant = merchant.split("НДС", 1)[0]
            return self.clean_merchant(merchant)

        if operation.lower().startswith("выплата поощрения"):
            return "Выплата поощрения"

        return self.clean_merchant(operation)

    def _counterparty_is_bank_self(self, counterparty: str) -> bool:
        normalized = self.clean_merchant(re.sub(r'[«»"]', " ", counterparty)).lower()
        normalized = re.sub(r"\s+", " ", normalized)
        return "банк санкт-петербург" in normalized or "bank sankt-pe" in normalized

    def _extract_merchant_raw(self, counterparty: str, operation: str) -> str:
        cleaned_counterparty = self.clean_merchant(COUNTERPARTY_ACCOUNT_RE.sub("", counterparty))
        if not cleaned_counterparty or self._counterparty_is_bank_self(cleaned_counterparty):
            return self._derive_from_operation(operation)
        return cleaned_counterparty

    def _row_hash(
        self,
        counterparty: str,
        operation: str,
        amount: str,
        duplicate_occurrence: int | None,
    ) -> str:
        payload = "|".join([counterparty, operation, self.collapse_spaces(amount)])
        if duplicate_occurrence is not None:
            payload = f"{payload}|dup:{duplicate_occurrence}"
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]

    def _build_transaction(
        self,
        lines: list[str],
        *,
        header_account: str,
        source_name: str | None,
        duplicate_occurrence: int | None,
    ) -> Transaction:
        date_text, counterparty, operation, amount_text = self._split_primary_line(lines[0])

        continuation_lines: list[str] = []
        for line in lines[1:]:
            cleaned_line = self._strip_account_prefix(line)
            if cleaned_line is None:
                continue
            continuation_lines.append(cleaned_line)

        if (
            continuation_lines
            and counterparty
            and not self._counterparty_is_bank_self(counterparty)
        ):
            name_tail, remainder = self._consume_name_tail(continuation_lines[0])
            if name_tail is not None:
                counterparty = self._normalize_text(f"{counterparty} {name_tail}")
                if remainder:
                    continuation_lines[0] = remainder
                else:
                    continuation_lines.pop(0)

        operation_parts = [operation, *continuation_lines]
        operation = self._normalize_text(" ".join(part for part in operation_parts if part))
        counterparty = self._normalize_text(counterparty)
        merchant_raw = self._extract_merchant_raw(counterparty, operation)
        occurred_at = self.parse_date_ru(date_text)
        row_hash = self._row_hash(counterparty, operation, amount_text, duplicate_occurrence)

        raw: dict[str, object] = {
            "counterparty": counterparty,
            "amount_text": amount_text,
            "source_name": source_name,
        }
        if duplicate_occurrence is not None:
            raw["duplicate_occurrence"] = duplicate_occurrence

        return Transaction(
            id=self.build_id("spb", header_account, occurred_at, row_hash),
            date=occurred_at,
            amount=self.parse_amount(amount_text, default_sign=1),
            merchant_raw=merchant_raw,
            description=operation,
            bank=self.bank,
            account=header_account,
            precision="date",
            raw=raw,
        )

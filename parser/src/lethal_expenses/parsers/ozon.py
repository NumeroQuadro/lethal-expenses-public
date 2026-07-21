from __future__ import annotations

import hashlib
import logging
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from lethal_expenses.parsers.base import BaseParser
from lethal_expenses.schema import BankName, Transaction

LOGGER = logging.getLogger(__name__)

DATE_RE = r"\d{2}\.\d{2}\.\d{4}"
TIME_RE = r"\d{2}:\d{2}:\d{2}"
AMOUNT_RE = r"[+\-–−]\s?\d[\d\s]*[.,]\d{2}(?:\s*[₽\x00])?"
RUBLE_AMOUNT_RE = r"[+\-–−]\s?\d[\d\s]*[.,]\d{2}(?:\s*₽)?"
SECONDARY_AMOUNT_RE = r"[+\-–−]\s?\d[\d\s]*[.,]\d{2}(?:\s*(?:₽|\$|€|£|[A-Z]{3}))?"

HEADER_ACCOUNT_RE = re.compile(
    r"Номер\s+лицевого\s+сч[её]та:\s*№\s*(?P<account>\d+)",
    re.IGNORECASE,
)
TRANSACTION_RE = re.compile(rf"^(?P<date>{DATE_RE})\s+(?P<document>\S+)\s+(?P<rest>.+)$")
AMOUNT_TAIL_RE = re.compile(rf"(?P<amount>{AMOUNT_RE})\s+(?P<currency>[A-ZА-Я]{{3}})$")
SAVINGS_ANCHOR_RE = re.compile(
    rf"^(?P<head>.*?)(?P<amount_rub>{RUBLE_AMOUNT_RE})\s+(?P<amount_tail>{RUBLE_AMOUNT_RE})$"
)
SAVINGS_PREFIX_RE = re.compile(
    rf"^(?:(?P<date>{DATE_RE})\s+)?(?:(?P<time>{TIME_RE})\s+)?(?P<document>\d{{1,12}})\b"
)
CARD_ANCHOR_RE = re.compile(
    rf"^(?P<head>.*?)(?P<amount_rub>{RUBLE_AMOUNT_RE})\s+(?P<amount_tail>{SECONDARY_AMOUNT_RE})$"
)
CARD_PREFIX_RE = re.compile(
    rf"^(?:(?P<date>{DATE_RE})\s+)?(?:(?P<time>{TIME_RE})\s+)?(?P<document>\d{{1,12}})\b"
)
CARD_DATE_RE = re.compile(DATE_RE)
CARD_TIME_RE = re.compile(TIME_RE)
SAVINGS_DATE_RE = re.compile(DATE_RE)
SAVINGS_TIME_RE = re.compile(TIME_RE)
SAVINGS_LEADING_DATE_RE = re.compile(rf"^(?P<date>{DATE_RE})\b\s*")
SAVINGS_LEADING_TIME_RE = re.compile(rf"^(?P<time>{TIME_RE})\b\s*")
CARD_LEADING_DATE_RE = re.compile(rf"^(?P<date>{DATE_RE})\b\s*")
CARD_LEADING_TIME_RE = re.compile(rf"^(?P<time>{TIME_RE})\b\s*")
CARD_TRANSACTION_START_RE = re.compile(
    r"^(Перевод|Оплата|Возврат|Зачисление|Платеж|Выплата|Пополнение|Отмена\s+перевода)\b",
    re.IGNORECASE,
)
CARD_CONTINUATION_RE = re.compile(
    r"^(?:Оплата\s+услуг\s+по\s+счету\s+\d+\s+//\s+ID:\d+\.|Получатель:\s+.+)$",
    re.IGNORECASE,
)
CARD_SERVICE_FRAGMENT_RE = re.compile(
    r"(?:Без\s+НДС\.?|НДС\s+не\s+облагается\.?)",
    re.IGNORECASE,
)

NOISE_PREFIXES = (
    "ООО «ОЗОН Банк»",
    "Справка о движении средств",
    "Дата операции",
    "Номер лицевого счёта:",
    "Период:",
    "Итого",
    "Всего",
)
CARD_NOISE_PREFIXES = NOISE_PREFIXES + (
    "вн.тер.г.",
    "Пресненская набережная",
    "ИНН/КПП",
    "Лицензия Банка России",
    "№ Ф-",
    "Владелец:",
    "Дата и время формирования документа:",
    "Период выписки:",
    "Валюта:",
    "Входящий остаток:",
    "Исходящий остаток:",
    "Сумма операции",
    "Дата операции Документ",
    "Российские рубли Валюта",
    "С уважением,",
    "Руководитель управления",
    "мидл-офисных операций",
    "департамента клиентского",
    "сервиса ",
    "Справка сформирована автоматически",
    "документа. Возможные",
    "Продолжение на следующей странице",
    "Страница ",
)
CARD_OWNER_NAME_RE = re.compile(r"^[А-ЯЁ][а-яё-]+(?:\s+[А-ЯЁ][а-яё-]+){2}$")
SAVINGS_NOISE_PREFIXES = NOISE_PREFIXES + (
    "Входящий остаток:",
    "Исходящий остаток:",
    "Сумма операции",
    "Российские рубли Валюта",
    "С уважением,",
    "Руководитель",
    "департамента клиентского",
    "сервиса ",
    "Справка сформирована автоматически",
    "документа. Возможные",
)
SELF_TRANSFER_TEXT = "Перевод собственных средств. Без НДС."
CARD_ACCOUNT_PREFIX = "408178109"
SAVINGS_ACCOUNT_PREFIX = "408178102"


@dataclass(frozen=True)
class CardLine:
    text: str
    account: str


class BaseOzonParser(BaseParser):
    bank: BankName = "ozon"

    def _has_ozon_header(self, text: str) -> bool:
        normalized = text.lower()
        return "озон банк" in normalized and "справка о движении средств" in normalized

    def _matches_account_prefix(self, text: str, *, prefix: str) -> bool:
        try:
            account_digits = self._extract_header_account_digits(text)
        except ValueError:
            return False
        return account_digits.startswith(prefix)

    def parse_text(self, text: str, *, source_name: str | None = None) -> Iterable[Transaction]:
        header_account = self._extract_header_account(text)
        pending_lines: list[str] = []

        for raw_line in text.splitlines():
            line = self.collapse_spaces(raw_line.replace("\x00", ""))
            if not line:
                continue

            if self._is_noise(line):
                continue

            if re.match(rf"^{DATE_RE}\b", line):
                if pending_lines:
                    yield self._build_transaction(
                        pending_lines,
                        header_account=header_account,
                        source_name=source_name,
                    )
                pending_lines = [line]
                continue

            if pending_lines:
                pending_lines.append(line)

        if pending_lines:
            yield self._build_transaction(
                pending_lines,
                header_account=header_account,
                source_name=source_name,
            )

    def _extract_header_account_digits(self, text: str) -> str:
        match = HEADER_ACCOUNT_RE.search(text)
        if match is None:
            raise ValueError("Could not determine Ozon account suffix from statement header")
        return re.sub(r"\D", "", match.group("account"))

    def _mask_account(self, account_digits: str) -> str:
        return f"****{account_digits[-4:]}"

    def _extract_header_account(self, text: str) -> str:
        return self._mask_account(self._extract_header_account_digits(text))

    def _is_noise(self, line: str) -> bool:
        return any(line.startswith(prefix) for prefix in NOISE_PREFIXES)

    def _row_hash(self, document: str, description: str, amount: str) -> str:
        payload = "|".join([document, description, self.collapse_spaces(amount)])
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]

    def _build_transaction(
        self,
        lines: list[str],
        *,
        header_account: str,
        source_name: str | None,
    ) -> Transaction:
        row_text = self.collapse_spaces(" ".join(lines).replace("\x00", ""))
        match = TRANSACTION_RE.match(row_text)
        if match is None:
            raise ValueError(f"Could not parse Ozon transaction row: {row_text}")

        rest = match.group("rest")
        amount_tail_match = AMOUNT_TAIL_RE.search(rest)
        if amount_tail_match is None:
            raise ValueError(f"Could not parse Ozon amount tail: {row_text}")

        occurred_at = self.parse_date_ru(match.group("date"))
        document = match.group("document")
        description = self.clean_merchant(rest[: amount_tail_match.start()])
        amount_text = amount_tail_match.group("amount")
        row_hash = self._row_hash(document, description, amount_text)
        is_likely_self_transfer = description.startswith(SELF_TRANSFER_TEXT)

        return Transaction(
            id=self.build_id("ozon", header_account, occurred_at, row_hash),
            date=occurred_at,
            amount=self.parse_amount(amount_text),
            merchant_raw=description,
            description=description,
            bank=self.bank,
            account=header_account,
            precision="date",
            raw={
                "document": document,
                "currency": amount_tail_match.group("currency"),
                "is_likely_self_transfer": is_likely_self_transfer,
                "source_name": source_name,
            },
        )


class OzonCardParser(BaseOzonParser):
    def can_parse_text(self, text: str) -> bool:
        return self._has_ozon_header(text) and self._matches_account_prefix(
            text,
            prefix=CARD_ACCOUNT_PREFIX,
        )

    def parse_text(self, text: str, *, source_name: str | None = None) -> Iterable[Transaction]:
        lines = self._collect_card_lines(text)
        anchor_indexes = [
            index
            for index, line in enumerate(lines)
            if CARD_ANCHOR_RE.search(line.text) is not None
        ]

        if not anchor_indexes:
            for line in lines:
                self._warn_dropped_card_line(
                    line.text,
                    source_name=source_name,
                    reason="non-noise line without anchor",
                )
            return

        used_indexes: set[int] = set()
        for anchor_position, anchor_index in enumerate(anchor_indexes):
            previous_anchor = anchor_indexes[anchor_position - 1] if anchor_position > 0 else None
            next_anchor = (
                anchor_indexes[anchor_position + 1]
                if anchor_position + 1 < len(anchor_indexes)
                else None
            )
            transaction, consumed_indexes = self._build_card_transaction(
                lines,
                anchor_index=anchor_index,
                previous_anchor_index=previous_anchor,
                next_anchor_index=next_anchor,
                source_name=source_name,
            )
            used_indexes.update(consumed_indexes)
            yield transaction

        for index, line in enumerate(lines):
            if index in used_indexes:
                continue
            self._warn_dropped_card_line(
                line.text,
                source_name=source_name,
                reason="unclassified card line",
            )

    def _collect_card_lines(self, text: str) -> list[CardLine]:
        lines: list[CardLine] = []
        current_account: str | None = None

        for raw_line in text.splitlines():
            line = self.collapse_spaces(raw_line.replace("\x00", ""))
            if not line:
                continue

            account_match = HEADER_ACCOUNT_RE.search(line)
            if account_match is not None:
                current_account = self._mask_account(
                    re.sub(r"\D", "", account_match.group("account"))
                )
                continue

            if self._is_card_noise(line):
                continue

            if current_account is None:
                continue

            lines.append(CardLine(text=line, account=current_account))

        return lines

    def _is_card_noise(self, line: str) -> bool:
        return (
            any(line.startswith(prefix) for prefix in CARD_NOISE_PREFIXES)
            or CARD_OWNER_NAME_RE.fullmatch(line) is not None
            or (line.isdigit() and len(line) <= 2)
        )

    def _build_card_transaction(
        self,
        lines: Sequence[CardLine],
        *,
        anchor_index: int,
        previous_anchor_index: int | None,
        next_anchor_index: int | None,
        source_name: str | None,
    ) -> tuple[Transaction, set[int]]:
        anchor_line = lines[anchor_index]
        anchor_match = CARD_ANCHOR_RE.search(anchor_line.text)
        if anchor_match is None:
            raise ValueError(f"Could not parse Ozon card anchor line: {anchor_line.text}")

        prefix_match = CARD_PREFIX_RE.match(anchor_line.text)
        if prefix_match is None:
            raise ValueError(f"Could not parse Ozon card document prefix: {anchor_line.text}")

        prefix_indexes = self._prefix_indexes(
            anchor_index,
            previous_anchor_index=previous_anchor_index,
        )
        suffix_candidate_indexes = self._suffix_candidate_indexes(
            anchor_index,
            line_count=len(lines),
            next_anchor_index=next_anchor_index,
        )

        date_text = self._extract_card_date(
            lines, anchor_index=anchor_index, prefix_indexes=prefix_indexes
        )
        time_text, time_line_index = self._extract_card_time(
            lines,
            anchor_index=anchor_index,
            suffix_candidate_indexes=suffix_candidate_indexes,
        )
        document = prefix_match.group("document")
        amount_text = anchor_match.group("amount_rub")
        amount_secondary = anchor_match.group("amount_tail")

        selected_suffix_indexes: list[int] = []
        for index in suffix_candidate_indexes:
            line = lines[index].text
            if self._is_card_continuation_line(line):
                selected_suffix_indexes.append(index)
                continue
            if time_line_index is not None and index == time_line_index:
                selected_suffix_indexes.append(index)
                continue
            if (
                time_line_index is not None
                and time_line_index != anchor_index
                and index > time_line_index
            ):
                selected_suffix_indexes.append(index)
                continue
            if not self._looks_like_next_transaction_prefix(line):
                selected_suffix_indexes.append(index)

        description_parts: list[str] = []
        consumed_indexes = {anchor_index}

        for index in prefix_indexes:
            consumed_indexes.add(index)
            cleaned = self._clean_card_context_line(lines[index].text)
            if cleaned:
                description_parts.append(cleaned)

        cleaned_anchor = self._clean_card_anchor_line(anchor_line.text)
        if cleaned_anchor:
            description_parts.append(cleaned_anchor)

        for index in selected_suffix_indexes:
            consumed_indexes.add(index)
            cleaned = self._clean_card_context_line(lines[index].text)
            if cleaned:
                description_parts.append(cleaned)

        description = self.clean_merchant(" ".join(description_parts))
        merchant_raw = self._extract_card_merchant_raw(description)
        occurred_at = self.parse_date_ru(date_text, time_text)
        row_hash = self._row_hash(document, description, amount_text)
        is_likely_self_transfer = description.startswith("Перевод собственных средств")

        return (
            Transaction(
                id=self.build_id("ozon", anchor_line.account, occurred_at, row_hash),
                date=occurred_at,
                amount=self.parse_amount(amount_text),
                merchant_raw=merchant_raw,
                description=description,
                bank=self.bank,
                account=anchor_line.account,
                precision="second",
                raw={
                    "document": document,
                    "amount_secondary": amount_secondary,
                    "is_likely_self_transfer": is_likely_self_transfer,
                    "source_name": source_name,
                },
            ),
            consumed_indexes,
        )

    def _prefix_indexes(self, anchor_index: int, *, previous_anchor_index: int | None) -> list[int]:
        lower_bound = previous_anchor_index + 1 if previous_anchor_index is not None else 0
        start = max(lower_bound, anchor_index - 2)
        return list(range(start, anchor_index))

    def _suffix_candidate_indexes(
        self,
        anchor_index: int,
        *,
        line_count: int,
        next_anchor_index: int | None,
    ) -> list[int]:
        upper_bound = next_anchor_index if next_anchor_index is not None else line_count
        stop = min(upper_bound, anchor_index + 3)
        return list(range(anchor_index + 1, stop))

    def _extract_card_date(
        self,
        lines: Sequence[CardLine],
        *,
        anchor_index: int,
        prefix_indexes: Sequence[int],
    ) -> str:
        candidate_indexes = [anchor_index, *reversed(prefix_indexes)]
        for index in candidate_indexes:
            match = CARD_DATE_RE.search(lines[index].text)
            if match is not None:
                return match.group(0)
        raise ValueError(f"Could not find Ozon card date near anchor: {lines[anchor_index].text}")

    def _extract_card_time(
        self,
        lines: Sequence[CardLine],
        *,
        anchor_index: int,
        suffix_candidate_indexes: Sequence[int],
    ) -> tuple[str, int | None]:
        anchor_match = CARD_TIME_RE.search(lines[anchor_index].text)
        if anchor_match is not None:
            return anchor_match.group(0), anchor_index

        for index in suffix_candidate_indexes:
            match = CARD_TIME_RE.search(lines[index].text)
            if match is not None:
                return match.group(0), index

        raise ValueError(f"Could not find Ozon card time near anchor: {lines[anchor_index].text}")

    def _clean_card_anchor_line(self, line: str) -> str:
        anchor_match = CARD_ANCHOR_RE.search(line)
        if anchor_match is None:
            return ""

        text = line[: anchor_match.start("amount_rub")].strip()
        prefix_match = CARD_PREFIX_RE.match(text)
        if prefix_match is not None:
            text = text[prefix_match.end("document") :].strip()
        return self._strip_card_service_tokens(text)

    def _clean_card_context_line(self, line: str) -> str:
        text = CARD_LEADING_DATE_RE.sub("", line, count=1)
        text = CARD_LEADING_TIME_RE.sub("", text, count=1)
        return self._strip_card_service_tokens(text)

    def _strip_card_service_tokens(self, text: str) -> str:
        stripped = CARD_SERVICE_FRAGMENT_RE.sub(" ", text)
        stripped = self.collapse_spaces(stripped)
        return stripped.strip(" -.,")

    def _extract_card_merchant_raw(self, description: str) -> str:
        if description.startswith("Платеж в пользу "):
            return self.clean_merchant(description.removeprefix("Платеж в пользу "))

        if "Платформе Ozon" in description:
            return "Платформа Ozon"

        payment_match = re.search(r"\bв\s+(?P<merchant>.+?)(?:\s+дата\b|\s+время\b|$)", description)
        if payment_match is not None:
            return self.clean_merchant(payment_match.group("merchant"))

        return self.clean_merchant(description)

    def _looks_like_next_transaction_prefix(self, line: str) -> bool:
        if self._is_card_continuation_line(line):
            return False
        return CARD_TRANSACTION_START_RE.match(line) is not None

    def _is_card_continuation_line(self, line: str) -> bool:
        return CARD_CONTINUATION_RE.match(line) is not None

    def _warn_dropped_card_line(
        self,
        line: str,
        *,
        source_name: str | None,
        reason: str,
    ) -> None:
        LOGGER.warning(
            "Dropped Ozon card line in %s (%s): %s",
            source_name or "<text>",
            reason,
            line,
        )


class OzonSavingsParser(BaseOzonParser):
    def can_parse_text(self, text: str) -> bool:
        return self._has_ozon_header(text) and self._matches_account_prefix(
            text,
            prefix=SAVINGS_ACCOUNT_PREFIX,
        )

    def parse_text(self, text: str, *, source_name: str | None = None) -> Iterable[Transaction]:
        lines = self._collect_savings_lines(text)
        if not any(self._is_savings_anchor(line) for line in lines):
            yield from super().parse_text(text, source_name=source_name)
            return

        header_account = self._extract_header_account(text)
        pending_prefix: list[str] = []
        index = 0

        while index < len(lines):
            line = lines[index]
            if not self._is_savings_anchor(line):
                pending_prefix.append(line)
                index += 1
                continue

            suffix_lines: list[str] = []
            next_index = index + 1
            while next_index < len(lines):
                candidate = lines[next_index]
                if self._is_savings_anchor(candidate):
                    break
                if not self._looks_like_savings_suffix(candidate):
                    break
                suffix_lines.append(candidate)
                next_index += 1

            yield self._build_savings_transaction(
                prefix_lines=pending_prefix,
                anchor_line=line,
                suffix_lines=suffix_lines,
                header_account=header_account,
                source_name=source_name,
            )
            pending_prefix = []
            index = next_index

        for line in pending_prefix:
            self._warn_dropped_savings_line(
                line,
                source_name=source_name,
                reason="unclassified savings line",
            )

    def _collect_savings_lines(self, text: str) -> list[str]:
        lines: list[str] = []

        for raw_line in text.splitlines():
            line = self.collapse_spaces(raw_line.replace("\x00", ""))
            if not line or self._is_savings_noise(line):
                continue
            lines.append(line)

        return lines

    def _is_savings_noise(self, line: str) -> bool:
        return any(line.startswith(prefix) for prefix in SAVINGS_NOISE_PREFIXES) or (
            line.isdigit() and len(line) <= 2
        )

    def _is_savings_anchor(self, line: str) -> bool:
        return SAVINGS_ANCHOR_RE.search(line) is not None

    def _looks_like_savings_suffix(self, line: str) -> bool:
        return line.lower().startswith("за период") or SAVINGS_TIME_RE.match(line) is not None

    def _build_savings_transaction(
        self,
        *,
        prefix_lines: Sequence[str],
        anchor_line: str,
        suffix_lines: Sequence[str],
        header_account: str,
        source_name: str | None,
    ) -> Transaction:
        anchor_match = SAVINGS_ANCHOR_RE.search(anchor_line)
        if anchor_match is None:
            raise ValueError(f"Could not parse Ozon savings anchor line: {anchor_line}")

        prefix_match = SAVINGS_PREFIX_RE.match(anchor_line)
        if prefix_match is None:
            raise ValueError(f"Could not parse Ozon savings document prefix: {anchor_line}")

        date_text = self._extract_savings_date(anchor_line, prefix_lines=prefix_lines)
        time_text = self._extract_savings_time(anchor_line, suffix_lines=suffix_lines)
        document = prefix_match.group("document")
        amount_text = anchor_match.group("amount_rub")

        description_parts: list[str] = []
        for line in prefix_lines:
            cleaned = self._clean_savings_prefix_line(line)
            if cleaned:
                description_parts.append(cleaned)

        cleaned_anchor = self._clean_savings_anchor_line(anchor_line)
        if cleaned_anchor:
            description_parts.append(cleaned_anchor)

        for line in suffix_lines:
            cleaned = self._clean_savings_suffix_line(line)
            if cleaned:
                description_parts.append(cleaned)

        description = self.clean_merchant(" ".join(description_parts))
        occurred_at = self.parse_date_ru(date_text, time_text)
        row_hash = self._row_hash(document, description, amount_text)
        is_likely_self_transfer = description.startswith("Перевод собственных средств")

        return Transaction(
            id=self.build_id("ozon", header_account, occurred_at, row_hash),
            date=occurred_at,
            amount=self.parse_amount(amount_text),
            merchant_raw=description,
            description=description,
            bank=self.bank,
            account=header_account,
            precision="second" if time_text is not None else "date",
            raw={
                "document": document,
                "amount_secondary": anchor_match.group("amount_tail"),
                "is_likely_self_transfer": is_likely_self_transfer,
                "source_name": source_name,
            },
        )

    def _extract_savings_date(self, anchor_line: str, *, prefix_lines: Sequence[str]) -> str:
        for line in [anchor_line, *reversed(prefix_lines)]:
            match = SAVINGS_DATE_RE.search(line)
            if match is not None:
                return match.group(0)
        raise ValueError(f"Could not find Ozon savings date near anchor: {anchor_line}")

    def _extract_savings_time(self, anchor_line: str, *, suffix_lines: Sequence[str]) -> str | None:
        for line in [anchor_line, *suffix_lines]:
            match = SAVINGS_TIME_RE.search(line)
            if match is not None:
                return match.group(0)
        return None

    def _clean_savings_prefix_line(self, line: str) -> str:
        text = SAVINGS_LEADING_DATE_RE.sub("", line, count=1)
        text = SAVINGS_LEADING_TIME_RE.sub("", text, count=1)
        return self.clean_merchant(text)

    def _clean_savings_anchor_line(self, line: str) -> str:
        anchor_match = SAVINGS_ANCHOR_RE.search(line)
        if anchor_match is None:
            return ""

        text = line[: anchor_match.start("amount_rub")].strip()
        prefix_match = SAVINGS_PREFIX_RE.match(text)
        if prefix_match is not None:
            text = text[prefix_match.end("document") :].strip()
        return self.clean_merchant(text)

    def _clean_savings_suffix_line(self, line: str) -> str:
        text = SAVINGS_LEADING_TIME_RE.sub("", line, count=1)
        return self.clean_merchant(text)

    def _warn_dropped_savings_line(
        self,
        line: str,
        *,
        source_name: str | None,
        reason: str,
    ) -> None:
        LOGGER.warning(
            "Dropped Ozon savings line in %s (%s): %s",
            source_name or "<text>",
            reason,
            line,
        )


OzonParser = OzonSavingsParser

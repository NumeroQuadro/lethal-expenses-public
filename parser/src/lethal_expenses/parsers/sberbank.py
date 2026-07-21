from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from lethal_expenses.parsers.base import BaseParser
from lethal_expenses.schema import BankName, Transaction

LOGGER = logging.getLogger(__name__)

CARD_LINE_ONE_RE = re.compile(
    r"^(?P<date>\d{2}\.\d{2}\.\d{4})\s+(?P<time>\d{2}:\d{2})\s+"
    r"(?P<label>.+?)\s+(?P<amount>[+-]?\d[\d\s]*,\d{2})$"
)
CARD_LINE_ONE_AMOUNT_BALANCE_RE = re.compile(
    r"^(?P<date>\d{2}\.\d{2}\.\d{4})\s+(?P<time>\d{2}:\d{2})\s+"
    r"(?P<label>.+?)\s+(?P<amount>[+-]?\d[\d\s]*,\d{2})\s+"
    r"(?P<balance>[+-]?\d[\d\s]*,\d{2})$"
)
CARD_LINE_TWO_RE = re.compile(
    r"^(?P<date>\d{2}\.\d{2}\.\d{4})\s+(?P<auth_code>\S+)\s+(?P<description>.+)$"
)
CARD_HEADER_ACCOUNT_RE = re.compile(
    r"^(?:"
    r"Номер\s+сч[её]та[:\s]*(?P<inline_account>\d(?:[\d ]*\d))"
    r"(?=\s+(?:Пополнение|Карта|Валюта|Дата)\b|$).*"
    r"|Номер\s+сч[её]та[:\s]*(?P<legacy_account>[\d* ]+)$"
    r")",
    re.IGNORECASE,
)
SAVINGS_HEADER_ACCOUNT_LINE_RE = re.compile(
    r"^(?:"
    r"Номер\s+сч[её]та[:\s]*(?P<inline_account>\d(?:[\d ]*\d))(?:\s+Пополнение\s+\d[\d\s]*,\d{2})?"
    r"|(?P<legacy_account>\d(?:[\d ]*\d))\s+\d{2}\.\d{2}\.\d{4}\s+-"
    r")$",
    re.IGNORECASE,
)
SAVINGS_ROW_RE = re.compile(
    r"^(?P<date>\d{2}\.\d{2}\.\d{4})\s+"
    r"(?P<label>.+?)\s+"
    r"(?P<entry_code>\d{2}),\s+№\s+(?P<document>[^\s]+)\s+"
    r"(?P<amount>[+-]?\d[\d\s]*,\d{2})\s+"
    r"(?P<balance>\d[\d\s]*,\d{2})$"
)
SAVINGS_CONTINUATION_RE = re.compile(r"^к/с\s+(?P<account>[\d ]+)$", re.IGNORECASE)
SAVINGS_SUMMARY_BALANCES_RE = re.compile(
    r"Остаток\s+средств\s+(?P<opening>\d[\d\s]*,\d{2})\s+"
    r"Остаток\s+средств\s+(?P<closing>\d[\d\s]*,\d{2})\s+"
    r"на\s+(?P<opening_date>\d{2}\.\d{2}\.\d{4})\s+"
    r"на\s+(?P<closing_date>\d{2}\.\d{2}\.\d{4})",
    re.IGNORECASE,
)
SAVINGS_SUMMARY_TOTALS_RE = re.compile(
    r"Пополнение\s+(?P<credits>\d[\d\s]*,\d{2})\s+"
    r"Списание\s+(?P<debits>\d[\d\s]*,\d{2})",
    re.IGNORECASE,
)
SAVINGS_SUMMARY_BALANCE_LINE_RE = re.compile(
    r"^Остаток\s+на\s+(?P<date>\d{2}\.\d{2}\.\d{4})\s+(?P<amount>\d[\d\s]*,\d{2})$",
    re.IGNORECASE,
)
SAVINGS_SUMMARY_CREDITS_RE = re.compile(
    r"\bПополнение\s+(?P<credits>\d[\d\s]*,\d{2})\b",
    re.IGNORECASE,
)
SAVINGS_SUMMARY_DEBITS_RE = re.compile(
    r"\bСписание\s+(?P<debits>\d[\d\s]*,\d{2})\b",
    re.IGNORECASE,
)
SAVINGS_NOISE_REGEXES = (
    re.compile(r"^[A-F0-9]{20,}$"),
    re.compile(r"^с\s+\d{2}\.\d{2}\.\d{4}\s+по\s+\d{2}\.\d{2}\.\d{4}$"),
    re.compile(r"^\d{2}\.\d{2}\.\d{4}$"),
)
ACCOUNT_TOKEN_RE = re.compile(r"\*{4}(?P<account4>\d{4})")
MASKED_ACCOUNT_RE = re.compile(r"\*{4}(?P<account4>\d{4})")
LEADING_TRANSFER_RE = re.compile(r"^Перевод\s+(?:от|для)\s+", re.IGNORECASE)
LEADING_SBSCR_RE = re.compile(r"^SBSCR_+", re.IGNORECASE)
TRAILING_OPERATION_RE = re.compile(r"\s+Операция\s+по\s+(?:карте|сч[её]ту).*$", re.IGNORECASE)
TRAILING_ACCOUNT_RE = re.compile(r"\s+\*{4}\d{4}$")
CARD_SUMMARY_BALANCE_LINE_RE = re.compile(
    r"^Остаток\s+на\s+(?P<date>\d{2}\.\d{2}\.\d{4})\s+(?P<amount>[+-]?\d[\d\s]*,\d{2})$",
    re.IGNORECASE,
)
CARD_SUMMARY_CREDITS_RE = re.compile(
    r"\bПополнение\s+(?P<credits>[+-]?\d[\d\s]*,\d{2})\b",
    re.IGNORECASE,
)
CARD_SUMMARY_DEBITS_RE = re.compile(
    r"\bСписание\s+(?P<debits>[+-]?\d[\d\s]*,\d{2})\b",
    re.IGNORECASE,
)
CARD_NOISE_REGEXES = (
    re.compile(r"^[A-F0-9]{20,}$"),
    re.compile(r"^с\s+\d{2}\.\d{2}\.\d{4}\s+по\s+\d{2}\.\d{2}\.\d{4}$"),
    re.compile(r"^\d{2}\.\d{2}\.\d{4}$"),
    re.compile(r"^\*$"),
)

CARD_NOISE_MARKERS = (
    "СберБанк Онлайн",
    "Индивидуальная выписка",
    "Выписка по платёжному счёту",
    "Номер счёта",
    "Продолжение на",
    "Страница ",
    "Действителен до",
    "Для проверки подлинности",
    "ВСЕГО ",
    "ДАТА ОПЕРАЦИИ (МСК) КАТЕГОРИЯ СУММА В ВАЛЮТЕ СЧЁТА ОСТАТОК СРЕДСТВ",
    "Дата обработки¹ Описание операции Сумма в валюте В валюте счёта",
    "ДАТА ОПЕРАЦИИ КАТЕГОРИЯ СУММА В ВАЛЮТЕ СЧЁТА",
    "Дата обработки¹ Описание операции Сумма в валюте",
    "и код авторизации операции²",
    "Зайдите в приложение",
    "Нажмите кнопку",
    "Получите документ",
    "Действителен",
    "Предоставляя QR-код",
)
CARD_NOISE_PREFIXES = (
    "Дата формирования документа",
    "ПАО Сбербанк. Генеральная лицензия",
    "Денежные средства списываются",
    "В выписке отображаются",
    "Срок обработки операций",
    "1 Дата списания / зачисления денежных средств на счёт карты",
    "2 По курсу банка на дату обработки операции",
    "* Согласно статье",
    "электронной подписью",
    "Проверить подпись",
)
SAVINGS_STATEMENT_MARKER = "выписка по счёту «накопительный счёт»"
DEPOSIT_STATEMENT_MARKER = "выписка по вкладу"
SAVINGS_TABLE_START_MARKER = "Расшифровка операций"
SAVINGS_NOISE_PREFIXES = (
    "Выписка по счёту «Накопительный счёт»",
    "Продолжение на следующей странице",
    "Для проверки подлинности документа",
    "1.",
    "2.",
    "3.",
    "Действителен",
    "до ",
    "Дата формирования документа",
    "Цель вклада",
    "На дату формирования выписки",
    "Сумма операции по кредиту",
    "Согласно статье",
    "электронной подписью",
    "правоотношениях",
    "Скачать электронный формат подписи",
    "Проверить подпись",
    "ПАО Сбербанк. Генеральная лицензия",
    "ДАТА НАИМЕНОВАНИЕ ОПЕРАЦИИ",
    "ОПЕРАЦИИ № корреспондирующего счёта",
)
DEPOSIT_NOISE_PREFIXES = SAVINGS_NOISE_PREFIXES + ("Выписка по вкладу",)
SAVINGS_NOISE_EXACT_LINES = {
    "1",
    "2",
    "3",
    "*",
}


def empty_description_parts() -> list[str]:
    return []


def empty_continuation_lines() -> list[str]:
    return []


def mask_account(account4: str) -> str:
    return f"****{account4}"


def amount_token(amount: Decimal) -> str:
    sign = "neg" if amount < 0 else "pos"
    normalized = amount.copy_abs().quantize(Decimal("0.01"))
    return f"{sign}{format(normalized, 'f').replace('.', '')}"


@dataclass(slots=True)
class PendingTransaction:
    date: datetime
    category_label: str
    amount: Decimal
    balance_after: Decimal | None = None
    auth_code: str | None = None
    description_parts: list[str] = field(default_factory=empty_description_parts)


@dataclass(slots=True)
class CardStatementSummary:
    opening_balance: Decimal | None
    closing_balance: Decimal | None
    total_credits: Decimal | None
    total_debits: Decimal | None
    opening_date: str | None
    closing_date: str | None


@dataclass(slots=True)
class SavingsStatementSummary:
    opening_balance: Decimal
    closing_balance: Decimal
    total_credits: Decimal
    total_debits: Decimal
    opening_date: str
    closing_date: str


@dataclass(slots=True)
class PendingSavingsTransaction:
    date_text: str
    label: str
    entry_code: str
    document_number: str
    amount_text: str
    balance_text: str
    continuation_lines: list[str] = field(default_factory=empty_continuation_lines)


@dataclass(slots=True)
class ParsedSavingsTransaction:
    transaction: Transaction
    balance_after: Decimal


class SberbankCardParser(BaseParser):
    bank: BankName = "sberbank"

    def can_parse_text(self, text: str) -> bool:
        normalized = text.lower()
        return "сбербанк" in normalized and (
            "индивидуальная выписка" in normalized or "выписка по платёжному счёту" in normalized
        )

    def parse_text(self, text: str, *, source_name: str | None = None) -> Iterable[Transaction]:
        header_account = self._extract_header_account(text)
        summary = self._extract_statement_summary(text)
        rows: list[Transaction] = []
        pending: PendingTransaction | None = None

        for raw_line in text.splitlines():
            line = self.collapse_spaces(raw_line)
            if not line or self._is_noise(line):
                continue

            first_line_match = CARD_LINE_ONE_AMOUNT_BALANCE_RE.match(line)
            if first_line_match:
                if pending is not None and pending.auth_code is not None:
                    rows.append(
                        self._build_transaction(
                            pending,
                            header_account=header_account,
                            source_name=source_name,
                        )
                    )
                pending = PendingTransaction(
                    date=self.parse_date_ru(
                        first_line_match.group("date"),
                        first_line_match.group("time"),
                    ),
                    category_label=self.collapse_spaces(first_line_match.group("label")),
                    amount=self.parse_amount(first_line_match.group("amount")),
                    balance_after=self.parse_amount(
                        first_line_match.group("balance"),
                        default_sign=1,
                    ),
                )
                continue

            first_line_match = CARD_LINE_ONE_RE.match(line)
            if first_line_match:
                if pending is not None and pending.auth_code is not None:
                    rows.append(
                        self._build_transaction(
                            pending,
                            header_account=header_account,
                            source_name=source_name,
                        )
                    )
                pending = PendingTransaction(
                    date=self.parse_date_ru(
                        first_line_match.group("date"),
                        first_line_match.group("time"),
                    ),
                    category_label=self.collapse_spaces(first_line_match.group("label")),
                    amount=self.parse_amount(first_line_match.group("amount")),
                )
                continue

            second_line_match = CARD_LINE_TWO_RE.match(line)
            if second_line_match and pending is not None:
                pending.auth_code = second_line_match.group("auth_code")
                description = self.collapse_spaces(second_line_match.group("description"))
                pending.description_parts = [description]
                continue

            if pending is not None and pending.auth_code is not None:
                pending.description_parts.append(line)

        if pending is not None and pending.auth_code is not None:
            rows.append(
                self._build_transaction(
                    pending,
                    header_account=header_account,
                    source_name=source_name,
                )
            )

        if not rows:
            raise ValueError(
                f"No Sberbank card transactions were parsed from {source_name or '<text>'}"
            )

        self._validate_statement(rows, summary=summary, source_name=source_name)
        return rows

    def _extract_header_account(self, text: str) -> str | None:
        for raw_line in text.splitlines():
            line = self.collapse_spaces(raw_line)
            if not line.startswith("Номер счёта"):
                continue
            match = CARD_HEADER_ACCOUNT_RE.match(line)
            if match is None:
                continue
            account_value = match.group("inline_account") or match.group("legacy_account")
            if account_value is None:
                continue
            digits = re.sub(r"\D", "", account_value)
            if len(digits) >= 4:
                return mask_account(digits[-4:])
        return None

    def _extract_statement_summary(self, text: str) -> CardStatementSummary:
        header_lines = self._header_lines(text)
        balance_matches = [
            match
            for line in header_lines
            if (match := CARD_SUMMARY_BALANCE_LINE_RE.match(line)) is not None
        ]
        credits_match = next(
            (
                match
                for line in header_lines
                if (match := CARD_SUMMARY_CREDITS_RE.search(line)) is not None
            ),
            None,
        )
        debits_match = next(
            (
                match
                for line in header_lines
                if (match := CARD_SUMMARY_DEBITS_RE.search(line)) is not None
            ),
            None,
        )
        opening_match = balance_matches[0] if len(balance_matches) >= 2 else None
        closing_match = balance_matches[-1] if len(balance_matches) >= 2 else None
        return CardStatementSummary(
            opening_balance=(
                self.parse_amount(opening_match.group("amount"), default_sign=1)
                if opening_match is not None
                else None
            ),
            closing_balance=(
                self.parse_amount(closing_match.group("amount"), default_sign=1)
                if closing_match is not None
                else None
            ),
            total_credits=(
                self.parse_amount(credits_match.group("credits"), default_sign=1)
                if credits_match is not None
                else None
            ),
            total_debits=(
                self.parse_amount(debits_match.group("debits"), default_sign=1)
                if debits_match is not None
                else None
            ),
            opening_date=opening_match.group("date") if opening_match is not None else None,
            closing_date=closing_match.group("date") if closing_match is not None else None,
        )

    def _header_lines(self, text: str) -> list[str]:
        lines: list[str] = []
        for raw_line in text.splitlines():
            line = self.collapse_spaces(raw_line)
            if not line:
                continue
            if line == SAVINGS_TABLE_START_MARKER:
                break
            lines.append(line)
        return lines

    def _is_noise(self, line: str) -> bool:
        return (
            any(marker in line for marker in CARD_NOISE_MARKERS)
            or any(pattern.match(line) is not None for pattern in CARD_NOISE_REGEXES)
            or any(line.startswith(prefix) for prefix in CARD_NOISE_PREFIXES)
        )

    def _resolve_account(self, header_account: str | None) -> str:
        if header_account is not None:
            return header_account
        raise ValueError("Could not determine Sberbank account suffix")

    def _build_transaction(
        self,
        pending: PendingTransaction,
        *,
        header_account: str | None,
        source_name: str | None,
    ) -> Transaction:
        description = self._normalize_description(pending.description_parts)
        account = self._resolve_account(header_account)
        merchant_raw = self._extract_merchant_raw(description)
        auth_code = pending.auth_code or "unknown"
        card_suffixes = [
            match.group("account4") for match in MASKED_ACCOUNT_RE.finditer(description)
        ]

        return Transaction(
            id=self.build_id(
                "sber", account, pending.date, auth_code, amount_token(pending.amount)
            ),
            bank=self.bank,
            account=account,
            date=pending.date,
            amount=pending.amount,
            merchant_raw=merchant_raw,
            description=description,
            precision="minute",
            raw={
                "auth_code": auth_code,
                "category_label": pending.category_label,
                "header_account": header_account,
                "card_suffix": card_suffixes[0] if card_suffixes else None,
                "card_suffixes": card_suffixes,
                "source_name": source_name,
            },
        )

    def _normalize_description(self, description_parts: list[str]) -> str:
        description = self.collapse_spaces(" ".join(description_parts))
        return "" if description == "-" else description

    def _extract_merchant_raw(self, description: str) -> str:
        if not description:
            return ""
        merchant = LEADING_TRANSFER_RE.sub("", description)
        merchant = LEADING_SBSCR_RE.sub("", merchant)
        merchant = TRAILING_OPERATION_RE.sub("", merchant)
        merchant = TRAILING_ACCOUNT_RE.sub("", merchant)
        return self.clean_merchant(merchant)

    def _validate_statement(
        self,
        rows: list[Transaction],
        *,
        summary: CardStatementSummary,
        source_name: str | None,
    ) -> None:
        source_label = source_name or "<text>"
        if summary.total_credits is not None:
            parsed_credits = sum((row.amount for row in rows if row.amount > 0), Decimal("0"))
            if parsed_credits != summary.total_credits:
                raise ValueError(
                    f"Sberbank card credit total mismatch for {source_label}: "
                    f"expected {summary.total_credits}, got {parsed_credits}"
                )
        if summary.total_debits is not None:
            parsed_debits = sum((-row.amount for row in rows if row.amount < 0), Decimal("0"))
            if parsed_debits != summary.total_debits.copy_abs():
                raise ValueError(
                    f"Sberbank card debit total mismatch for {source_label}: "
                    f"expected {summary.total_debits.copy_abs()}, got {parsed_debits}"
                )
        if (
            summary.opening_balance is not None
            and summary.closing_balance is not None
            and summary.opening_date is not None
            and min(row.date.date() for row in rows)
            == datetime.strptime(summary.opening_date, "%d.%m.%Y").date()
        ):
            net = sum((row.amount for row in rows), Decimal("0"))
            if summary.opening_balance + net != summary.closing_balance:
                raise ValueError(
                    f"Sberbank card balance mismatch for {source_label}: "
                    f"expected {summary.closing_balance}, got {summary.opening_balance + net}"
                )


class SberbankSavingsParser(BaseParser):
    bank: BankName = "sberbank"

    def can_parse_text(self, text: str) -> bool:
        normalized = text.lower()
        return SAVINGS_STATEMENT_MARKER in normalized and "сбербанк" in normalized

    def parse_text(self, text: str, *, source_name: str | None = None) -> Iterable[Transaction]:
        header_account = self._extract_header_account(text)
        summary = self._extract_statement_summary(text)
        rows: list[ParsedSavingsTransaction] = []
        pending: PendingSavingsTransaction | None = None
        inside_transaction_table = False

        for raw_line in text.splitlines():
            line = self.collapse_spaces(raw_line)
            if not line:
                continue

            if line == SAVINGS_TABLE_START_MARKER:
                inside_transaction_table = True
                continue

            if not inside_transaction_table:
                continue

            if self._is_noise(line):
                continue

            row_match = SAVINGS_ROW_RE.match(line)
            if row_match is not None:
                if pending is not None:
                    rows.append(
                        self._build_savings_transaction(
                            pending,
                            header_account=header_account,
                            source_name=source_name,
                        )
                    )
                pending = PendingSavingsTransaction(
                    date_text=row_match.group("date"),
                    label=self.clean_merchant(row_match.group("label")),
                    entry_code=row_match.group("entry_code"),
                    document_number=row_match.group("document"),
                    amount_text=row_match.group("amount"),
                    balance_text=row_match.group("balance"),
                )
                continue

            continuation_match = SAVINGS_CONTINUATION_RE.match(line)
            if continuation_match is not None and pending is not None:
                pending.continuation_lines.append(self.collapse_spaces(line))
                continue

            self._warn_dropped_line(line, source_name=source_name)

        if pending is not None:
            rows.append(
                self._build_savings_transaction(
                    pending,
                    header_account=header_account,
                    source_name=source_name,
                )
            )

        if not rows:
            raise ValueError(
                f"No Sberbank savings transactions were parsed from {source_name or '<text>'}"
            )

        self._validate_statement(rows, summary=summary, source_name=source_name)
        return (row.transaction for row in rows)

    def _extract_header_account(self, text: str) -> str:
        header_lines = self._header_lines(text)
        for line in header_lines:
            match = SAVINGS_HEADER_ACCOUNT_LINE_RE.match(line)
            if match is None or match.group("inline_account") is None:
                continue
            digits = re.sub(r"\D", "", match.group("inline_account"))
            if len(digits) >= 4:
                return mask_account(digits[-4:])

        for index, line in enumerate(header_lines):
            if not line.startswith("Номер счёта"):
                continue
            for candidate in header_lines[index + 1 : index + 4]:
                match = SAVINGS_HEADER_ACCOUNT_LINE_RE.match(candidate)
                if match is None or match.group("legacy_account") is None:
                    continue
                digits = re.sub(r"\D", "", match.group("legacy_account"))
                if len(digits) >= 4:
                    return mask_account(digits[-4:])
        raise ValueError("Could not determine Sberbank savings account suffix")

    def _extract_statement_summary(self, text: str) -> SavingsStatementSummary:
        header_lines = self._header_lines(text)
        collapsed_text = self.collapse_spaces(" ".join(header_lines))
        balance_match = SAVINGS_SUMMARY_BALANCES_RE.search(collapsed_text)
        totals_match = SAVINGS_SUMMARY_TOTALS_RE.search(collapsed_text)
        if balance_match is not None and totals_match is not None:
            return SavingsStatementSummary(
                opening_balance=self.parse_amount(balance_match.group("opening"), default_sign=1),
                closing_balance=self.parse_amount(balance_match.group("closing"), default_sign=1),
                total_credits=self.parse_amount(totals_match.group("credits"), default_sign=1),
                total_debits=self.parse_amount(totals_match.group("debits"), default_sign=1),
                opening_date=balance_match.group("opening_date"),
                closing_date=balance_match.group("closing_date"),
            )

        balance_matches = [
            match
            for line in header_lines
            if (match := SAVINGS_SUMMARY_BALANCE_LINE_RE.match(line)) is not None
        ]
        credits_match = next(
            (
                match
                for line in header_lines
                if (match := SAVINGS_SUMMARY_CREDITS_RE.search(line)) is not None
            ),
            None,
        )
        debits_match = next(
            (
                match
                for line in header_lines
                if (match := SAVINGS_SUMMARY_DEBITS_RE.search(line)) is not None
            ),
            None,
        )
        if len(balance_matches) >= 2 and credits_match is not None and debits_match is not None:
            opening_match = balance_matches[0]
            closing_match = balance_matches[-1]
            return SavingsStatementSummary(
                opening_balance=self.parse_amount(opening_match.group("amount"), default_sign=1),
                closing_balance=self.parse_amount(closing_match.group("amount"), default_sign=1),
                total_credits=self.parse_amount(credits_match.group("credits"), default_sign=1),
                total_debits=self.parse_amount(debits_match.group("debits"), default_sign=1),
                opening_date=opening_match.group("date"),
                closing_date=closing_match.group("date"),
            )

        raise ValueError("Could not determine Sberbank savings statement summary")

    def _header_lines(self, text: str) -> list[str]:
        lines: list[str] = []
        for raw_line in text.splitlines():
            line = self.collapse_spaces(raw_line)
            if not line:
                continue
            if line == SAVINGS_TABLE_START_MARKER:
                break
            lines.append(line)
        return lines

    def _is_noise(self, line: str) -> bool:
        return (
            line in SAVINGS_NOISE_EXACT_LINES
            or any(pattern.match(line) is not None for pattern in SAVINGS_NOISE_REGEXES)
            or any(line.startswith(prefix) for prefix in SAVINGS_NOISE_PREFIXES)
        )

    def _build_savings_transaction(
        self,
        pending: PendingSavingsTransaction,
        *,
        header_account: str,
        source_name: str | None,
    ) -> ParsedSavingsTransaction:
        occurred_at = self.parse_date_ru(pending.date_text)
        amount = self.parse_amount(pending.amount_text)
        balance_after = self.parse_amount(pending.balance_text, default_sign=1)
        description_parts = [
            f"{pending.label} {pending.entry_code}, № {pending.document_number}",
            *pending.continuation_lines,
        ]
        description = self.collapse_spaces(" ".join(description_parts))
        counterparty_accounts = [
            re.sub(r"\D", "", continuation_line) for continuation_line in pending.continuation_lines
        ]

        transaction = Transaction(
            id=self.build_id("sber", header_account, occurred_at, pending.document_number),
            bank=self.bank,
            account=header_account,
            date=occurred_at,
            amount=amount,
            merchant_raw=pending.label,
            description=description,
            precision="date",
            raw={
                "entry_code": pending.entry_code,
                "document_number": pending.document_number,
                "counterparty_accounts": counterparty_accounts,
                "balance_after": balance_after,
                "source_name": source_name,
            },
        )
        return ParsedSavingsTransaction(transaction=transaction, balance_after=balance_after)

    def _validate_statement(
        self,
        rows: list[ParsedSavingsTransaction],
        *,
        summary: SavingsStatementSummary,
        source_name: str | None,
    ) -> None:
        running_balance = summary.opening_balance
        source_label = source_name or "<text>"

        for row in reversed(rows):
            expected_balance = running_balance + row.transaction.amount
            if expected_balance != row.balance_after:
                raise ValueError(
                    "Sberbank savings balance invariant failed for "
                    f"{source_label}: {running_balance} + {row.transaction.amount} != "
                    f"{row.balance_after} ({row.transaction.description})"
                )
            running_balance = row.balance_after

        if running_balance != summary.closing_balance:
            raise ValueError(
                "Sberbank savings closing balance mismatch for "
                f"{source_label}: parsed {running_balance} != summary {summary.closing_balance}"
            )

        positive_total = sum(
            (row.transaction.amount for row in rows if row.transaction.amount > 0),
            Decimal("0"),
        )
        negative_total = sum(
            (-row.transaction.amount for row in rows if row.transaction.amount < 0),
            Decimal("0"),
        )
        if positive_total != summary.total_credits:
            raise ValueError(
                "Sberbank savings credit total mismatch for "
                f"{source_label}: parsed {positive_total} != summary {summary.total_credits}"
            )
        if negative_total != summary.total_debits:
            raise ValueError(
                "Sberbank savings debit total mismatch for "
                f"{source_label}: parsed {negative_total} != summary {summary.total_debits}"
            )

    def _warn_dropped_line(self, line: str, *, source_name: str | None) -> None:
        LOGGER.warning(
            "Dropped Sberbank savings line in %s: %s",
            source_name or "<text>",
            line,
        )


class SberbankDepositParser(SberbankSavingsParser):
    def can_parse_text(self, text: str) -> bool:
        normalized = text.lower()
        return DEPOSIT_STATEMENT_MARKER in normalized and (
            "сбербанк" in normalized or "sberbank" in normalized
        )

    def _is_noise(self, line: str) -> bool:
        return (
            line in SAVINGS_NOISE_EXACT_LINES
            or any(pattern.match(line) is not None for pattern in SAVINGS_NOISE_REGEXES)
            or any(line.startswith(prefix) for prefix in DEPOSIT_NOISE_PREFIXES)
        )

    def _warn_dropped_line(self, line: str, *, source_name: str | None) -> None:
        LOGGER.warning(
            "Dropped Sberbank deposit line in %s: %s",
            source_name or "<text>",
            line,
        )


SberbankParser = SberbankCardParser

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from hashlib import sha256

from lethal_expenses.schema import MOSCOW_TZ, Transaction

LOGGER = logging.getLogger(__name__)

TRANSFER_INDICATOR_RE = re.compile(
    r"Перевод|СБП|carta|перенос|собственных|"
    r"Перевод\s+между\s+собственными\s+счетами|"
    r"Перенос\s+денежных\s+средств\s+с\s+ЭДС|"
    r"^Получатель:\s|"
    r"Tinkoff\s+Bank|"
    r"Возврат\s+средств|"
    r"через\s+СБП|"
    r"Отмена\s+перевода|"
    r"Капитализация\s+вклада|"
    r"SBERBANK\s+ONL@IN\s+(?:VKLAD-KARTA|KARTA-VKLAD)|"
    r"MAPP_SBERBANK_ONL@IN_PAY|"
    r"(?:Списание|Пополнение|Зачисление)\b.*к/с\b",
    re.IGNORECASE,
)
SINGLE_SIDED_TRANSFER_RE = re.compile(
    r"^(?:Списание|Пополнение|Зачисление)\s+\d+,?\s*(?:№|N[oо]?)\s*\S+\s+к/с\s+"
    r"\d{5}\s+\d{3}\s+\d\s+\d{4}\s+\d{7}$|"
    r"Перевод\s+собственных\s+средств\.\s*Без\s+НДС\.?$|"
    r"SBERBANK\s+ONL@IN\s+(?:VKLAD-KARTA|KARTA-VKLAD)|"
    r"MAPP_SBERBANK_ONL@IN_PAY",
    re.IGNORECASE,
)
MAX_TRANSFER_DELTA = timedelta(minutes=30)
MAX_REVERSAL_DELTA = timedelta(minutes=5)
REVERSAL_INDICATOR_RE = re.compile(r"Отмена\s+перевода", re.IGNORECASE)
TRANSFER_TOKEN_RE = re.compile(r"\b[AB][A-Z0-9]{12,}\b", re.IGNORECASE)


@dataclass(slots=True)
class TransferDedupeStats:
    pass_a_pairs: int = 0
    pass_b_pairs: int = 0
    pass_c_single_sided_rows: int = 0
    pass_d_pairs: int = 0


def description_suggests_transfer(description: str) -> bool:
    return TRANSFER_INDICATOR_RE.search(description) is not None


def description_is_high_confidence_single_sided_transfer(description: str) -> bool:
    return SINGLE_SIDED_TRANSFER_RE.search(description) is not None


def description_mentions_reversal(description: str) -> bool:
    return REVERSAL_INDICATOR_RE.search(description) is not None


def extract_transfer_tokens(description: str) -> set[str]:
    return {token.upper() for token in TRANSFER_TOKEN_RE.findall(description)}


def _same_absolute_amount(first: Transaction, second: Transaction) -> bool:
    return abs(first.amount) == abs(second.amount)


def _opposite_signs(first: Transaction, second: Transaction) -> bool:
    return (first.amount < 0 < second.amount) or (second.amount < 0 < first.amount)


def _descriptions_suggest_transfer(first: Transaction, second: Transaction) -> bool:
    return description_suggests_transfer(first.description) or description_suggests_transfer(
        second.description
    )


def _different_logical_accounts(first: Transaction, second: Transaction) -> bool:
    return (first.bank, first.account) != (second.bank, second.account)


def _same_logical_account(first: Transaction, second: Transaction) -> bool:
    return (first.bank, first.account) == (second.bank, second.account)


def _has_shared_transfer_token(first: Transaction, second: Transaction) -> bool:
    return bool(
        extract_transfer_tokens(first.description) & extract_transfer_tokens(second.description)
    )


def _descriptions_link_reversal(first: Transaction, second: Transaction) -> bool:
    return (
        _has_shared_transfer_token(first, second)
        or description_mentions_reversal(first.description)
        or description_mentions_reversal(second.description)
    )


def _has_same_account_offset_candidate(
    transaction: Transaction,
    transactions: Sequence[Transaction],
    *,
    matched_indexes: set[int],
    current_index: int,
) -> bool:
    for candidate_index, candidate in enumerate(transactions):
        if candidate_index == current_index or candidate_index in matched_indexes:
            continue
        if (transaction.bank, transaction.account) != (candidate.bank, candidate.account):
            continue
        if not _same_absolute_amount(transaction, candidate) or not _opposite_signs(
            transaction, candidate
        ):
            continue

        if _is_date_only(transaction) or _is_date_only(candidate):
            continue
        if abs(transaction.date - candidate.date) > MAX_TRANSFER_DELTA:
            continue

        return True

    return False


def _can_pair_structurally(first: Transaction, second: Transaction) -> bool:
    return (
        _same_absolute_amount(first, second)
        and _opposite_signs(first, second)
        and _different_logical_accounts(first, second)
        and _descriptions_suggest_transfer(first, second)
    )


def _moscow_calendar_day(transaction: Transaction) -> date:
    return transaction.date.astimezone(MOSCOW_TZ).date()


def _is_date_only(transaction: Transaction) -> bool:
    return transaction.precision == "date"


def _find_best_timed_positive_match(
    negative_transaction: Transaction,
    positive_indexes: Sequence[int],
    transactions: Sequence[Transaction],
    *,
    matched_indexes: set[int],
) -> int | None:
    candidates: list[tuple[timedelta, str, int]] = []

    for positive_index in positive_indexes:
        if positive_index in matched_indexes:
            continue

        positive_transaction = transactions[positive_index]
        if _is_date_only(positive_transaction):
            continue
        if not _can_pair_structurally(negative_transaction, positive_transaction):
            continue

        delta = abs(positive_transaction.date - negative_transaction.date)
        if delta > MAX_TRANSFER_DELTA:
            continue

        candidates.append((delta, positive_transaction.id, positive_index))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[0], item[1]))
    return candidates[0][2]


def _find_best_same_account_reversal_match(
    negative_transaction: Transaction,
    positive_indexes: Sequence[int],
    transactions: Sequence[Transaction],
    *,
    matched_indexes: set[int],
) -> int | None:
    candidates: list[tuple[int, timedelta, str, int]] = []

    for positive_index in positive_indexes:
        if positive_index in matched_indexes:
            continue

        positive_transaction = transactions[positive_index]
        if _is_date_only(positive_transaction):
            continue
        if not _same_logical_account(negative_transaction, positive_transaction):
            continue
        if not _same_absolute_amount(negative_transaction, positive_transaction):
            continue
        if not _opposite_signs(negative_transaction, positive_transaction):
            continue

        delta = abs(positive_transaction.date - negative_transaction.date)
        if delta > MAX_REVERSAL_DELTA:
            continue
        if not _descriptions_link_reversal(negative_transaction, positive_transaction):
            continue

        shared_token_rank = (
            0 if _has_shared_transfer_token(negative_transaction, positive_transaction) else 1
        )
        candidates.append((shared_token_rank, delta, positive_transaction.id, positive_index))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    return candidates[0][3]


def _find_date_only_candidates(
    date_only_transaction: Transaction,
    transactions: Sequence[Transaction],
    *,
    matched_indexes: set[int],
    date_only_index: int,
) -> list[int]:
    candidates: list[int] = []

    for candidate_index, candidate in enumerate(transactions):
        if candidate_index == date_only_index or candidate_index in matched_indexes:
            continue
        if not _can_pair_structurally(date_only_transaction, candidate):
            continue
        if _moscow_calendar_day(candidate) != _moscow_calendar_day(date_only_transaction):
            continue
        candidates.append(candidate_index)

    return candidates


def _resolve_date_only_candidate(
    date_only_transaction: Transaction,
    candidate_indexes: Sequence[int],
    transactions: Sequence[Transaction],
) -> int | None:
    if not candidate_indexes:
        return None

    if len(candidate_indexes) == 1:
        return candidate_indexes[0]

    preferred_indexes = [
        candidate_index
        for candidate_index in candidate_indexes
        if _is_date_only(transactions[candidate_index])
    ]
    if len(preferred_indexes) == 1:
        return preferred_indexes[0]

    candidate_ids = [transactions[candidate_index].id for candidate_index in candidate_indexes]
    LOGGER.warning(
        "ambiguous date-only match for txid %s, candidates: %s",
        date_only_transaction.id,
        candidate_ids,
    )
    return None


def stable_transfer_pair_id(first: Transaction, second: Transaction) -> str:
    # Keep pair IDs byte-stable across rebuilds so transactions.json diffs
    # only reflect semantic row changes, not fresh UUID churn.
    payload = "|".join(sorted([first.id, second.id]))
    return sha256(payload.encode("utf-8")).hexdigest()[:16]


def _mark_transfer_pair(normalized: list[Transaction], first_index: int, second_index: int) -> None:
    transfer_pair_id = stable_transfer_pair_id(
        normalized[first_index],
        normalized[second_index],
    )
    normalized[first_index] = normalized[first_index].model_copy(
        update={"is_transfer": True, "transfer_pair_id": transfer_pair_id},
        deep=True,
    )
    normalized[second_index] = normalized[second_index].model_copy(
        update={"is_transfer": True, "transfer_pair_id": transfer_pair_id},
        deep=True,
    )


def _mark_single_sided_transfer(normalized: list[Transaction], index: int) -> None:
    normalized[index] = normalized[index].model_copy(
        update={"is_transfer": True, "transfer_pair_id": None},
        deep=True,
    )


def dedupe_self_transfers(
    transactions: list[Transaction],
    *,
    stats: TransferDedupeStats | None = None,
) -> list[Transaction]:
    normalized = [transaction.model_copy(deep=True) for transaction in transactions]
    timed_positive_indexes_by_amount: dict[Decimal, list[int]] = {}

    for index, transaction in enumerate(normalized):
        if transaction.amount <= 0 or _is_date_only(transaction):
            continue
        timed_positive_indexes_by_amount.setdefault(transaction.amount, []).append(index)

    matched_indexes: set[int] = set()

    # Pass A: pair timed rows across any two different logical accounts.
    for negative_index, negative_transaction in enumerate(normalized):
        if negative_transaction.amount >= 0 or _is_date_only(negative_transaction):
            continue

        positive_indexes = timed_positive_indexes_by_amount.get(
            abs(negative_transaction.amount), []
        )
        matched_positive_index = _find_best_timed_positive_match(
            negative_transaction,
            positive_indexes,
            normalized,
            matched_indexes=matched_indexes,
        )
        if matched_positive_index is None:
            continue

        _mark_transfer_pair(normalized, negative_index, matched_positive_index)
        matched_indexes.add(negative_index)
        matched_indexes.add(matched_positive_index)
        if stats is not None:
            stats.pass_a_pairs += 1

    # Pass B: fall back to same-day structural matching
    # for date-only rows on different logical accounts.
    for index, transaction in enumerate(normalized):
        if index in matched_indexes or not _is_date_only(transaction):
            continue

        candidate_indexes = _find_date_only_candidates(
            transaction,
            normalized,
            matched_indexes=matched_indexes,
            date_only_index=index,
        )
        matched_candidate_index = _resolve_date_only_candidate(
            transaction,
            candidate_indexes,
            normalized,
        )
        if matched_candidate_index is None:
            continue

        _mark_transfer_pair(normalized, index, matched_candidate_index)
        matched_indexes.add(index)
        matched_indexes.add(matched_candidate_index)
        if stats is not None:
            stats.pass_b_pairs += 1

    # Pass C: tag unmatched rows whose descriptions unambiguously encode
    # an internal transfer even when the opposite-side statement is missing.
    single_sided_count = 0
    for index, transaction in enumerate(normalized):
        if index in matched_indexes or transaction.amount == 0:
            continue
        if not description_is_high_confidence_single_sided_transfer(transaction.description):
            continue
        if _has_same_account_offset_candidate(
            transaction,
            normalized,
            matched_indexes=matched_indexes,
            current_index=index,
        ):
            continue

        _mark_single_sided_transfer(normalized, index)
        matched_indexes.add(index)
        single_sided_count += 1

    if stats is not None:
        stats.pass_c_single_sided_rows = single_sided_count
    if single_sided_count:
        LOGGER.info("Pass C: tagged %s rows single-sided", single_sided_count)

    pass_d_pairs = 0
    for negative_index, negative_transaction in enumerate(normalized):
        if negative_index in matched_indexes:
            continue
        if negative_transaction.amount >= 0 or _is_date_only(negative_transaction):
            continue

        positive_indexes = timed_positive_indexes_by_amount.get(
            abs(negative_transaction.amount), []
        )
        matched_positive_index = _find_best_same_account_reversal_match(
            negative_transaction,
            positive_indexes,
            normalized,
            matched_indexes=matched_indexes,
        )
        if matched_positive_index is None:
            continue

        _mark_transfer_pair(normalized, negative_index, matched_positive_index)
        matched_indexes.add(negative_index)
        matched_indexes.add(matched_positive_index)
        pass_d_pairs += 1

    if stats is not None:
        stats.pass_d_pairs = pass_d_pairs
    if pass_d_pairs:
        LOGGER.info("Pass D: paired %s same-account reversal pairs", pass_d_pairs)

    return normalized

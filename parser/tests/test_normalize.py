from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from lethal_expenses.normalize import (
    TransferDedupeStats,
    dedupe_self_transfers,
    description_is_high_confidence_single_sided_transfer,
    description_suggests_transfer,
    stable_transfer_pair_id,
)
from lethal_expenses.parsers.base import BaseParser
from lethal_expenses.schema import BankName, Transaction, TransactionPrecision


def build_transaction(
    *,
    id: str,
    bank: BankName,
    account: str,
    date_text: str,
    time_text: str,
    precision: TransactionPrecision = "minute",
    amount: str,
    merchant_raw: str,
    description: str,
) -> Transaction:
    return Transaction(
        id=id,
        bank=bank,
        account=account,
        date=BaseParser.parse_date_ru(date_text, time_text),
        amount=Decimal(amount),
        merchant_raw=merchant_raw,
        description=description,
        precision=precision,
        raw={},
    )


def test_dedupe_self_transfers_marks_both_ends() -> None:
    debit = build_transaction(
        id="sber-7000-20260424-13:15-auth04",
        bank="sberbank",
        account="****7000",
        date_text="24.04.2026",
        time_text="13:15",
        amount="-3000.00",
        merchant_raw="Иван Иванович И.",
        description="Перевод СБП Иван Иванович И.",
    )
    credit = build_transaction(
        id="yandex-eds-2026-04-24T13:17:00+03:00-deadbeefcafe",
        bank="yandex",
        account="ЭДС",
        date_text="24.04.2026",
        time_text="13:17",
        amount="3000.00",
        merchant_raw="Tinkoff Black",
        description="Перевод с карты Tinkoff Black на Яндекс Счёт",
    )

    normalized = dedupe_self_transfers([debit, credit])

    assert normalized[0].is_transfer is True
    assert normalized[1].is_transfer is True
    assert normalized[0].transfer_pair_id is not None
    assert normalized[0].transfer_pair_id == normalized[1].transfer_pair_id


def test_stable_transfer_pair_id_is_order_independent_and_repeatable() -> None:
    debit = build_transaction(
        id="sber-7000-20260424-13:15-auth04",
        bank="sberbank",
        account="****7000",
        date_text="24.04.2026",
        time_text="13:15",
        amount="-3000.00",
        merchant_raw="Иван Иванович И.",
        description="Перевод СБП Иван Иванович И.",
    )
    credit = build_transaction(
        id="yandex-eds-2026-04-24T13:17:00+03:00-deadbeefcafe",
        bank="yandex",
        account="ЭДС",
        date_text="24.04.2026",
        time_text="13:17",
        amount="3000.00",
        merchant_raw="Tinkoff Black",
        description="Перевод с карты Tinkoff Black на Яндекс Счёт",
    )

    expected_pair_id = stable_transfer_pair_id(debit, credit)

    assert expected_pair_id == stable_transfer_pair_id(credit, debit)
    assert dedupe_self_transfers([debit, credit])[0].transfer_pair_id == expected_pair_id
    assert dedupe_self_transfers([debit, credit])[1].transfer_pair_id == expected_pair_id


def test_dedupe_self_transfers_pairs_same_bank_different_accounts() -> None:
    debit = build_transaction(
        id="sber-2000-20260424-13:15-outgoing",
        bank="sberbank",
        account="****2000",
        date_text="24.04.2026",
        time_text="13:15",
        amount="-1000.00",
        merchant_raw="Списание",
        description="Списание 03, № 1 к/с 40817 810 1 5517 5566000",
    )
    credit = build_transaction(
        id="sber-7000-20260424-13:16-incoming",
        bank="sberbank",
        account="****7000",
        date_text="24.04.2026",
        time_text="13:16",
        amount="1000.00",
        merchant_raw="Иван Иванович И.",
        description="Перевод СБП Иван Иванович И.",
    )

    normalized = dedupe_self_transfers([debit, credit])

    assert normalized[0].is_transfer is True
    assert normalized[1].is_transfer is True
    assert normalized[0].transfer_pair_id is not None
    assert normalized[0].transfer_pair_id == normalized[1].transfer_pair_id


def test_dedupe_self_transfers_does_not_pair_same_account_refund_like_rows() -> None:
    debit = build_transaction(
        id="ozon-0784-20260424-13:15-outgoing",
        bank="ozon",
        account="****0784",
        date_text="24.04.2026",
        time_text="13:15",
        amount="-1000.00",
        merchant_raw="Перевод собственных средств. Без НДС.",
        description="Перевод собственных средств. Без НДС.",
    )
    credit = build_transaction(
        id="ozon-0784-20260424-13:20-incoming",
        bank="ozon",
        account="****0784",
        date_text="24.04.2026",
        time_text="13:20",
        amount="1000.00",
        merchant_raw="Перевод собственных средств. Без НДС.",
        description="Перевод собственных средств. Без НДС.",
    )

    normalized = dedupe_self_transfers([debit, credit])

    assert normalized[0].is_transfer is False
    assert normalized[1].is_transfer is False
    assert normalized[0].transfer_pair_id is None
    assert normalized[1].transfer_pair_id is None


def test_dedupe_self_transfers_pairs_same_account_reversal_rows_with_linkage() -> None:
    debit = build_transaction(
        id="ozon-0784-20260419-11:04-outgoing",
        bank="ozon",
        account="****0784",
        date_text="19.04.2026",
        time_text="11:04",
        amount="-35343.00",
        merchant_raw='Получатель: ООО "ТЕХНОПАРК - ЦЕНТР"',
        description=(
            'Получатель: ООО "ТЕХНОПАРК - ЦЕНТР" Перевод '
            "AD10002S5PJ6ICA99VSRN8GIAK54N4BP через СБП."
        ),
    )
    reversal = build_transaction(
        id="ozon-0784-20260419-11:04-cancel",
        bank="ozon",
        account="****0784",
        date_text="19.04.2026",
        time_text="11:04",
        amount="35343.00",
        merchant_raw='ООО "ТЕХНОПАРК - ЦЕНТР"',
        description=(
            "Отмена перевода AD10002S5PJ6ICA99VSRN8GIAK54N4BP через СБП. "
            'Получатель: ООО "ТЕХНОПАРК - ЦЕНТР"'
        ),
    )
    stats = TransferDedupeStats()

    normalized = dedupe_self_transfers([debit, reversal], stats=stats)

    assert normalized[0].is_transfer is True
    assert normalized[1].is_transfer is True
    assert normalized[0].transfer_pair_id is not None
    assert normalized[0].transfer_pair_id == normalized[1].transfer_pair_id
    assert stats.pass_d_pairs == 1


def test_dedupe_self_transfers_prefers_smallest_time_delta() -> None:
    debit = build_transaction(
        id="sber-7000-20260424-13:15-auth04",
        bank="sberbank",
        account="****7000",
        date_text="24.04.2026",
        time_text="13:15",
        amount="-3000.00",
        merchant_raw="Иван Иванович И.",
        description="Перевод СБП Иван Иванович И.",
    )
    farther_credit = build_transaction(
        id="ozon-3456-20260424-13:19-deadbeefcafe",
        bank="ozon",
        account="****3456",
        date_text="24.04.2026",
        time_text="13:19",
        amount="3000.00",
        merchant_raw="Перевод собственных средств. Без НДС.",
        description="Перевод собственных средств. Без НДС.",
    )
    closer_credit = build_transaction(
        id="yandex-eds-2026-04-24T13:16:00+03:00-deadbeefcafe",
        bank="yandex",
        account="ЭДС",
        date_text="24.04.2026",
        time_text="13:16",
        amount="3000.00",
        merchant_raw="Tinkoff Black",
        description="Перевод с карты Tinkoff Black на Яндекс Счёт",
    )

    normalized = dedupe_self_transfers([debit, farther_credit, closer_credit])

    assert normalized[0].transfer_pair_id == normalized[2].transfer_pair_id
    assert normalized[0].transfer_pair_id is not None
    assert normalized[1].is_transfer is True
    assert normalized[1].transfer_pair_id is None


def test_dedupe_self_transfers_matches_known_cross_bank_drift_within_thirty_minutes() -> None:
    debit = build_transaction(
        id="sber-6000-20250502-12:01-auth04",
        bank="sberbank",
        account="****6000",
        date_text="02.05.2025",
        time_text="12:01",
        amount="-1000.00",
        merchant_raw="Иван Иванович И.",
        description="Перевод для И. Иван Иванович. Операция по счету ****6000",
    )
    credit = build_transaction(
        id="ozon-0784-20250502-12:24-5857133103",
        bank="ozon",
        account="****0784",
        date_text="02.05.2025",
        time_text="12:24",
        amount="1000.00",
        merchant_raw="Иван Иванович И.",
        description=(
            "Перевод A5122092409326070000070011491301 через СБП. "
            "Отправитель: Иван Иванович И. Без НДС."
        ),
    )

    normalized = dedupe_self_transfers([debit, credit])

    assert normalized[0].is_transfer is True
    assert normalized[1].is_transfer is True
    assert normalized[0].transfer_pair_id is not None
    assert normalized[0].transfer_pair_id == normalized[1].transfer_pair_id


def test_dedupe_self_transfers_still_pairs_with_external_account_rows() -> None:
    debit = build_transaction(
        id="sber-6000-20260424-13:15-outgoing",
        bank="sberbank",
        account="****6000",
        date_text="24.04.2026",
        time_text="13:15",
        amount="-3000.00",
        merchant_raw="Иван Иванович И.",
        description="Перевод СБП Иван Иванович И.",
    )
    credit = build_transaction(
        id="sber-4000-20260424-13:16-incoming",
        bank="sberbank",
        account="****4000",
        date_text="24.04.2026",
        time_text="13:16",
        amount="3000.00",
        merchant_raw="Иван Иванович И.",
        description="Перевод от И. Иван Иванович. Операция по счету ****4000",
    ).model_copy(update={"is_external_account": True})

    normalized = dedupe_self_transfers([debit, credit])

    assert normalized[0].is_transfer is True
    assert normalized[1].is_transfer is True
    assert normalized[0].transfer_pair_id is not None
    assert normalized[0].transfer_pair_id == normalized[1].transfer_pair_id
    assert normalized[1].is_external_account is True


def test_dedupe_self_transfers_matches_date_only_rows_on_same_calendar_day() -> None:
    date_only_debit = build_transaction(
        id="sber-2000-20250321-473068710339-80",
        bank="sberbank",
        account="****2000",
        date_text="21.03.2025",
        time_text="00:00",
        precision="date",
        amount="-875.01",
        merchant_raw="Списание",
        description="Списание 03, № 473068710339-80 к/с 40817 810 1 5517 5566000",
    )
    timed_credit = build_transaction(
        id="yandex-6839-2025-03-21T19:44:00+03:00-deadbeefcafe",
        bank="yandex",
        account="****6839",
        date_text="21.03.2025",
        time_text="19:44",
        precision="minute",
        amount="875.01",
        merchant_raw="Перевод между счетами одного клиента",
        description="Перевод между счетами одного клиента",
    )

    normalized = dedupe_self_transfers([date_only_debit, timed_credit])

    assert normalized[0].is_transfer is True
    assert normalized[1].is_transfer is True
    assert normalized[0].transfer_pair_id == normalized[1].transfer_pair_id


def test_dedupe_self_transfers_prefers_date_precision_candidate_for_date_only_rows() -> None:
    date_only_debit = build_transaction(
        id="sber-2000-20250321-473068710339-80",
        bank="sberbank",
        account="****2000",
        date_text="21.03.2025",
        time_text="00:00",
        precision="date",
        amount="-875.01",
        merchant_raw="Списание",
        description="Списание 03, № 473068710339-80 к/с 40817 810 1 5517 5566000",
    )
    timed_credit = build_transaction(
        id="yandex-6839-2025-03-21T19:44:00+03:00-deadbeefcafe",
        bank="yandex",
        account="****6839",
        date_text="21.03.2025",
        time_text="19:44",
        precision="minute",
        amount="875.01",
        merchant_raw="Перевод между счетами одного клиента",
        description="Перевод между счетами одного клиента",
    )
    date_credit = build_transaction(
        id="ozon-1234-20250321-date-candidate",
        bank="ozon",
        account="****1234",
        date_text="21.03.2025",
        time_text="00:00",
        precision="date",
        amount="875.01",
        merchant_raw="Пополнение",
        description="Пополнение 02, № 1 к/с 30233 810 3 5500 0100000",
    )

    normalized = dedupe_self_transfers([date_only_debit, timed_credit, date_credit])

    assert normalized[0].transfer_pair_id == normalized[2].transfer_pair_id
    assert normalized[0].transfer_pair_id is not None
    assert normalized[1].is_transfer is False


def test_dedupe_self_transfers_warns_on_ambiguous_date_only_matches_then_single_side_tags(
    caplog: Any,
) -> None:
    date_only_debit = build_transaction(
        id="sber-2000-20250321-473068710339-80",
        bank="sberbank",
        account="****2000",
        date_text="21.03.2025",
        time_text="00:00",
        precision="date",
        amount="-875.01",
        merchant_raw="Списание",
        description="Списание 03, № 473068710339-80 к/с 40817 810 1 5517 5566000",
    )
    first_timed_credit = build_transaction(
        id="yandex-6839-2025-03-21T19:44:00+03:00-deadbeefcafe",
        bank="yandex",
        account="****6839",
        date_text="21.03.2025",
        time_text="19:44",
        precision="minute",
        amount="875.01",
        merchant_raw="Перевод между счетами одного клиента",
        description="Перевод между счетами одного клиента",
    )
    second_timed_credit = build_transaction(
        id="spb-4242-20250321-ambiguous",
        bank="spb",
        account="****4242",
        date_text="21.03.2025",
        time_text="18:40",
        precision="minute",
        amount="875.01",
        merchant_raw="Пополнение",
        description="Обычное пополнение без второй выписки",
    )

    with caplog.at_level(logging.WARNING, logger="lethal_expenses.normalize"):
        normalized = dedupe_self_transfers(
            [date_only_debit, first_timed_credit, second_timed_credit]
        )

    assert normalized[0].is_transfer is True
    assert normalized[0].transfer_pair_id is None
    assert normalized[1].is_transfer is False
    assert normalized[2].is_transfer is False
    assert any(
        "ambiguous date-only match for txid sber-2000-20250321-473068710339-80"
        in record.getMessage()
        for record in caplog.records
        if record.name == "lethal_expenses.normalize" and record.levelno >= logging.WARNING
    )


def test_description_suggests_transfer_covers_sber_transfer_shapes() -> None:
    cases = [
        "Списание 03, № 700002-2 к/с 40817 810 0 5519 0181000",
        "Пополнение 02, № 700004-4 к/с 40817 810 1 5517 5566000",
        "Зачисление 02, № 700001-5 к/с 30233 810 3 5500 0100000",
        "Капитализация вклада 08, № 700003-3 к/с 47411 810 7 5519 0181000",
        "Перевод между собственными счетами.",
        "Перенос денежных средств с ЭДС",
        'Получатель: ООО "ТЕХНОПАРК ЦЕНТР"',
        "Tinkoff Bank.",
        "через СБП. Возврат средств Перевод B61091209233410Q0B10110011740901 через СБП.",
        "Отмена перевода",
        "SBERBANK ONL@IN VKLAD-KARTA. Операция по счету ****6000",
        "SBERBANK ONL@IN KARTA-VKLAD. Операция по карте ****7000",
        "MAPP_SBERBANK_ONL@IN_PAY. Операция по карте ****7875",
    ]

    for description in cases:
        assert description_suggests_transfer(description) is True


def test_description_suggests_transfer_keeps_non_transfer_descriptions_false() -> None:
    assert description_suggests_transfer("Покупка в супермаркете Лента") is False
    assert description_suggests_transfer("ATM 60082626 SANKT-PETERBU RUS.") is False
    assert description_suggests_transfer("OZON. Покупка на маркетплейсе") is False
    assert description_suggests_transfer("Tinkoff Pro") is False


def test_description_suggests_single_sided_transfer_shapes() -> None:
    cases = [
        "Списание 03, № 700002-2 к/с 40817 810 0 5519 0181000",
        "Перевод собственных средств. Без НДС.",
        "Шум префикса Перевод собственных средств. Без НДС.",
        "SBERBANK ONL@IN VKLAD-KARTA. Операция по счету ****6000",
        "MAPP_SBERBANK_ONL@IN_PAY. Операция по карте ****7875",
    ]

    for description in cases:
        assert description_is_high_confidence_single_sided_transfer(description) is True


def test_dedupe_self_transfers_tags_single_sided_ozon_transfer_rows_without_counterpart() -> None:
    transaction = build_transaction(
        id="ozon-0950-20260421-19:44-orphan",
        bank="ozon",
        account="****0950",
        date_text="21.04.2026",
        time_text="19:44",
        amount="-7000.00",
        merchant_raw="Перевод собственных средств. Без НДС.",
        description="Перевод собственных средств. Без НДС.",
    )

    normalized = dedupe_self_transfers([transaction])

    assert normalized[0].is_transfer is True
    assert normalized[0].transfer_pair_id is None


def test_dedupe_self_transfers_keeps_ozon_own_transfer_rows_paired_when_counterpart_exists() -> (
    None
):
    debit = build_transaction(
        id="ozon-0950-20260421-19:44-orphan",
        bank="ozon",
        account="****0950",
        date_text="21.04.2026",
        time_text="19:44",
        amount="-7000.00",
        merchant_raw="Перевод собственных средств. Без НДС.",
        description="Перевод собственных средств. Без НДС.",
    )
    credit = build_transaction(
        id="ozon-0784-20260421-19:44-counterpart",
        bank="ozon",
        account="****0784",
        date_text="21.04.2026",
        time_text="19:44",
        amount="7000.00",
        merchant_raw="Перевод собственных средств",
        description="Перевод собственных средств",
    )

    normalized = dedupe_self_transfers([debit, credit])

    assert normalized[0].is_transfer is True
    assert normalized[1].is_transfer is True
    assert normalized[0].transfer_pair_id is not None
    assert normalized[0].transfer_pair_id == normalized[1].transfer_pair_id


def test_dedupe_self_transfers_does_not_tag_platform_ozon_rows_single_sided() -> None:
    transaction = build_transaction(
        id="ozon-0784-20260421-marketplace",
        bank="ozon",
        account="****0784",
        date_text="21.04.2026",
        time_text="19:44",
        amount="-7000.00",
        merchant_raw="Платформа Ozon",
        description="Платформа Ozon",
    )

    normalized = dedupe_self_transfers([transaction])

    assert normalized[0].is_transfer is False
    assert normalized[0].transfer_pair_id is None


def test_dedupe_self_transfers_tags_single_sided_sber_transfer_rows_without_counterpart() -> None:
    transaction = build_transaction(
        id="sber-2000-20250321-single-sided",
        bank="sberbank",
        account="****2000",
        date_text="21.03.2025",
        time_text="00:00",
        precision="date",
        amount="-875.01",
        merchant_raw="Списание",
        description="Списание 03, № 473068710339-80 к/с 40817 810 1 5517 5566000",
    )

    normalized = dedupe_self_transfers([transaction])

    assert normalized[0].is_transfer is True
    assert normalized[0].transfer_pair_id is None


def test_dedupe_self_transfers_does_not_tag_regular_purchase_rows_single_sided() -> None:
    transaction = build_transaction(
        id="sber-7875-20250321-purchase",
        bank="sberbank",
        account="****7875",
        date_text="21.03.2025",
        time_text="13:15",
        amount="-119.00",
        merchant_raw="Пятёрочка",
        description="Покупка в супермаркете Пятёрочка",
    )

    normalized = dedupe_self_transfers([transaction])

    assert normalized[0].is_transfer is False
    assert normalized[0].transfer_pair_id is None


def test_dedupe_self_transfers_keeps_zero_amount_capitalization_unmatched() -> None:
    transaction = build_transaction(
        id="sber-2000-20250314-zero-interest",
        bank="sberbank",
        account="****2000",
        date_text="14.03.2025",
        time_text="00:00",
        precision="date",
        amount="0.00",
        merchant_raw="Капитализация вклада",
        description="Капитализация вклада 08, № 473068710339-78 к/с 47411 810 1 5517 5892000",
    )

    normalized = dedupe_self_transfers([transaction])

    assert normalized[0].is_transfer is False
    assert normalized[0].transfer_pair_id is None


def test_dedupe_self_transfers_skips_different_amounts() -> None:
    debit = build_transaction(
        id="sber-7000-20260424-13:15-auth04",
        bank="sberbank",
        account="****7000",
        date_text="24.04.2026",
        time_text="13:15",
        amount="-3000.00",
        merchant_raw="Иван Иванович И.",
        description="Перевод СБП Иван Иванович И.",
    )
    credit = build_transaction(
        id="yandex-eds-2026-04-24T13:17:00+03:00-deadbeefcafe",
        bank="yandex",
        account="ЭДС",
        date_text="24.04.2026",
        time_text="13:17",
        amount="2999.99",
        merchant_raw="Tinkoff Black",
        description="Перевод с карты Tinkoff Black на Яндекс Счёт",
    )

    normalized = dedupe_self_transfers([debit, credit])

    assert all(transaction.is_transfer is False for transaction in normalized)
    assert all(transaction.transfer_pair_id is None for transaction in normalized)

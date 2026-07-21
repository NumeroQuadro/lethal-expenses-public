# pyright: reportPrivateUsage=false
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from lethal_expenses.categories import (
    DEFAULT_CATEGORY,
    SBER_LABEL_FALLBACK_MAP,
    _normalize_override_rules,
    apply_categories,
    build_categorization_text,
    categorize,
    load_override_rules,
)
from lethal_expenses.parsers.base import BaseParser
from lethal_expenses.schema import Transaction


def build_transaction(
    *,
    merchant_raw: str,
    description: str,
    category_label: object = None,
) -> Transaction:
    return Transaction(
        id=BaseParser.build_id(
            "sber",
            "****7000",
            BaseParser.parse_date_ru("25.12.2025", "22:40"),
            merchant_raw,
        ),
        date=BaseParser.parse_date_ru("25.12.2025", "22:40"),
        amount=Decimal("-123.45"),
        merchant_raw=merchant_raw,
        description=description,
        bank="sberbank",
        account="****7000",
        raw={} if category_label is None else {"category_label": category_label},
    )


def test_categorize_defaults_to_prochee() -> None:
    assert categorize("Редкий магазин", "Уникальная оплата", None) == DEFAULT_CATEGORY


def test_category_rules_cover_seed_inventory() -> None:
    cases = [
        ("ПЯТЁРОЧКА", "Покупка продуктов", None, "Еда"),
        ("DIXY-78018D SANKT-PETERBU RUS.", "Покупка продуктов", None, "Еда"),
        ("SPAR 904 SANKT-PETERBU RUS.", "Покупка продуктов", None, "Еда"),
        ("YANDEX GO", "Поездка домой", None, "Транспорт"),
        ("YM*URENT MOSCOW RUS.", "Аренда самоката", None, "Транспорт"),
        ("WHOOSH BIKE Gorod Moskva RUS.", "Поездка", None, "Транспорт"),
        ("Urent MOSKVA RUS.", "Аренда самоката", None, "Транспорт"),
        (
            "Оплата товаров и услуг",
            "Оплата товаров и услуг PASSAZHIRAVTOTRANS",
            None,
            "Транспорт",
        ),
        ("NETFLIX", "Ежемесячная подписка", None, "Подписки"),
        ("TIMEWEB.CLOUD SANKT-PETERBU RUS.", "Оплата облака", None, "Подписки"),
        ("YM*PLUS Gorod Moskva RUS.", "Ежемесячная подписка", None, "Подписки"),
        (
            'Северо Западный филиал ОАО "МегаФон" (МегаФон Северо-Запад)',
            "Оплата за телефон № 9213971428",
            None,
            "Подписки",
        ),
        ("DNS", "Покупка монитора", None, "Электроника"),
        ("plati.market.", "Покупка цифрового товара", None, "Электроника"),
        ("Y.M*CITILINK.RU MOSKVA RU", "Покупка монитора", None, "Электроника"),
        ("ТЕХНОПАРК", "Покупка техники", None, "Электроника"),
        ("Платформа Ozon", "Покупка на маркетплейсе", None, "Покупки"),
        ("YM*MARKET.YANDEX MOSCOW RUS.", "Покупка на маркетплейсе", None, "Покупки"),
        ("КОФЕ 1886", "Утренний кофе", None, "Кафе"),
        ("KFC VLADIMIRSKAYA Gorod Sankt-P RUS.", "Ужин", None, "Кафе"),
        ("BURGER KING 0574 Gorod Sankt-P RUS.", "Обед", None, "Кафе"),
        ("АПТЕКА", "Покупка лекарств", None, "Здоровье"),
        ("APTEKA 94 SANKT-PETERBU RUS.", "Покупка лекарств", None, "Здоровье"),
        ("Банк", "Перевод СБП Иван Иванович И.", None, "Переводы"),
        (
            "Перевод по СБП, . НДС не облагается.",
            "Перевод по СБП, . НДС не облагается.",
            None,
            "Переводы",
        ),
        (
            "И. Иван Иванович.",
            "И. Иван Иванович. Входящий перевод СБП, Сбербанк",
            None,
            "Переводы",
        ),
        (
            "SBERBANK ONL@IN VKLAD-KARTA. Операция по счету ****6000",
            "SBERBANK ONL@IN VKLAD-KARTA. Операция по счету ****6000",
            None,
            "Переводы",
        ),
        (
            "MAPP_SBERBANK_ONL@IN_PAY.",
            "MAPP_SBERBANK_ONL@IN_PAY. Операция по карте ****7000",
            None,
            "Переводы",
        ),
        (
            "Перевод между счетами одного клиента",
            "Перевод между счетами одного клиента",
            None,
            "Переводы",
        ),
        (
            "Перевод между собственными счетами.",
            "Перевод между собственными счетами.",
            None,
            "Переводы",
        ),
        (
            "Перенос денежных средств с ЭДС",
            "Перенос денежных средств с ЭДС",
            None,
            "Переводы",
        ),
        (
            'Получатель: ООО "ТЕХНОПАРК ЦЕНТР"',
            'Получатель: ООО "ТЕХНОПАРК ЦЕНТР" Отмена перевода',
            None,
            "Переводы",
        ),
        (
            "Возврат средств",
            "через СБП. Возврат средств Перевод B61091209233410Q0B10110011740901 через СБП.",
            None,
            "Переводы",
        ),
        (
            "Исходящий перевод по номеру",
            "Исходящий перевод по номеру карты (KORONAPAY.COM/ONLINE)",
            None,
            "Переводы",
        ),
        (
            "P2P_byPhone_tinkoff-bank.",
            "P2P_byPhone_tinkoff-bank. Операция по карте ****7000",
            None,
            "Переводы",
        ),
        ("ATM 60082626 SANKT-PETERBU RUS.", "Снятие наличных", None, "Снятие наличных"),
        ("METRO.SPB.RU St Petersburg RUS.", "Пополнение метро", None, "Транспорт"),
        ("TEREMOK R KRONVERSKIY Gorod Sankt-P RUS.", "Обед", None, "Кафе"),
        ("LEROY MERLIN MARKET Gorod Moskva RUS.", "Покупка для дома", None, "Покупки"),
        ("Alipay.", "Покупка зарубежом", None, "Покупки"),
        ("DOMRU_SPB Gorod Sankt-P RUS.", "Оплата интернета", None, "Коммунальные"),
        ("GAZPROM MEZHREGIONGAZ SPB RUS.", "Оплата газа", None, "Коммунальные"),
        ('АО "ЕИРЦ СПб".', "Коммунальный платеж", None, "Коммунальные"),
        ("Tinkoff Bank.", "Перевод в Тинькофф", None, "Переводы"),
        ("YM*GOSUSLUGI MOSCOW RUS.", "Госпошлина", None, "Госуслуги"),
        (
            "Списание",
            "Списание 03, № 700002-2 к/с 40817 810 0 5519 0181000",
            None,
            "Переводы",
        ),
        ("Капитализация вклада", "Капитализация вклада 08, № 700003-3", None, "Переводы"),
        (
            "Зачисление",
            "Зачисление 02, № 700001-5 к/с 30233 810 3 5500 0100000",
            None,
            "Переводы",
        ),
        (
            "Погашение основного долга по",
            "Погашение основного долга по договору",
            None,
            "Кредит",
        ),
        ("Сервисы Яндекса", "Сервисы Яндекса", None, "Прочее"),
        ("OPENAI", "OpenAI API usage", None, "Подписки"),
        ("OZON.", "Покупка на маркетплейсе", None, "Покупки"),
        ("YM*OZON Gorod Moskva RUS.", "Покупка на маркетплейсе", None, "Покупки"),
        ("ООО КИНОКАССА.", "Покупка билетов", None, "Развлечения"),
        (
            "пользу Steam, test_user. НДС не облагается",
            "Платеж в пользу Steam, test_user. НДС не облагается",
            None,
            "Развлечения",
        ),
    ]

    for merchant_raw, description, category_label, expected in cases:
        assert categorize(merchant_raw, description, category_label) == expected


@pytest.mark.parametrize(
    ("merchant_raw", "description", "category_label", "expected"),
    [
        ("SBOL.", "SBOL. Операция по карте ****7875", None, DEFAULT_CATEGORY),
        ("ATMOSFERA", "Редкая покупка", None, DEFAULT_CATEGORY),
        ("OZONBANK", "Перевод в банк", None, DEFAULT_CATEGORY),
        ("CITI DRIVE", "Аренда машины", None, DEFAULT_CATEGORY),
        ("METROPOLIS", "Редкая покупка", None, DEFAULT_CATEGORY),
        ("UNIVERSAL SEASON", "Редкая покупка", None, DEFAULT_CATEGORY),
        ("BULOCHNAYA 14", "Редкая покупка", None, DEFAULT_CATEGORY),
        ("TEREM", "Редкая покупка", None, DEFAULT_CATEGORY),
        ("ROYAL MERLIN", "Редкая покупка", None, DEFAULT_CATEGORY),
        ("Alior Bank", "Редкая покупка", None, DEFAULT_CATEGORY),
        ("DOMOVOY", "Редкая покупка", None, DEFAULT_CATEGORY),
        ("YM*GOSTINICA MOSCOW RUS.", "Редкая покупка", None, DEFAULT_CATEGORY),
        ("Tinkoff Pro", "Подписка", None, DEFAULT_CATEGORY),
    ],
)
def test_new_category_rules_do_not_overmatch_controls(
    merchant_raw: str,
    description: str,
    category_label: str | None,
    expected: str,
) -> None:
    assert categorize(merchant_raw, description, category_label) == expected


def test_categorize_uses_sber_category_label_fallback_for_empty_merchants() -> None:
    for label, expected in SBER_LABEL_FALLBACK_MAP.items():
        assert categorize("", "", label) == expected
        assert categorize("-", "", label) == expected


def test_categorize_uses_sber_category_label_fallback_for_nonempty_merchant() -> None:
    assert categorize("Редкий магазин", "Уникальная оплата", "Супермаркеты") == "Еда"


def test_categorize_uses_sber_category_label_fallback_for_sbol_merchants() -> None:
    assert categorize("SBOL.", "SBOL. Операция по карте ****7875", "Перевод с карты") == "Переводы"
    assert categorize("SBOL", "SBOL. Операция по карте ****7875", "Супермаркеты") == "Еда"


def test_categorize_keeps_description_match_stronger_than_sber_label_fallback() -> None:
    assert categorize("-", "Покупка в PYATEROCHKA", "Транспорт") == "Еда"
    assert categorize("DNS", "Покупка монитора", "Супермаркеты") == "Электроника"


def test_electronics_rules_win_over_general_shopping_and_sber_label_fallback() -> None:
    assert (
        categorize("Y.M*CITILINK.RU MOSKVA RU", "Покупка монитора", "Все для дома") == "Электроника"
    )
    assert (
        categorize("plati.market.", "Покупка цифрового товара", "Одежда и аксессуары")
        == "Электроника"
    )


def test_category_overrides_win_over_built_in_rules(tmp_path: Path) -> None:
    override_path = tmp_path / "categories_overrides.yaml"
    override_path.write_text(
        """
- pattern: MAGNIT
  category: Дом
""".strip()
        + "\n",
        encoding="utf-8",
    )

    assert categorize("MAGNIT", "Покупка продуктов", None, override_path=override_path) == "Дом"


def test_normalize_override_rules_supports_mapping_and_sequence_forms() -> None:
    mapping_rules = _normalize_override_rules({"SHOP": "Дом"})
    list_rules = _normalize_override_rules(
        [
            {"pattern": "CAFE", "category": "Кафе"},
            ["BOOK", "Покупки"],
            ("SUB", "Подписки"),
        ]
    )

    assert mapping_rules == [("SHOP", "Дом")]
    assert list_rules == [
        ("CAFE", "Кафе"),
        ("BOOK", "Покупки"),
        ("SUB", "Подписки"),
    ]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({1: "Дом"}, "string pattern/category pairs"),
        ([["only-one-item"]], "exactly two items"),
        ([{"pattern": object(), "category": "Дом"}], "string pattern/category values"),
        ([object()], "mappings with pattern/category or 2-item sequences"),
        (42, "must be a mapping or a list of rule entries"),
    ],
)
def test_normalize_override_rules_rejects_invalid_payloads(payload: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _normalize_override_rules(payload)


def test_load_override_rules_returns_empty_when_override_file_is_missing(tmp_path: Path) -> None:
    assert load_override_rules(override_path=tmp_path / "missing.yaml") == []


def test_build_categorization_text_uses_only_merchant_and_description() -> None:
    assert build_categorization_text("Merchant", "Description", "Ignored") == "Merchant Description"
    assert build_categorization_text("Merchant", "", None) == "Merchant"


def test_apply_categories_updates_transactions_without_mutating_inputs() -> None:
    original = build_transaction(merchant_raw="MAGNIT", description="Покупка")
    uncategorized = build_transaction(
        merchant_raw="Редкая покупка",
        description="Уникальное описание",
        category_label=123,
    )

    categorized = apply_categories([original, uncategorized])

    assert categorized[0].category == "Еда"
    assert categorized[1].category == DEFAULT_CATEGORY
    assert original.category == DEFAULT_CATEGORY
    assert uncategorized.category == DEFAULT_CATEGORY

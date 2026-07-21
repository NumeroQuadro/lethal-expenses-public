from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from importlib import import_module
from pathlib import Path
from typing import Any, cast

from lethal_expenses.schema import Transaction

type RawCategoryRule = tuple[str, str]
type CompiledCategoryRule = tuple[re.Pattern[str], str]

DEFAULT_CATEGORY = "Прочее"
PARSER_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OVERRIDE_PATH = PARSER_ROOT / "categories_overrides.yaml"
SBER_LABEL_FALLBACK_MAP: dict[str, str] = {
    "Супермаркеты": "Еда",
    "Рестораны и кафе": "Кафе",
    "Транспорт": "Транспорт",
    "Здоровье и красота": "Здоровье",
    "Коммунальные платежи, связь, интернет.": "Коммунальные",
    "Отдых и развлечения": "Развлечения",
    "Перевод СБП": "Переводы",
    "Перевод на карту": "Переводы",
    "Перевод с карты": "Переводы",
    "Прочие операции": "Прочее",
    "Прочие расходы": "Прочее",
    "Оплата по QR–коду СБП": "Переводы",
    "Все для дома": "Покупки",
    "все для дома": "Покупки",
    "Одежда и аксессуары": "Покупки",
    "Выдача наличных": "Снятие наличных",
    "Образование": "Образование",
}
CATEGORY_RULES: list[RawCategoryRule] = [
    (
        r"PYATEROCHKA|MAGNIT|LENTA|VKUSVILL|PEREKRESTOK|DIXY|SPAR\b|31YY\s*Пятерочка|"
        r"АШАН|ВКУСВИЛЛ|ПЯТЁРОЧКА|KRASNOE\s*&?\s*BELOE",
        "Еда",
    ),
    (
        r"YANDEX[\.\s]GO|YM\*URENT|URENT|WHOOSH|Go_Scooter|SCOOTERS|UBER|TAXI|"
        r"GOREH?LEKTROTRANS|PASSAZHIRAVTOTRANS|TRANSPORT\s+PITER|DOMTRANSAVTO|"
        r"AVTOBUSNYJ\s+PARK|АВТОБУСНЫЙ|VEST-SERVIS|bilet\.nspk|METRO\s+TPP|"
        r"METRO[\s_]|METRO\.SPB\.RU|МЕТРО ",
        "Транспорт",
    ),
    (
        r"Погашение\s+основного\s+долга|Погашение\s+процентов",
        "Кредит",
    ),
    (
        r"BOOSTY|YANDEX[\.\s]PLUS|YM\*PLUS|NETFLIX|SPOTIFY|SBSCR_|APPLE\.COM/BILL|"
        r"GOOGLE\s*\*|TIMEWEB|CLOUD|JETBRAINS|GITHUB|OPENAI|ANTHROPIC|MEGAFON|"
        r"МегаФон",
        "Подписки",
    ),
    (
        r"DOMRU(?:_SPB|_)|DOM\.RU|GAZPROM\s+MEZHREGIONGAZ|PES\s+Gorod\s+Sankt-P|"
        r'АО\s+"ЕИРЦ|АО\s+"ВЦКП|KVARTPLATA\.INFO_QR|ТГК1|TGK1|ЭР-ТЕЛЕКОМ',
        "Коммунальные",
    ),
    (r"^ATM\s+\d+", "Снятие наличных"),
    (
        r"Перевод\s+между\s+собственными\s+счетами|Перенос\s+денежных\s+средств\s+с\s+ЭДС|"
        r"^Получатель:\s|Возврат\s+средств|через\s+СБП|Отмена\s+перевода|Tinkoff\s+Bank|"
        r"P2P_byPhone_tinkoff-bank|Перевод\s+клиенту\s+Банка",
        "Переводы",
    ),
    (
        r"BIGGEEK|DNS\b|MVIDEO|Сайт\s+М\.Видео|Y\.M\*CITILINK\.RU|CITILINK|"
        r"ТЕХНОПАРК|plati\.market|www\.digiseller\.ru|digiseller",
        "Электроника",
    ),
    (
        r"WILDBERRIES|OZON\.RU|Платформа\s+Ozon|YANDEX[\.\s]MARKET|YM\*MARKET\.YANDEX|"
        r"YM\*OZON|Gold\s+Apple|AVITO|ALIEXPRESS|^OZON\.|LEROY\s+MERLIN|Alipay|"
        r"SPORTMASTER",
        "Покупки",
    ),
    (
        r"STEAM|КИНОКАССА|КИНО",
        "Развлечения",
    ),
    (
        r"KAFE|RESTAURANT|РЕСТОРАН|КАФЕ|БАР\b|PUB\b|YANDEX[\.\s]EATS|"
        r"DELIVERY|STARBUCKS|COFFEE|TEREMOK|КОФЕ|KFC|BURGER\s+KING",
        "Кафе",
    ),
    (
        r"АПТЕКА|APTEKA|PHARMACY|ZDOROVYE|ОЗДОРОВ|36,?6|ЗДРАВ",
        "Здоровье",
    ),
    (r"YM\*GOSUSLUGI|GOSUSLUGI", "Госуслуги"),
    (
        r"^(?:[А-Я]\.\s*[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:ович|евич|овна|евна)\.?|"
        r"[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:ович|евич|овна|евна)\s+[А-Я]\.?)"
        r"(?:$|\s)",
        "Переводы",
    ),
    (
        r"Перевод СБП|Перевод по СБП|Перевод на карту|Перевод с карты|"
        r"Исходящий перевод по номеру|Перевод собственных|Перевод между счетами|"
        r"Перевод денежных|Капитализация\s+вклада|"
        r"SBERBANK\s+ONL@IN\s+(?:KARTA-VKLAD|VKLAD-KARTA)|MAPP_SBERBANK|"
        r"(?:Списание|Пополнение|Зачисление).+к/с",
        "Переводы",
    ),
    (r"Сервисы\s+Яндекса", "Прочее"),
]


def _compile_rules(rules: Sequence[RawCategoryRule]) -> tuple[CompiledCategoryRule, ...]:
    return tuple((re.compile(pattern, re.IGNORECASE), category) for pattern, category in rules)


def _load_yaml_payload(path: Path) -> object:
    yaml_module = cast(Any, import_module("yaml"))
    with path.open("r", encoding="utf-8") as handle:
        return cast(object, yaml_module.safe_load(handle))


def _normalize_override_rules(payload: object) -> list[RawCategoryRule]:
    if payload is None:
        return []

    if isinstance(payload, dict):
        mapping_payload = cast(Mapping[object, object], payload)
        rules: list[RawCategoryRule] = []
        for pattern, category in mapping_payload.items():
            if not isinstance(pattern, str) or not isinstance(category, str):
                raise ValueError(
                    "Category override mappings must use string pattern/category pairs"
                )
            rules.append((pattern, category))
        return rules

    if isinstance(payload, list):
        sequence_payload = cast(list[object], payload)
        rules = []
        for entry in sequence_payload:
            pattern: object
            category: object

            if isinstance(entry, dict):
                entry_mapping = cast(Mapping[object, object], entry)
                pattern = entry_mapping.get("pattern")
                category = entry_mapping.get("category")
            elif isinstance(entry, (list, tuple)):
                sequence_entry = cast(Sequence[object], entry)
                if len(sequence_entry) != 2:
                    raise ValueError(
                        "Category override sequence entries must contain exactly two items"
                    )
                pattern = sequence_entry[0]
                category = sequence_entry[1]
            else:
                raise ValueError(
                    "Category override entries must be mappings with pattern/category "
                    "or 2-item sequences"
                )

            if not isinstance(pattern, str) or not isinstance(category, str):
                raise ValueError(
                    "Category override entries must contain string pattern/category values"
                )
            rules.append((pattern, category))
        return rules

    raise ValueError("Category overrides must be a mapping or a list of rule entries")


def load_override_rules(*, override_path: Path | None = None) -> list[RawCategoryRule]:
    path = DEFAULT_OVERRIDE_PATH if override_path is None else override_path
    if not path.exists():
        return []
    return _normalize_override_rules(_load_yaml_payload(path))


def get_effective_rules(*, override_path: Path | None = None) -> tuple[CompiledCategoryRule, ...]:
    override_rules = load_override_rules(override_path=override_path)
    return _compile_rules([*override_rules, *CATEGORY_RULES])


def build_categorization_text(
    merchant_raw: str,
    description: str,
    category_label: str | None,
) -> str:
    _ = category_label
    # Built-in matching intentionally stays on merchant_raw + description per C-006.
    return " ".join(part for part in (merchant_raw, description) if part).strip()


def categorize_with_rules(
    merchant_raw: str,
    description: str,
    category_label: str | None,
    *,
    compiled_rules: Sequence[CompiledCategoryRule],
) -> str:
    haystack = build_categorization_text(merchant_raw, description, category_label)
    for pattern, category in compiled_rules:
        if pattern.search(haystack) is not None:
            return category

    if category_label in SBER_LABEL_FALLBACK_MAP:
        return SBER_LABEL_FALLBACK_MAP[category_label]

    return DEFAULT_CATEGORY


def categorize(
    merchant_raw: str,
    description: str,
    category_label: str | None,
    *,
    override_path: Path | None = None,
) -> str:
    return categorize_with_rules(
        merchant_raw,
        description,
        category_label,
        compiled_rules=get_effective_rules(override_path=override_path),
    )


def apply_categories(
    transactions: Sequence[Transaction],
    *,
    override_path: Path | None = None,
) -> list[Transaction]:
    compiled_rules = get_effective_rules(override_path=override_path)
    categorized: list[Transaction] = []

    for transaction in transactions:
        category_label_value = transaction.raw.get("category_label")
        category_label = category_label_value if isinstance(category_label_value, str) else None
        category = categorize_with_rules(
            transaction.merchant_raw,
            transaction.description,
            category_label,
            compiled_rules=compiled_rules,
        )
        categorized.append(transaction.model_copy(update={"category": category}, deep=True))

    return categorized
